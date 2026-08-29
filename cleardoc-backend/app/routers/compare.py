from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.document import Document
from app.models.result import Result
from app.services.anthropic_service import compare_document
from app.cache import cache_get, cache_set

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/{document_id}")
async def compare(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"compare:{document_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    comparison = await compare_document(document.original_text)

    # Save flags to result record
    result_row = await db.execute(
        select(Result).where(Result.document_id == document_id)
    )
    result_obj = result_row.scalar_one_or_none()
    if result_obj:
        result_obj.comparison_flags = comparison.get("flags", [])
        await db.commit()

    await cache_set(cache_key, comparison, ttl_seconds=86400)
    return comparison
