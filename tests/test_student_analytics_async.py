from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.db import Base
from backend.enums import UserRole
from backend.models import (
    Course,
    CourseEnrollment,
    Lesson,
    LessonProgress,
    Module,
    Recommendation,
    StudentModuleMetric,
    Test as Assessment,
    TestAttempt as Attempt,
    User,
)
from backend.services.student_analytics_async import (
    build_personal_recommendations_from_read_model,
    build_personal_snapshot_from_read_model,
    build_progress_from_read_model,
)


@pytest.mark.anyio
async def test_student_reads_use_materialized_metrics():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        student = User(username="read-model-student", password_hash="x", role=UserRole.STUDENT)
        course = Course(title="Cybersecurity", is_published=True)
        db.add_all([student, course])
        await db.flush()
        module = Module(course_id=course.id, title="AppSec")
        db.add(module)
        await db.flush()
        lesson = Lesson(module_id=module.id, title="OWASP")
        assessment = Assessment(
            course_id=course.id,
            module_id=module.id,
            title="Control",
            passing_score=60,
            is_active=True,
        )
        db.add_all([lesson, assessment, CourseEnrollment(user_id=student.id, course_id=course.id)])
        await db.flush()
        now = datetime.now(timezone.utc)
        db.add_all(
            [
                LessonProgress(
                    user_id=student.id,
                    lesson_id=lesson.id,
                    is_completed=True,
                    completed_at=now,
                ),
                Attempt(
                    user_id=student.id,
                    test_id=assessment.id,
                    started_at=now,
                    finished_at=now,
                    score=5,
                    max_score=10,
                ),
                StudentModuleMetric(
                    user_id=student.id,
                    module_id=module.id,
                    attempts_count=3,
                    completed_attempts_count=3,
                    failed_attempts_count=3,
                    average_percentage=50,
                    best_percentage=55,
                    first_percentage=45,
                    last_percentage=50,
                    progress_delta=5,
                    trend="stable",
                    stability_index=0.8,
                    completed_lessons_ratio=1,
                    weakness_level="medium",
                    risk_level="high",
                    learning_state="stagnant",
                    is_weak_topic=True,
                ),
                Recommendation(
                    module_id=module.id,
                    title="Repeat OWASP",
                    description="Review access control.",
                ),
            ]
        )
        await db.commit()

        progress = await build_progress_from_read_model(db, student.id, course_id=course.id)
        snapshot = await build_personal_snapshot_from_read_model(db, student.id)
        recommendations = await build_personal_recommendations_from_read_model(db, student.id)

        assert progress.completed_lessons == 1
        assert progress.passed_tests == 0
        assert snapshot.topicResults[0].average_percentage == 50
        assert snapshot.weakTopics[0].module_title == "AppSec"
        assert recommendations[0].module_id == module.id
        assert recommendations[0].priority == "medium"

    await engine.dispose()
