import uuid

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDBase


class Chunk(UUIDBase):
    __tablename__ = "chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(255))
    topic_tag: Mapped[str | None] = mapped_column(String(255))

    document = relationship("Document", back_populates="chunks")
