from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from analytics.topic_result_service import WeakTopicDetector
from backend.models import Lesson, LessonProgress, Recommendation, Test, TestAttempt


@dataclass(frozen=True, slots=True)
class RecommendationRule:
    key: str
    sort_order: int


RULES: tuple[RecommendationRule, ...] = (
    RecommendationRule("low_average", 0),
    RecommendationRule("repeated_failures", 1),
    RecommendationRule("unfinished_lessons", 2),
)


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.weak_topic_detector = WeakTopicDetector(db)

    def get_personal_recommendations(self, user_id: int) -> list[dict]:
        return self._get_recommendations(user_id)

    def get_course_recommendations(self, user_id: int, course_id: int) -> list[dict]:
        return self._get_recommendations(user_id, course_id=course_id)

    def get_module_recommendations(self, user_id: int, module_id: int) -> list[dict]:
        return self._get_recommendations(user_id, module_id=module_id)

    def match_topic_results_with_recommendations(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        topic_results = self.weak_topic_detector.prepare_recommendation_data(
            user_id,
            course_id=course_id,
            module_id=module_id,
        )
        contexts = self._build_contexts(user_id, topic_results)
        recommendations_by_module = self._get_recommendation_entities(contexts.keys())

        matched: list[dict] = []
        for module_id, context in contexts.items():
            recommendations = recommendations_by_module.get(module_id, [])
            matching_rules = self._get_matching_rules(context)
            for recommendation, rule in zip(recommendations, matching_rules):
                matched.append(self.to_frontend_payload(recommendation, context, rule.key))

        return sorted(matched, key=self._recommendation_sort_key)

    def determine_priority(self, context: dict, rule_key: str) -> str:
        if rule_key == "repeated_failures":
            return "high" if context["consecutive_failed_attempts"] >= 3 else "medium"
        if rule_key == "low_average":
            return "high" if context["average_percentage"] < 50 else "medium"
        if context["unfinished_lessons_count"] >= 3:
            return "medium"
        return "low"

    def build_reason_explanation(self, context: dict, rule_key: str) -> str:
        if rule_key == "low_average":
            return (
                f"Средний результат по модулю {context['average_percentage']:.2f}% "
                "ниже порога 60%, поэтому стоит повторить ключевые материалы."
            )
        if rule_key == "repeated_failures":
            return (
                f"Зафиксировано {context['failed_attempts_count']} неуспешных попыток, "
                f"из них подряд {context['consecutive_failed_attempts']}. Рекомендуется точечное повторение."
            )
        return (
            f"В модуле осталось {context['unfinished_lessons_count']} незавершенных уроков. "
            "Их прохождение поможет закрыть пробелы перед следующими попытками."
        )

    def to_frontend_payload(self, recommendation: Recommendation, context: dict, rule_key: str) -> dict:
        return {
            "id": recommendation.id,
            "module_id": recommendation.module_id,
            "module_title": context["module_title"],
            "title": recommendation.title,
            "description": recommendation.description,
            "resource_url": recommendation.resource_url,
            "current_percentage": context["average_percentage"],
            "weakness_level": context["weakness_level"],
            "rule_key": rule_key,
            "priority": self.determine_priority(context, rule_key),
            "reason": self.build_reason_explanation(context, rule_key),
            "topic_reason": context.get("reason"),
        }

    def _get_recommendations(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        return self.match_topic_results_with_recommendations(
            user_id,
            course_id=course_id,
            module_id=module_id,
        )

    def _build_contexts(self, user_id: int, topic_results: list[dict]) -> dict[int, dict]:
        module_ids = [topic["module_id"] for topic in topic_results]
        failed_attempt_metrics = self._get_failed_attempt_metrics(user_id, module_ids)
        unfinished_lessons = self._get_unfinished_lessons_count(user_id, module_ids)

        contexts: dict[int, dict] = {}
        for topic in topic_results:
            module_id = topic["module_id"]
            failed = failed_attempt_metrics.get(
                module_id,
                {"failed_attempts_count": 0, "consecutive_failed_attempts": 0},
            )
            contexts[module_id] = {
                **topic,
                **failed,
                "unfinished_lessons_count": unfinished_lessons.get(module_id, 0),
            }
        return contexts

    def _get_failed_attempt_metrics(self, user_id: int, module_ids: list[int]) -> dict[int, dict]:
        if not module_ids:
            return {}

        attempts = list(
            self.db.scalars(
                select(TestAttempt)
                .join(Test, Test.id == TestAttempt.test_id)
                .where(
                    TestAttempt.user_id == user_id,
                    TestAttempt.finished_at.is_not(None),
                    Test.module_id.in_(module_ids),
                )
                .options(selectinload(TestAttempt.test))
                .order_by(Test.module_id, TestAttempt.finished_at.desc(), TestAttempt.id.desc())
            )
        )

        grouped: dict[int, list[TestAttempt]] = {}
        for attempt in attempts:
            if attempt.test is None or attempt.test.module_id is None:
                continue
            grouped.setdefault(attempt.test.module_id, []).append(attempt)

        metrics: dict[int, dict] = {}
        for module_id, module_attempts in grouped.items():
            failed_attempts_count = len([attempt for attempt in module_attempts if not attempt.is_passed])
            consecutive_failed_attempts = 0
            for attempt in module_attempts:
                if attempt.is_passed:
                    break
                consecutive_failed_attempts += 1
            metrics[module_id] = {
                "failed_attempts_count": failed_attempts_count,
                "consecutive_failed_attempts": consecutive_failed_attempts,
            }
        return metrics

    def _get_unfinished_lessons_count(self, user_id: int, module_ids: list[int]) -> dict[int, int]:
        if not module_ids:
            return {}

        total_lessons = dict(
            self.db.execute(
                select(Lesson.module_id, func.count(Lesson.id))
                .where(Lesson.module_id.in_(module_ids))
                .group_by(Lesson.module_id)
            ).all()
        )
        completed_lessons = dict(
            self.db.execute(
                select(Lesson.module_id, func.count(LessonProgress.id))
                .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
                .where(
                    Lesson.module_id.in_(module_ids),
                    LessonProgress.user_id == user_id,
                    LessonProgress.is_completed.is_(True),
                )
                .group_by(Lesson.module_id)
            ).all()
        )

        return {
            module_id: max(total_lessons.get(module_id, 0) - completed_lessons.get(module_id, 0), 0)
            for module_id in module_ids
        }

    def _get_matching_rules(self, context: dict) -> list[RecommendationRule]:
        matching_rules: list[RecommendationRule] = []
        for rule in RULES:
            if rule.key == "low_average" and context["attempts_count"] > 0 and context["average_percentage"] < 60:
                matching_rules.append(rule)
            elif rule.key == "repeated_failures" and context["failed_attempts_count"] >= 2:
                matching_rules.append(rule)
            elif rule.key == "unfinished_lessons" and context["unfinished_lessons_count"] > 0:
                matching_rules.append(rule)
        return matching_rules

    def _get_recommendation_entities(self, module_ids: list[int]) -> dict[int, list[Recommendation]]:
        if not module_ids:
            return {}

        recommendations = list(
            self.db.scalars(
                select(Recommendation)
                .where(Recommendation.module_id.in_(module_ids))
                .order_by(Recommendation.module_id, Recommendation.id)
            )
        )
        grouped: dict[int, list[Recommendation]] = {}
        for recommendation in recommendations:
            grouped.setdefault(recommendation.module_id, []).append(recommendation)
        return grouped

    def _recommendation_sort_key(self, item: dict) -> tuple[int, float, str]:
        priority_order = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (
            priority_order.get(item["priority"], 99),
            item["current_percentage"],
            item["title"],
        )
