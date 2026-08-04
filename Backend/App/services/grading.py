from app.services.embeddings import generate_embeddings
import numpy as np


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    dot = np.dot(va, vb)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return float(dot / (na * nb)) if na and nb else 0.0


def grade_mcq(selected: str, correct: str) -> bool:
    return selected.strip().upper() == correct.strip().upper()


def grade_tf(selected: str, correct: bool) -> bool:
    return selected.strip().lower() in (str(correct).lower(), "true" if correct else "false")


async def grade_short(user_answer: str, model_answer: str, key_terms: list[str]) -> tuple[bool, float]:
    user_lower = user_answer.lower()
    if key_terms:
        matches = sum(1 for t in key_terms if t.lower() in user_lower)
        keyword_ratio = matches / len(key_terms)
    else:
        keyword_ratio = 0.0

    try:
        embs = await generate_embeddings([user_answer, model_answer])
        cosine = _cosine_similarity(embs[0], embs[1])
    except Exception:
        cosine = 0.0

    score = 0.4 * keyword_ratio + 0.6 * cosine
    return score >= 0.6, score
