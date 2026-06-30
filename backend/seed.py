from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import hash_password
from backend.lesson_content import build_legacy_blocks, serialize_lesson_blocks
from backend.models import (
    AnswerOption,
    Course,
    CourseEnrollment,
    Lesson,
    LessonProgress,
    Module,
    Question,
    Recommendation,
    Task,
    Test,
    TestAttempt,
    TopicResult,
    User,
    UserAnswer,
    UserAnswerOptionSelection,
)

SEED_MODELS = {
    "users": User,
    "courses": Course,
    "course_enrollments": CourseEnrollment,
    "modules": Module,
    "lessons": Lesson,
    "lesson_progress": LessonProgress,
    "tasks": Task,
    "tests": Test,
    "questions": Question,
    "answer_options": AnswerOption,
    "recommendations": Recommendation,
    "test_attempts": TestAttempt,
    "user_answers": UserAnswer,
    "user_answer_option_selections": UserAnswerOptionSelection,
    "topic_results": TopicResult,
}

SEQUENCE_MODELS = [
    User,
    Course,
    CourseEnrollment,
    Module,
    Lesson,
    LessonProgress,
    Task,
    Test,
    Question,
    AnswerOption,
    Recommendation,
    TestAttempt,
    UserAnswer,
    TopicResult,
]

DATETIME_FIELDS = {
    "created_at",
    "updated_at",
    "completed_at",
    "started_at",
    "finished_at",
    "answered_at",
    "last_attempt_at",
}


def seed_database_if_empty(db: Session) -> bool:
    if not settings.seed_on_startup:
        return False
    if db.scalar(select(User.id).limit(1)) is not None:
        return False

    manifest_path = settings.seed_data_dir / "manifest.json"
    if not manifest_path.exists():
        return False

    manifest = _read_json(manifest_path)
    import_order = manifest.get("import_order", [])

    for filename in import_order:
        stem = Path(filename).stem
        model = SEED_MODELS.get(stem)
        if model is None:
            continue

        payload_path = settings.seed_data_dir / filename
        if not payload_path.exists():
            continue

        for row in _read_json(payload_path):
            db.add(model(**_prepare_payload(stem, row)))

    db.commit()
    _sync_postgres_sequences(db)
    return True


def bootstrap_database_if_empty(db: Session) -> bool:
    if db.scalar(select(User.id).limit(1)) is not None:
        return False

    sqlite_path = settings.migrate_sqlite_path
    if sqlite_path and sqlite_path.exists():
        import_sqlite_database(db, sqlite_path)
        return True

    return seed_database_if_empty(db)


def import_sqlite_database(db: Session, sqlite_path: Path) -> bool:
    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row

    try:
        available_tables = {
            row[0]
            for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for dataset_name, model in SEED_MODELS.items():
            if dataset_name not in available_tables:
                continue
            rows = source.execute(
                f"SELECT * FROM {dataset_name} ORDER BY ROWID"
            ).fetchall()
            for row in rows:
                db.add(model(**_prepare_payload(dataset_name, dict(row))))

        db.commit()
        _sync_postgres_sequences(db)
        return True
    finally:
        source.close()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_manifest_models() -> list[tuple[str, type]]:
    manifest_path = settings.seed_data_dir / "manifest.json"
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        import_order = manifest.get("import_order", [])
        models = []
        for filename in import_order:
            dataset_name = Path(filename).stem
            model = SEED_MODELS.get(dataset_name)
            if model is not None:
                models.append((dataset_name, model))
        if models:
            return models

    return list(SEED_MODELS.items())


def _prepare_payload(dataset_name: str, row: dict[str, Any]) -> dict[str, Any]:
    model = SEED_MODELS[dataset_name]
    allowed_columns = set(model.__table__.columns.keys())
    payload = {
        key: _normalize_value(key, value)
        for key, value in row.items()
        if key in allowed_columns
    }

    if dataset_name == "users" and "password_hash" not in payload:
        password = row.get("password")
        if password:
            payload["password_hash"] = hash_password(password)

    if dataset_name == "lessons":
        payload = _prepare_lesson_payload(payload, row)

    return payload


def _prepare_lesson_payload(
    payload: dict[str, Any],
    original_row: dict[str, Any],
) -> dict[str, Any]:
    content_blocks = payload.get("content_blocks")
    if isinstance(content_blocks, list):
        payload["content_blocks"] = json.dumps(
            content_blocks,
            ensure_ascii=False,
        )
    elif content_blocks in (None, ""):
        legacy_content = original_row.get("content")
        if legacy_content:
            payload["content_blocks"] = serialize_lesson_blocks(
                build_legacy_blocks(legacy_content)
            )
    return payload


def _normalize_value(field_name: str, value: Any) -> Any:
    if value is None:
        return None
    if field_name in DATETIME_FIELDS and isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return value


def _sync_postgres_sequences(db: Session) -> None:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    for model in SEQUENCE_MODELS:
        max_id = db.scalar(select(func.max(model.id)))
        db.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence(:table_name, 'id'),
                    :sequence_value,
                    :is_called
                )
                """
            ),
            {
                "table_name": model.__tablename__,
                "sequence_value": max_id or 1,
                "is_called": max_id is not None,
            },
        )

    db.commit()
