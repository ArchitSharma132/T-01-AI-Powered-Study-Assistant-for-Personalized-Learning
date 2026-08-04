import httpx
from app.core.config import settings


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embed",
            json={"model": settings.OLLAMA_EMBED_MODEL, "input": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


async def generate_single_embedding(text: str) -> list[float]:
    result = await generate_embeddings([text])
    return result[0]
