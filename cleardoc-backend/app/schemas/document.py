from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DocumentExplainRequest(BaseModel):
    text: str = Field(default="", description="Plain text of the document")
    language: str = Field(default="en", description="Response language code")
    user_id: str = Field(..., description="UUID from localStorage")


class DocumentExplainResponse(BaseModel):
    document_id: str
    summary: str
    key_points: List[str]
    next_steps: List[str]
    urgency_flag: bool
    urgency_message: Optional[str] = None
    doc_type: str
    language: str
    created_at: str


class FollowupRequest(BaseModel):
    document_id: str
    question: str
    language: str = "en"


class FollowupResponse(BaseModel):
    answer: str
