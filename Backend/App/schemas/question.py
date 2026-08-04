import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionGenerateRequest(BaseModel):
    topic_id: uuid.UUID
    count: int = 5
    difficulty: str | None = None
    type: str = "mcq"


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    question_text: str
    options: dict | None = None
    difficulty: str


class QuizResponse(BaseModel):
    topic: str
    questions: list[QuestionOut]


class AnswerSubmit(BaseModel):
    question_id: uuid.UUID
    selected_answer: str
    time_taken_sec: float = 0.0


class AnswerResult(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str | None = None
