"""Add the pending analytics event processing index.

Revision ID: 20261114_0003
Revises: 20261113_0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261114_0003"
down_revision = "20261113_0002"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_learning_events_processing"


def upgrade() -> None:
    connection = op.get_bind()
    existing = {item["name"] for item in inspect(connection).get_indexes("learning_events")}
    if INDEX_NAME not in existing:
        op.create_index(
            INDEX_NAME,
            "learning_events",
            ["processed_at", "id"],
            unique=False,
            postgresql_where=sa.text("processed_at IS NULL"),
        )


def downgrade() -> None:
    connection = op.get_bind()
    existing = {item["name"] for item in inspect(connection).get_indexes("learning_events")}
    if INDEX_NAME in existing:
        op.drop_index(INDEX_NAME, table_name="learning_events")
