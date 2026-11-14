from __future__ import annotations

from collections import defaultdict

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.recommendation_service import RecommendationService
from backend.models import (
    Course,
    CourseEnrollment,
    Lesson,
    LessonProgress,
    Module,
    Recommendation,
    StudentModuleMetric,
    Test,
    TestAttempt,
)
from backend.schemas import (
    AnalyticsDynamicsPointRead,
    PersonalAnalyticsSnapshotRead,
    PersonalRecommendationRead,
    ProgressRead,
    TopicResultRead,
    UserAnalyticsSummaryRead,
)

MAX_DYNAMICS_POINTS = 100
MAX_PERSONAL_RECOMMENDATIONS = 20


def _percentage(score, max_score):
    return case((max_score > 0, score * 100.0 / max_score), else_=0.0)


def _scope_filters(course_id: int | None, module_id: int | None) -> list:
    filters: list = []
    if module_id is not None:
        filters.append(Module.id == module_id)
    elif course_id is not None:
        filters.append(Module.course_id == course_id)
    return filters


async def build_progress_from_read_model(
    db: AsyncSession,
    user_id: int,
    *,
    course_id: int | None = None,
    module_id: int | None = None,
) -> ProgressRead:
    module_filters = _scope_filters(course_id, module_id)

    lesson_scope = (
        select(Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .join(Course, Course.id == Module.course_id)
        .join(
            CourseEnrollment,
            and_(
                CourseEnrollment.course_id == Module.course_id,
                CourseEnrollment.user_id == user_id,
            ),
        )
        .where(Course.is_published.is_(True), *module_filters)
    )
    test_scope = (
        select(Test.id)
        .join(Module, Module.id == Test.module_id)
        .join(Course, Course.id == Module.course_id)
        .join(
            CourseEnrollment,
            and_(
                CourseEnrollment.course_id == Module.course_id,
                CourseEnrollment.user_id == user_id,
            ),
        )
        .where(Course.is_published.is_(True), Test.is_active.is_(True), *module_filters)
    )
    percentage = _percentage(TestAttempt.score, TestAttempt.max_score)
    total_lessons = select(func.count()).select_from(lesson_scope.subquery()).scalar_subquery()
    completed_lessons = (
        select(func.count(LessonProgress.id))
        .where(
            LessonProgress.user_id == user_id,
            LessonProgress.is_completed.is_(True),
            LessonProgress.lesson_id.in_(lesson_scope),
        )
        .scalar_subquery()
    )
    total_tests = select(func.count()).select_from(test_scope.subquery()).scalar_subquery()
    passed_tests = (
        select(func.count(distinct(TestAttempt.test_id)))
        .join(Test, Test.id == TestAttempt.test_id)
        .where(
            TestAttempt.user_id == user_id,
            TestAttempt.finished_at.is_not(None),
            TestAttempt.test_id.in_(test_scope),
            percentage >= Test.passing_score,
        )
        .scalar_subquery()
    )
    average_test_percentage = (
        select(func.coalesce(func.avg(percentage), 0.0))
        .where(
            TestAttempt.user_id == user_id,
            TestAttempt.finished_at.is_not(None),
            TestAttempt.test_id.in_(test_scope),
        )
        .scalar_subquery()
    )

    row = (
        await db.execute(
            select(
                total_lessons.label("total_lessons"),
                completed_lessons.label("completed_lessons"),
                total_tests.label("total_tests"),
                passed_tests.label("passed_tests"),
                average_test_percentage.label("average_test_percentage"),
            )
        )
    ).one()
    denominator = int(row.total_lessons) + int(row.total_tests)
    completion_rate = (
        round((int(row.completed_lessons) + int(row.passed_tests)) * 100 / denominator, 2)
        if denominator
        else 0.0
    )
    scope_type = "module" if module_id is not None else "course" if course_id is not None else "global"
    return ProgressRead(
        scope_type=scope_type,
        scope_id=module_id if module_id is not None else course_id,
        completed_lessons=int(row.completed_lessons),
        total_lessons=int(row.total_lessons),
        passed_tests=int(row.passed_tests),
        total_tests=int(row.total_tests),
        average_test_percentage=round(float(row.average_test_percentage), 2),
        completion_rate=completion_rate,
    )


async def _load_topics(
    db: AsyncSession,
    user_id: int,
    *,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[dict]:
    stmt = (
        select(Module, StudentModuleMetric)
        .join(Course, Course.id == Module.course_id)
        .join(
            CourseEnrollment,
            and_(
                CourseEnrollment.course_id == Module.course_id,
                CourseEnrollment.user_id == user_id,
            ),
        )
        .outerjoin(
            StudentModuleMetric,
            and_(
                StudentModuleMetric.module_id == Module.id,
                StudentModuleMetric.user_id == user_id,
            ),
        )
        .where(Course.is_published.is_(True), *_scope_filters(course_id, module_id))
        .order_by(Module.course_id, Module.order, Module.id)
    )
    rows = (await db.execute(stmt)).all()
    return [_topic_dict(module, metric) for module, metric in rows]


def _topic_dict(module: Module, metric: StudentModuleMetric | None) -> dict:
    values = {
        "id": metric.id if metric else None,
        "module_id": module.id,
        "module_title": module.title,
        "attempts_count": metric.attempts_count if metric else 0,
        "average_percentage": metric.average_percentage if metric else 0.0,
        "best_percentage": metric.best_percentage if metric else 0.0,
        "last_percentage": metric.last_percentage if metric else 0.0,
        "first_percentage": metric.first_percentage if metric else 0.0,
        "progress_delta": metric.progress_delta if metric else 0.0,
        "trend": metric.trend if metric else "not_enough_data",
        "stability_index": metric.stability_index if metric else None,
        "completed_lessons_ratio": metric.completed_lessons_ratio if metric else 0.0,
        "completed_attempts_count": metric.completed_attempts_count if metric else 0,
        "passed_attempts_count": metric.passed_attempts_count if metric else 0,
        "failed_attempts_count": metric.failed_attempts_count if metric else 0,
        "weakness_level": metric.weakness_level if metric else "not_enough_data",
        "risk_level": metric.risk_level if metric else "medium",
        "learning_state": metric.learning_state if metric else "not_enough_data",
        "reason_code": metric.reason_code if metric else "no_progress",
        "last_attempt_at": metric.last_attempt_at if metric else None,
        "updated_at": metric.computed_at if metric else None,
        "is_weak_topic": metric.is_weak_topic if metric else False,
        "is_strong_topic": metric.is_strong_topic if metric else False,
    }
    category = _topic_category(values)
    values["category"] = category
    values["reason"] = _topic_reason(values, category)
    values["tags"] = _topic_tags(values, category)
    return values


def _topic_category(topic: dict) -> str:
    if topic["completed_attempts_count"] < 2:
        return "not_enough_data"
    if topic["is_weak_topic"]:
        return "weak"
    if topic["is_strong_topic"]:
        return "strong"
    if topic["learning_state"] == "unstable" or (
        topic["stability_index"] is not None and topic["stability_index"] < 0.55
    ):
        return "unstable"
    if topic["trend"] == "improving" or topic["progress_delta"] >= 15:
        return "improving"
    return "neutral"


def _topic_reason(topic: dict, category: str) -> str:
    if category == "not_enough_data":
        return "По теме пока недостаточно завершенных попыток для устойчивого вывода."
    if category == "weak":
        return f"Средний результат {topic['average_percentage']:.2f}%; тема требует повторения."
    if category == "strong":
        return f"Тема освоена: средний результат {topic['average_percentage']:.2f}%."
    if category == "unstable":
        return "Результаты заметно колеблются между попытками."
    if category == "improving":
        return "Последние попытки показывают положительную динамику."
    return f"Средний результат по теме составляет {topic['average_percentage']:.2f}%."


def _topic_tags(topic: dict, category: str) -> list[str]:
    tags: list[str] = []
    if category == "weak":
        tags.append("нуждается в пересмотре")
    if category == "unstable":
        tags.append("нестабильный результат")
    if category == "improving":
        tags.append("улучшение")
    if topic["risk_level"] == "high":
        tags.append("высокий риск")
    if topic["completed_lessons_ratio"] < 0.75:
        tags.append("теория не завершена")
    if category == "strong":
        tags.append("освоен")
    if category == "not_enough_data":
        tags.append("недостаточно данных")
    return tags


async def _load_dynamics(db: AsyncSession, user_id: int) -> list[AnalyticsDynamicsPointRead]:
    percentage = _percentage(TestAttempt.score, TestAttempt.max_score)
    rows = (
        await db.execute(
            select(
                TestAttempt.id,
                TestAttempt.finished_at,
                TestAttempt.started_at,
                Test.id.label("test_id"),
                Test.title.label("test_title"),
                Test.passing_score,
                Module.id.label("module_id"),
                Module.title.label("module_title"),
                percentage.label("percentage"),
            )
            .join(Test, Test.id == TestAttempt.test_id)
            .outerjoin(Module, Module.id == Test.module_id)
            .where(TestAttempt.user_id == user_id, TestAttempt.finished_at.is_not(None))
            .order_by(TestAttempt.finished_at.desc(), TestAttempt.id.desc())
            .limit(MAX_DYNAMICS_POINTS)
        )
    ).all()
    return [
        AnalyticsDynamicsPointRead(
            attempt_id=row.id,
            date=row.finished_at or row.started_at,
            test_id=row.test_id,
            test_title=row.test_title,
            module_id=row.module_id,
            module_title=row.module_title,
            percentage=round(float(row.percentage), 2),
            is_passed=float(row.percentage) >= float(row.passing_score),
        )
        for row in reversed(rows)
    ]


async def build_personal_snapshot_from_read_model(
    db: AsyncSession,
    user_id: int,
) -> PersonalAnalyticsSnapshotRead:
    topics = await _load_topics(db, user_id)
    progress = await build_progress_from_read_model(db, user_id)
    dynamics = await _load_dynamics(db, user_id)

    completed_attempts = sum(item["completed_attempts_count"] for item in topics)
    average_percentage = (
        sum(item["average_percentage"] * item["completed_attempts_count"] for item in topics)
        / completed_attempts
        if completed_attempts
        else 0.0
    )
    average_score = float(
        await db.scalar(
            select(func.coalesce(func.avg(TestAttempt.score), 0.0)).where(
                TestAttempt.user_id == user_id,
                TestAttempt.finished_at.is_not(None),
            )
        )
        or 0.0
    )
    unique_courses_started = int(
        await db.scalar(
            select(func.count(distinct(Test.course_id)))
            .join(TestAttempt, TestAttempt.test_id == Test.id)
            .where(TestAttempt.user_id == user_id)
        )
        or 0
    )
    summary = UserAnalyticsSummaryRead(
        total_attempts=sum(item["attempts_count"] for item in topics),
        completed_attempts=completed_attempts,
        passed_attempts=sum(item["passed_attempts_count"] for item in topics),
        average_score=round(average_score, 2),
        average_percentage=round(average_percentage, 2),
        lessons_completed=progress.completed_lessons,
        unique_courses_started=unique_courses_started,
    )

    topic_models = [TopicResultRead(**item) for item in topics]
    by_category = defaultdict(list)
    for item in topic_models:
        by_category[item.category].append(item)
    weak = sorted(by_category["weak"], key=lambda item: (item.average_percentage, item.module_title))
    strong = sorted(by_category["strong"], key=lambda item: (-item.average_percentage, item.module_title))
    unstable = sorted(
        by_category["unstable"],
        key=lambda item: (item.stability_index if item.stability_index is not None else 1.0),
    )
    improving = sorted(by_category["improving"], key=lambda item: -item.progress_delta)
    not_enough = sorted(by_category["not_enough_data"], key=lambda item: item.module_title)
    return PersonalAnalyticsSnapshotRead(
        progress=progress,
        summary=summary,
        topicResults=topic_models,
        weakTopics=weak,
        strongTopics=strong,
        bestTopics=strong,
        unstableTopics=unstable,
        improvingTopics=improving,
        topicsWithoutEnoughData=not_enough,
        dynamics=dynamics,
    )


async def build_personal_recommendations_from_read_model(
    db: AsyncSession,
    user_id: int,
    *,
    course_id: int | None = None,
    module_id: int | None = None,
) -> list[PersonalRecommendationRead]:
    topics = await _load_topics(db, user_id, course_id=course_id, module_id=module_id)
    candidates = [item for item in topics if not item["is_strong_topic"]]
    module_ids = [item["module_id"] for item in candidates]
    if not module_ids:
        return []

    attempt_rows = (
        await db.execute(
            select(Test.module_id, TestAttempt.score, TestAttempt.max_score, Test.passing_score)
            .join(Test, Test.id == TestAttempt.test_id)
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.finished_at.is_not(None),
                Test.module_id.in_(module_ids),
            )
            .order_by(Test.module_id, TestAttempt.finished_at.desc(), TestAttempt.id.desc())
        )
    ).all()
    failure_streaks: dict[int, int] = defaultdict(int)
    streak_open: dict[int, bool] = defaultdict(lambda: True)
    for row in attempt_rows:
        if row.module_id is None or not streak_open[row.module_id]:
            continue
        percentage = float(row.score) * 100 / float(row.max_score) if row.max_score else 0.0
        if percentage >= float(row.passing_score):
            streak_open[row.module_id] = False
        else:
            failure_streaks[row.module_id] += 1

    recommendation_rows = list(
        (
            await db.scalars(
                select(Recommendation)
                .where(Recommendation.module_id.in_(module_ids))
                .order_by(Recommendation.module_id, Recommendation.id)
            )
        ).all()
    )
    recommendations_by_module: dict[int, list[Recommendation]] = defaultdict(list)
    for recommendation in recommendation_rows:
        recommendations_by_module[recommendation.module_id].append(recommendation)

    rule_service = RecommendationService(db)  # Pure rule methods; no synchronous IO is used.
    result: list[dict] = []
    for topic in candidates:
        context = {
            **topic,
            "failure_streak": failure_streaks[topic["module_id"]],
            "current_result": topic["last_percentage"] if topic["completed_attempts_count"] else 0.0,
            "topic_state": topic["learning_state"],
            "unfinished_lessons_count": 1 if topic["completed_lessons_ratio"] < 1 else 0,
        }
        rules = rule_service._get_matching_rules(context)
        for recommendation, rule in zip(recommendations_by_module[topic["module_id"]], rules):
            result.append(rule_service.to_frontend_payload(recommendation, context, rule.key))

    result.sort(key=rule_service._recommendation_sort_key)
    return [PersonalRecommendationRead(**item) for item in result[:MAX_PERSONAL_RECOMMENDATIONS]]
