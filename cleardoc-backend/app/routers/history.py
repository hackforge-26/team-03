from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.result import Result
from app.cache import (
    cache_get,
    cache_set,
    cache_delete,
    make_history_cache_key,
    make_result_cache_key,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def get_history(
    user_id: str = Query(...),
    limit: int = Query(20, le=50),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    # Check cache first (60 second TTL)
    cache_key = make_history_cache_key(user_id)
    cached = await cache_get(cache_key)
    if cached and offset == 0:
        return cached

    # Find user
    user_result = await db.execute(select(User).where(User.device_id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return []

    # Query with JOIN — single DB call
    stmt = (
        select(Document, Result)
        .join(Result, Result.document_id == Document.id)
        .where(Document.user_id == user.id)
        .where(Document.is_saved == True)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    rows = await db.execute(stmt)
    history = []

    for document, result in rows:
        summary_preview = (
            result.summary[:80] + "..." if len(result.summary) > 80 else result.summary
        )
        history.append(
            {
                "id": str(document.id),
                "doc_type": document.doc_type.value,
                "summary_preview": summary_preview,
                "urgency_flag": result.urgency_flag,
                "language": document.language,
                "created_at": document.created_at.isoformat(),
            }
        )

    # Cache for 60 seconds
    if offset == 0:
        await cache_set(cache_key, history, ttl_seconds=60)

    return history


@router.get("/{document_id}")
async def get_history_item(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Check cache first
    cached = await cache_get(make_result_cache_key(document_id))
    if cached:
        return cached

    stmt = (
        select(Document, Result)
        .join(Result, Result.document_id == Document.id)
        .where(Document.id == document_id)
    )
    row = await db.execute(stmt)
    pair = row.first()

    if not pair:
        raise HTTPException(status_code=404, detail="Document not found")

    document, result = pair

    return {
        "document_id": str(document.id),
        "summary": result.summary,
        "key_points": result.key_points,
        "next_steps": result.next_steps,
        "urgency_flag": result.urgency_flag,
        "urgency_message": result.urgency_message,
        "doc_type": document.doc_type.value,
        "language": document.language,
        "created_at": document.created_at.isoformat(),
    }


@router.post("/save")
async def save_to_history(data: dict, db: AsyncSession = Depends(get_db)):
    document_id = data.get("document_id")
    user_id = data.get("user_id")

    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document.is_saved = True
    await db.commit()

    # Invalidate history cache
    await cache_delete(make_history_cache_key(user_id))

    return {"success": True}


@router.delete("/{document_id}")
async def delete_history_item(
    document_id: str,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    stmt = delete(Document).where(Document.id == document_id)
    await db.execute(stmt)
    await db.commit()

    await cache_delete(make_history_cache_key(user_id))
    await cache_delete(make_result_cache_key(document_id))

    return {"success": True}
