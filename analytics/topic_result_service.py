from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from analytics.progress_service import ProgressService
from backend.attempt_metrics import build_attempt_percentage_expression
from backend.models import Module, Test, TestAttempt, TopicResult


class TopicResultService:
    def __init__(self, db: Session):
        self.db = db
        self.progress_service = ProgressService(db)

    def update_topic_result_after_attempt(self, user_id: int, module_id: int) -> dict:
        module = self.db.get(Module, module_id)
        if module is None:
            return {}

        values = self._calculate_topic_result_values(user_id, module_id)
        topic_result = self.get_or_create_topic_result(user_id, module_id)
        topic_result.last_attempt_at = values["last_attempt_at"]
        self.db.flush()
        return self._serialize_topic_result(topic_result, module, values)

    def get_or_create_topic_result(self, user_id: int, module_id: int) -> TopicResult:
        topic_result = self.db.scalar(
            select(TopicResult).where(
                TopicResult.user_id == user_id,
                TopicResult.module_id == module_id,
            )
        )
        if topic_result is None:
            topic_result = TopicResult(user_id=user_id, module_id=module_id)
            self.db.add(topic_result)
        return topic_result

    def calculate_weakness_level(self, average_percentage: float, attempts_count: int) -> str:
        if attempts_count == 0:
            return "not_enough_data"
        if average_percentage < 50:
            return "high"
        if average_percentage < 70:
            return "medium"
        if average_percentage < 85:
            return "low"
        return "none"

    def get_user_topic_results(self, user_id: int) -> list[dict]:
        return self._get_scope_topic_results(user_id)

    def get_course_topic_results(self, user_id: int, course_id: int) -> list[dict]:
        return self._get_scope_topic_results(user_id, course_id=course_id)

    def get_module_topic_results(self, user_id: int, module_id: int) -> list[dict]:
        return self._get_scope_topic_results(user_id, module_id=module_id)

    def _get_scope_topic_results(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        modules = self.progress_service.get_modules_for_scope(
            user_id,
            course_id=course_id,
            module_id=module_id,
        )
        return [self._build_topic_result_payload(user_id, module) for module in modules]

    def _build_topic_result_payload(self, user_id: int, module: Module) -> dict:
        topic_result = self.db.scalar(
            select(TopicResult).where(
                TopicResult.user_id == user_id,
                TopicResult.module_id == module.id,
            )
        )
        values = self._calculate_topic_result_values(user_id, module.id)
        return self._serialize_topic_result(topic_result, module, values)

    def _calculate_topic_result_values(self, user_id: int, module_id: int) -> dict:
        percentage_expr = build_attempt_percentage_expression(
            TestAttempt.score,
            TestAttempt.max_score,
        )
        row = self.db.execute(
            select(
                func.count(TestAttempt.id),
                func.avg(percentage_expr),
                func.max(percentage_expr),
                func.max(TestAttempt.finished_at),
            )
            .join(Test, Test.id == TestAttempt.test_id)
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.finished_at.is_not(None),
                Test.module_id == module_id,
            )
        ).one()

        attempts_count = int(row[0] or 0)
        average_percentage = round(float(row[1] or 0.0), 2)
        best_percentage = round(float(row[2] or 0.0), 2)
        return {
            "attempts_count": attempts_count,
            "average_percentage": average_percentage,
            "best_percentage": best_percentage,
            "weakness_level": self.calculate_weakness_level(average_percentage, attempts_count),
            "last_attempt_at": row[3],
        }

    def _serialize_topic_result(
        self,
        topic_result: TopicResult | None,
        module: Module,
        values: dict,
    ) -> dict:
        return {
            "id": topic_result.id if topic_result else None,
            "module_id": module.id,
            "module_title": module.title,
            "attempts_count": values["attempts_count"],
            "average_percentage": values["average_percentage"],
            "best_percentage": values["best_percentage"],
            "weakness_level": values["weakness_level"],
            "last_attempt_at": values["last_attempt_at"],
            "updated_at": topic_result.updated_at if topic_result else None,
        }


