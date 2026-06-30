from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, selectinload

from analytics.student_summary import average
from analytics.topic_result_service import WeakTopicDetector
from backend.attempt_metrics import calculate_attempt_is_passed
from backend.deps import get_db, require_teacher_or_admin
from backend.enums import UserRole
from backend.models import (
    Course,
    CourseEnrollment,
    Lesson,
    LessonProgress,
    Module,
    Test,
    TestAttempt,
    User,
)
from backend.schemas import (
    PersonalAnalyticsSnapshotRead,
    PersonalRecommendationRead,
    TeacherCourseDashboardRead,
    TeacherCourseSummaryRead,
    TeacherGroupSummaryRead,
    TeacherStudentSummaryRead,
    TopicResultAggregateRead,
    TopicResultRead,
    UserAnalyticsSummaryRead,
)
from backend.services.analytics import (
    build_personal_recommendations,
    build_progress,
    build_topic_result_aggregates,
    compute_topic_result_row,
    compute_topic_results,
)
from backend.schemas import CourseRead

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def get_course_or_404(course_id: int, db: Session) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return course


def get_student_for_course_or_404(course_id: int, student_id: int, db: Session) -> User:
    student = db.get(User, student_id)
    if student is None or student.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    enrollment = db.scalar(
        select(CourseEnrollment.id).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == student_id,
        )
    )
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student is not enrolled in this course.",
        )
    return student


def get_students_for_course(course_id: int, db: Session) -> list[User]:
    enrollments = list(
        db.scalars(
            select(CourseEnrollment)
            .where(CourseEnrollment.course_id == course_id)
            .options(selectinload(CourseEnrollment.user))
        )
    )
    students = [
        enrollment.user
        for enrollment in enrollments
        if enrollment.user is not None and enrollment.user.role == UserRole.STUDENT
    ]
    return sorted(
        students,
        key=lambda item: (
            item.group or "",
            item.last_name or "",
            item.first_name or "",
            item.username,
        ),
    )


def build_scoped_summary(db: Session, user_id: int, course_id: int) -> UserAnalyticsSummaryRead:
    attempts = list(
        db.scalars(
            select(TestAttempt)
            .join(Test, Test.id == TestAttempt.test_id)
            .where(
                TestAttempt.user_id == user_id,
                Test.course_id == course_id,
            )
            .options(selectinload(TestAttempt.test))
        )
    )
    completed_attempts = [attempt for attempt in attempts if attempt.finished_at is not None]
    passed_attempts = [
        attempt
        for attempt in completed_attempts
        if calculate_attempt_is_passed(
            attempt.score,
            attempt.max_score,
            attempt.test.passing_score if attempt.test is not None else 0.0,
            attempt.finished_at,
        )
    ]
    lessons_completed = int(
        db.scalar(
            select(func.count(LessonProgress.id))
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.is_completed.is_(True),
                Module.course_id == course_id,
            )
        )
        or 0
    )
    unique_courses_started = len(
        list(
            db.scalars(
                select(distinct(Test.course_id))
                .join(TestAttempt, TestAttempt.test_id == Test.id)
                .where(
                    TestAttempt.user_id == user_id,
                    Test.course_id == course_id,
                )
            )
        )
    )
    if unique_courses_started == 0 and lessons_completed > 0:
        unique_courses_started = 1

    return UserAnalyticsSummaryRead(
        total_attempts=len(attempts),
        completed_attempts=len(completed_attempts),
        passed_attempts=len(passed_attempts),
        average_score=average([attempt.score for attempt in completed_attempts]),
        average_percentage=average([attempt.percentage for attempt in completed_attempts]),
        lessons_completed=lessons_completed,
        unique_courses_started=unique_courses_started,
    )


def build_scoped_dynamics(db: Session, user_id: int, course_id: int) -> list[dict]:
    attempts = list(
        db.scalars(
            select(TestAttempt)
            .join(Test, Test.id == TestAttempt.test_id)
            .where(
                TestAttempt.user_id == user_id,
                Test.course_id == course_id,
                TestAttempt.finished_at.is_not(None),
            )
            .options(
                selectinload(TestAttempt.test).selectinload(Test.module),
            )
            .order_by(TestAttempt.finished_at, TestAttempt.id)
        )
    )
    items: list[dict] = []
    for attempt in attempts:
        module = attempt.test.module if attempt.test is not None else None
        items.append(
            {
                "attempt_id": attempt.id,
                "date": attempt.finished_at or attempt.started_at,
                "test_id": attempt.test_id,
                "test_title": attempt.test.title if attempt.test is not None else "Тест",
                "module_id": module.id if module is not None else None,
                "module_title": module.title if module is not None else None,
                "percentage": attempt.percentage,
                "is_passed": attempt.is_passed,
            }
        )
    return items


