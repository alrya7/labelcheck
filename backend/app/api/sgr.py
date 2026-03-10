import os
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.sgr import SgrRecord
from app.schemas.sgr import SgrListResponse, SgrRecordResponse, SgrUploadResponse
from app.services.sgr_parser import parse_sgr_document

router = APIRouter(prefix="/sgr", tags=["SGR"])


@router.post("/upload", response_model=SgrUploadResponse)
async def upload_sgr(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an SGR document, parse it, and save to database."""
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "document"

    # Save file to disk
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = uuid.uuid4().hex[:12]
    ext = os.path.splitext(filename)[1] or ".pdf"
    saved_path = os.path.join(settings.upload_dir, f"sgr_{file_id}{ext}")
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # Parse document
    result = await parse_sgr_document(file_bytes, filename, content_type)
    extracted = result["extracted"]

    numb_doc = extracted.get("numb_doc", "")
    if not numb_doc:
        raise HTTPException(status_code=422, detail="Не удалось извлечь номер СГР из документа")

    # Verify that SGR was found in the registry
    registry_data = result.get("registry_data")
    if not registry_data:
        raise HTTPException(
            status_code=422,
            detail=f"СГР {numb_doc} не найден в реестре ЕАЭС. Проверьте корректность документа.",
        )

    # Check if already exists in DB
    existing = await db.execute(
        select(SgrRecord).where(SgrRecord.numb_doc == numb_doc)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"СГР {numb_doc} уже существует в базе")

    # Parse date fields
    def parse_date(val):
        if not val:
            return None
        if isinstance(val, date):
            return val
        try:
            return date.fromisoformat(str(val)[:10])
        except (ValueError, TypeError):
            return None

    # Create record from merged data (registry = ground truth, AI = supplement)
    record = SgrRecord(
        numb_doc=numb_doc,
        date_doc=parse_date(extracted.get("date_doc")),
        status=extracted.get("status"),
        name_prod=extracted.get("name_prod"),
        okp_prod=extracted.get("okp_prod"),
        firmget_name=extracted.get("firmget_name"),
        firmget_addr=extracted.get("firmget_addr"),
        firmmade_name=extracted.get("firmmade_name"),
        firmmade_addr=extracted.get("firmmade_addr"),
        doc_norm=extracted.get("doc_norm"),
        doc_usearea=extracted.get("doc_usearea"),
        doc_protocol=extracted.get("doc_protocol"),
        doc_condition=extracted.get("doc_condition"),
        doc_label=extracted.get("doc_label"),
        doc_gighark=extracted.get("doc_gighark"),
        who=extracted.get("who"),
        serialnumb=extracted.get("serialnumb"),
        n_alfa_name=extracted.get("n_alfa_name"),
        source_file_path=saved_path,
        raw_extracted_data=result.get("ai_raw"),
        eaeu_registry_data=result.get("registry_data"),
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    return SgrUploadResponse(
        sgr=SgrRecordResponse.model_validate(record),
        registry_discrepancies=result.get("registry_discrepancies", []),
        message=f"СГР {numb_doc} успешно загружен и обработан",
    )


@router.get("", response_model=SgrListResponse)
async def list_sgr(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all SGR records."""
    result = await db.execute(
        select(SgrRecord).order_by(SgrRecord.created_at.desc()).offset(offset).limit(limit)
    )
    records = result.scalars().all()

    count_result = await db.execute(select(SgrRecord))
    total = len(count_result.scalars().all())

    return SgrListResponse(
        items=[SgrRecordResponse.model_validate(r) for r in records],
        total=total,
    )


@router.get("/{sgr_id}", response_model=SgrRecordResponse)
async def get_sgr(sgr_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific SGR record."""
    result = await db.execute(select(SgrRecord).where(SgrRecord.id == sgr_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="СГР не найден")
    return SgrRecordResponse.model_validate(record)
