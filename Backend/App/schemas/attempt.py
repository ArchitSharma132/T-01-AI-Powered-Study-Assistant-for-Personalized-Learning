import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    is_correct: bool
    time_taken_sec: float
    attempted_at: datetime
