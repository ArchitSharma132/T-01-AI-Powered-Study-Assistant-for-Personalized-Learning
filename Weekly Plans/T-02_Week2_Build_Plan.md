# Week 2 -- Document Ingestion Pipeline: Build Plan

Goal: A user uploads a PDF, the system extracts text, chunks it, generates embeddings, and stores everything so it's searchable via FAISS.

---

## Overview

| Part | Focus | Dependencies | Est. Hours |

| 1 | New backend dependencies + Ollama embed model | None | 1 hr |
| 2 | File upload endpoint + storage | Part 1 | 2-3 hrs |
| 3 | PDF text extraction service | Part 2 | 2 hrs |
| 4 | Text chunking service | Part 3 | 2 hrs |
| 5 | Embedding generation + FAISS index | Part 4 | 3-4 hrs |
| 6 | Topic tagging (LLM-based) | Part 5 | 2 hrs |
| 7 | Background ingestion pipeline | Parts 3-6 | 2-3 hrs |
| 8 | Frontend upload UI + status polling | Part 7 | 3 hrs |
| 9 | Integration testing with real PDFs | All | 2 hrs |
| | **Total** | | **~19-22 hrs** |

---

## Part 1 -- Dependencies + Ollama Embed Model

### Backend packages to add to `requirements.txt`

```
PyMuPDF>=1.24
faiss-cpu
langchain-text-splitters
```

### Ollama model to pull

```bash
ollama pull nomic-embed-text
```

This model outputs 768-dim vectors. It runs locally, no API cost.

### Verify

- `python -c "import fitz; print(fitz.__doc__)"` prints version
- `python -c "import faiss; print(faiss.__version__)"` prints version
- `ollama run nomic-embed-text "test"` returns an embedding

### Done when
- All 3 packages install without errors
- `nomic-embed-text` model responds to embedding requests

---

## Part 2 -- File Upload Endpoint

### API

| Method | Path | Request | Response |

| POST | `/documents/upload` | `multipart/form-data` with `file` field | `DocumentUploadResponse` |
| GET | `/documents/{id}/status` | -- | `DocumentStatusResponse` |
| GET | `/documents` | query: `user_id` | list of `DocumentUploadResponse` |

### Files to create/modify

| File | Action |

| `backend/app/api/documents.py` | New -- upload + status endpoints |
| `backend/app/api/router.py` | Add documents router |

### Logic

1. Validate file type (`.pdf` only) and size (max 20MB)
2. Save file to `backend/uploads/{document_id}.pdf`
3. Create `documents` row with `status = "uploading"`
4. Return `DocumentUploadResponse` immediately
5. Kick off background ingestion (Part 7)

### Constraints
- Cap file size at 20MB via FastAPI's `UploadFile`
- Create `uploads/` directory if it doesn't exist
- Add `uploads/` to `.gitignore`

### Done when
- `POST /documents/upload` with a real PDF returns 201 with a document ID
- `GET /documents/{id}/status` returns `"uploading"`
- File exists on disk at `backend/uploads/{id}.pdf`

---

## Part 3 -- PDF Text Extraction Service

### Files to create

| File | Purpose |

| `backend/app/services/extraction.py` | `extract_text_from_pdf(file_path) -> str` |

### Implementation

Use PyMuPDF (fitz) to extract text page-by-page:

```python
def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text
```

### Edge cases
- Empty pages: skip silently
- Scanned PDFs (image-only): return empty string, set document status to `failed` with a message
- Encoding issues: PyMuPDF handles most internally

### Done when
- Function extracts clean text from 3+ sample PDFs
- Extracted text stored in `documents.raw_text_path` (save as `.txt` file alongside the PDF)

---

## Part 4 -- Text Chunking Service

### Files to create

| File | Purpose |

| `backend/app/services/chunking.py` | `chunk_text(text, chunk_size, overlap) -> list[str]` |

### Implementation

