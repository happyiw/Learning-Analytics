from __future__ import annotations

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from analytics import (
    ProgressService,
    RecommendationService,
    StudentSummaryService,
    TestAnalyticsService,
    TopicResultService,
    WeakTopicDetector,
)
from backend.models import (
    Lesson,
    LessonProgress,
    Module,
    Test,
    TestAttempt,
    TopicResult,
    User,
)
from backend.schemas import (
    AnalyticsDynamicsPointRead,
    PersonalAnalyticsSnapshotRead,
    PersonalRecommendationRead,
    ProgressRead,
    TestAnalyticsRead,
    TopicResultAggregateRead,
    TopicResultRead,
    UserAnalyticsSummaryRead,
)


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def get_modules_for_scope(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[Module]:
    return ProgressService(db).get_modules_for_scope(user_id, course_id=course_id, module_id=module_id)


def build_progress(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> ProgressRead:
    service = ProgressService(db)
    if module_id is not None:
        return service.get_module_progress(user_id, module_id)
    if course_id is not None:
        return service.get_course_progress(user_id, course_id)
    return service.get_overall_progress(user_id)


def compute_topic_result_row(
    db: Session,
    user_id: int,
    module: Module,
) -> TopicResultRead:
    payload = TopicResultService(db).get_module_topic_results(user_id, module.id)
    if not payload:
        return TopicResultRead(
            id=None,
            module_id=module.id,
            module_title=module.title,
            attempts_count=0,
            average_percentage=0.0,
            best_percentage=0.0,
            weakness_level="not_enough_data",
            last_attempt_at=None,
            created_at=module.created_at,
            updated_at=module.updated_at,
        )
    return TopicResultRead(**payload[0])


def compute_topic_results(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[TopicResultRead]:
    service = TopicResultService(db)
    if module_id is not None:
        payload = service.get_module_topic_results(user_id, module_id)
    elif course_id is not None:
        payload = service.get_course_topic_results(user_id, course_id)
    else:
        payload = service.get_user_topic_results(user_id)
    return [TopicResultRead(**item) for item in payload]


def upsert_topic_result(
    db: Session,
    user_id: int,
    module_id: int,
) -> TopicResult | None:
    module = db.get(Module, module_id)
    if module is None:
        return None

    TopicResultService(db).update_topic_result_after_attempt(user_id, module_id)
    return db.scalar(
        select(TopicResult).where(
            TopicResult.user_id == user_id,
            TopicResult.module_id == module_id,
        )
    )


def build_test_analytics(db: Session, user_id: int, test_id: int) -> TestAnalyticsRead:
    payload = TestAnalyticsService(db).build_test_analytics(user_id, test_id)
    return TestAnalyticsRead(**payload)


def build_summary(db: Session, user_id: int) -> UserAnalyticsSummaryRead:
    payload = StudentSummaryService(db).get_summary(user_id)
    return UserAnalyticsSummaryRead(**payload)


def build_dynamics(db: Session, user_id: int) -> list[AnalyticsDynamicsPointRead]:
    payload = StudentSummaryService(db).get_dynamics(user_id)
    return [AnalyticsDynamicsPointRead(**item) for item in payload]


def build_personal_analytics_snapshot(db: Session, user_id: int) -> PersonalAnalyticsSnapshotRead:
    payload = StudentSummaryService(db).build_analytics_snapshot(user_id)
    return PersonalAnalyticsSnapshotRead(
        progress=payload["progress"],
        summary=UserAnalyticsSummaryRead(**payload["summary"]),
        topicResults=[TopicResultRead(**item) for item in payload["topicResults"]],
        weakTopics=[TopicResultRead(**item) for item in payload["weakTopics"]],
        bestTopics=[TopicResultRead(**item) for item in payload["bestTopics"]],
        dynamics=[AnalyticsDynamicsPointRead(**item) for item in payload["dynamics"]],
    )


def build_weak_topics(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[TopicResultRead]:
    payload = WeakTopicDetector(db).get_weak_topics(
        user_id,
        course_id=course_id,
        module_id=module_id,
    )
    return [TopicResultRead(**item) for item in payload]


def build_best_topics(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[TopicResultRead]:
    payload = WeakTopicDetector(db).get_strong_topics(
        user_id,
        course_id=course_id,
        module_id=module_id,
    )
    return [TopicResultRead(**item) for item in payload]


def build_personal_recommendations(
    db: Session,
    user_id: int,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[PersonalRecommendationRead]:
    service = RecommendationService(db)
    if module_id is not None:
        payload = service.get_module_recommendations(user_id, module_id)
    elif course_id is not None:
        payload = service.get_course_recommendations(user_id, course_id)
    else:
        payload = service.get_personal_recommendations(user_id)
    return [PersonalRecommendationRead(**item) for item in payload]


def build_topic_result_aggregates(
    db: Session,
    course_id: int | None = None,
    module_id: int | None = None,
    group_id: str | None = None,
) -> list[TopicResultAggregateRead]:
    if module_id is not None:
        module = db.get(Module, module_id)
        modules = [module] if module else []
    elif course_id is not None:
        modules = list(
            db.scalars(
                select(Module).where(Module.course_id == course_id).order_by(Module.order, Module.id)
            )
        )
    else:
        modules = list(db.scalars(select(Module).order_by(Module.order, Module.id)))

    if group_id is not None:
        users = list(db.scalars(select(User).where(User.group == group_id)))
    else:
        lesson_stmt = select(Lesson.id).join(Module, Module.id == Lesson.module_id)
        if module_id is not None:
            lesson_stmt = lesson_stmt.where(Lesson.module_id == module_id)
        elif course_id is not None:
            lesson_stmt = lesson_stmt.where(Module.course_id == course_id)
        lesson_ids = list(db.scalars(lesson_stmt))

        test_stmt = select(Test.id)
        if module_id is not None:
            test_stmt = test_stmt.where(Test.module_id == module_id)
        elif course_id is not None:
            test_stmt = test_stmt.where(Test.course_id == course_id)
        test_ids = list(db.scalars(test_stmt))

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
