import uuid

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDBase


class Topic(UUIDBase):
    __tablename__ = "topics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)

    document = relationship("Document", back_populates="topics")
    questions = relationship("Question", back_populates="topic", cascade="all, delete-orphan")