Use `langchain-text-splitters.RecursiveCharacterTextSplitter`:

```python
def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(text)
```

### Parameters

| Param | Default | Rationale |

| `chunk_size` | 500 chars | Balances context richness vs embedding quality |
| `chunk_overlap` | 50 chars | Prevents losing context at boundaries |
| `separators` | paragraph, line, sentence, word | Preserves logical structure |

### Done when
- A 10-page PDF produces 30-80 chunks (reasonable range)
- No chunk exceeds `chunk_size + overlap`
- Chunks are stored in the `chunks` table with `document_id` FK

---

## Part 5 -- Embedding Generation + FAISS Index

### Files to create

| File | Purpose |

| `backend/app/services/embeddings.py` | `generate_embeddings(texts) -> list[list[float]]` |
| `backend/app/services/vector_store.py` | FAISS index management (add, search, save, load) |

### Embedding via Ollama

Call Ollama's `/api/embed` endpoint using httpx:

```python
async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embed",
            json={"model": settings.OLLAMA_EMBED_MODEL, "input": texts}
        )
        return response.json()["embeddings"]
```

### FAISS index

| Operation | Method |

| Create index | `faiss.IndexFlatIP(dimension)` (inner product for normalized vectors) |
| Add vectors | `index.add(np.array(embeddings))` |
| Search | `index.search(query_vector, k)` returns `(distances, indices)` |
| Save to disk | `faiss.write_index(index, path)` |
| Load from disk | `faiss.read_index(path)` |

### Storage strategy
- One global FAISS index file: `backend/data/faiss_index.bin`
- A metadata JSON mapping FAISS index positions to `chunk_id` values
- On each document ingestion, append to the existing index
- Store `embedding_id` (FAISS position) in the `chunks` table

### Done when
- Chunks from a real PDF are embedded and added to FAISS
- A text query like "what is process scheduling" returns relevant chunk IDs
- Index persists to disk and can be reloaded

---

## Part 6 -- Topic Tagging via LLM

### Files to create

| File | Purpose |

| `backend/app/services/topic_tagger.py` | `tag_topics(chunks) -> list[str]` |

### Implementation

Send batches of chunks to Ollama and ask for a short topic label:

```
Prompt: Given these text chunks from a study document, assign a short
topic label (2-5 words) to each chunk. Return a JSON array of labels.

Chunks:
1. [chunk text...]
2. [chunk text...]
...
```

### Topic storage
- Save unique topics to the `topics` table
- Tag each chunk with `topic_tag` (string match back to topic name)
- Batch chunks in groups of 10-15 to reduce LLM calls

### Fallback
If the LLM call fails or returns malformed JSON, fall back to a simple heuristic: use the first line or heading of each chunk as the topic tag.

### Done when
- Chunks have `topic_tag` values populated
- `topics` table has entries linked to the document

---

## Part 7 -- Background Ingestion Pipeline

### Files to create/modify

| File | Purpose |

| `backend/app/services/ingestion.py` | Orchestrates the full pipeline |
| `backend/app/api/documents.py` | Trigger background task on upload |

### Pipeline steps (in order)

```
1. Set document status -> "processing"
2. Extract text (Part 3)
3. Save raw text to disk
4. Chunk text (Part 4)
5. Store chunks in DB
6. Generate embeddings (Part 5)
7. Add to FAISS index (Part 5)
8. Tag topics via LLM (Part 6)
9. Create topic entries in DB
10. Set document status -> "ready"

On any error: set status -> "failed", log the error
```

### Execution
Use FastAPI's `BackgroundTasks` to run the pipeline asynchronously after upload returns. No Celery needed for v1.

### Done when
- Upload a PDF -> document status goes from `uploading` -> `processing` -> `ready`
- All tables populated: `documents`, `chunks`, `topics`
- FAISS index on disk contains the new vectors

---

## Part 8 -- Frontend Upload UI + Status Polling

### Files to modify

| File | Changes |