def build_scoped_snapshot(
    db: Session,
    user_id: int,
    course_id: int,
) -> PersonalAnalyticsSnapshotRead:
    detector = WeakTopicDetector(db)
    analytics_data = detector.prepare_analytics_data(user_id, course_id=course_id)
    return PersonalAnalyticsSnapshotRead(
        progress=build_progress(db, user_id, course_id=course_id),
        summary=build_scoped_summary(db, user_id, course_id),
        topicResults=[TopicResultRead(**item) for item in analytics_data["topic_results"]],
        weakTopics=[TopicResultRead(**item) for item in analytics_data["weak_topics"]],
        strongTopics=[TopicResultRead(**item) for item in analytics_data["strong_topics"]],
        bestTopics=[TopicResultRead(**item) for item in analytics_data["best_topics"]],
        unstableTopics=[TopicResultRead(**item) for item in analytics_data["unstable_topics"]],
        improvingTopics=[TopicResultRead(**item) for item in analytics_data["improving_topics"]],
        topicsWithoutEnoughData=[
            TopicResultRead(**item) for item in analytics_data["topics_without_enough_data"]
        ],
        dynamics=build_scoped_dynamics(db, user_id, course_id),
    )


def build_last_activity_at(db: Session, user_id: int, course_id: int) -> datetime | None:
    lesson_activity = db.scalar(
        select(func.max(LessonProgress.completed_at))
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .where(
            LessonProgress.user_id == user_id,
            LessonProgress.is_completed.is_(True),
            Module.course_id == course_id,
        )
    )
    test_activity = db.scalar(
        select(func.max(func.coalesce(TestAttempt.finished_at, TestAttempt.started_at)))
        .join(Test, Test.id == TestAttempt.test_id)
        .where(
            TestAttempt.user_id == user_id,
            Test.course_id == course_id,
        )
    )
    candidates = [item for item in [lesson_activity, test_activity] if item is not None]
    return max(candidates) if candidates else None


def build_student_summary_row(
    db: Session,
    student: User,
    course_id: int,
) -> TeacherStudentSummaryRead:
    progress = build_progress(db, student.id, course_id=course_id)
    topic_results = compute_topic_results(db, student.id, course_id=course_id)
    attempts_count = int(
        db.scalar(
            select(func.count(TestAttempt.id))
            .join(Test, Test.id == TestAttempt.test_id)
            .where(
                TestAttempt.user_id == student.id,
                Test.course_id == course_id,
            )
        )
        or 0
    )
    weak_topics_count = len([item for item in topic_results if item.category == "weak"])
    high_risk_topics_count = len([item for item in topic_results if item.risk_level == "high"])
    unfinished_topics_count = len(
        [item for item in topic_results if item.completed_attempts_count < 2]
    )

    return TeacherStudentSummaryRead(
        id=student.id,
        username=student.username,
        first_name=student.first_name,
        last_name=student.last_name,
        group=student.group,
        course_year=student.course_year,
        completion_rate=progress.completion_rate,
        average_test_percentage=progress.average_test_percentage,
        completed_lessons=progress.completed_lessons,
        total_lessons=progress.total_lessons,
        passed_tests=progress.passed_tests,
        total_tests=progress.total_tests,
        attempts_count=attempts_count,
        weak_topics_count=weak_topics_count,
        high_risk_topics_count=high_risk_topics_count,
        unfinished_topics_count=unfinished_topics_count,
        last_activity_at=build_last_activity_at(db, student.id, course_id),
    )


def build_group_summaries(
    student_rows: list[TeacherStudentSummaryRead],
) -> list[TeacherGroupSummaryRead]:
    grouped: dict[str, list[TeacherStudentSummaryRead]] = {}
    for row in student_rows:
        group_id = row.group or "Без группы"
        grouped.setdefault(group_id, []).append(row)

    items: list[TeacherGroupSummaryRead] = []
    for group_id, rows in sorted(grouped.items()):
        items.append(
            TeacherGroupSummaryRead(
                group_id=group_id,
                students_count=len(rows),
                average_completion_rate=average([row.completion_rate for row in rows]),
                average_test_percentage=average(
                    [row.average_test_percentage for row in rows]
                ),
                average_completed_lessons=average(
                    [float(row.completed_lessons) for row in rows]
                ),
                average_passed_tests=average([float(row.passed_tests) for row in rows]),
                at_risk_students_count=len(
                    [
                        row
                        for row in rows
                        if row.high_risk_topics_count > 0 or row.weak_topics_count > 0
                    ]
                ),
                low_activity_students_count=len(
                    [
                        row
                        for row in rows
                        if row.attempts_count < 2 or row.completion_rate < 25
                    ]
                ),
            )
        )
    return items


