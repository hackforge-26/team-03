import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import JSON, Text, Boolean, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Result(Base):
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Core AI output
    summary: Mapped[str] = mapped_column(Text)
    key_points: Mapped[list] = mapped_column(JSON)
    next_steps: Mapped[list] = mapped_column(JSON)
    comparison_flags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Urgency
    urgency_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    urgency_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    served_from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    document: Mapped["Document"] = relationship(back_populates="result")
