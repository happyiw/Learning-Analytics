from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from analytics.topic_result_service import TopicResultService, WeakTopicDetector
from backend.enums import UserRole
from backend.models import (
    CourseEnrollment,
    LearningEvent,
    Module,
    StudentModuleMetric,
    User,
)


def record_learning_event(
    db: Session,
    *,
    event_type: str,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> LearningEvent:
    event = LearningEvent(
        event_type=event_type,
        user_id=user_id,
        course_id=course_id,
        module_id=module_id,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=json.dumps(payload, ensure_ascii=False) if payload else None,
    )
    db.add(event)
    db.flush()
    return event


def refresh_student_module_metric(
    db: Session,
    user_id: int,
    module_id: int,
    *,
    event: LearningEvent | None = None,
) -> StudentModuleMetric | None:
    module = db.get(Module, module_id)
    if module is None:
        return None

    topic_service = TopicResultService(db)
    values = topic_service._calculate_topic_result_values(user_id, module_id)
    detector = WeakTopicDetector(db)

    metric = db.scalar(
        select(StudentModuleMetric).where(
            StudentModuleMetric.user_id == user_id,
            StudentModuleMetric.module_id == module_id,
        )
    )
    if metric is None:
        metric = StudentModuleMetric(user_id=user_id, module_id=module_id)
        db.add(metric)

    for field in (
        "attempts_count",
        "completed_attempts_count",
        "passed_attempts_count",
        "failed_attempts_count",
        "average_percentage",
        "best_percentage",
        "first_percentage",
        "last_percentage",
        "progress_delta",
        "trend",
        "stability_index",
        "completed_lessons_ratio",
        "weakness_level",
        "risk_level",
        "learning_state",
        "reason_code",
        "last_attempt_at",
    ):
        setattr(metric, field, values[field])

    metric.is_weak_topic = detector._is_weak_topic(values)
    metric.is_strong_topic = detector._is_strong_topic(values)
    metric.computed_at = datetime.now(timezone.utc)
    if event is not None:
        event.processed_at = metric.computed_at
    db.flush()
    return metric


def process_pending_learning_events(batch_size: int = 100) -> int:
    """Materialize a locked outbox batch outside the API request transaction."""
    from backend.db import SessionLocal

    with SessionLocal() as db:
        return process_pending_learning_events_in_session(db, batch_size)


def process_pending_learning_events_in_session(db: Session, batch_size: int = 100) -> int:
    events = list(
        db.scalars(
            select(LearningEvent)
            .where(
                LearningEvent.processed_at.is_(None),
                LearningEvent.module_id.is_not(None),
            )
            .order_by(LearningEvent.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    )
    if not events:
        return 0

    latest_by_pair: dict[tuple[int, int], LearningEvent] = {}
    for event in events:
        if event.module_id is not None:
            latest_by_pair[(event.user_id, event.module_id)] = event

    processed_at = datetime.now(timezone.utc)
    for (user_id, module_id), event in latest_by_pair.items():
        refresh_student_module_metric(db, user_id, module_id, event=event)
    for event in events:
        event.processed_at = processed_at
    db.commit()
    return len(events)


def refresh_all_student_module_metrics(db: Session) -> int:
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        return _refresh_all_metrics_postgresql(db)

    pairs = list(
        db.execute(
            select(CourseEnrollment.user_id, Module.id)
            .join(Module, Module.course_id == CourseEnrollment.course_id)
            .join(User, User.id == CourseEnrollment.user_id)
            .where(User.role == UserRole.STUDENT)
            .order_by(CourseEnrollment.user_id, Module.id)
        ).all()
    )
    for user_id, module_id in pairs:
        refresh_student_module_metric(db, user_id, module_id)
    db.commit()
    return len(pairs)


def _refresh_all_metrics_postgresql(db: Session) -> int:
    pairs_count = int(
        db.scalar(
            select(func.count())
            .select_from(CourseEnrollment)
            .join(Module, Module.course_id == CourseEnrollment.course_id)
            .join(User, User.id == CourseEnrollment.user_id)
            .where(User.role == UserRole.STUDENT)
        )
        or 0
    )
    db.execute(
        text(
            """
            WITH enrolled AS (
                SELECT ce.user_id, m.id AS module_id
                FROM course_enrollments ce
                JOIN modules m ON m.course_id = ce.course_id
                JOIN users u ON u.id = ce.user_id
                WHERE u.role = 'student'
            ),
            lesson_totals AS (
                SELECT module_id, COUNT(*)::int AS total_lessons
                FROM lessons
                GROUP BY module_id
            ),
            lesson_completed AS (
                SELECT lp.user_id, l.module_id, COUNT(*)::int AS completed_lessons
                FROM lesson_progress lp
                JOIN lessons l ON l.id = lp.lesson_id
                WHERE lp.is_completed IS TRUE
                GROUP BY lp.user_id, l.module_id
            ),
            attempt_source AS (
                SELECT
                    ta.user_id,
                    t.module_id,
                    ta.id,
                    ta.started_at,
                    ta.finished_at,
                    t.passing_score,
                    CASE WHEN ta.max_score > 0 THEN ta.score * 100.0 / ta.max_score ELSE 0.0 END AS percentage
                FROM test_attempts ta
                JOIN tests t ON t.id = ta.test_id
                WHERE t.module_id IS NOT NULL
            ),
            attempt_stats AS (
                SELECT
                    user_id,
                    module_id,
                    COUNT(*)::int AS attempts_count,
                    COUNT(*) FILTER (WHERE finished_at IS NOT NULL)::int AS completed_attempts_count,
                    COUNT(*) FILTER (
                        WHERE finished_at IS NOT NULL AND percentage >= passing_score
                    )::int AS passed_attempts_count,
                    AVG(percentage) FILTER (WHERE finished_at IS NOT NULL) AS average_percentage,
                    MAX(percentage) FILTER (WHERE finished_at IS NOT NULL) AS best_percentage,
                    MIN(percentage) FILTER (WHERE finished_at IS NOT NULL) AS worst_percentage,
                    (ARRAY_AGG(percentage ORDER BY started_at, id)
                        FILTER (WHERE finished_at IS NOT NULL))[1] AS first_percentage,
                    (ARRAY_AGG(percentage ORDER BY started_at DESC, id DESC)
                        FILTER (WHERE finished_at IS NOT NULL))[1] AS last_percentage,
                    MAX(finished_at) AS last_attempt_at
                FROM attempt_source
                GROUP BY user_id, module_id
            ),
            values_base AS (
                SELECT
                    e.user_id,
                    e.module_id,
                    COALESCE(a.attempts_count, 0) AS attempts_count,
                    COALESCE(a.completed_attempts_count, 0) AS completed_attempts_count,
                    COALESCE(a.passed_attempts_count, 0) AS passed_attempts_count,
                    COALESCE(a.completed_attempts_count, 0) - COALESCE(a.passed_attempts_count, 0)
                        AS failed_attempts_count,
                    ROUND(COALESCE(a.average_percentage, 0)::numeric, 2)::float AS average_percentage,
                    ROUND(COALESCE(a.best_percentage, 0)::numeric, 2)::float AS best_percentage,
                    ROUND(COALESCE(a.first_percentage, 0)::numeric, 2)::float AS first_percentage,
                    ROUND(COALESCE(a.last_percentage, 0)::numeric, 2)::float AS last_percentage,
                    ROUND((COALESCE(a.last_percentage, 0) - COALESCE(a.first_percentage, 0))::numeric, 2)::float
                        AS progress_delta,
                    CASE
                        WHEN COALESCE(a.completed_attempts_count, 0) < 2 THEN 'not_enough_data'
                        WHEN COALESCE(a.last_percentage, 0) - COALESCE(a.first_percentage, 0) >= 15 THEN 'improving'
                        WHEN COALESCE(a.last_percentage, 0) - COALESCE(a.first_percentage, 0) <= -15 THEN 'declining'
                        ELSE 'stable'
                    END AS trend,
                    CASE
                        WHEN COALESCE(a.completed_attempts_count, 0) < 2 THEN NULL
                        ELSE ROUND(GREATEST(0, 1 - ((a.best_percentage - a.worst_percentage) / 100.0))::numeric, 4)::float
                    END AS stability_index,
                    CASE
                        WHEN COALESCE(lt.total_lessons, 0) = 0 THEN 0.0
                        ELSE ROUND((COALESCE(lc.completed_lessons, 0)::numeric / lt.total_lessons), 4)::float
                    END AS completed_lessons_ratio,
                    CASE
                        WHEN COALESCE(a.completed_attempts_count, 0) = 0 THEN 'none'
                        WHEN COALESCE(a.average_percentage, 0) < 50 THEN 'high'
                        WHEN COALESCE(a.average_percentage, 0) < 70 THEN 'medium'
                        WHEN COALESCE(a.average_percentage, 0) < 85 THEN 'low'
                        ELSE 'none'
                    END AS weakness_level,
                    a.last_attempt_at
                FROM enrolled e
                LEFT JOIN attempt_stats a ON a.user_id = e.user_id AND a.module_id = e.module_id
                LEFT JOIN lesson_totals lt ON lt.module_id = e.module_id
                LEFT JOIN lesson_completed lc ON lc.user_id = e.user_id AND lc.module_id = e.module_id
            ),
            states AS (
                SELECT
                    v.*,
                    CASE
                        WHEN completed_attempts_count = 0 THEN 'not_enough_data'
                        WHEN average_percentage >= 85 THEN 'mastered'
                        WHEN stability_index IS NOT NULL AND stability_index < 0.45 THEN 'unstable'
                        WHEN trend = 'improving' THEN 'improving'
                        ELSE 'stagnant'
                    END AS learning_state,
                    CASE
                        WHEN completed_attempts_count = 0 AND completed_lessons_ratio < 0.5 THEN 'high'
                        WHEN completed_attempts_count = 0 THEN 'medium'
                        WHEN failed_attempts_count::float / NULLIF(completed_attempts_count, 0) >= 0.6
                            OR weakness_level = 'high' THEN 'high'
                        WHEN failed_attempts_count::float / NULLIF(completed_attempts_count, 0) >= 0.3
                            OR weakness_level IN ('medium', 'low') OR completed_lessons_ratio < 0.75 THEN 'medium'
                        ELSE 'low'
                    END AS risk_level
                FROM values_base v
            ),
            final AS (
                SELECT
                    s.*,
                    CASE
                        WHEN completed_attempts_count = 0 AND completed_lessons_ratio < 1 THEN 'unfinished_lessons'
                        WHEN completed_attempts_count = 0 THEN 'no_progress'
                        WHEN failed_attempts_count::float / NULLIF(completed_attempts_count, 0) >= 0.6
                            THEN 'high_failure_rate'
                        WHEN average_percentage < 60 THEN 'low_average'
                        WHEN completed_lessons_ratio < 0.5 THEN 'unfinished_lessons'
                        WHEN learning_state IN ('stagnant', 'unstable') THEN 'no_progress'
                        ELSE NULL
                    END AS reason_code,
                    (
                        completed_attempts_count > 0 AND average_percentage < 85 AND (
                            average_percentage < 60
                            OR (completed_attempts_count >= 3 AND progress_delta < 15 AND trend <> 'improving')
                            OR (completed_lessons_ratio < 0.5 AND failed_attempts_count > 0)
                            OR (learning_state = 'unstable' AND failed_attempts_count >= 2)
                        )
                    ) AS is_weak_topic,
                    (
                        completed_attempts_count >= 2
                        AND average_percentage >= 85
                        AND (stability_index IS NULL OR stability_index >= 0.7)
                        AND trend IN ('improving', 'stable')
                        AND progress_delta >= -2
                        AND completed_lessons_ratio >= 0.7
                        AND learning_state <> 'unstable'
                        AND failed_attempts_count::float / NULLIF(completed_attempts_count, 0) <= 0.2
                    ) AS is_strong_topic
                FROM states s
            )
            INSERT INTO student_module_metrics (
                user_id, module_id, attempts_count, completed_attempts_count,
                passed_attempts_count, failed_attempts_count, average_percentage,
                best_percentage, first_percentage, last_percentage, progress_delta,
                trend, stability_index, completed_lessons_ratio, weakness_level,
                risk_level, learning_state, reason_code, is_weak_topic,
                is_strong_topic, last_attempt_at, computed_at
            )
            SELECT
                user_id, module_id, attempts_count, completed_attempts_count,
                passed_attempts_count, failed_attempts_count, average_percentage,
                best_percentage, first_percentage, last_percentage, progress_delta,
                trend, stability_index, completed_lessons_ratio, weakness_level,
                risk_level, learning_state, reason_code, is_weak_topic,
                is_strong_topic, last_attempt_at, NOW()
            FROM final
            ON CONFLICT (user_id, module_id) DO UPDATE SET
                attempts_count = EXCLUDED.attempts_count,
                completed_attempts_count = EXCLUDED.completed_attempts_count,
                passed_attempts_count = EXCLUDED.passed_attempts_count,
                failed_attempts_count = EXCLUDED.failed_attempts_count,
                average_percentage = EXCLUDED.average_percentage,
                best_percentage = EXCLUDED.best_percentage,
                first_percentage = EXCLUDED.first_percentage,
                last_percentage = EXCLUDED.last_percentage,
                progress_delta = EXCLUDED.progress_delta,
                trend = EXCLUDED.trend,
                stability_index = EXCLUDED.stability_index,
                completed_lessons_ratio = EXCLUDED.completed_lessons_ratio,
                weakness_level = EXCLUDED.weakness_level,
                risk_level = EXCLUDED.risk_level,
                learning_state = EXCLUDED.learning_state,
                reason_code = EXCLUDED.reason_code,
                is_weak_topic = EXCLUDED.is_weak_topic,
                is_strong_topic = EXCLUDED.is_strong_topic,
                last_attempt_at = EXCLUDED.last_attempt_at,
                computed_at = EXCLUDED.computed_at
            """
        )
    )
    db.commit()
    return pairs_count


def backfill_analytics_if_empty(db: Session) -> int:
    if (db.scalar(select(func.count(StudentModuleMetric.id))) or 0) > 0:
        return 0
    return refresh_all_student_module_metrics(db)