def build_group_topic_results_for_course(
    db: Session,
    course_id: int,
    group_id: str,
) -> list[TopicResultAggregateRead]:
    modules = list(
        db.scalars(
            select(Module)
            .where(Module.course_id == course_id)
            .order_by(Module.order, Module.id)
        )
    )
    students = list(
        db.scalars(
            select(User)
            .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
            .where(
                CourseEnrollment.course_id == course_id,
                User.group == group_id,
                User.role == UserRole.STUDENT,
            )
            .order_by(User.last_name, User.first_name, User.username)
        )
    )
    if not students:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    results: list[TopicResultAggregateRead] = []
    for module in modules:
        topic_rows = [compute_topic_result_row(db, student.id, module) for student in students]
        results.append(
            TopicResultAggregateRead(
                module_id=module.id,
                module_title=module.title,
                users_count=len(topic_rows),
                attempts_count=sum(item.attempts_count for item in topic_rows),
                average_percentage=average([item.average_percentage for item in topic_rows]),
                best_percentage=average([item.best_percentage for item in topic_rows]),
                high_weakness_count=len(
                    [item for item in topic_rows if item.weakness_level == "high"]
                ),
                medium_weakness_count=len(
                    [item for item in topic_rows if item.weakness_level == "medium"]
                ),
                low_weakness_count=len(
                    [item for item in topic_rows if item.weakness_level == "low"]
                ),
            )
        )
    return results


@router.get("/courses/{course_id}/dashboard/", response_model=TeacherCourseDashboardRead)
def get_course_dashboard(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> TeacherCourseDashboardRead:
    _ = current_user
    course = get_course_or_404(course_id, db)
    students = get_students_for_course(course_id, db)
    student_rows = [build_student_summary_row(db, student, course_id) for student in students]
    groups = build_group_summaries(student_rows)
    at_risk_students_count = len(
        [
            row
            for row in student_rows
            if row.high_risk_topics_count > 0 or row.weak_topics_count > 0
        ]
    )
    active_students_count = len(
        [
            row
            for row in student_rows
            if row.attempts_count > 0 or row.completed_lessons > 0
        ]
    )

    return TeacherCourseDashboardRead(
        course=CourseRead.model_validate(course),
        summary=TeacherCourseSummaryRead(
            enrolled_students_count=len(student_rows),
            groups_count=len(groups),
            active_students_count=active_students_count,
            average_completion_rate=average([row.completion_rate for row in student_rows]),
            average_test_percentage=average(
                [row.average_test_percentage for row in student_rows]
            ),
            at_risk_students_count=at_risk_students_count,
        ),
        groups=groups,
        students=student_rows,
        module_topic_results=build_topic_result_aggregates(db, course_id=course_id),
    )


@router.get(
    "/courses/{course_id}/groups/{group_id}/topic-results/",
    response_model=list[TopicResultAggregateRead],
)
def get_group_topic_results_for_course(
    course_id: int,
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[TopicResultAggregateRead]:
    _ = current_user
    _ = get_course_or_404(course_id, db)
    return build_group_topic_results_for_course(db, course_id, group_id)


@router.get(
    "/courses/{course_id}/students/{student_id}/summary/",
    response_model=TeacherStudentSummaryRead,
)
def get_student_summary_for_course(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> TeacherStudentSummaryRead:
    _ = current_user
    _ = get_course_or_404(course_id, db)
    student = get_student_for_course_or_404(course_id, student_id, db)
    return build_student_summary_row(db, student, course_id)


@router.get(
    "/courses/{course_id}/students/{student_id}/snapshot/",
    response_model=PersonalAnalyticsSnapshotRead,
)
def get_student_snapshot_for_course(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> PersonalAnalyticsSnapshotRead:
    _ = current_user
    _ = get_course_or_404(course_id, db)
    student = get_student_for_course_or_404(course_id, student_id, db)
    return build_scoped_snapshot(db, student.id, course_id)


@router.get(
    "/courses/{course_id}/students/{student_id}/recommendations/",
    response_model=list[PersonalRecommendationRead],
)
def get_student_recommendations_for_course(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[PersonalRecommendationRead]:
    _ = current_user
    _ = get_course_or_404(course_id, db)
    student = get_student_for_course_or_404(course_id, student_id, db)
    return build_personal_recommendations(db, student.id, course_id=course_id)
