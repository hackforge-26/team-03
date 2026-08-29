import uuid
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class DocType(str, enum.Enum):
    medical_bill = "medical_bill"
    legal_notice = "legal_notice"
    govt_form = "govt_form"
    landlord_letter = "landlord_letter"
    other = "other"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    original_text: Mapped[str] = mapped_column(Text)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    doc_type: Mapped[DocType] = mapped_column(Enum(DocType), default=DocType.other, index=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    is_saved: Mapped[bool] = mapped_column(default=False)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")
    result: Mapped[Optional["Result"]] = relationship(
        back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
