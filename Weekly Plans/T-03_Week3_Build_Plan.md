# Week 3 -- Question Generation Engine (RAG): Build Plan

Goal: Given a topic from an uploaded document, retrieve relevant chunks via FAISS and use the local LLM (Ollama/qwen2.5) to generate grounded MCQ, True/False, and Short-Answer questions. Build the quiz-taking UI.

---

## Overview

| Part | Focus | Dependencies | Est. Hours |

| 1 | RAG retrieval service | Week 2 (FAISS + embeddings) | 2-3 hrs |
| 2 | Prompt templates for question generation | Part 1 | 2-3 hrs |
| 3 | LLM service (Ollama integration) | Part 2 | 2-3 hrs |
| 4 | Response parsing + validation | Part 3 | 2 hrs |
| 5 | Quiz generation API endpoint | Parts 1-4 | 2-3 hrs |
| 6 | Answer submission + grading endpoint | Part 5 | 2 hrs |
| 7 | Question caching layer | Part 5 | 1-2 hrs |
| 8 | Frontend: quiz-taking UI | Part 5 | 4-5 hrs |
| 9 | Difficulty scaling + quality tuning | All | 2-3 hrs |
| | **Total** | | **~19-25 hrs** |

---

## Part 1 -- RAG Retrieval Service

### Files to create

| File | Purpose |

| `backend/app/services/rag.py` | `retrieve_context(query, top_k, document_id?) -> list[ChunkResult]` |

### Logic

```
1. Embed the query using Ollama (nomic-embed-text)
2. Search FAISS index for top-k nearest neighbors
3. Map FAISS indices back to chunk_ids via the metadata store
4. Fetch chunk texts from the chunks table
5. Optionally filter by document_id or topic_id
6. Return ordered list of (chunk_text, similarity_score, topic_tag)
```

### Parameters

| Param | Default | Rationale |

| `top_k` | 5 | Enough context without overwhelming the LLM prompt |
| `score_threshold` | 0.3 | Discard irrelevant chunks below this similarity |
| `document_id` | None | Optional -- scope retrieval to a single document |

### Data structure

```python
class ChunkResult:
    chunk_id: uuid.UUID
    chunk_text: str
    topic_tag: str | None
    score: float
```

### Done when
- Query "explain process scheduling" against an OS syllabus returns chunks about scheduling
- Query "SQL normalization" returns chunks about database normal forms
- Results are ordered by relevance score

---

## Part 2 -- Prompt Templates

### Files to create

| File | Purpose |

| `backend/app/services/prompts.py` | Prompt templates for each question type |

### Template: MCQ

```
You are a quiz generator for students. Generate exactly {count} multiple-choice questions based ONLY on the provided context. Do not use any information outside the context.

Context:
{context}

Requirements:
- Each question must have exactly 4 options labeled A, B, C, D
- Exactly one option must be correct
- Include a brief explanation for the correct answer
- Difficulty level: {difficulty}

Return a JSON array with this exact structure:
[
  {
    "question": "...",
    "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct": "A",
    "explanation": "...",
    "difficulty": "easy|medium|hard"
  }
]

Return ONLY the JSON array, no other text.
```

### Template: True/False

```
Generate exactly {count} true/false statements based ONLY on the provided context.

Context:
{context}

Return a JSON array:
[
  {
    "question": "Statement text here",
    "correct": true,
    "explanation": "...",
    "difficulty": "easy|medium|hard"
  }
]

Return ONLY the JSON array, no other text.
```

### Template: Short Answer

```
Generate exactly {count} short-answer questions based ONLY on the provided context.

Context:
{context}

Return a JSON array:
[
  {
    "question": "...",
    "model_answer": "Expected answer in 1-3 sentences",
    "key_terms": ["term1", "term2"],
    "difficulty": "easy|medium|hard"
  }
]

Return ONLY the JSON array, no other text.
```

### Design decisions
- Explicit "ONLY on the provided context" instruction reduces hallucination
- "Return ONLY the JSON" reduces preamble/explanation that breaks parsing
- Key terms for short-answer enable simple keyword-based grading in v1
- Difficulty passed as a prompt parameter, not inferred post-hoc

