from pydantic import BaseModel
from typing import List


class HistoryItem(BaseModel):
    id: str
    doc_type: str
    summary_preview: str
    urgency_flag: bool
    language: str
    created_at: str


class HistoryListResponse(BaseModel):
    items: List[HistoryItem]
    total: int


class SaveToHistoryRequest(BaseModel):
    document_id: str
    user_id: str
