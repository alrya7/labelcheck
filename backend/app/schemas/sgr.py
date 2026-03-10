import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SgrRecordBase(BaseModel):
    numb_doc: str
    date_doc: date | None = None
    status: str | None = None
    status_date: datetime | None = None
    name_prod: str | None = None
    prod_app: str | None = None
    okp_prod: str | None = None
    firmget_name: str | None = None
    firmget_addr: str | None = None
    firmget_inn: str | None = None
    firmget_country: str | None = None
    firmmade_name: str | None = None
    firmmade_addr: str | None = None
    firmmade_country: str | None = None
    doc_norm: str | None = None
    doc_usearea: str | None = None
    doc_protocol: str | None = None
    doc_condition: str | None = None
    doc_label: str | None = None
    doc_gighark: dict | list | None = None
    who: str | None = None
    serialnumb: str | None = None
    n_alfa_name: str | None = None


class SgrRecordResponse(SgrRecordBase):
    id: str
    created_at: datetime
    updated_at: datetime
    eaeu_registry_data: dict | None = None
    raw_extracted_data: dict | None = None

    model_config = {"from_attributes": True}


class SgrUploadResponse(BaseModel):
    sgr: SgrRecordResponse
    registry_discrepancies: list[dict] = []
    message: str


class SgrListResponse(BaseModel):
    items: list[SgrRecordResponse]
    total: int
