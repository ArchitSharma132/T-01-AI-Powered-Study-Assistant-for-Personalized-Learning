import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, async_session
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentUploadResponse, DocumentStatusResponse
from app.services.ingestion import run_ingestion

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MAX_FILE_SIZE = 20 * 1024 * 1024

TEMP_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _run_ingestion_with_session(document_id: str, file_path: str):
    async with async_session() as db:
        await run_ingestion(document_id, file_path, db)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    doc = Document(
        user_id=TEMP_USER_ID,
        filename=file.filename,
        status=DocumentStatus.UPLOADING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    file_path = UPLOAD_DIR / f"{doc.id}.pdf"
    file_path.write_bytes(content)

    background_tasks.add_task(_run_ingestion_with_session, str(doc.id), str(file_path))

    return doc


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/", response_model=list[DocumentUploadResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.user_id == TEMP_USER_ID).order_by(Document.upload_date.desc())
    )
    return result.scalars().all()
