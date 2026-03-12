import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sgr_record_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sgr_records.id"), nullable=True
    )
    label_file_path: Mapped[str | None] = mapped_column(Text)
    label_file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    label_file_mime: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Results
    overall_status: Mapped[str | None] = mapped_column(String(20))  # pass / fail / warning
    score: Mapped[int | None] = mapped_column(Integer)  # 0-100
    checks: Mapped[dict | None] = mapped_column(JSON)
    ai_analysis: Mapped[str | None] = mapped_column(Text)
    extracted_label_text: Mapped[str | None] = mapped_column(Text)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
