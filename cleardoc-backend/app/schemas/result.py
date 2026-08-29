from pydantic import BaseModel
from typing import Optional, List


class ComparisonFlag(BaseModel):
    clause: str
    severity: str
    message: str


class ResultResponse(BaseModel):
    document_id: str
    summary: str
    key_points: List[str]
    next_steps: List[str]
    urgency_flag: bool
    urgency_message: Optional[str] = None
    doc_type: str
    language: str
    created_at: str


class CompareResponse(BaseModel):
    flags: List[ComparisonFlag]
    all_clear: bool
