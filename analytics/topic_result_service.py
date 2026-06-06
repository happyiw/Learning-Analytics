from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.progress_service import ProgressService
from backend.models import Module, TestAttempt, TopicResult


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
        topic_result.attempts_count = values["attempts_count"]
        topic_result.average_percentage = values["average_percentage"]
        topic_result.best_percentage = values["best_percentage"]
        topic_result.weakness_level = values["weakness_level"]
        topic_result.last_attempt_at = values["last_attempt_at"]
        self.db.flush()
        return self._serialize_topic_result(topic_result, module)

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

    def calculate_average_percentage(self, attempts: list[TestAttempt]) -> float:
        if not attempts:
            return 0.0
        return round(sum(attempt.percentage for attempt in attempts) / len(attempts), 2)

    def calculate_best_percentage(self, attempts: list[TestAttempt]) -> float:
        if not attempts:
            return 0.0
        return round(max(attempt.percentage for attempt in attempts), 2)

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
        existing = self.db.scalar(
            select(TopicResult).where(
                TopicResult.user_id == user_id,
                TopicResult.module_id == module.id,
            )
        )
        values = self._calculate_topic_result_values(user_id, module.id)
        payload = {
            "id": existing.id if existing else None,
            "module_id": module.id,
            "module_title": module.title,
            "attempts_count": values["attempts_count"],
            "average_percentage": values["average_percentage"],
            "best_percentage": values["best_percentage"],
            "weakness_level": values["weakness_level"],
            "last_attempt_at": values["last_attempt_at"],
            "created_at": existing.created_at if existing else module.created_at,
            "updated_at": existing.updated_at if existing else module.updated_at,
        }
        return payload

    def _calculate_topic_result_values(self, user_id: int, module_id: int) -> dict:
        attempts = self._get_finished_attempts(user_id, module_id)
        attempts_count = len(attempts)
        average_percentage = self.calculate_average_percentage(attempts)
        best_percentage = self.calculate_best_percentage(attempts)
        weakness_level = self.calculate_weakness_level(average_percentage, attempts_count)
        last_attempt_at = attempts[-1].finished_at if attempts else None
        return {
            "attempts_count": attempts_count,
            "average_percentage": average_percentage,
            "best_percentage": best_percentage,
            "weakness_level": weakness_level,
            "last_attempt_at": last_attempt_at,
        }

    def _get_finished_attempts(self, user_id: int, module_id: int) -> list[TestAttempt]:
        test_ids = self.progress_service.get_scope_test_ids(user_id, module_id=module_id)
        if not test_ids:
            return []
        return list(
            self.db.scalars(
                select(TestAttempt)
                .where(
                    TestAttempt.user_id == user_id,
                    TestAttempt.finished_at.is_not(None),
                    TestAttempt.test_id.in_(test_ids),
                )
                .order_by(TestAttempt.finished_at, TestAttempt.id)
            )
        )

    def _serialize_topic_result(self, topic_result: TopicResult, module: Module) -> dict:
        return {
            "id": topic_result.id,
            "module_id": module.id,
            "module_title": module.title,
            "attempts_count": topic_result.attempts_count,
            "average_percentage": round(topic_result.average_percentage, 2),
            "best_percentage": round(topic_result.best_percentage, 2),
            "weakness_level": topic_result.weakness_level,
            "last_attempt_at": topic_result.last_attempt_at,
            "created_at": topic_result.created_at,
            "updated_at": topic_result.updated_at,
        }
