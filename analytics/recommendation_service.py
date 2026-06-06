from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.topic_result_service import WeakTopicDetector
from backend.models import Recommendation


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
        recommendations = self._get_recommendation_entities(topic_results)
        topic_map = {topic["module_id"]: topic for topic in topic_results}

        matched: list[dict] = []
        for recommendation in recommendations:
            topic_result = topic_map.get(recommendation.module_id)
            if topic_result is None:
                continue
            if not self.is_recommendation_suitable(topic_result, recommendation):
                continue
            matched.append(
                self.to_frontend_payload(recommendation, topic_result)
            )
        return sorted(matched, key=self._recommendation_sort_key)

    def is_recommendation_suitable(self, topic_result: dict, recommendation: Recommendation) -> bool:
        if topic_result["attempts_count"] == 0:
            return True
        return topic_result["average_percentage"] <= recommendation.trigger_score_threshold

    def determine_priority(self, topic_result: dict, recommendation: Recommendation) -> str:
        if topic_result["attempts_count"] == 0:
            return "medium"
        if topic_result["weakness_level"] == "high":
            return "high"
        if topic_result["average_percentage"] <= recommendation.trigger_score_threshold - 10:
            return "high"
        if topic_result["weakness_level"] == "medium":
            return "medium"
        return "low"

    def build_reason_explanation(self, topic_result: dict, recommendation: Recommendation) -> str:
        if topic_result["attempts_count"] == 0:
            return (
                "Рекомендация выдана, потому что по теме пока нет завершенных попыток, "
                "и материал полезен для первичного освоения."
            )
        return (
            f"Рекомендация выдана, потому что средний результат по теме составляет "
            f"{topic_result['average_percentage']:.2f}% при пороге {recommendation.trigger_score_threshold:.2f}%."
        )

    def to_frontend_payload(self, recommendation: Recommendation, topic_result: dict) -> dict:
        return {
            "id": recommendation.id,
            "module_id": recommendation.module_id,
            "module_title": topic_result["module_title"],
            "title": recommendation.title,
            "description": recommendation.description,
            "resource_url": recommendation.resource_url,
            "trigger_score_threshold": recommendation.trigger_score_threshold,
            "current_percentage": topic_result["average_percentage"],
            "weakness_level": topic_result["weakness_level"],
            "priority": self.determine_priority(topic_result, recommendation),
            "reason": self.build_reason_explanation(topic_result, recommendation),
            "topic_reason": topic_result.get("reason"),
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

    def _get_recommendation_entities(self, topic_results: list[dict]) -> list[Recommendation]:
        module_ids = [topic["module_id"] for topic in topic_results]
        if not module_ids:
            return []
        return list(
            self.db.scalars(
                select(Recommendation)
                .where(Recommendation.module_id.in_(module_ids))
                .order_by(Recommendation.id)
            )
        )

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
