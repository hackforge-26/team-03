import uuid
import hashlib
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocType
from app.models.result import Result
from app.services.anthropic_service import explain_document
from app.services.parser_service import extract_text_from_file
from app.cache import (
    cache_delete,
    make_history_cache_key,
    make_result_cache_key,
    cache_set,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/explain", tags=["explain"])


@router.post("")
async def explain(
    text: str = Form(""),
    language: str = Form("en"),
    user_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    request_start = time.time()

    # Step 1: Get document text
    document_text = text.strip()
    file_name = None

    if file and file.filename:
        file_bytes = await file.read()
        extracted, error = await extract_text_from_file(file_bytes, file.filename)
        if error:
            raise HTTPException(status_code=400, detail=error)
        document_text = extracted
        file_name = file.filename

    if not document_text:
        raise HTTPException(
            status_code=400, detail="Please paste document text or upload a file."
        )

    if len(document_text) > 10000:
        document_text = document_text[:10000]

    # Step 2: Get or create user
    user_result = await db.execute(select(User).where(User.device_id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        user = User(device_id=user_id, language_preference=language)
        db.add(user)
        await db.flush()

    # Step 3: Call Claude (with cache check inside)
    ai_result, from_cache = await explain_document(document_text, language)

    # Step 4: Detect document type
    doc_type_str = ai_result.get("doc_type", "other")
    try:
        doc_type = DocType(doc_type_str)
    except ValueError:
        doc_type = DocType.other

    # Step 5: Save to PostgreSQL
    input_hash = hashlib.sha256((document_text + language).encode()).hexdigest()

    document = Document(
        user_id=user.id,
        original_text=document_text,
        file_name=file_name,
        doc_type=doc_type,
        language=language,
        is_saved=False,
        input_hash=input_hash,
    )
    db.add(document)
    await db.flush()

    result = Result(
        document_id=document.id,
        summary=ai_result["summary"],
        key_points=ai_result["key_points"],
        next_steps=ai_result["next_steps"],
        urgency_flag=ai_result.get("urgency_flag", False),
        urgency_message=ai_result.get("urgency_message"),
        processing_time_ms=ai_result.get("processing_time_ms", 0),
        served_from_cache=from_cache,
    )
    db.add(result)
    await db.commit()

    # Step 6: Invalidate history cache
    await cache_delete(make_history_cache_key(user_id))

    result_cache_data = {
        "document_id": str(document.id),
        "summary": result.summary,
        "key_points": result.key_points,
        "next_steps": result.next_steps,
        "urgency_flag": result.urgency_flag,
        "urgency_message": result.urgency_message,
        "doc_type": doc_type.value,
        "language": language,
        "created_at": document.created_at.isoformat(),
    }
    await cache_set(
        make_result_cache_key(str(document.id)),
        result_cache_data,
        ttl_seconds=86400,
    )

    logger.info(
        "explain_complete",
        document_id=str(document.id),
        from_cache=from_cache,
        processing_ms=int((time.time() - request_start) * 1000),
    )

    return result_cache_data
