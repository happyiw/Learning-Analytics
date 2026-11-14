from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.enums import UserRole
from backend.models import (
    Course,
    CourseEnrollment,
    Lesson,
    LessonProgress,
    Module,
    StudentModuleMetric,
    Test,
    TestAttempt,
    User,
)
from backend.schemas import (
    CourseRead,
    TeacherCourseDashboardRead,
    TeacherCourseSummaryRead,
    TeacherGroupSummaryRead,
    TeacherStudentSummaryRead,
    TopicResultAggregateRead,
)


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


async def _module_aggregates(
    db: AsyncSession,
    course_id: int,
    group_id: str | None = None,
) -> list[TopicResultAggregateRead]:
    stmt = (
        select(
            Module.id,
            Module.title,
            func.count(distinct(CourseEnrollment.user_id)),
            func.coalesce(func.sum(StudentModuleMetric.attempts_count), 0),
            func.coalesce(func.avg(StudentModuleMetric.average_percentage), 0),
            func.coalesce(func.avg(StudentModuleMetric.best_percentage), 0),
            func.count(StudentModuleMetric.id).filter(StudentModuleMetric.weakness_level == "high"),
            func.count(StudentModuleMetric.id).filter(StudentModuleMetric.weakness_level == "medium"),
            func.count(StudentModuleMetric.id).filter(StudentModuleMetric.weakness_level == "low"),
        )
        .join(CourseEnrollment, CourseEnrollment.course_id == Module.course_id)
        .join(User, User.id == CourseEnrollment.user_id)
        .outerjoin(
            StudentModuleMetric,
            and_(
                StudentModuleMetric.module_id == Module.id,
                StudentModuleMetric.user_id == CourseEnrollment.user_id,
            ),
        )
        .where(Module.course_id == course_id, User.role == UserRole.STUDENT)
        .group_by(Module.id, Module.title, Module.order)
        .order_by(Module.order, Module.id)
    )
    if group_id is not None:
        stmt = stmt.where(User.group == group_id)

    rows = (await db.execute(stmt)).all()
    if group_id is not None and not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    return [
        TopicResultAggregateRead(
            module_id=row[0],
            module_title=row[1],
            users_count=row[2],
            attempts_count=int(row[3]),
            average_percentage=round(float(row[4]), 2),
            best_percentage=round(float(row[5]), 2),
            high_weakness_count=row[6],
            medium_weakness_count=row[7],
            low_weakness_count=row[8],
        )
        for row in rows
    ]


