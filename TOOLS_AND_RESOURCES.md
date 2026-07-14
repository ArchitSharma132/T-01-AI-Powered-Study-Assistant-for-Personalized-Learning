# Tools, Resources & API Keys Registry
> Last updated: 2026-07-14

This file tracks **every** external tool, service, library, and API key used in the project. No paid APIs — everything is free or runs locally.

---

## API Keys & Secrets

| Key / Secret | Source | Cost | Where Used | How to Get |
|---|---|---|---|---|
| `OLLAMA_BASE_URL` | Ollama (local) | **Free** | LLM chat + embeddings | Install Ollama → runs on `localhost:11434` |
| `JWT_SECRET` | Self-generated | **Free** | Auth token signing | Generate any random string |
| `DATABASE_URL` | PostgreSQL (Docker) | **Free** | All data storage | Auto-configured via Docker Compose |
| `REDIS_URL` | Redis (Docker) | **Free** | Caching, session store | Auto-configured via Docker Compose |

> [!NOTE]
> No OpenAI, Hugging Face, or any paid API key is required. All AI features run through **Ollama** on your local machine.

---

## AI / ML Models (via Ollama — all local, all free)

| Model | Purpose | Pull Command | Size |
|---|---|---|---|
| `mistral` | Question generation, topic tagging, grading | `ollama pull mistral` | ~4.1 GB |
| `nomic-embed-text` | Text embeddings for RAG/FAISS | `ollama pull nomic-embed-text` | ~274 MB |

**Alternative models** (if your machine struggles with Mistral):
| Model | Pull Command | Size | Notes |
|---|---|---|---|
| `llama3.2:3b` | `ollama pull llama3.2:3b` | ~2 GB | Lighter, still good quality |
| `phi3:mini` | `ollama pull phi3:mini` | ~2.3 GB | Microsoft's small model, fast |
| `gemma2:2b` | `ollama pull gemma2:2b` | ~1.6 GB | Google's small model |

---

## Backend Stack

| Tool / Library | Version | Purpose | License |
|---|---|---|---|
| Python | 3.11+ (you have 3.14.3) | Backend runtime | PSF |
| FastAPI | ≥0.110 | Web framework / REST API | MIT |
| Uvicorn | latest | ASGI server | BSD |
| SQLAlchemy | ≥2.0 (async) | ORM / database toolkit | MIT |
| asyncpg | latest | PostgreSQL async driver | Apache 2.0 |
| Alembic | latest | Database migrations | MIT |
| Pydantic / pydantic-settings | latest | Config + validation | MIT |
| python-jose | latest | JWT token handling | MIT |
| passlib + bcrypt | latest | Password hashing | BSD |
| python-multipart | latest | File upload parsing | BSD |
| redis (Python client) | latest | Redis connection | MIT |
| PyMuPDF (fitz) | latest | PDF text extraction | AGPL |
| FAISS (faiss-cpu) | latest | Vector similarity search | MIT |
| sentence-transformers | latest | Embedding models (backup if not using Ollama embeds) | Apache 2.0 |
| langchain-text-splitters | latest | Text chunking | MIT |
| APScheduler | latest | Background job scheduling | MIT |
| httpx | latest | HTTP client for Ollama API calls | BSD |
| pytest | latest | Testing framework | MIT |

---

## Frontend Stack

| Tool / Library | Version | Purpose | License |
|---|---|---|---|
| Node.js | 18+ (you have 24.13.1) | Frontend runtime | MIT |
| React | 18/19 | UI framework | MIT |
| Vite | latest | Build tool / dev server | MIT |
| React Router | v6+ | Client-side routing | MIT |
| Axios | latest | HTTP client | MIT |
| TailwindCSS | v4 | Utility-first CSS | MIT |
| Recharts | latest | Charts for analytics dashboard | MIT |
| react-dropzone | latest | File upload UI | MIT |

---

## Infrastructure (Docker — all free)

| Service | Image | Purpose |
|---|---|---|
| PostgreSQL | `postgres:15-alpine` | Primary database |
| Redis | `redis:7-alpine` | Caching, background job queue |
| Backend | Custom (Python 3.11-slim) | FastAPI application |
| Frontend | Custom (Node 18-alpine) | React dev server / nginx prod |

---

## Dev Tools

| Tool | Version (yours) | Purpose |
|---|---|---|
| Git | 2.51.0 | Version control |
| Docker Desktop | 29.6.1 | Containerization |
| Docker Compose | 5.3.0 | Multi-container orchestration |
| Ollama | 0.32.0 | Local LLM server |
| npm | 11.8.0 | Node package manager |

---

## Total Cost

| Category | Cost |
|---|---|
| AI / LLM | **$0** (Ollama, local) |
| Database | **$0** (Docker PostgreSQL) |
| Cache | **$0** (Docker Redis) |
| Vector Store | **$0** (FAISS, local) |
| Hosting (dev) | **$0** (localhost) |
| **Total** | **$0** |

---

## Notes

- **Ollama** replaces OpenAI entirely. It exposes the same-style API at `http://localhost:11434` with endpoints like `/api/generate`, `/api/chat`, and `/api/embeddings`.
- **FAISS** replaces Pinecone. Runs in-process, stores indexes to disk. Zero network calls.
- If you later want to deploy to the cloud, you can swap Ollama for any OpenAI-compatible API by just changing the `OLLAMA_BASE_URL` and model names — the code architecture supports this.
