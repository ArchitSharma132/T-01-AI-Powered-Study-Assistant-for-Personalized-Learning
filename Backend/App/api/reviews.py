import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.review_schedule import ReviewSchedule
from app.models.question import Question

router = APIRouter(prefix="/reviews", tags=["reviews"])

TEMP_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/due")
async def get_due_reviews(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReviewSchedule, Question)
        .join(Question, ReviewSchedule.question_id == Question.id)
        .where(
            ReviewSchedule.user_id == TEMP_USER_ID,
            ReviewSchedule.next_review_date <= date.today(),
        )
        .order_by(ReviewSchedule.next_review_date.asc())
        .limit(limit)
    )
    rows = result.all()
    items = []
    for sched, question in rows:
        items.append({
            "schedule_id": str(sched.id),
            "question_id": str(question.id),
            "question_text": question.question_text,
            "question_type": question.type.value if hasattr(question.type, "value") else question.type,
            "options": question.options,
            "difficulty": question.difficulty.value if hasattr(question.difficulty, "value") else question.difficulty,
            "ease_factor": sched.ease_factor,
            "interval_days": sched.interval_days,
            "next_review_date": str(sched.next_review_date),
            "repetitions": sched.repetitions,
        })
    return {"count": len(items), "reviews": items}


@router.get("/stats")
async def get_review_stats(db: AsyncSession = Depends(get_db)):
    today = date.today()
    week_end = today + __import__("datetime").timedelta(days=7)

    due_today = await db.execute(
        select(func.count()).where(
            ReviewSchedule.user_id == TEMP_USER_ID,
            ReviewSchedule.next_review_date <= today,
        )
    )
    due_week = await db.execute(
        select(func.count()).where(
            ReviewSchedule.user_id == TEMP_USER_ID,
            ReviewSchedule.next_review_date <= week_end,
        )
    )
    total = await db.execute(
        select(func.count()).where(ReviewSchedule.user_id == TEMP_USER_ID)
    )
    avg_ef = await db.execute(
        select(func.avg(ReviewSchedule.ease_factor)).where(ReviewSchedule.user_id == TEMP_USER_ID)
    )

    return {
        "due_today": due_today.scalar() or 0,
        "due_this_week": due_week.scalar() or 0,
        "total_reviewed": total.scalar() or 0,
        "average_ease_factor": round(avg_ef.scalar() or 2.5, 2),
    }
