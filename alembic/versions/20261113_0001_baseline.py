"""Baseline the transactional schema and analytics read model.

Revision ID: 20261113_0001
Revises:
"""
from alembic import op

from backend.db import Base
import backend.models  # noqa: F401

revision = "20261113_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # checkfirst keeps this baseline compatible with databases created by the
    # pre-Alembic bootstrap while creating the full schema for clean installs.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