### Done when
- Templates are callable functions: `build_mcq_prompt(context, count, difficulty) -> str`
- Each returns a well-formed prompt string ready for LLM consumption

---

## Part 3 -- LLM Service (Ollama Integration)

### Files to create

| File | Purpose |

| `backend/app/services/llm.py` | `generate_questions_raw(prompt) -> str` |

### Implementation

Call Ollama's `/api/generate` endpoint:

```python
async def call_ollama(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_CHAT_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 4096,
                }
            }
        )
        return response.json()["response"]
```

### LLM parameters

| Param | Value | Why |

| `temperature` | 0.7 | Balanced creativity -- not too random, not too deterministic |
| `num_predict` | 4096 | Enough tokens for 5-10 questions in JSON format |
| `timeout` | 60s | Local LLM can be slow on first load |
| `stream` | False | Simpler parsing; streaming not needed for quiz gen |

### Error handling

| Error | Response |

| Ollama not running | Return 503 with "LLM service unavailable" |
| Timeout (>60s) | Retry once with reduced `num_predict`, then 504 |
| Invalid JSON in response | Retry once, then return partial results or error |
| Empty response | Return 500 with "LLM returned empty response" |

### Done when
- `call_ollama("Say hello")` returns a string response
- Function handles timeout and connection errors gracefully
- Logs LLM call duration for performance tracking

---

## Part 4 -- Response Parsing + Validation

### Files to create

| File | Purpose |

| `backend/app/services/parser.py` | Parse raw LLM output into validated Pydantic models |

### Parsing strategy

```
1. Strip any markdown code fences (```json ... ```)
2. Find the first [ and last ] to extract the JSON array
3. json.loads() the extracted string
4. Validate each item against a Pydantic schema
5. Discard malformed items, keep valid ones
6. If zero valid items, trigger a retry with the LLM
```

### Pydantic validation schemas

```python
class MCQGenerated(BaseModel):
    question: str
    options: dict[str, str]    # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct: str               # "A", "B", "C", or "D"
    explanation: str
    difficulty: str

class TFGenerated(BaseModel):
    question: str
    correct: bool
    explanation: str
    difficulty: str

class ShortAnswerGenerated(BaseModel):
    question: str
    model_answer: str
    key_terms: list[str]
    difficulty: str
```

### Validation rules

| Check | Action on failure |

| `correct` not in `options` keys | Discard question |
| `options` has != 4 entries (MCQ) | Discard question |
| `difficulty` not in [easy, medium, hard] | Default to "medium" |
| `question` is empty | Discard question |
| Duplicate question text | Keep first, discard rest |

### Done when
- Clean JSON from LLM parses into validated models
- Messy JSON (extra text, markdown fences) still parses correctly
- Malformed items are discarded without crashing
- Unit tests cover 5+ edge cases (empty response, partial JSON, missing fields)

---

## Part 5 -- Quiz Generation API Endpoint

### API

| Method | Path | Request | Response |

| POST | `/quiz/generate` | `QuestionGenerateRequest` | `QuizResponse` |
| GET | `/quiz/topics/{document_id}` | -- | list of available topics |

### Request schema (already exists in `schemas/question.py`)

```python
class QuestionGenerateRequest(BaseModel):
    topic_id: uuid.UUID
    count: int = 5           # number of questions
    difficulty: str | None   # easy, medium, hard, or None for mixed
    type: str = "mcq"        # mcq, tf, short
```

### Endpoint logic

```
1. Look up topic -> get document_id
2. Build a search query from the topic name
3. Retrieve context chunks via RAG (Part 1)
4. Build prompt from template (Part 2)
5. Call LLM (Part 3)
6. Parse + validate response (Part 4)
7. Store valid questions in the questions table
8. Return QuizResponse with generated questions
```

### Files to create/modify

| File | Action |

| `backend/app/api/quiz.py` | New -- quiz generation + topic listing endpoints |
| `backend/app/api/router.py` | Add quiz router |
| `backend/app/schemas/question.py` | Add `type` field to `QuestionGenerateRequest` |

### Performance target
- Under 3 seconds per request (NFR from build plan)
- If too slow: reduce `top_k` to 3, reduce `count` to 3, cache retrieval results

