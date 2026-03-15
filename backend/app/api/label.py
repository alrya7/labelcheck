import json
import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.sgr import SgrRecord
from app.models.verification import VerificationReport
from app.schemas.verification import VerificationReportResponse
from app.services.label_checker import check_label, pdf_to_pngs, _merge_checks
from app.services.rules import compute_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/label", tags=["Label Check"])

# Cyrillic → Latin map for SGR number normalization
_CYR_TO_LAT = {"А": "A", "В": "B", "С": "C", "Е": "E", "К": "K", "М": "M", "О": "O", "Р": "R", "Т": "T"}


def _normalize_sgr(num: str) -> str:
    """Normalize SGR number: replace Cyrillic look-alikes with Latin."""
    return "".join(_CYR_TO_LAT.get(ch, ch) for ch in num)


def _sgr_to_dict(record: SgrRecord) -> dict:
    """Convert SgrRecord to dict matching EAEU registry format for _check_registry."""
    return {
        "data": {
            "NUMB_DOC": record.numb_doc,
            "DATE_DOC": str(record.date_doc) if record.date_doc else None,
            "STATUS": {"name": record.status or ""},
            "NAME_PROD": record.name_prod,
            "FIRMGET_NAME": record.firmget_name,
            "FIRMGET_ADDR": record.firmget_addr,
            "FIRMMADE_NAME": record.firmmade_name,
            "DOC_NORM": record.doc_norm,
        }
    }


@router.post("/check", response_model=VerificationReportResponse)
async def check_label_endpoint(
    file: UploadFile = File(...),
    sgr_record_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a label image/PDF and get a verification report."""
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "label"

    # Save file
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = uuid.uuid4().hex[:12]
    ext = os.path.splitext(filename)[1] or ".pdf"
    saved_path = os.path.join(settings.upload_dir, f"label_{file_id}{ext}")
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # Generate PNG preview for storage in DB
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")
    preview_bytes: bytes | None = None
    preview_mime = content_type
    if is_pdf:
        try:
            png_pages = pdf_to_pngs(file_bytes)
            if png_pages:
                preview_bytes = png_pages[0]
                preview_mime = "image/png"
                logger.info("Generated PNG preview from PDF (%d bytes)", len(preview_bytes))
        except Exception as e:
            logger.warning("Failed to create PNG preview: %s", e)
    else:
        # For image uploads, store the original bytes
        preview_bytes = file_bytes
        preview_mime = content_type

    # Load SGR data if provided, or auto-detect later
    sgr_data = None
    sgr_record = None
    if sgr_record_id:
        db_result = await db.execute(select(SgrRecord).where(SgrRecord.id == sgr_record_id))
        sgr_record = db_result.scalar_one_or_none()
        if sgr_record:
            # Combine extracted AI data + registry data for cross-reference
            sgr_data = sgr_record.raw_extracted_data or {}
            if sgr_record.eaeu_registry_data:
                sgr_data["_registry"] = sgr_record.eaeu_registry_data

    # Run label check (first pass — without SGR cross-reference)
    result = await check_label(file_bytes, filename, content_type, sgr_data)

    # Try to find SGR in local DB by number extracted from label
    sgr_record_data = None
    if not sgr_record_id and result.get("sgr_number"):
        sgr_num = result["sgr_number"]
        # Try exact match, then normalized (cyrillic -> latin)
        for num in [sgr_num, _normalize_sgr(sgr_num)]:
            db_result = await db.execute(
                select(SgrRecord).where(SgrRecord.numb_doc == num)
            )
            found = db_result.scalar_one_or_none()
            if found:
                sgr_record_id = found.id
                sgr_record_data = _sgr_to_dict(found)
                break
        # Fallback: fuzzy search by product name
        if not sgr_record_data and result.get("product_name"):
            db_result = await db.execute(
                select(SgrRecord).where(
                    SgrRecord.name_prod.ilike(f"%{result['product_name']}%")
                )
            )
            found = db_result.scalar_one_or_none()
            if found:
                sgr_record_id = found.id
                sgr_record_data = _sgr_to_dict(found)
    elif sgr_record and not sgr_record_data:
        sgr_record_data = _sgr_to_dict(sgr_record)

    # Re-merge checks with SGR data (no second AI call needed)
    if sgr_record_data:
        ai_result = json.loads(result.get("ai_analysis", "{}") or "{}")
        ai_checks = ai_result.get("checks", [])
        checks = _merge_checks(ai_checks, sgr_record_data, ai_result)

        # Re-apply SGR number pass if found
        sgr_number = result.get("sgr_number")
        if sgr_number:
            for check in checks:
                if check["id"] == "sgr_number":
                    check["status"] = "pass"
                    check["details"] = f"Номер СГР найден на этикетке: {sgr_number}"
                    check["found_text"] = sgr_number
                    break

        # Re-apply not_applicable logic for conditional checks
        CONDITIONAL_CHECK_IDS = {"importer", "nutritional_value", "allergens", "gmo_info"}
        for check in checks:
            if not check["required"] and check["status"] in ("warning", "fail") and check["id"] in CONDITIONAL_CHECK_IDS:
                check["status"] = "not_applicable"
                if check["id"] == "importer":
                    check["details"] = "Не применимо (продукция не импортная или импортёр = изготовитель)"
                elif check["id"] == "nutritional_value":
                    check["details"] = "Не применимо (БАД в капсулах/таблетках с незначительной энерг. ценностью)"
                elif check["id"] == "allergens":
                    check["details"] = "Не применимо (типичные аллергены не обнаружены в составе)"
                elif check["id"] == "gmo_info":
                    check["details"] = "Не применимо (БАД не содержит ГМО)"

        score, overall_status = compute_score(checks)
        result["checks"] = checks
        result["score"] = score
        result["overall_status"] = overall_status
        logger.info("Re-merged checks with SGR data from local DB")

    # Auto-name from product name detected by AI
    product_name = result.get("product_name") or filename

    # Save report with image data in DB (persists across deploys)
    report = VerificationReport(
        name=product_name,
        sgr_record_id=sgr_record_id,
        label_file_path=saved_path,
        label_file_data=preview_bytes,
        label_file_mime=preview_mime,
        overall_status=result["overall_status"],
        score=result["score"],
        checks=result["checks"],
        ai_analysis=result["ai_analysis"],
        extracted_label_text=result["extracted_label_text"],
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Image URL now points to the DB-backed endpoint
    label_url = f"/api/v1/reports/{report.id}/image"

    return VerificationReportResponse(
        id=report.id,
        name=report.name,
        sgr_record_id=report.sgr_record_id,
        overall_status=report.overall_status,
        score=report.score,
        checks=result["checks"],
        spelling_errors=result.get("spelling_errors", []),
        therapeutic_claims=result.get("therapeutic_claims", []),
        pictograms=result.get("pictograms"),
        extracted_label_text=report.extracted_label_text or "",
        label_file_url=label_url,
        created_at=report.created_at,
    )
