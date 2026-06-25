# T-01: AI-Powered Study Assistant for Personalized Learning

## Domain
**AI/ML · EdTech**

## Problem Statement
Students struggle with generic study materials that don't adapt to individual knowledge gaps, learning pace, or exam patterns. Existing tools are either too broad or lack university-specific context, leading to inefficient preparation.

## Project Objectives
1. Build an AI assistant that generates personalized quizzes based on syllabus topics
2. Implement spaced repetition scheduling for revision reminders
3. Track student progress and identify weak areas with heatmaps
4. Support multi-format input: PDF notes, text, and topic keywords
5. Provide concept explanations with difficulty-scaled depth
6. Integrate a performance analytics dashboard

## Functional Requirements
- Upload syllabus/notes in PDF or text format
- Auto-generate MCQs, short-answer, and true/false questions
- Adaptive difficulty adjustment based on historical performance
- Spaced repetition algorithm (SM-2 or Leitner system)
- Dashboard: score trends, topic mastery %, time-per-topic
- User authentication and session persistence
- Export quiz results as PDF report

## Non-Functional Requirements
| Attribute | Requirement |
| :--- | :--- |
| Performance | Quiz generation < 3s; dashboard load < 2s |
| Scalability | Support 500 concurrent users |
| Security | JWT auth; encrypted user data |
| Reliability | 99% uptime; graceful error handling |
| Accessibility | WCAG 2.1 AA compliant UI |

## Suggested Technical Stack
| Layer | Option |
| :--- | :--- |
| Frontend | React.js + TailwindCSS |
| Backend | FastAPI (Python) |
| AI/NLP | OpenAI API / Hugging Face transformers |
| Database | PostgreSQL + Redis (caching) |
| Cloud | AWS EC2 / Render |
| Optional | LangChain for RAG pipeline |

## System Design Requirements
- **Architecture**: Three-tier (Frontend → REST API → AI Engine + DB). The NLP module processes uploaded documents through a chunking pipeline, embeds content into a vector store (FAISS or Pinecone), and retrieves relevant context for question generation via RAG. The scheduler service runs as a background worker triggering spaced repetition notifications. Analytics are pre-computed nightly and served via cached API endpoints.
- **Main Modules**: Document Ingestion, Question Generation Engine, Spaced Repetition Scheduler, User Progress Tracker, Analytics Dashboard, Auth Service.
- **Data Flow**: Upload → Chunk + Embed → Store in Vector DB → Query on demand → LLM generates questions → Results stored → Analytics updated.

## Expected Deliverables
- [ ] Source code (GitHub, well-structured)
- [ ] README with setup and architecture overview
- [ ] Deployment guide (Docker Compose preferred)
- [ ] Sample dataset (5+ syllabus PDFs tested)
- [ ] Testing report (unit + integration)
- [ ] 5-minute demo video

## Milestones & Timeline
| Week | Goal |
| :--- | :--- |
| 1 | Requirements finalization, tech stack setup, DB schema design |
| 2 | Document ingestion pipeline + vector embedding |
| 3 | Question generation engine (MCQ + short-answer) |
| 4 | Spaced repetition scheduler + user auth |
| 5 | Analytics dashboard (frontend + API) |
| 6 | Testing, bug fixes, documentation, demo |

## Evaluation Criteria
| Criterion | Marks |
| :--- | :--- |
| Functionality (quiz gen, scheduling, dashboard) | 35 |
| Code Quality (structure, comments, tests) | 20 |
| Documentation (README, architecture, API docs) | 20 |
| Innovation (adaptive difficulty, RAG quality) | 15 |
| Presentation | 10 |

## Bonus Features
- Voice-based Q&A using Web Speech API
- Collaborative study rooms (shared flashcard decks)
- Integration with university LMS (Moodle/Canvas API)
- Multi-language support for regional students
