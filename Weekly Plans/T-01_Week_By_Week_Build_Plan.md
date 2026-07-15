# T-01: AI-Powered Study Assistant — Week-by-Week Build Plan

This document expands the project README into a detailed, actionable weekly plan. Each week includes goals, concrete tasks, technical decisions, code/folder structure where relevant, and a "definition of done" so you know when to move on.

---

## Before Week 1: Environment & Account Setup

Do this before the clock starts so Week 1 isn't eaten by setup friction.

- [ ] Create GitHub repo with `main` + `dev` branches, add `.gitignore` (Python + Node)
- [ ] Install: Python 3.11+, Node 18+, PostgreSQL 15+, Redis, Docker Desktop
- [ ] Create accounts: OpenAI (or Hugging Face if avoiding cost), and pick a deploy target (Render/AWS)
- [ ] Decide vector store now: **FAISS (local, free)** vs Pinecone (managed, has free tier limits). Recommendation: start with FAISS, migrate later only if needed.
- [ ] Set up `.env.example` with placeholders for `DATABASE_URL`, `OPENAI_API_KEY`, `JWT_SECRET`, `REDIS_URL`

### Suggested repo structure
```
study-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/            # route handlers
│   │   ├── core/           # config, security, JWT
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # ingestion, rag, scheduler, analytics
│   │   ├── db/              # session, migrations
│   │   └── workers/        # background jobs (scheduler, nightly analytics)
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/             # axios/fetch client
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── sample_data/             # 5+ syllabus PDFs
└── README.md
```

---

## Week 1 — Foundations: Requirements, Stack, DB Schema

**Goal:** Nothing AI-related yet. Get the skeleton running end-to-end (empty pages, empty endpoints, DB connected) so every later week is additive.

### Tasks
1. **Finalize scope** — write a one-page scope doc: which question types ship in v1 (MCQ is mandatory; decide if short-answer/T-F are v1 or stretch)
2. **Design the database schema** (Postgres). Minimum tables:
   - `users` (id, email, password_hash, created_at)
   - `documents` (id, user_id, filename, upload_date, status, raw_text_path)
   - `chunks` (id, document_id, chunk_text, embedding_id, topic_tag)
   - `topics` (id, name, document_id)
   - `questions` (id, topic_id, type[mcq/short/tf], question_text, options JSON, correct_answer, difficulty)
   - `attempts` (id, user_id, question_id, is_correct, time_taken_sec, attempted_at)
   - `review_schedule` (id, user_id, question_id, ease_factor, interval_days, next_review_date, repetitions)
   - `sessions` (id, user_id, jwt_id, created_at, expires_at) — if you want revocable sessions
3. **Set up FastAPI skeleton**: `/health` endpoint, CORS config, config loading via `pydantic-settings`
4. **Set up React skeleton**: TailwindCSS installed, routing (React Router), a placeholder login page and dashboard page
5. **Docker Compose**: containers for `backend`, `frontend`, `postgres`, `redis` — confirm all four start together with `docker compose up`
6. **Write ADRs (Architecture Decision Records)** — short markdown notes on why FAISS vs Pinecone, why SM-2 vs Leitner, why OpenAI vs HF. Graders reward this under "Documentation."

### Definition of Done
- `docker compose up` boots backend + frontend + db + redis with no errors
- `/health` returns 200 from the browser
- ER diagram of the schema committed to `/docs`
- Empty login page renders in browser

---

## Week 2 — Document Ingestion Pipeline

**Goal:** A user can upload a PDF or paste text, and it ends up chunked, embedded, and searchable.

### Tasks
1. **File upload endpoint** (`POST /documents/upload`) — accept PDF or raw text, store file, create `documents` row with status `processing`
2. **Text extraction** — use `PyMuPDF` (fitz) or `pdfplumber` for PDF text extraction (PyMuPDF is faster and handles more layouts)
3. **Chunking strategy** — split text into ~300–500 token chunks with ~50 token overlap (use `langchain.text_splitter.RecursiveCharacterTextSplitter` or write your own). Overlap prevents losing context at chunk boundaries.
4. **Topic tagging (lightweight)** — either:
   - Use heading detection from the PDF (font size/bold heuristics) to tag chunks by section, or
   - Ask the LLM to assign a short topic label per chunk (cheap, 1 call per chunk batch)
5. **Embedding generation** — use `sentence-transformers` (`all-MiniLM-L6-v2`, free, local) or OpenAI `text-embedding-3-small` (cheap, better quality). Store vectors in FAISS index, persist index to disk per-document or globally with document_id metadata filtering.
6. **Update document status** to `ready` once embedding completes; frontend polls or uses a simple websocket/status endpoint
7. **Frontend**: file upload UI with progress state (uploading → processing → ready)

