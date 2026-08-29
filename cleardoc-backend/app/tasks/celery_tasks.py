from celery import Celery
from app.config import settings
import structlog

logger = structlog.get_logger()

# Celery app configuration
celery_app = Celery(
    "cleardoc",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


@celery_app.task(bind=True, max_retries=3)
def send_reminder_email_task(self, email: str, deadline_text: str):
    """Background task to send reminder emails."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

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

        logger.info("reminder_email_sent", email=email)
        return {"success": True, "email": email}

    except Exception as exc:
        logger.error("reminder_email_failed", error=str(exc))
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task
def check_pending_reminders():
    """Periodic task to check and send pending reminders."""
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.models.reminder import Reminder
    from datetime import datetime

    async def _check():
        engine = create_async_engine(settings.database_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            now = datetime.utcnow()
            result = await db.execute(
                select(Reminder)
                .where(Reminder.is_sent == False)
                .where(Reminder.scheduled_at <= now)
            )
            reminders = list(result.scalars().all())

            for reminder in reminders:
                send_reminder_email_task.delay(
                    reminder.email, reminder.deadline_text
                )
                reminder.is_sent = True
                reminder.sent_at = now
                await db.commit()

            logger.info("pending_reminders_checked", count=len(reminders))

        await engine.dispose()

    asyncio.run(_check())


# Periodic task schedule
celery_app.conf.beat_schedule = {
    "check-reminders-every-hour": {
        "task": "app.tasks.celery_tasks.check_pending_reminders",
        "schedule": 3600.0,
    },
}
