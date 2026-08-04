import enum
import uuid

from sqlalchemy import String, Text, Enum, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDBase


class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    SHORT = "short"
    TF = "tf"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(UUIDBase):
    __tablename__ = "questions"

    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), nullable=False, index=True)
    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), default=Difficulty.MEDIUM)

    topic = relationship("Topic", back_populates="questions")
    attempts = relationship("Attempt", back_populates="question", cascade="all, delete-orphan")
    review_schedules = relationship("ReviewSchedule", back_populates="question", cascade="all, delete-orphan")
