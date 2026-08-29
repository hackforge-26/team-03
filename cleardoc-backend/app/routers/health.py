from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import redis_client
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    status = {"status": "ok", "services": {}}

    try:
        await db.execute(text("SELECT 1"))
        status["services"]["postgresql"] = "ok"
    except Exception as e:
        status["services"]["postgresql"] = f"error: {str(e)}"
        status["status"] = "degraded"

    try:
        if redis_client is None:
            raise RuntimeError("Redis not initialized")
        await redis_client.ping()
        status["services"]["redis"] = "ok"
    except Exception as e:
        status["services"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return status