async def build_async_group_topic_results(
    db: AsyncSession,
    course_id: int,
    group_id: str,
) -> list[TopicResultAggregateRead]:
    if await db.get(Course, course_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    group_exists = await db.scalar(
        select(User.id)
        .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
        .where(
            CourseEnrollment.course_id == course_id,
            User.group == group_id,
            User.role == UserRole.STUDENT,
        )
        .limit(1)
    )
    if group_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    return await _module_aggregates(db, course_id, group_id)


async def build_async_course_dashboard(
    db: AsyncSession,
    course_id: int,
) -> TeacherCourseDashboardRead:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    students = list(
        (
            await db.scalars(
                select(User)
                .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
                .where(
                    CourseEnrollment.course_id == course_id,
                    User.role == UserRole.STUDENT,
                )
                .order_by(User.group, User.last_name, User.first_name, User.username)
            )
        ).all()
    )
    user_ids = [student.id for student in students]

    total_lessons = int(
        await db.scalar(
            select(func.count(Lesson.id))
            .join(Module, Module.id == Lesson.module_id)
            .where(Module.course_id == course_id)
        )
        or 0
    )
    total_tests = int(
        await db.scalar(
            select(func.count(Test.id)).where(Test.course_id == course_id, Test.is_active.is_(True))
        )
        or 0
    )

    completed_by_user: dict[int, tuple[int, datetime | None]] = {}
    attempt_by_user: dict[int, tuple[int, int, float, datetime | None]] = {}
    risk_by_user: dict[int, tuple[int, int, int]] = {}
    if user_ids:
        lesson_rows = (
            await db.execute(
                select(
                    LessonProgress.user_id,
                    func.count(distinct(LessonProgress.lesson_id)),
                    func.max(LessonProgress.completed_at),
                )
                .join(Lesson, Lesson.id == LessonProgress.lesson_id)
                .join(Module, Module.id == Lesson.module_id)
                .where(
                    LessonProgress.user_id.in_(user_ids),
                    LessonProgress.is_completed.is_(True),
                    Module.course_id == course_id,
                )
                .group_by(LessonProgress.user_id)
            )
        ).all()
        completed_by_user = {row[0]: (row[1], row[2]) for row in lesson_rows}

        percentage = case(
            (TestAttempt.max_score > 0, TestAttempt.score * 100.0 / TestAttempt.max_score),
            else_=0.0,
        )
        passed_test = case(
            (
                and_(
                    TestAttempt.finished_at.is_not(None),
                    percentage >= Test.passing_score,
                ),
                TestAttempt.test_id,
            ),
            else_=None,
        )
        attempt_rows = (
            await db.execute(
                select(
                    TestAttempt.user_id,
                    func.count(TestAttempt.id),
                    func.count(distinct(passed_test)),
                    func.coalesce(
                        func.avg(percentage).filter(TestAttempt.finished_at.is_not(None)),
                        0,
                    ),
                    func.max(func.coalesce(TestAttempt.finished_at, TestAttempt.started_at)),
                )
                .join(Test, Test.id == TestAttempt.test_id)
                .where(TestAttempt.user_id.in_(user_ids), Test.course_id == course_id)
                .group_by(TestAttempt.user_id)
            )
        ).all()
        attempt_by_user = {
            row[0]: (row[1], row[2], round(float(row[3]), 2), row[4]) for row in attempt_rows
        }

        risk_rows = (
            await db.execute(
                select(
                    StudentModuleMetric.user_id,
                    func.count(StudentModuleMetric.id).filter(StudentModuleMetric.is_weak_topic.is_(True)),
                    func.count(StudentModuleMetric.id).filter(StudentModuleMetric.risk_level == "high"),
                    func.count(StudentModuleMetric.id).filter(
                        StudentModuleMetric.completed_attempts_count < 2
                    ),
                )
                .join(Module, Module.id == StudentModuleMetric.module_id)
                .where(
                    StudentModuleMetric.user_id.in_(user_ids),
                    Module.course_id == course_id,
                )
                .group_by(StudentModuleMetric.user_id)
            )
        ).all()
        risk_by_user = {row[0]: (row[1], row[2], row[3]) for row in risk_rows}

    student_rows: list[TeacherStudentSummaryRead] = []
    denominator = total_lessons + total_tests
    for student in students:
        completed_lessons, lesson_activity = completed_by_user.get(student.id, (0, None))
        attempts_count, passed_tests, average_percentage, test_activity = attempt_by_user.get(
            student.id, (0, 0, 0.0, None)
        )
        weak_count, high_risk_count, unfinished_count = risk_by_user.get(student.id, (0, 0, 0))
        activity = max(
            [value for value in (lesson_activity, test_activity) if value is not None],
            default=None,
        )
        completion_rate = (
            round(((completed_lessons + passed_tests) / denominator) * 100, 2)
            if denominator
            else 0.0
        )
        student_rows.append(
            TeacherStudentSummaryRead(
                id=student.id,
                username=student.username,
                first_name=student.first_name,
                last_name=student.last_name,
                group=student.group,
                course_year=student.course_year,
                completion_rate=completion_rate,
                average_test_percentage=average_percentage,
                completed_lessons=completed_lessons,
                total_lessons=total_lessons,
                passed_tests=passed_tests,
                total_tests=total_tests,
                attempts_count=attempts_count,
                weak_topics_count=weak_count,
                high_risk_topics_count=high_risk_count,
                unfinished_topics_count=unfinished_count,
                last_activity_at=activity,
            )
        )

    grouped: dict[str, list[TeacherStudentSummaryRead]] = {}
    for row in student_rows:
        grouped.setdefault(row.group or "Без группы", []).append(row)
    groups = [
        TeacherGroupSummaryRead(
            group_id=group_id,
            students_count=len(rows),
            average_completion_rate=_average([row.completion_rate for row in rows]),
            average_test_percentage=_average([row.average_test_percentage for row in rows]),
            average_completed_lessons=_average([float(row.completed_lessons) for row in rows]),
            average_passed_tests=_average([float(row.passed_tests) for row in rows]),
            at_risk_students_count=len(
                [row for row in rows if row.high_risk_topics_count or row.weak_topics_count]
            ),
            low_activity_students_count=len(
                [row for row in rows if row.attempts_count < 2 or row.completion_rate < 25]
            ),
        )
        for group_id, rows in sorted(grouped.items())
    ]
    at_risk = len(
        [row for row in student_rows if row.high_risk_topics_count or row.weak_topics_count]
    )
    active = len([row for row in student_rows if row.attempts_count or row.completed_lessons])

    return TeacherCourseDashboardRead(
        course=CourseRead.model_validate(course),
        summary=TeacherCourseSummaryRead(
            enrolled_students_count=len(student_rows),
            groups_count=len(groups),
            active_students_count=active,
            average_completion_rate=_average([row.completion_rate for row in student_rows]),
            average_test_percentage=_average(
                [row.average_test_percentage for row in student_rows]
            ),
            at_risk_students_count=at_risk,
        ),
        groups=groups,
        students=student_rows,
        module_topic_results=await _module_aggregates(db, course_id),
    )
