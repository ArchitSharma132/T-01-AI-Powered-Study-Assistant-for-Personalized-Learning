import uuid
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.topic import Topic
from app.models.question import Question, QuestionType, Difficulty
from app.models.attempt import Attempt
from app.models.review_schedule import ReviewSchedule
from app.schemas.question import (
    QuestionGenerateRequest, QuizResponse, QuestionOut, AnswerSubmit, AnswerResult,
)
from app.services.rag import retrieve_context
from app.services.prompts import build_mcq_prompt, build_tf_prompt, build_short_prompt
from app.services.llm import call_ollama
from app.services.parser import parse_mcq, parse_tf, parse_short
from app.services.grading import grade_mcq, grade_tf, grade_short
from app.services.scheduler import sm2

router = APIRouter(prefix="/quiz", tags=["quiz"])

TEMP_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/topics/{document_id}")
async def list_topics(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic).where(Topic.document_id == document_id))
    topics = result.scalars().all()
    return [{"id": str(t.id), "name": t.name} for t in topics]


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(req: QuestionGenerateRequest, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, req.topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")

    qtype = getattr(req, "type", "mcq") or "mcq"

    existing = await db.execute(
        select(Question).where(
            Question.topic_id == topic.id,
            Question.type == qtype,
        ).limit(req.count)
    )
    cached = existing.scalars().all()
    if len(cached) >= req.count:
        return QuizResponse(
            topic=topic.name,
            questions=[QuestionOut.model_validate(q) for q in cached[:req.count]],
        )

    ctx = await retrieve_context(topic.name, db, top_k=5, document_id=str(topic.document_id))
    if not ctx:
        raise HTTPException(404, "No context found for this topic")

    context_text = "\n\n".join(c["chunk_text"] for c in ctx)

    if qtype == "tf":
        prompt = build_tf_prompt(context_text, req.count, req.difficulty)
    elif qtype == "short":
        prompt = build_short_prompt(context_text, req.count, req.difficulty)
    else:
        prompt = build_mcq_prompt(context_text, req.count, req.difficulty)

    try:
        raw = await call_ollama(prompt)
    except Exception:
        raise HTTPException(503, "LLM service unavailable")

    questions = []
    if qtype == "tf":
        parsed = parse_tf(raw)
        for p in parsed[:req.count]:
            q = Question(
                topic_id=topic.id, type=QuestionType.TF,
                question_text=p.question, options=None,
                correct_answer=str(p.correct), difficulty=Difficulty(p.difficulty),
            )
            db.add(q)
            await db.flush()
            questions.append(q)
    elif qtype == "short":
        parsed = parse_short(raw)
        for p in parsed[:req.count]:
            q = Question(
                topic_id=topic.id, type=QuestionType.SHORT,
                question_text=p.question,
                options={"model_answer": p.model_answer, "key_terms": p.key_terms},
                correct_answer=p.model_answer, difficulty=Difficulty(p.difficulty),
            )
            db.add(q)
            await db.flush()
            questions.append(q)
    else:
        parsed = parse_mcq(raw)
        for p in parsed[:req.count]:
            q = Question(
                topic_id=topic.id, type=QuestionType.MCQ,
                question_text=p.question, options=p.options,
                correct_answer=p.correct, difficulty=Difficulty(p.difficulty),
            )
            db.add(q)
            await db.flush()
            questions.append(q)

    await db.commit()

    if not questions:
        raise HTTPException(500, "Failed to generate questions")

    return QuizResponse(
        topic=topic.name,
        questions=[QuestionOut.model_validate(q) for q in questions],
    )


@router.post("/answer", response_model=AnswerResult)
async def submit_answer(answer: AnswerSubmit, db: AsyncSession = Depends(get_db)):
    question = await db.get(Question, answer.question_id)
    if not question:
        raise HTTPException(404, "Question not found")

    if question.type == QuestionType.TF:
        is_correct = grade_tf(answer.selected_answer, question.correct_answer.lower() == "true")
        explanation = None
    elif question.type == QuestionType.SHORT:
        key_terms = question.options.get("key_terms", []) if question.options else []
        is_correct, _ = await grade_short(answer.selected_answer, question.correct_answer, key_terms)
        explanation = f"Model answer: {question.correct_answer}"
    else:
        is_correct = grade_mcq(answer.selected_answer, question.correct_answer)
        explanation = None

    attempt = Attempt(
        user_id=TEMP_USER_ID,
        question_id=question.id,
        is_correct=is_correct,
        time_taken_sec=answer.time_taken_sec,
    )
    db.add(attempt)

    schedule = await db.execute(
        select(ReviewSchedule).where(
            ReviewSchedule.user_id == TEMP_USER_ID,
            ReviewSchedule.question_id == question.id,
        )
    )
    sched = schedule.scalar_one_or_none()
    if not sched:
        sched = ReviewSchedule(
            user_id=TEMP_USER_ID, question_id=question.id,
            ease_factor=2.5, interval_days=0, repetitions=0,
            next_review_date=date.today(),
        )
        db.add(sched)
        await db.flush()

    if is_correct and answer.time_taken_sec <= 30:
        quality = 5
    elif is_correct:
        quality = 3
    else:
        quality = 1

    new_interval, new_ef, new_reps = sm2(quality, sched.repetitions, sched.ease_factor, sched.interval_days)
    sched.interval_days = new_interval
    sched.ease_factor = new_ef
    sched.repetitions = new_reps
    sched.next_review_date = date.today() + timedelta(days=new_interval)

    await db.commit()

    return AnswerResult(
        is_correct=is_correct,
        correct_answer=question.correct_answer,
        explanation=explanation,
    )
