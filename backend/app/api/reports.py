import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.verification import VerificationReport
from app.schemas.verification import ReportListResponse, VerificationReportResponse

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
        .order_by(VerificationReport.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    reports = result.scalars().all()

    count_result = await db.execute(select(VerificationReport))
    total = len(count_result.scalars().all())

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


def _label_file_url(report: VerificationReport) -> str | None:
    """Build a URL to the label file relative to /uploads/."""
    if not report.label_file_path:
        return None
    upload_dir = os.path.abspath(settings.upload_dir)
    abs_path = os.path.abspath(report.label_file_path)
    if abs_path.startswith(upload_dir):
        rel = os.path.relpath(abs_path, upload_dir)
        return f"/uploads/{rel}"
    # Fallback: use just the filename
    return f"/uploads/{os.path.basename(report.label_file_path)}"


def _to_response(report: VerificationReport) -> VerificationReportResponse:
    checks = report.checks or []
    return VerificationReportResponse(
        id=report.id,
        sgr_record_id=report.sgr_record_id,
        overall_status=report.overall_status or "unknown",
        score=report.score or 0,
        checks=checks,
        extracted_label_text=report.extracted_label_text or "",
        label_file_url=_label_file_url(report),
        created_at=report.created_at,
    )