class WeakTopicDetector:
    def __init__(self, db: Session):
        self.db = db
        self.topic_result_service = TopicResultService(db)

    def get_weak_topics(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        topics = self._get_topics(user_id, course_id=course_id, module_id=module_id)
        weak_topics = [
            self._attach_weak_reason(topic)
            for topic in topics
            if self._is_weak_topic(topic)
        ]
        return self.sort_topics_by_problem_severity(weak_topics)

    def get_strong_topics(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        topics = self._get_topics(user_id, course_id=course_id, module_id=module_id)
        strong_topics = [
            self._attach_strong_reason(topic)
            for topic in topics
            if self._is_strong_topic(topic)
        ]
        return self.sort_topics_by_success(strong_topics)

    def sort_topics_by_problem_severity(self, topics: list[dict]) -> list[dict]:
        severity_order = {
            "not_enough_data": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "none": 4,
        }
        return sorted(
            topics,
            key=lambda item: (
                severity_order.get(item["weakness_level"], 99),
                item["average_percentage"],
                item["best_percentage"],
                item["module_title"],
            ),
        )

    def sort_topics_by_success(self, topics: list[dict]) -> list[dict]:
        return sorted(
            topics,
            key=lambda item: (
                -item["best_percentage"],
                -item["average_percentage"],
                -item["attempts_count"],
                item["module_title"],
            ),
        )

    def determine_weak_topic_reason(self, topic_result: dict) -> str:
        attempts_count = topic_result["attempts_count"]
        average_percentage = topic_result["average_percentage"]
        best_percentage = topic_result["best_percentage"]
        weakness_level = topic_result["weakness_level"]

        if attempts_count == 0:
            return "Недостаточно данных: пользователь еще не завершал тесты по этой теме."
        if weakness_level == "high":
            return (
                f"Средний результат по теме составляет {average_percentage:.2f}%, "
                "что указывает на выраженные трудности в освоении материала."
            )
        if weakness_level == "medium":
            return (
                f"Средний результат по теме составляет {average_percentage:.2f}%, "
                "поэтому тему стоит дополнительно повторить и закрепить."
            )
        if weakness_level == "low":
            return (
                f"Тема в целом усвоена, но средний результат {average_percentage:.2f}% "
                f"и лучший результат {best_percentage:.2f}% оставляют пространство для улучшения."
            )
        return "Тема не относится к слабым, но включена в общую аналитику."

    def determine_strong_topic_reason(self, topic_result: dict) -> str:
        attempts_count = topic_result["attempts_count"]
        average_percentage = topic_result["average_percentage"]
        best_percentage = topic_result["best_percentage"]

        if attempts_count == 0:
            return "Тема пока не оценена: завершенных попыток нет."
        if average_percentage >= 90:
            return f"Средний результат {average_percentage:.2f}% показывает устойчиво высокое освоение темы."
        if best_percentage >= 90:
            return (
                f"Лучший результат {best_percentage:.2f}% показывает, "
                "что тема может считаться одной из сильных сторон пользователя."
            )
        return (
            f"Средний результат {average_percentage:.2f}% и лучший результат {best_percentage:.2f}% "
            "позволяют считать тему одной из наиболее успешно освоенных."
        )

    def prepare_analytics_data(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> dict:
        topics = [
            self._attach_analytics_reason(topic)
            for topic in self._get_topics(user_id, course_id=course_id, module_id=module_id)
        ]
        return {
            "topic_results": topics,
            "weak_topics": self.get_weak_topics(user_id, course_id=course_id, module_id=module_id),
            "best_topics": self.get_strong_topics(user_id, course_id=course_id, module_id=module_id),
        }

    def prepare_recommendation_data(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        topics = self._get_topics(user_id, course_id=course_id, module_id=module_id)
        prepared: list[dict] = []
        for topic in topics:
            item = dict(topic)
            item["is_weak_topic"] = self._is_weak_topic(item, include_not_enough_data=True)
            item["is_strong_topic"] = self._is_strong_topic(item)
            item["reason"] = (
                self.determine_weak_topic_reason(item)
                if item["is_weak_topic"]
                else self.determine_strong_topic_reason(item)
            )
            prepared.append(item)
        return prepared

    def _get_topics(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        if module_id is not None:
            return self.topic_result_service.get_module_topic_results(user_id, module_id)
        if course_id is not None:
            return self.topic_result_service.get_course_topic_results(user_id, course_id)
        return self.topic_result_service.get_user_topic_results(user_id)

    def _is_weak_topic(self, topic_result: dict, include_not_enough_data: bool = False) -> bool:
        if topic_result["attempts_count"] == 0:
            return include_not_enough_data
        return topic_result["weakness_level"] in {"high", "medium", "low"}

    def _is_strong_topic(self, topic_result: dict) -> bool:
        return topic_result["attempts_count"] > 0 and (
            topic_result["weakness_level"] == "none"
            or topic_result["average_percentage"] >= 85
            or topic_result["best_percentage"] >= 90
        )

    def _attach_weak_reason(self, topic_result: dict) -> dict:
        item = dict(topic_result)
        item["reason"] = self.determine_weak_topic_reason(item)
        item["category"] = "weak"
        return item

    def _attach_strong_reason(self, topic_result: dict) -> dict:
        item = dict(topic_result)
        item["reason"] = self.determine_strong_topic_reason(item)
        item["category"] = "strong"
        return item

    def _attach_analytics_reason(self, topic_result: dict) -> dict:
        if self._is_weak_topic(topic_result, include_not_enough_data=True):
            return self._attach_weak_reason(topic_result)
        if self._is_strong_topic(topic_result):
            return self._attach_strong_reason(topic_result)
        item = dict(topic_result)
        item["reason"] = (
            f"Тема находится в промежуточной зоне: средний результат {item['average_percentage']:.2f}%."
        )
        item["category"] = "neutral"
        return item
