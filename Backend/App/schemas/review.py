import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class ReviewDue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    ease_factor: float
    interval_days: int
    next_review_date: date
    repetitions: int


class ReviewDueList(BaseModel):
    count: int
    reviews: list[ReviewDue]
