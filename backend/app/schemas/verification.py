import uuid
from datetime import datetime

from pydantic import BaseModel


class CheckItem(BaseModel):
    id: str
    name: str
    category: str
    source: str = ""
    required: bool
    status: str  # pass / fail / warning / not_applicable
    details: str = ""
    found_text: str | None = None


class SpellingError(BaseModel):
    word: str
    suggestion: str
    context: str = ""


class TherapeuticClaim(BaseModel):
    text: str
    reason: str


class Pictograms(BaseModel):
    eac: bool = False
    mobius_loop: bool = False
    barcode: bool = False
    datamatrix: bool = False
    glass_fork: bool = False
    other: list[str] = []


class VerificationReportResponse(BaseModel):
    id: str
    sgr_record_id: str | None = None
    overall_status: str
    score: int
    checks: list[CheckItem]
    spelling_errors: list[SpellingError] = []
    therapeutic_claims: list[TherapeuticClaim] = []
    pictograms: Pictograms | None = None
    extracted_label_text: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[VerificationReportResponse]
    total: int
