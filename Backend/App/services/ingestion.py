import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.topic import Topic
from app.services.extraction import extract_text_from_pdf
from app.services.chunking import chunk_text
from app.services.embeddings import generate_embeddings
from app.services.vector_store import add_to_index
from app.services.topic_tagger import tag_topics

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


async def run_ingestion(document_id: str, file_path: str, db: AsyncSession):
    doc = await db.get(Document, uuid.UUID(document_id))
    if not doc:
        logger.error(f"Document {document_id} not found")
        return

    try:
        doc.status = DocumentStatus.PROCESSING
        await db.commit()

        raw_text = extract_text_from_pdf(file_path)
        if not raw_text.strip():
            doc.status = DocumentStatus.FAILED
            await db.commit()
            logger.error(f"No text extracted from {file_path}")
            return

        txt_path = Path(file_path).with_suffix(".txt")
        txt_path.write_text(raw_text, encoding="utf-8")

        chunks = chunk_text(raw_text)
        if not chunks:
            doc.status = DocumentStatus.FAILED
            await db.commit()
            return

        topic_tags = await tag_topics(chunks)

        topic_cache = {}
        for tag in set(topic_tags):
            existing = await db.execute(
                select(Topic).where(Topic.name == tag, Topic.document_id == doc.id)
            )
            topic = existing.scalar_one_or_none()
            if not topic:
                topic = Topic(name=tag, document_id=doc.id)
                db.add(topic)
                await db.flush()
            topic_cache[tag] = topic.id

        chunk_ids = []
        for i, (text, tag) in enumerate(zip(chunks, topic_tags)):
            chunk = Chunk(
                document_id=doc.id,
                chunk_text=text,
                topic_tag=tag,
                embedding_id=None,
            )
            db.add(chunk)
            await db.flush()
            chunk_ids.append(str(chunk.id))

        batch_size = 30
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            embs = await generate_embeddings(batch)
            all_embeddings.extend(embs)

        add_to_index(all_embeddings, chunk_ids, str(doc.id))

        for i, cid in enumerate(chunk_ids):
            chunk_obj = await db.get(Chunk, uuid.UUID(cid))
            if chunk_obj:
                chunk_obj.embedding_id = str(i)

        doc.status = DocumentStatus.READY
        await db.commit()
        logger.info(f"Ingestion complete: {len(chunks)} chunks, {len(topic_cache)} topics")

    except Exception as e:
        logger.exception(f"Ingestion failed for {document_id}: {e}")
        await db.rollback()
        doc = await db.get(Document, uuid.UUID(document_id))
        if doc:
            doc.status = DocumentStatus.FAILED
            await db.commit()
