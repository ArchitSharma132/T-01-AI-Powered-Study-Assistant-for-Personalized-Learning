"""initial_schema

Revision ID: 873d0d6f4677
Revises:
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "873d0d6f4677"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("upload_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.Enum("uploading", "processing", "ready", "failed", name="documentstatus"), nullable=False),
        sa.Column("raw_text_path", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(255)),
        sa.Column("topic_tag", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("topic_id", sa.Uuid(), sa.ForeignKey("topics.id"), nullable=False, index=True),
        sa.Column("type", sa.Enum("mcq", "short", "tf", name="questiontype"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSON()),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Enum("easy", "medium", "hard", name="difficulty"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False, index=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("time_taken_sec", sa.Float(), default=0.0),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "review_schedule",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id"), nullable=False, index=True),
        sa.Column("ease_factor", sa.Float(), default=2.5),
        sa.Column("interval_days", sa.Integer(), default=1),
        sa.Column("next_review_date", sa.Date(), nullable=False),
        sa.Column("repetitions", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("jwt_id", sa.String(255), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("review_schedule")
    op.drop_table("attempts")
    op.drop_table("questions")
    op.drop_table("topics")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS questiontype")
    op.execute("DROP TYPE IF EXISTS difficulty")
