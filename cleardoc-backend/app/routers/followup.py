from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.document import Document
from app.services.anthropic_service import get_followup_answer

router = APIRouter(prefix="/followup", tags=["followup"])


class FollowupRequest(BaseModel):
    document_id: str
    question: str
    language: str = "en"


@router.post("")
async def followup(
    request: FollowupRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty")

    # Get original document for context
    result = await db.execute(
        select(Document).where(Document.id == request.document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    answer = await get_followup_answer(
        document.original_text, request.question, request.language
    )

    return {"answer": answer}
