import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def call_ollama(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_CHAT_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 4096},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"]
