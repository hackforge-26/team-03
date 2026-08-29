from pydantic import BaseModel, EmailStr
from typing import Optional


class ReminderRequest(BaseModel):
    user_id: str
    document_id: str
    email: EmailStr
    deadline_text: str
    remind_before: str = "3_days"


class ReminderResponse(BaseModel):
    success: bool
    message: str
    reminder_id: Optional[str] = None
