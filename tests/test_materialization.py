from datetime import datetime, timezone

from backend.enums import UserRole
from backend.models import (
    Course,
    CourseEnrollment,
    Lesson,
    LessonProgress,
    Module,
    Test as AssessmentModel,
    TestAttempt as AttemptModel,
    User,
)
from backend.services.analytics_materialization import (
    process_pending_learning_events_in_session,
    record_learning_event,
    refresh_student_module_metric,
)


def test_event_is_materialized_into_student_module_metric(db):
    user = User(username="student", password_hash="x", role=UserRole.STUDENT)
    course = Course(title="Course", is_published=True)
    db.add_all([user, course])
    db.flush()
    module = Module(course_id=course.id, title="Module")
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="Lesson")
    test = AssessmentModel(course_id=course.id, module_id=module.id, title="Test", passing_score=60)
    db.add_all([lesson, test, CourseEnrollment(user_id=user.id, course_id=course.id)])
    db.flush()
    now = datetime.now(timezone.utc)
    db.add(LessonProgress(user_id=user.id, lesson_id=lesson.id, is_completed=True, completed_at=now))
    db.add(
        AttemptModel(
            user_id=user.id,
            test_id=test.id,
            started_at=now,
            finished_at=now,
            score=4,
            max_score=10,
        )
    )
    db.flush()

    event = record_learning_event(
        db,
        event_type="test.attempt.completed",
        user_id=user.id,
        course_id=course.id,
        module_id=module.id,
    )
    metric = refresh_student_module_metric(db, user.id, module.id, event=event)

    assert metric is not None
    assert metric.average_percentage == 40
    assert metric.completed_lessons_ratio == 1
    assert metric.weakness_level == "high"
    assert metric.is_weak_topic is True
    assert event.processed_at is not None


def test_pending_event_is_processed_outside_request(db):
    user = User(username="queued-student", password_hash="x", role=UserRole.STUDENT)
    course = Course(title="Queued course", is_published=True)
    db.add_all([user, course])
    db.flush()
    module = Module(course_id=course.id, title="Queued module")
    db.add(module)
    db.flush()
    db.add(CourseEnrollment(user_id=user.id, course_id=course.id))
    event = record_learning_event(
        db,
        event_type="lesson.completed",
        user_id=user.id,
        course_id=course.id,
        module_id=module.id,
    )
    db.commit()

    processed = process_pending_learning_events_in_session(db)
    db.refresh(event)

    assert processed == 1
    assert event.processed_at is not None
