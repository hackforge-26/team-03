import time

import structlog
from fastapi import HTTPException, Request

from app.cache import redis_client
from app.config import settings

logger = structlog.get_logger()


async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    if redis_client is None:
        return await call_next(request)

    ip = request.headers.get(
        "X-Forwarded-For",
        request.headers.get("X-Real-IP", (request.client.host if request.client else "unknown")),
    )
    ip = ip.split(",")[0].strip() if ip else "unknown"

    now = int(time.time())
    minute_key = f"rate:minute:{ip}:{now // 60}"
    day_key = f"rate:day:{ip}:{now // 86400}"

    pipe = redis_client.pipeline()
    pipe.incr(minute_key)
    pipe.expire(minute_key, 60)
    pipe.incr(day_key)
    pipe.expire(day_key, 86400)
    results = await pipe.execute()

    minute_count = int(results[0])
    day_count = int(results[2])

    if minute_count > settings.rate_limit_per_minute:
        retry_after = 60 - (now % 60)
        logger.warning("rate_limit_minute", ip=ip, count=minute_count)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too many requests. Please wait a moment.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    if day_count > settings.rate_limit_per_day:
        retry_after = 86400 - (now % 86400)
        logger.warning("rate_limit_day", ip=ip, count=day_count)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily limit reached. Try again tomorrow.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining-Minute"] = str(
        max(0, settings.rate_limit_per_minute - minute_count)
    )
    return response