### Done when
- `POST /quiz/generate` with a real topic returns 5 well-formed MCQs
- Questions reference content from the uploaded document, not hallucinated facts
- Questions stored in the `questions` table linked to `topic_id`
- `GET /quiz/topics/{document_id}` returns topics for a given document

---

## Part 6 -- Answer Submission + Grading

### API

| Method | Path | Request | Response |

| POST | `/quiz/answer` | `AnswerSubmit` | `AnswerResult` |
| POST | `/quiz/submit-batch` | list of `AnswerSubmit` | list of `AnswerResult` |

### Grading logic by question type

| Type | Grading method |

| MCQ | Exact match: `selected_answer == correct_answer` |
| True/False | Exact match: `selected_answer == str(correct)` |
| Short Answer | Keyword match + cosine similarity (see below) |

### Short-answer grading (v1 approach)

```
1. Tokenize user answer and model_answer into words
2. Check what fraction of key_terms appear in the user answer
3. Embed both answers using Ollama
4. Compute cosine similarity between embeddings
5. Score = 0.4 * keyword_match_ratio + 0.6 * cosine_similarity
6. Correct if score >= 0.6
```

This is a documented, defensible v1 tradeoff. Not perfect, but avoids the NLP research rabbit hole.

### Files to create/modify

| File | Action |

| `backend/app/api/quiz.py` | Add answer submission endpoints |
| `backend/app/services/grading.py` | New -- grading logic per question type |

### On answer submission
1. Grade the answer
2. Create an `attempts` row
3. Return `AnswerResult` with `is_correct`, `correct_answer`, `explanation`
4. (Week 4 will add SM-2 scheduling here)

### Done when
- Submit an MCQ answer, get correct/incorrect feedback
- Submit a T/F answer, get correct/incorrect feedback
- Submit a short answer, get a score-based correct/incorrect with the model answer shown
- All attempts recorded in the `attempts` table

---

## Part 7 -- Question Caching Layer

### Purpose
Avoid calling the LLM for the same topic + difficulty + type combination repeatedly. Saves time and compute.

### Strategy

```
1. Before calling the LLM, check if we already have enough unused questions
   for this topic + difficulty + type in the questions table
2. If yes, return those directly (mark as "served")
3. If no, generate new ones via LLM, store them, return them
```

### Cache invalidation
- When a new document is uploaded and processed, existing questions for that document's topics remain valid
- Questions are never deleted, only new ones are added
- A `served_count` column on questions can track how many times each was used (optional, useful for analytics)

### Files to create

| File | Action |

| `backend/app/services/quiz_cache.py` | New -- cache check + generation orchestration |

### Done when
- First request for a topic generates and stores questions
- Second request for the same topic returns stored questions without calling the LLM
- Different difficulty or type for the same topic triggers a new LLM call

---

## Part 8 -- Frontend: Quiz-Taking UI

### Files to modify/create

| File | Action |

| `frontend/src/pages/QuizPage.jsx` | Full rewrite -- quiz configuration + taking UI |
| `frontend/src/components/QuestionCard.jsx` | New -- renders a single question |
| `frontend/src/components/QuizResults.jsx` | New -- shows results after quiz completion |

### UI flow

```
[Select Document] -> [Select Topic] -> [Choose Count + Difficulty + Type]
     -> [Generate] -> [Question 1/5] -> [Question 2/5] -> ... -> [Results]
```

### QuizPage states

| State | What's shown |

| `configure` | Dropdowns for document, topic, count, difficulty, type |
| `loading` | "Generating questions..." with a spinner |
| `active` | Current question card with options/input, progress bar |
| `reviewing` | Single question result (correct/incorrect + explanation) |
| `complete` | Full quiz results summary |

### QuestionCard component

**MCQ layout:**
```
Question text here?

[ ] A. Option one
[ ] B. Option two
[ ] C. Option three
[ ] D. Option four

          [Submit]
```

**True/False layout:**
```
Statement text here.

[True]    [False]
```

**Short Answer layout:**
```
Question text here?

[Text input area        ]

          [Submit]
```

### QuizResults component

```
Quiz Complete

Score: 4/5 (80%)

1. [correct]   What is process scheduling?
2. [correct]   Define virtual memory.
3. [incorrect] Which algorithm is used for...
4. [correct]   True or False: A semaphore...
5. [correct]   Explain deadlock prevention.

[Retake Quiz]  [New Quiz]  [Back to Dashboard]
```

