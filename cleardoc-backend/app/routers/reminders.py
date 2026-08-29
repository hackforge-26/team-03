from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.reminder import Reminder
from app.models.user import User
from app.services.reminder_service import send_confirmation_email
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/reminders", tags=["reminders"])

REMIND_DAYS_MAP = {
    "1_day": 1,
    "3_days": 3,
    "1_week": 7,
}


class ReminderRequest(BaseModel):
    user_id: str
    document_id: str
    email: EmailStr
    deadline_text: str
    remind_before: str  # "1_day" | "3_days" | "1_week"


@router.post("")
async def set_reminder(
    request: ReminderRequest,
    db: AsyncSession = Depends(get_db),
):
    remind_days = REMIND_DAYS_MAP.get(request.remind_before, 3)

    # Find user
    user_result = await db.execute(
        select(User).where(User.device_id == request.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reminder = Reminder(
        user_id=user.id,
        document_id=request.document_id,
        email=request.email,
        deadline_text=request.deadline_text,
        remind_before_days=remind_days,
        is_sent=False,
    )
    db.add(reminder)
    await db.commit()

    # Send confirmation email
    await send_confirmation_email(request.email, request.deadline_text)

    return {"success": True, "message": "Reminder set successfully"}
