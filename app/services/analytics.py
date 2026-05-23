from __future__ import annotations

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.models import (
    Lesson,
    LessonProgress,
    Module,
    Recommendation,
    Test,
    TestAttempt,
    TopicResult,
    User,
)
from app.schemas import (
    AnalyticsDynamicsPointRead,
    PersonalRecommendationRead,
    ProgressRead,
    TopicResultAggregateRead,
    TopicResultRead,
    UserAnalyticsSummaryRead,
)


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def weakness_from_percentage(average_percentage: float, attempts_count: int) -> str:
    if attempts_count == 0 or average_percentage < 50:
        return "high"
    if average_percentage < 75:
        return "medium"
    return "low"


def get_modules_for_scope(
    db: Session,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[Module]:
    if module_id is not None:
        module = db.get(Module, module_id)
        return [module] if module else []
    if course_id is not None:
        return list(
            db.scalars(
                select(Module).where(Module.course_id == course_id).order_by(Module.order, Module.id)
            )
        )
    return list(db.scalars(select(Module).order_by(Module.order, Module.id)))


def get_scope_test_ids(
    db: Session,
    course_id: int | None = None,
    module_id: int | None = None,
    only_active: bool = False,
) -> list[int]:
    stmt = select(Test.id)
    if only_active:
        stmt = stmt.where(Test.is_active.is_(True))
    if module_id is not None:
        stmt = stmt.where(Test.module_id == module_id)
    elif course_id is not None:
        stmt = stmt.where(Test.course_id == course_id)
    return list(db.scalars(stmt))


def get_scope_lesson_ids(
    db: Session,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[int]:
    stmt = select(Lesson.id).join(Module, Module.id == Lesson.module_id)
    if module_id is not None:
        stmt = stmt.where(Lesson.module_id == module_id)
    elif course_id is not None:
        stmt = stmt.where(Module.course_id == course_id)
    return list(db.scalars(stmt))


def build_progress(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> ProgressRead:
    lesson_ids = get_scope_lesson_ids(db, course_id=course_id, module_id=module_id)
    test_ids = get_scope_test_ids(db, course_id=course_id, module_id=module_id, only_active=True)

    completed_lessons = (
        len(
            list(
                db.scalars(
                    select(LessonProgress.id).where(
                        LessonProgress.user_id == user_id,
                        LessonProgress.is_completed.is_(True),
                        LessonProgress.lesson_id.in_(lesson_ids),
                    )
                )
            )
        )
        if lesson_ids
        else 0
    )
    passed_tests = (
        len(
            list(
                db.scalars(
                    select(distinct(TestAttempt.test_id)).where(
                        TestAttempt.user_id == user_id,
                        TestAttempt.is_passed.is_(True),
                        TestAttempt.test_id.in_(test_ids),
                    )
                )
            )
        )
        if test_ids
        else 0
    )
    percentages = (
        list(
            db.scalars(
                select(TestAttempt.percentage).where(
                    TestAttempt.user_id == user_id,
                    TestAttempt.finished_at.is_not(None),
                    TestAttempt.test_id.in_(test_ids),
                )
            )
        )
        if test_ids
        else []
    )

    total_lessons = len(lesson_ids)
    total_tests = len(test_ids)
    denominator = total_lessons + total_tests
    completion_rate = round(((completed_lessons + passed_tests) / denominator) * 100, 2) if denominator else 0.0

    if module_id is not None:
        scope_type = "module"
        scope_id = module_id
    elif course_id is not None:
        scope_type = "course"
        scope_id = course_id
    else:
        scope_type = "global"
        scope_id = None

    return ProgressRead(
        scope_type=scope_type,
        scope_id=scope_id,
        completed_lessons=completed_lessons,
        total_lessons=total_lessons,
        passed_tests=passed_tests,
        total_tests=total_tests,
        average_test_percentage=average(percentages),
        completion_rate=completion_rate,
    )


def compute_topic_result_row(
    db: Session,
    user_id: int,
    module: Module,
) -> TopicResultRead:
    existing = db.scalar(
        select(TopicResult).where(TopicResult.user_id == user_id, TopicResult.module_id == module.id)
    )
    test_ids = get_scope_test_ids(db, module_id=module.id)
    attempts = (
        list(
            db.scalars(
                select(TestAttempt).where(
                    TestAttempt.user_id == user_id,
                    TestAttempt.finished_at.is_not(None),
                    TestAttempt.test_id.in_(test_ids),
                )
            )
        )
        if test_ids
        else []
    )
    percentages = [attempt.percentage for attempt in attempts]
    attempts_count = len(attempts)
    average_percentage = average(percentages)
    best_percentage = round(max(percentages), 2) if percentages else 0.0
    weakness_level = weakness_from_percentage(average_percentage, attempts_count)
    last_attempt_at = max((attempt.finished_at or attempt.started_at for attempt in attempts), default=None)

    return TopicResultRead(
        id=existing.id if existing else None,
        module_id=module.id,
        module_title=module.title,
        attempts_count=attempts_count,
        average_percentage=average_percentage,
        best_percentage=best_percentage,
        weakness_level=weakness_level,
        last_attempt_at=last_attempt_at,
        updated_at=existing.updated_at if existing else None,
    )


def compute_topic_results(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[TopicResultRead]:
    modules = get_modules_for_scope(db, course_id=course_id, module_id=module_id)
    return [compute_topic_result_row(db, user_id, module) for module in modules]


def upsert_topic_result(
    db: Session,
    user_id: int,
    module_id: int,
) -> TopicResult | None:
    module = db.get(Module, module_id)
    if module is None:
        return None

    computed = compute_topic_result_row(db, user_id, module)
    topic_result = db.scalar(
        select(TopicResult).where(TopicResult.user_id == user_id, TopicResult.module_id == module_id)
    )
    if topic_result is None:
        topic_result = TopicResult(user_id=user_id, module_id=module_id)
        db.add(topic_result)

    topic_result.attempts_count = computed.attempts_count
    topic_result.average_percentage = computed.average_percentage
    topic_result.best_percentage = computed.best_percentage
    topic_result.weakness_level = computed.weakness_level
    topic_result.last_attempt_at = computed.last_attempt_at
    db.flush()
    return topic_result


def build_summary(db: Session, user_id: int) -> UserAnalyticsSummaryRead:
    attempts = list(db.scalars(select(TestAttempt).where(TestAttempt.user_id == user_id)))
    completed_attempts = [attempt for attempt in attempts if attempt.finished_at is not None]
    passed_attempts = [attempt for attempt in attempts if attempt.is_passed]
    lessons_completed = len(
        list(
            db.scalars(
                select(LessonProgress.id).where(
                    LessonProgress.user_id == user_id,
                    LessonProgress.is_completed.is_(True),
                )
            )
        )
    )
    unique_courses_started = len(
        list(
            db.scalars(
                select(distinct(Test.course_id))
                .join(TestAttempt, TestAttempt.test_id == Test.id)
                .where(TestAttempt.user_id == user_id)
            )
        )
    )
    return UserAnalyticsSummaryRead(
        total_attempts=len(attempts),
        completed_attempts=len(completed_attempts),
        passed_attempts=len(passed_attempts),
        average_score=average([attempt.score for attempt in completed_attempts]),
        average_percentage=average([attempt.percentage for attempt in completed_attempts]),
        lessons_completed=lessons_completed,
        unique_courses_started=unique_courses_started,
    )


def build_dynamics(db: Session, user_id: int) -> list[AnalyticsDynamicsPointRead]:
    attempts = list(
        db.scalars(
            select(TestAttempt)
            .join(Test, Test.id == TestAttempt.test_id)
            .where(TestAttempt.user_id == user_id, TestAttempt.finished_at.is_not(None))
            .order_by(TestAttempt.finished_at, TestAttempt.id)
        )
    )
    points: list[AnalyticsDynamicsPointRead] = []
    for attempt in attempts:
        module = attempt.test.module
        points.append(
            AnalyticsDynamicsPointRead(
                attempt_id=attempt.id,
                date=attempt.finished_at or attempt.started_at,
                test_id=attempt.test_id,
                test_title=attempt.test.title,
                module_id=module.id if module else None,
                module_title=module.title if module else None,
                percentage=attempt.percentage,
                is_passed=attempt.is_passed,
            )
        )
    return points


def build_personal_recommendations(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[PersonalRecommendationRead]:
    modules = get_modules_for_scope(db, course_id=course_id, module_id=module_id)
    module_map = {module.id: module for module in modules}
    topic_results = {result.module_id: result for result in compute_topic_results(db, user_id, course_id=course_id, module_id=module_id)}
    recommendations = list(
        db.scalars(
            select(Recommendation)
            .where(Recommendation.module_id.in_(list(module_map.keys())))
            .order_by(Recommendation.id)
        )
    ) if module_map else []

    items: list[PersonalRecommendationRead] = []
    for recommendation in recommendations:
        topic_result = topic_results.get(recommendation.module_id)
        current_percentage = topic_result.average_percentage if topic_result else 0.0
        weakness_level = topic_result.weakness_level if topic_result else "high"
        attempts_count = topic_result.attempts_count if topic_result else 0
        if attempts_count == 0 or current_percentage <= recommendation.trigger_score_threshold:
            module = module_map[recommendation.module_id]
            items.append(
                PersonalRecommendationRead(
                    id=recommendation.id,
                    module_id=module.id,
                    module_title=module.title,
                    title=recommendation.title,
                    description=recommendation.description,
                    resource_url=recommendation.resource_url,
                    trigger_score_threshold=recommendation.trigger_score_threshold,
                    current_percentage=current_percentage,
                    weakness_level=weakness_level,
                )
            )
    return items


def build_topic_result_aggregates(
    db: Session,
    course_id: int | None = None,
    module_id: int | None = None,
    group_id: str | None = None,
) -> list[TopicResultAggregateRead]:
    modules = get_modules_for_scope(db, course_id=course_id, module_id=module_id)
    if group_id is not None:
        users = list(db.scalars(select(User).where(User.group == group_id)))
    else:
        lesson_ids = get_scope_lesson_ids(db, course_id=course_id, module_id=module_id)
        test_ids = get_scope_test_ids(db, course_id=course_id, module_id=module_id)
        user_ids = set()
        if lesson_ids:
            user_ids.update(
                db.scalars(
                    select(distinct(LessonProgress.user_id)).where(
                        LessonProgress.lesson_id.in_(lesson_ids),
                    )
                )
            )
        if test_ids:
            user_ids.update(
                db.scalars(
                    select(distinct(TestAttempt.user_id)).where(
                        TestAttempt.test_id.in_(test_ids),
                    )
                )
            )
        users = list(db.scalars(select(User).where(User.id.in_(list(user_ids))))) if user_ids else []

    aggregates: list[TopicResultAggregateRead] = []
    for module in modules:
        topic_results = [compute_topic_result_row(db, user.id, module) for user in users]
        aggregates.append(
            TopicResultAggregateRead(
                module_id=module.id,
                module_title=module.title,
                users_count=len(topic_results),
                attempts_count=sum(result.attempts_count for result in topic_results),
                average_percentage=average([result.average_percentage for result in topic_results]),
                best_percentage=average([result.best_percentage for result in topic_results]),
                high_weakness_count=len(
                    [result for result in topic_results if result.weakness_level == "high"]
                ),
                medium_weakness_count=len(
                    [result for result in topic_results if result.weakness_level == "medium"]
                ),
                low_weakness_count=len(
                    [result for result in topic_results if result.weakness_level == "low"]
                ),
            )
        )
    return aggregates