### API calls needed

| Action | Endpoint |

| List documents | `GET /documents` |
| List topics for document | `GET /quiz/topics/{document_id}` |
| Generate quiz | `POST /quiz/generate` |
| Submit answer | `POST /quiz/answer` |

### Done when
- Can select a topic and generate a quiz from the UI
- Can answer each question type (MCQ click, T/F click, short-answer type)
- Immediate feedback shown after each answer (correct/incorrect + explanation)
- Results summary shown at the end with score
- All interactions feel responsive (loading states, transitions)

---

## Part 9 -- Difficulty Scaling + Quality Tuning

### Difficulty via prompt

The prompt already includes a `{difficulty}` variable. Tune the prompt wording per level:

| Difficulty | Prompt instruction |

| Easy | "Focus on definitions, basic recall, and straightforward facts" |
| Medium | "Test understanding, application, and connections between concepts" |
| Hard | "Require analysis, comparison, edge cases, and deeper reasoning" |

### Quality checks to run

| Check | Fix |

| Questions too generic / not grounded | Add more context chunks (increase top_k to 7) |
| Questions repeat each other | Add dedup in parser (Part 4) |
| Wrong answers marked correct | Verify JSON parsing maps correct option properly |
| LLM ignores difficulty instruction | Make difficulty instruction more explicit, add examples |
| Short-answer grading too strict/loose | Tune the 0.6 threshold up or down |

### Performance tuning

| If this happens... | Do this |

| Generation > 3 seconds | Reduce top_k to 3, reduce count to 3 |
| LLM frequently returns bad JSON | Add a retry with "Please fix the JSON" appended |
| FAISS search is slow | Check index size, consider IndexIVFFlat for large indexes |

### Done when
- Easy questions are noticeably simpler than hard questions
- Quality is acceptable across 3+ different subjects
- Generation consistently completes under 3 seconds

---

## Dependency Graph

```
Week 2 (FAISS index + chunks in DB)
  |
Part 1 (RAG retrieval)
  |
Part 2 (prompt templates)
  |
Part 3 (Ollama LLM service)
  |
Part 4 (response parsing)                Part 8 (frontend quiz UI)
  |                                          |
Part 5 (quiz generation endpoint) ----------+
  |
Part 6 (answer submission + grading)
  |
Part 7 (caching layer)
  |
Part 9 (quality tuning)
```

Parts 2 and 3 can be developed in parallel.
Part 8 (frontend) can start once Part 5 endpoint is stubbed.

---

## Risk Notes

- **LLM JSON output is unreliable.** qwen2.5 is generally good at structured output but will occasionally produce invalid JSON, extra commentary, or markdown fences. The parser (Part 4) must be extremely defensive.
- **Short-answer grading is a known weak point.** Document the cosine similarity approach and its limitations as a deliberate v1 tradeoff. Do not spend more than 2 hours trying to perfect it.
- **Context window limits.** qwen2.5 (7B) has a ~32k token context window. 5 chunks of ~500 chars each plus the prompt template is well within limits, but monitor if you increase top_k.
- **First LLM call is slow.** Ollama loads the model into memory on first call (~5-15s). Subsequent calls are fast. Consider a warmup call on app startup.

---

## Files Created/Modified Summary

| File | Action | Part |

| `backend/app/services/rag.py` | New | 1 |
| `backend/app/services/prompts.py` | New | 2 |
| `backend/app/services/llm.py` | New | 3 |
| `backend/app/services/parser.py` | New | 4 |
| `backend/app/api/quiz.py` | New | 5, 6 |
| `backend/app/api/router.py` | Modified | 5 |
| `backend/app/schemas/question.py` | Modified | 5 |
| `backend/app/services/grading.py` | New | 6 |
| `backend/app/services/quiz_cache.py` | New | 7 |
| `frontend/src/pages/QuizPage.jsx` | Modified | 8 |
| `frontend/src/components/QuestionCard.jsx` | New | 8 |
| `frontend/src/components/QuizResults.jsx` | New | 8 |
| `backend/tests/test_rag.py` | New | 9 |
| `backend/tests/test_parser.py` | New | 9 |
