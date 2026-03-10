import uuid

from pydantic import BaseModel

from app.schemas.verification import VerificationReportResponse


class LabelCheckRequest(BaseModel):
    sgr_record_id: uuid.UUID | None = None


class LabelCheckResponse(BaseModel):
    report: VerificationReportResponse
    message: str
