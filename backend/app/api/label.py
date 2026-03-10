import json
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
from app.services.label_checker import check_label

router = APIRouter(prefix="/label", tags=["Label Check"])


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

    # Run label check
    result = await check_label(file_bytes, filename, content_type, sgr_data)

    # If no SGR was provided, try to find one by the SGR number on the label
    if not sgr_record_id and result.get("sgr_number"):
        sgr_num = result["sgr_number"]
        db_result = await db.execute(
            select(SgrRecord).where(SgrRecord.numb_doc == sgr_num)
        )
        found = db_result.scalar_one_or_none()
        if found:
            sgr_record_id = found.id

    # Save report
    report = VerificationReport(
        sgr_record_id=sgr_record_id,
        label_file_path=saved_path,
        overall_status=result["overall_status"],
        score=result["score"],
        checks=result["checks"],
        ai_analysis=result["ai_analysis"],
        extracted_label_text=result["extracted_label_text"],
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return VerificationReportResponse(
        id=report.id,
        sgr_record_id=report.sgr_record_id,
        overall_status=report.overall_status,
        score=report.score,
        checks=result["checks"],
        spelling_errors=result.get("spelling_errors", []),
        therapeutic_claims=result.get("therapeutic_claims", []),
        pictograms=result.get("pictograms"),
        extracted_label_text=report.extracted_label_text or "",
        created_at=report.created_at,
    )