| `frontend/src/pages/UploadPage.jsx` | Full upload UI with drag-drop, file selection, progress |
| `frontend/src/pages/DashboardPage.jsx` | Show document count from API |

### Upload flow

```
[Select file] -> [Upload] -> [Show "Processing..."] -> [Poll status] -> [Show "Ready"]
```

### Implementation

1. Use a native `<input type="file">` or add `react-dropzone`
2. POST to `/documents/upload` with `FormData`
3. On success, poll `GET /documents/{id}/status` every 2 seconds
4. Display status transitions: uploading, processing, ready, failed
5. Show a list of previously uploaded documents

### Status display

| Status | UI |

| uploading | "Uploading..." with a progress indicator |
| processing | "Processing document..." |
| ready | "Ready" with a checkmark |
| failed | "Failed" with an error message |

### Done when
- Can upload a PDF through the browser UI
- Status updates from processing to ready automatically
- Document appears in the document list on dashboard

---

## Part 9 -- Integration Testing

### Test with real PDFs
- Upload at least 3 different syllabus PDFs (varied subjects, page counts)
- Verify text extraction quality (spot-check extracted text vs original)
- Verify chunk count is reasonable (not too few, not too many)
- Verify FAISS search returns relevant results for sample queries

### Test script to create

| File | Purpose |

| `backend/tests/test_ingestion.py` | Upload a PDF, verify chunks + embeddings created |
| `backend/tests/test_vector_search.py` | Query FAISS, verify relevant chunks returned |

### Sample queries to test

| Query | Expected topic match |

| "what is process scheduling" | OS / Scheduling |
| "explain normalization in databases" | DBMS / Normalization |
| "dijkstra's algorithm" | DAA / Graphs |

### Done when
- 3+ PDFs upload and process without errors
- FAISS search returns relevant chunks for test queries
- End-to-end test passes: upload -> process -> search

---

## Dependency Graph

```
Part 1 (deps)
  |
Part 2 (upload endpoint)
  |
Part 3 (text extraction)
  |
Part 4 (chunking)
  |
Part 5 (embeddings + FAISS)
  |
Part 6 (topic tagging)      Part 8 (frontend UI)
  |                              |
Part 7 (pipeline orchestrator) --+
  |
Part 9 (integration tests)
```

Parts 5 and 6 can be developed in parallel. Part 8 (frontend) can be started as soon as Part 2 is done.

---

## Risk Notes

- **PDF quality is the #1 risk.** Scanned PDFs or complex layouts (tables, columns) will produce garbage text. Test early with real PDFs, not ideal samples.
- **Ollama embedding speed.** `nomic-embed-text` is fast but batching matters. Embedding 100 chunks individually is slow; batch them in groups of 20-50.
- **FAISS index corruption.** Always write to a temp file first, then rename. Never write directly to the live index file.
- **LLM topic tagging can be flaky.** Always have the heuristic fallback ready. Don't let a failed LLM call block the entire pipeline.

---

## Files Created/Modified Summary

| File | Action | Part |

| `backend/requirements.txt` | Modified (add 3 deps) | 1 |
| `backend/app/api/documents.py` | New | 2 |
| `backend/app/api/router.py` | Modified | 2 |
| `backend/app/services/extraction.py` | New | 3 |
| `backend/app/services/chunking.py` | New | 4 |
| `backend/app/services/embeddings.py` | New | 5 |
| `backend/app/services/vector_store.py` | New | 5 |
| `backend/app/services/topic_tagger.py` | New | 6 |
| `backend/app/services/ingestion.py` | New | 7 |
| `frontend/src/pages/UploadPage.jsx` | Modified | 8 |
| `frontend/src/pages/DashboardPage.jsx` | Modified | 8 |
| `backend/tests/test_ingestion.py` | New | 9 |
| `backend/tests/test_vector_search.py` | New | 9 |
| `.gitignore` | Modified (add uploads/) | 2 |
