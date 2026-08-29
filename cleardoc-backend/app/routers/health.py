from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.cache import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    status = {"status": "ok", "services": {}}

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        status["services"]["postgresql"] = "ok"
    except Exception as e:
        status["services"]["postgresql"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check Redis
    try:
        await redis_client.ping()
        status["services"]["redis"] = "ok"
    except Exception as e:
        status["services"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return status
