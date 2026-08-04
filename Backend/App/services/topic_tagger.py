import json
import httpx
from app.core.config import settings


async def tag_topics(chunks: list[str], batch_size: int = 10) -> list[str]:
    all_tags = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        tags = await _tag_batch(batch)
        all_tags.extend(tags)
    return all_tags


async def _tag_batch(chunks: list[str]) -> list[str]:
    numbered = "\n".join(f"{i+1}. {c[:200]}" for i, c in enumerate(chunks))
    prompt = (
        "Assign a short topic label (2-5 words) to each of the following text chunks "
        "from a study document. Return ONLY a JSON array of strings, one label per chunk, "
        "in the same order.\n\n"
        f"Chunks:\n{numbered}\n\n"
        "Return ONLY the JSON array, no other text."
    )
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": settings.OLLAMA_CHAT_MODEL, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            raw = resp.json()["response"]
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start != -1 and end > start:
                tags = json.loads(raw[start:end])
                if len(tags) == len(chunks):
                    return [str(t).strip() for t in tags]
    except Exception:
        pass
    return [_heuristic_tag(c) for c in chunks]


def _heuristic_tag(chunk: str) -> str:
    first_line = chunk.strip().split("\n")[0].strip()
    words = first_line.split()[:5]
    return " ".join(words) if words else "General"
