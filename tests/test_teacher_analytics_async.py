import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.db import Base
from backend.enums import UserRole
from backend.models import (
    Course,
    CourseEnrollment,
    Module,
    StudentModuleMetric,
    User,
)
from backend.services.teacher_analytics_async import (
    build_async_course_dashboard,
    build_async_group_topic_results,
)


@pytest.mark.anyio
async def test_async_dashboard_uses_materialized_metrics():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        student = User(
            username="async-student",
            password_hash="x",
            role=UserRole.STUDENT,
            group="G-1",
        )
        course = Course(title="Async course", is_published=True)
        db.add_all([student, course])
        await db.flush()
        module = Module(course_id=course.id, title="Async module")
        db.add(module)
        await db.flush()
        db.add(CourseEnrollment(user_id=student.id, course_id=course.id))
        db.add(
            StudentModuleMetric(
                user_id=student.id,
                module_id=module.id,
                attempts_count=3,
                completed_attempts_count=3,
                average_percentage=55,
                best_percentage=70,
                weakness_level="medium",
                risk_level="high",
                is_weak_topic=True,
            )
        )
        await db.commit()

        dashboard = await build_async_course_dashboard(db, course.id)
        group_results = await build_async_group_topic_results(db, course.id, "G-1")

        assert dashboard.summary.enrolled_students_count == 1
        assert dashboard.summary.at_risk_students_count == 1
        assert dashboard.students[0].weak_topics_count == 1
        assert dashboard.module_topic_results[0].attempts_count == 3
        assert group_results[0].average_percentage == 55

    await engine.dispose()
