import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SgrRecord(Base):
    __tablename__ = "sgr_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Core fields from EAEU registry
    numb_doc: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    date_doc: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(50))
    status_date: Mapped[datetime | None] = mapped_column(DateTime)
    name_prod: Mapped[str | None] = mapped_column(Text)
    prod_app: Mapped[str | None] = mapped_column(Text)
    okp_prod: Mapped[str | None] = mapped_column(String(100))

    # Applicant
    firmget_name: Mapped[str | None] = mapped_column(Text)
    firmget_addr: Mapped[str | None] = mapped_column(Text)
    firmget_inn: Mapped[str | None] = mapped_column(String(50))
    firmget_country: Mapped[str | None] = mapped_column(String(100))

    # Manufacturer
    firmmade_name: Mapped[str | None] = mapped_column(Text)
    firmmade_addr: Mapped[str | None] = mapped_column(Text)
    firmmade_country: Mapped[str | None] = mapped_column(String(100))

    # Documents
    doc_norm: Mapped[str | None] = mapped_column(Text)
    doc_usearea: Mapped[str | None] = mapped_column(Text)
    doc_protocol: Mapped[str | None] = mapped_column(Text)
    doc_condition: Mapped[str | None] = mapped_column(Text)
    doc_label: Mapped[str | None] = mapped_column(Text)
    doc_gighark: Mapped[dict | None] = mapped_column(JSON)

    # Technical
    who: Mapped[str | None] = mapped_column(String(200))
    serialnumb: Mapped[str | None] = mapped_column(String(50))
    blankver: Mapped[str | None] = mapped_column(String(10))
    n_alfa_name: Mapped[str | None] = mapped_column(String(50))

    # Metadata
    source_file_path: Mapped[str | None] = mapped_column(Text)
    raw_extracted_data: Mapped[dict | None] = mapped_column(JSON)
    eaeu_registry_data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
