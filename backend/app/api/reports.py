import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.config import settings
from app.database import get_db
from app.models.verification import VerificationReport
from app.schemas.verification import ReportListResponse, ReportNameUpdate, VerificationReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=ReportListResponse)
async def list_reports(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all verification reports."""
    result = await db.execute(
        select(VerificationReport)
        .options(defer(VerificationReport.label_file_data))
        .order_by(VerificationReport.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    reports = result.scalars().all()

    count_result = await db.execute(select(func.count(VerificationReport.id)))
    total = count_result.scalar() or 0

    return ReportListResponse(
        items=[_to_response(r) for r in reports],
        total=total,
    )


@router.get("/{report_id}", response_model=VerificationReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific verification report."""
    result = await db.execute(
        select(VerificationReport).where(VerificationReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    return _to_response(report)


@router.get("/{report_id}/image")
async def get_report_image(report_id: str, db: AsyncSession = Depends(get_db)):
    """Serve the label image stored in the database."""
    result = await db.execute(
        select(VerificationReport).where(VerificationReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report or not report.label_file_data:
        raise HTTPException(status_code=404, detail="Изображение не найдено")
    mime = report.label_file_mime or "image/png"
    return Response(
        content=report.label_file_data,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.patch("/{report_id}/name")
async def update_report_name(report_id: str, body: ReportNameUpdate, db: AsyncSession = Depends(get_db)):
    """Update the report name."""
    result = await db.execute(
        select(VerificationReport).where(VerificationReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    report.name = body.name
    await db.commit()
    return {"detail": "Название обновлено"}


@router.delete("/{report_id}")
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a verification report."""
    result = await db.execute(
        select(VerificationReport).where(VerificationReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    await db.delete(report)
    await db.commit()
    return {"detail": "Отчёт удалён"}


def _to_response(report: VerificationReport) -> VerificationReportResponse:
    checks = report.checks or []
    # Use DB-backed image endpoint if image data is stored, otherwise fallback to file path
    label_url = None
    if report.label_file_mime:
        label_url = f"/api/v1/reports/{report.id}/image"
    elif report.label_file_path:
        upload_dir = os.path.abspath(settings.upload_dir)
        abs_path = os.path.abspath(report.label_file_path)
        if abs_path.startswith(upload_dir):
            label_url = f"/uploads/{os.path.relpath(abs_path, upload_dir)}"
        else:
            label_url = f"/uploads/{os.path.basename(report.label_file_path)}"
    return VerificationReportResponse(
        id=report.id,
        name=report.name,
        sgr_record_id=report.sgr_record_id,
        overall_status=report.overall_status or "unknown",
        score=report.score or 0,
        checks=checks,
        extracted_label_text=report.extracted_label_text or "",
        label_file_url=label_url,
        created_at=report.created_at,
    )
