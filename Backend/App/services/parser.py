import json
import logging
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


class MCQParsed(BaseModel):
    question: str
    options: dict[str, str]
    correct: str
    explanation: str = ""
    difficulty: str = "medium"

    @field_validator("difficulty", mode="before")
    @classmethod
    def norm_diff(cls, v):
        return v.lower() if isinstance(v, str) and v.lower() in ("easy", "medium", "hard") else "medium"


class TFParsed(BaseModel):
    question: str
    correct: bool
    explanation: str = ""
    difficulty: str = "medium"

    @field_validator("difficulty", mode="before")
    @classmethod
    def norm_diff(cls, v):
        return v.lower() if isinstance(v, str) and v.lower() in ("easy", "medium", "hard") else "medium"


class ShortParsed(BaseModel):
    question: str
    model_answer: str
    key_terms: list[str] = []
    difficulty: str = "medium"

    @field_validator("difficulty", mode="before")
    @classmethod
    def norm_diff(cls, v):
        return v.lower() if isinstance(v, str) and v.lower() in ("easy", "medium", "hard") else "medium"


def _extract_json_array(raw: str) -> list[dict]:
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end <= start:
        return []
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return []


def parse_mcq(raw: str) -> list[MCQParsed]:
    items = _extract_json_array(raw)
    results = []
    seen = set()
    for item in items:
        try:
            parsed = MCQParsed(**item)
            if parsed.correct not in parsed.options:
                continue
            if len(parsed.options) != 4:
                continue
            if parsed.question in seen:
                continue
            seen.add(parsed.question)
            results.append(parsed)
        except Exception:
            continue
    return results


def parse_tf(raw: str) -> list[TFParsed]:
    items = _extract_json_array(raw)
    results = []
    seen = set()
    for item in items:
        try:
            parsed = TFParsed(**item)
            if parsed.question in seen:
                continue
            seen.add(parsed.question)
            results.append(parsed)
        except Exception:
            continue
    return results


def parse_short(raw: str) -> list[ShortParsed]:
    items = _extract_json_array(raw)
    results = []
    seen = set()
    for item in items:
        try:
            parsed = ShortParsed(**item)
            if parsed.question in seen:
                continue
            seen.add(parsed.question)
            results.append(parsed)
        except Exception:
            continue
    return results