### Technical notes
- Run ingestion as a background task (FastAPI `BackgroundTasks` is enough for v1; don't over-engineer with Celery unless you have time later)
- Cap file size (e.g. 20MB) and page count to keep processing under the 3s generation target for later steps
- Store chunk text in Postgres AND embeddings in FAISS — Postgres is source of truth, FAISS is the search index

### Definition of Done
- Upload a real syllabus PDF → see chunks in the `chunks` table
- A test script can query FAISS with a sample question and get back relevant chunks
- At least 3 of your 5 sample PDFs process without errors

---

## Week 3 — Question Generation Engine (RAG)

**Goal:** Given a topic, generate real MCQ (and short-answer if in scope) questions grounded in the uploaded material.

### Tasks
1. **Retrieval step** — given a topic/keyword, embed the query, retrieve top-k (e.g. 5) relevant chunks from FAISS
2. **Prompt design** — write a structured prompt template that:
   - Gives the LLM the retrieved context
   - Asks for JSON output (question, 4 options, correct answer index, explanation, difficulty)
   - Explicitly instructs "only use facts from the provided context" to reduce hallucination
3. **LLM call + parsing** — call OpenAI/HF, parse JSON response defensively (wrap in try/except, validate against a Pydantic schema, retry once on malformed JSON)
4. **Question types**:
   - MCQ: 4 options, 1 correct
   - True/False: statement + boolean
   - Short-answer: question + model answer (grading short-answer is genuinely hard — for v1, do simple keyword/semantic-similarity matching against the model answer rather than trying to build an exact grader)
5. **Difficulty scaling** — tag generated questions as easy/medium/hard based on a prompt instruction, or post-hoc based on chunk complexity (sentence length, technical term density)
6. **Store generated questions** in the `questions` table, linked to `topic_id`
7. **API endpoint**: `POST /quiz/generate` — takes topic_id + count + difficulty preference, returns a quiz
8. **Frontend**: quiz-taking UI — question card, options, submit, immediate feedback + explanation

### Definition of Done
- Hit `/quiz/generate` for a real uploaded document and get back 5 well-formed MCQs grounded in that document's content
- Generation completes in under 3 seconds (per the non-functional requirement) — if not, cache retrieval results or reduce k
- Frontend can render and let a user answer a generated quiz

---

## Week 4 — Spaced Repetition Scheduler + Auth

**Goal:** Answering a question updates a real spaced-repetition schedule, and the whole app is behind login.

### Tasks: Auth
1. Implement JWT auth: `/auth/register`, `/auth/login`, `/auth/refresh`
2. Password hashing with `bcrypt` / `passlib`
3. Protect all data endpoints with a dependency that validates the JWT
4. Frontend: auth context, protected routes, token storage (memory + refresh, not localStorage for the access token if you want to be strict about security)

### Tasks: Spaced Repetition (SM-2 recommended over Leitner — SM-2 is the algorithm behind Anki and is well-documented)
1. Implement SM-2 core logic as a pure function:
   - Inputs: previous ease factor, previous interval, repetition count, quality of response (0–5 or simplified to correct/incorrect/partial)
   - Outputs: new ease factor, new interval (days), next repetition count
2. `POST /attempts` — when a user answers a question, record the attempt AND run SM-2 to update `review_schedule`
3. `GET /reviews/due` — returns questions where `next_review_date <= today` for the logged-in user
4. **Background worker** — a scheduled job (APScheduler or a simple cron + script) that checks for due reviews and could trigger notifications (email/in-app) — even a stub/log-only version satisfies the requirement if you're time-constrained
5. Frontend: a "Due for Review" section on the dashboard separate from "New Quiz"

### Definition of Done
- Registering, logging in, and hitting protected endpoints works end-to-end
- Answering a question correctly pushes its next review date further out; answering incorrectly resets/shortens the interval (verify with a manual test sequence of 3–4 attempts on the same question)
- `/reviews/due` returns the right questions on the right day (test by manually adjusting `next_review_date` in the DB)

---

## Week 5 — Analytics Dashboard

**Goal:** Turn stored attempts into visual insight: score trends, topic mastery, time-per-topic, weak-area heatmap.

### Tasks
1. **Aggregation queries / nightly job**:
   - Score trend: attempts grouped by day/week, % correct
   - Topic mastery %: correct attempts / total attempts per topic, rolling window
   - Time-per-topic: average `time_taken_sec` per topic
   - Weak areas: topics with mastery % below a threshold (e.g. <60%)
2. Decide compute strategy per the system design doc: **pre-compute nightly, serve from cache (Redis)** rather than computing live on every dashboard load — this is what hits the "<2s dashboard load" NFR
3. Build `/analytics/summary` and `/analytics/heatmap` endpoints reading from the cached/pre-aggregated tables
4. **Frontend charts** — use `recharts` or `chart.js`:
   - Line chart: score over time
   - Bar chart: mastery % per topic
   - Heatmap grid: topic × week, colored by mastery
5. **PDF export** — `GET /reports/export` generates a PDF summary of quiz results (use `reportlab` or `weasyprint` on the backend)

### Definition of Done
- Dashboard loads in under 2 seconds with realistic seeded data (seed ~200 attempts across multiple topics/days for testing)
- Heatmap visually distinguishes strong vs weak topics
- Exported PDF report opens correctly and reflects real attempt data

---

## Week 6 — Testing, Hardening, Documentation, Demo

**Goal:** Everything the evaluation criteria explicitly reward: tests, docs, polish, presentation.

### Tasks
1. **Testing**
   - Unit tests: SM-2 function, chunking function, JSON parsing/validation for LLM output, JWT validation
   - Integration tests: upload → ingest → generate quiz → answer → check schedule updated (full pipeline test)
   - Aim for meaningful coverage on `services/` (ingestion, rag, scheduler) — these are the highest-risk modules
   - Write a short **Testing Report** (what's covered, what isn't, known limitations)
2. **Accessibility pass** — check WCAG 2.1 AA basics: color contrast, alt text on charts/icons, keyboard navigation, form labels
3. **Error handling pass** — graceful failure for: malformed PDF upload, LLM API timeout/failure (retry + fallback message), expired JWT, empty quiz generation (no chunks found for topic)
4. **Documentation**
   - Finalize README: setup instructions, architecture diagram, API docs (auto-generate with FastAPI's OpenAPI/Swagger, link it)
   - Deployment guide: `docker compose up` instructions, environment variable reference, and one path to a live deploy (Render/AWS)
5. **Sample dataset** — confirm 5+ syllabus PDFs are in `/sample_data` and documented (subject, size, what to expect when uploaded)
6. **Demo video (5 min)** — suggested structure:
   - 0:00–0:30 — problem statement, one sentence
   - 0:30–2:00 — upload a syllabus, show ingestion status change
   - 2:00–3:30 — generate and take a quiz, show explanation/feedback
   - 3:30–4:30 — dashboard walkthrough: trends, heatmap, due reviews
   - 4:30–5:00 — architecture diagram, close
7. **Bonus features (only if time remains, in this priority order)**:
   1. Multi-language support (highest reuse of existing pipeline — just change prompt language)
   2. Collaborative study rooms (shared flashcard decks)
   3. Voice-based Q&A (Web Speech API on frontend, no backend change needed for STT)
   4. LMS integration (Moodle/Canvas API — highest effort, lowest expected marks return, do last if at all)

### Definition of Done
- `docker compose up` on a clean machine produces a fully working app with no manual steps beyond `.env` setup
- Test suite runs green in CI (GitHub Actions workflow recommended, even a minimal one)
- README + deployment guide are complete enough that someone unfamiliar with the project could run it
- Demo video recorded and under 5 minutes

---

## Risk Notes (read this before Week 2)

- **Biggest risk: ingestion + RAG quality (Weeks 2–3).** If PDF text extraction is messy (scanned PDFs, weird layouts), question quality collapses downstream. Test with real, varied syllabus PDFs early — don't build against one clean sample.
- **LLM cost/rate limits**: budget for this if using OpenAI; cache generated questions so re-requesting the same topic doesn't always trigger a new paid API call.
- **Don't over-build the scheduler worker** — a real-time notification system is not required by the spec ("triggering spaced repetition notifications" can be satisfied by a background job that logs/flags due reviews; a full push-notification system is scope creep).
- **Short-answer grading is a trap** — exact-match grading will frustrate users, full NLP grading is a research problem. Semantic similarity threshold (cosine similarity between embeddings of user answer and model answer) is a reasonable, defensible v1 solution — document this tradeoff rather than trying to solve it perfectly.

---

## Mapping to Evaluation Criteria

| Criterion | Where it's earned in this plan |

| Functionality (35) | Weeks 2–5 (ingestion, generation, scheduling, dashboard) |
| Code Quality (20) | Consistent structure from Week 1 skeleton + tests in Week 6 |
| Documentation (20) | ADRs (Week 1), README/API docs/deployment guide (Week 6) |
| Innovation (15) | RAG quality (Week 3), adaptive difficulty, heatmap design (Week 5) |
| Presentation (10) | Demo video + architecture diagram (Week 6) |
