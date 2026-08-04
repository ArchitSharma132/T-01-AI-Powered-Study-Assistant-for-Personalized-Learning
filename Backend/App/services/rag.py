import uuid
from app.services.embeddings import generate_single_embedding
from app.services.vector_store import search_index
from app.models.chunk import Chunk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def retrieve_context(
    query: str,
    db: AsyncSession,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict]:
    query_emb = await generate_single_embedding(query)
    results = search_index(query_emb, top_k=top_k, document_id=document_id)
    if not results:
        return []

    chunk_ids = [uuid.UUID(r["chunk_id"]) for r in results]
    score_map = {r["chunk_id"]: r["score"] for r in results}

    rows = await db.execute(select(Chunk).where(Chunk.id.in_(chunk_ids)))
    chunks = {str(c.id): c for c in rows.scalars().all()}

    context = []
    for r in results:
        c = chunks.get(r["chunk_id"])
        if c:
            context.append({
                "chunk_id": str(c.id),
                "chunk_text": c.chunk_text,
                "topic_tag": c.topic_tag,
                "score": score_map[r["chunk_id"]],
            })
    return context
