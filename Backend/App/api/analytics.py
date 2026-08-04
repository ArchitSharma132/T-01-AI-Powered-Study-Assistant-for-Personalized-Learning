import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.question import Question
from app.models.topic import Topic

router = APIRouter(prefix="/analytics", tags=["analytics"])

TEMP_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    total = await db.execute(
        select(func.count()).where(Attempt.user_id == TEMP_USER_ID)
    )
    correct = await db.execute(
        select(func.count()).where(Attempt.user_id == TEMP_USER_ID, Attempt.is_correct == True)
    )
    avg_time = await db.execute(
        select(func.avg(Attempt.time_taken_sec)).where(Attempt.user_id == TEMP_USER_ID)
    )
    t = total.scalar() or 0
    c = correct.scalar() or 0
    return {
        "total_attempts": t,
        "correct_attempts": c,
        "accuracy": round(c / t * 100, 1) if t else 0,
        "avg_time_sec": round(avg_time.scalar() or 0, 1),
    }


@router.get("/score-trend")
async def get_score_trend(days: int = 30, db: AsyncSession = Depends(get_db)):
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            cast(Attempt.attempted_at, Date).label("day"),
            func.count().label("total"),
            func.sum(case((Attempt.is_correct == True, 1), else_=0)).label("correct"),
        )
        .where(Attempt.user_id == TEMP_USER_ID, cast(Attempt.attempted_at, Date) >= since)
        .group_by(cast(Attempt.attempted_at, Date))
        .order_by(cast(Attempt.attempted_at, Date))
    )
    return [
        {"date": str(row.day), "total": row.total, "correct": row.correct,
         "accuracy": round(row.correct / row.total * 100, 1) if row.total else 0}
        for row in result.all()
    ]


@router.get("/topic-mastery")
async def get_topic_mastery(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Topic.name,
            func.count().label("total"),
            func.sum(case((Attempt.is_correct == True, 1), else_=0)).label("correct"),
            func.avg(Attempt.time_taken_sec).label("avg_time"),
        )
        .join(Question, Question.topic_id == Topic.id)
        .join(Attempt, Attempt.question_id == Question.id)
        .where(Attempt.user_id == TEMP_USER_ID)
        .group_by(Topic.name)
        .order_by(Topic.name)
    )
    return [
        {"topic": row.name, "total": row.total, "correct": row.correct,
         "mastery": round(row.correct / row.total * 100, 1) if row.total else 0,
         "avg_time_sec": round(row.avg_time or 0, 1)}
        for row in result.all()
    ]


@router.get("/heatmap")
async def get_heatmap(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Topic.name,
            cast(Attempt.attempted_at, Date).label("day"),
            func.count().label("total"),
            func.sum(case((Attempt.is_correct == True, 1), else_=0)).label("correct"),
        )
        .join(Question, Question.topic_id == Topic.id)
        .join(Attempt, Attempt.question_id == Question.id)
        .where(Attempt.user_id == TEMP_USER_ID)
        .group_by(Topic.name, cast(Attempt.attempted_at, Date))
        .order_by(cast(Attempt.attempted_at, Date))
    )
    return [
        {"topic": row.name, "date": str(row.day), "total": row.total, "correct": row.correct,
         "mastery": round(row.correct / row.total * 100, 1) if row.total else 0}
        for row in result.all()
    ]
