"""Add composite indexes for analytics hot paths.

Revision ID: 20261113_0002
Revises: 20261113_0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261113_0002"
down_revision = "20261113_0001"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_test_attempts_user_test_finished", "test_attempts", ["user_id", "test_id", "finished_at"]),
    ("ix_test_attempts_user_finished", "test_attempts", ["user_id", "finished_at"]),
    (
        "ix_lesson_progress_user_completed_lesson",
        "lesson_progress",
        ["user_id", "is_completed", "lesson_id"],
    ),
    (
        "ix_student_module_metrics_module_risk",
        "student_module_metrics",
        ["module_id", "risk_level"],
    ),
    (
        "ix_student_module_metrics_module_weakness",
        "student_module_metrics",
        ["module_id", "weakness_level"],
    ),
    ("ix_learning_events_outbox", "learning_events", ["published_at", "id"]),
)


def upgrade() -> None:
    connection = op.get_bind()
    learning_event_columns = {
        item["name"] for item in inspect(connection).get_columns("learning_events")
    }
    if "published_at" not in learning_event_columns:
        op.add_column(
            "learning_events",
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        )
    for index_name, table_name, columns in INDEXES:
        existing = {item["name"] for item in inspect(connection).get_indexes(table_name)}
        if index_name not in existing:
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    for index_name, table_name, _ in reversed(INDEXES):
        existing = {item["name"] for item in inspect(connection).get_indexes(table_name)}
        if index_name in existing:
            op.drop_index(index_name, table_name=table_name)
