import hashlib
import json
from typing import Any, Optional

import structlog
from redis.asyncio import Redis, from_url

from app.config import settings

logger = structlog.get_logger()

redis_client: Optional[Redis] = None


async def init_redis():
    global redis_client
    redis_client = from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )
    await redis_client.ping()
    logger.info("redis_connected")


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def make_document_cache_key(text: str) -> str:
    normalized = text.strip().lower()
    hash_val = hashlib.sha256(normalized.encode()).hexdigest()
    return f"doc_result:{hash_val}"


def make_history_cache_key(user_id: str) -> str:
    return f"history:{user_id}"


def make_result_cache_key(document_id: str) -> str:
    return f"result:{document_id}"


async def cache_get(key: str) -> Optional[Any]:
    if redis_client is None:
        return None
    try:
        value = await redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning("cache_get_failed", key=key, error=str(e))
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600):
    if redis_client is None:
        return
    try:
        await redis_client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as e:
        logger.warning("cache_set_failed", key=key, error=str(e))


async def cache_delete(key: str):
    if redis_client is None:
        return
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.warning("cache_delete_failed", key=key, error=str(e))


async def cache_delete_pattern(pattern: str):
    if redis_client is None:
        return
    try:
        keys = [key async for key in redis_client.scan_iter(match=pattern)]
        if keys:
            await redis_client.delete(*keys)
    except Exception as e:
        logger.warning("cache_pattern_delete_failed", error=str(e))
