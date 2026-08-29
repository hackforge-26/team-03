import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.reminder import Reminder
from app.config import settings
import structlog

logger = structlog.get_logger()


async def send_confirmation_email(email: str, deadline_text: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_user
        msg["To"] = email
        msg["Subject"] = "ClearDoc: Reminder Set ✓"

        body = f"""
Hi,

Your reminder has been set for: {deadline_text}

We'll email you before this deadline so you don't miss it.

— ClearDoc Team
        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, email, msg.as_string())

        return True
    except Exception as e:
        logger.error("email_send_failed", error=str(e))
        return False


async def send_reminder_email(email: str, deadline_text: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_user
        msg["To"] = email
        msg["Subject"] = f"ClearDoc Reminder: {deadline_text[:50]}"

        body = f"""
Hi,

This is a reminder about your upcoming deadline:

{deadline_text}

Please review your document and take the necessary steps.

— ClearDoc Team
        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, email, msg.as_string())

        return True
    except Exception as e:
        logger.error("reminder_email_failed", error=str(e))
        return False


async def get_pending_reminders(db: AsyncSession) -> List[Reminder]:
    now = datetime.utcnow()
    result = await db.execute(
        select(Reminder)
        .where(Reminder.is_sent == False)
        .where(Reminder.scheduled_at <= now)
    )
    return list(result.scalars().all())


async def mark_reminder_sent(db: AsyncSession, reminder_id) -> None:
    reminder = await db.get(Reminder, reminder_id)
    if reminder:
        reminder.is_sent = True
        reminder.sent_at = datetime.utcnow()
        await db.commit()
