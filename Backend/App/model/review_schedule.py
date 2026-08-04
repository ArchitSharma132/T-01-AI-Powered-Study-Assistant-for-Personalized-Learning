import uuid
from datetime import date

from sqlalchemy import Float, Integer, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDBase


class ReviewSchedule(UUIDBase):
    __tablename__ = "review_schedule"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    next_review_date: Mapped[date] = mapped_column(Date, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship("User", back_populates="review_schedules")
    question = relationship("Question", back_populates="review_schedules")
