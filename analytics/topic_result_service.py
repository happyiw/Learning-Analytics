from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from analytics.progress_service import ProgressService
from backend.models import Lesson, LessonProgress, Module, Test, TestAttempt, TopicResult


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

    def calculate_topic_state(
        self,
        average_percentage: float,
        completed_attempts_count: int,
        passed_attempts_count: int,
        failed_attempts_count: int,
        progress_trend: str,
        stability_index: float | None,
        completed_lessons_ratio: float,
    ) -> dict:
        if completed_attempts_count == 0:
            return {
                "weakness_level": "none",
                "risk_level": "high" if completed_lessons_ratio < 0.5 else "medium",
                "learning_state": "not_enough_data",
                "reason_code": "unfinished_lessons" if completed_lessons_ratio < 1 else "no_progress",
            }

        failure_rate = failed_attempts_count / completed_attempts_count if completed_attempts_count else 0.0
        weakness_level = self._calculate_weakness_level_from_average(average_percentage)

        if (
            average_percentage >= 90
            and passed_attempts_count == completed_attempts_count
            and completed_lessons_ratio >= 0.8
            and (stability_index is None or stability_index >= 0.7)
        ):
            learning_state = "mastered"
        elif stability_index is not None and stability_index < 0.45:
            learning_state = "unstable"
        elif progress_trend == "improving":
            learning_state = "improving"
        else:
            learning_state = "stagnant"

        if failure_rate >= 0.6 or weakness_level == "high":
            risk_level = "high"
        elif failure_rate >= 0.3 or weakness_level in {"medium", "low"} or completed_lessons_ratio < 0.75:
            risk_level = "medium"
        else:
            risk_level = "low"

        reason_code: str | None
        if failure_rate >= 0.6:
            reason_code = "high_failure_rate"
        elif average_percentage < 60:
            reason_code = "low_average"
        elif completed_lessons_ratio < 0.5:
            reason_code = "unfinished_lessons"
        elif learning_state in {"stagnant", "unstable"}:
            reason_code = "no_progress"
        else:
            reason_code = None

        return {
            "weakness_level": weakness_level,
            "risk_level": risk_level,
            "learning_state": learning_state,
            "reason_code": reason_code,
        }

    def calculate_weakness_level(self, average_percentage: float, attempts_count: int) -> str:
        if attempts_count == 0:
            return "not_enough_data"
        return self._calculate_weakness_level_from_average(average_percentage)

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
        attempts = list(
            self.db.scalars(
                select(TestAttempt)
                .join(Test, Test.id == TestAttempt.test_id)
                .where(
                    TestAttempt.user_id == user_id,
                    Test.module_id == module_id,
                )
                .options(selectinload(TestAttempt.test))
                .order_by(TestAttempt.started_at, TestAttempt.id)
            )
        )
        completed_attempts = [attempt for attempt in attempts if attempt.finished_at is not None]
        percentages = [attempt.percentage for attempt in completed_attempts]

        attempts_count = len(attempts)
        completed_attempts_count = len(completed_attempts)
        average_percentage = round(sum(percentages) / completed_attempts_count, 2) if completed_attempts_count else 0.0
        best_percentage = round(max(percentages), 2) if percentages else 0.0
        first_percentage = round(percentages[0], 2) if percentages else 0.0
        last_percentage = round(percentages[-1], 2) if percentages else 0.0
        progress_delta = round(last_percentage - first_percentage, 2) if percentages else 0.0
        passed_attempts_count = len([attempt for attempt in completed_attempts if attempt.is_passed])
        failed_attempts_count = completed_attempts_count - passed_attempts_count
        last_attempt_at = completed_attempts[-1].finished_at if completed_attempts else None
        completed_lessons_ratio = self._get_module_lesson_completion_ratio(user_id, module_id)
        progress_trend = self._calculate_progress_trend(percentages)
        stability_index = self._calculate_stability_index(percentages)
        topic_state = self.calculate_topic_state(
            average_percentage=average_percentage,
            completed_attempts_count=completed_attempts_count,
            passed_attempts_count=passed_attempts_count,
            failed_attempts_count=failed_attempts_count,
            progress_trend=progress_trend,
            stability_index=stability_index,
            completed_lessons_ratio=completed_lessons_ratio,
        )

        return {
            "attempts_count": attempts_count,
            "average_percentage": average_percentage,
            "best_percentage": best_percentage,
            "last_percentage": last_percentage,
            "first_percentage": first_percentage,
            "progress_delta": progress_delta,
            "last_attempt_at": last_attempt_at,
            "completed_attempts_count": completed_attempts_count,
            "passed_attempts_count": passed_attempts_count,
            "failed_attempts_count": failed_attempts_count,
            "trend": progress_trend,
            "stability_index": stability_index,
            "completed_lessons_ratio": completed_lessons_ratio,
            **topic_state,
        }

    def _calculate_progress_trend(self, percentages: list[float]) -> str:
        if len(percentages) < 2:
            return "not_enough_data"

        progress_delta = percentages[-1] - percentages[0]
        if progress_delta >= 5:
            return "improving"
        if progress_delta <= -5:
            return "declining"
        return "stable"

    def _calculate_stability_index(self, percentages: list[float]) -> float | None:
        if len(percentages) < 2:
            return None

        spread = max(percentages) - min(percentages)
        return round(max(0.0, 1.0 - (spread / 100.0)), 4)

    def _get_module_lesson_completion_ratio(self, user_id: int, module_id: int) -> float:
        total_lessons = int(
            self.db.scalar(
                select(func.count(Lesson.id)).where(Lesson.module_id == module_id)
            )
            or 0
        )
        if total_lessons == 0:
            return 0.0

        completed_lessons = int(
            self.db.scalar(
                select(func.count(LessonProgress.id))
                .join(Lesson, Lesson.id == LessonProgress.lesson_id)
                .where(
                    Lesson.module_id == module_id,
                    LessonProgress.user_id == user_id,
                    LessonProgress.is_completed.is_(True),
                )
            )
            or 0
        )
        return round(completed_lessons / total_lessons, 4)

    def _calculate_weakness_level_from_average(self, average_percentage: float) -> str:
        if average_percentage < 50:
            return "high"
        if average_percentage < 70:
            return "medium"
        if average_percentage < 85:
            return "low"
        return "none"

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
            "last_percentage": values["last_percentage"],
            "first_percentage": values["first_percentage"],
            "progress_delta": values["progress_delta"],
            "trend": values["trend"],
            "stability_index": values["stability_index"],
            "completed_lessons_ratio": values["completed_lessons_ratio"],
            "completed_attempts_count": values["completed_attempts_count"],
            "passed_attempts_count": values["passed_attempts_count"],
            "failed_attempts_count": values["failed_attempts_count"],
            "weakness_level": values["weakness_level"],
            "risk_level": values["risk_level"],
            "learning_state": values["learning_state"],
            "reason_code": values["reason_code"],
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
            self._decorate_topic(topic, "weak")
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
            self._decorate_topic(topic, "strong")
            for topic in topics
            if self._is_strong_topic(topic)
        ]
        return self.sort_topics_by_success(strong_topics)

    def get_unstable_topics(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        topics = self._get_topics(user_id, course_id=course_id, module_id=module_id)
        unstable_topics = [
            self._decorate_topic(topic, "unstable")
            for topic in topics
            if self._is_unstable_topic(topic)
        ]
        return self.sort_topics_by_instability(unstable_topics)

    def get_improving_topics(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        topics = self._get_topics(user_id, course_id=course_id, module_id=module_id)
        improving_topics = [
            self._decorate_topic(topic, "improving")
            for topic in topics
            if self._is_improving_topic(topic)
        ]
        return self.sort_topics_by_growth(improving_topics)

    def get_topics_without_enough_data(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[dict]:
        topics = self._get_topics(user_id, course_id=course_id, module_id=module_id)
        topics_without_enough_data = [
            self._decorate_topic(topic, "not_enough_data")
            for topic in topics
            if self._is_topic_without_enough_data(topic)
        ]
        return self.sort_topics_with_limited_data(topics_without_enough_data)

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
                -item["failed_attempts_count"],
                item["module_title"],
            ),
        )

    def sort_topics_by_success(self, topics: list[dict]) -> list[dict]:
        return sorted(
            topics,
            key=lambda item: (
                -(item["stability_index"] or 0.0),
                -item["best_percentage"],
                -item["average_percentage"],
                -item["completed_lessons_ratio"],
                item["module_title"],
            ),
        )

    def sort_topics_by_instability(self, topics: list[dict]) -> list[dict]:
        return sorted(
            topics,
            key=lambda item: (
                item["stability_index"] if item["stability_index"] is not None else 1.0,
                -item["failed_attempts_count"],
                item["average_percentage"],
                item["module_title"],
            ),
        )

    def sort_topics_by_growth(self, topics: list[dict]) -> list[dict]:
        return sorted(
            topics,
            key=lambda item: (
                -item["progress_delta"],
                -item["last_percentage"],
                -item["completed_lessons_ratio"],
                item["module_title"],
            ),
        )

    def sort_topics_with_limited_data(self, topics: list[dict]) -> list[dict]:
        return sorted(
            topics,
            key=lambda item: (
                item["completed_attempts_count"],
                item["completed_lessons_ratio"],
                item["module_title"],
            ),
        )

    def determine_weak_topic_reason(self, topic_result: dict) -> str:
        attempts_count = topic_result["completed_attempts_count"]
        average_percentage = topic_result["average_percentage"]
        progress_delta = topic_result["progress_delta"]
        failed_attempts_count = topic_result["failed_attempts_count"]
        completed_lessons_ratio = topic_result["completed_lessons_ratio"]
        learning_state = topic_result["learning_state"]
        stability_index = topic_result["stability_index"]

        if attempts_count == 0:
            return "По теме пока нет завершенных попыток, поэтому рано делать устойчивый вывод."
        if average_percentage < 60:
            return (
                f"Средний результат по теме составляет {average_percentage:.2f}%, "
                "что указывает на низкий уровень усвоения материала."
            )
        if attempts_count >= 3 and progress_delta < 5 and topic_result["trend"] != "improving":
            return (
                f"После {attempts_count} завершенных попыток прирост составляет только {progress_delta:.2f} п.п., "
                "поэтому заметного прогресса по теме пока нет."
            )
        if completed_lessons_ratio < 0.5 and failed_attempts_count > 0:
            return (
                f"Тема начата без прохождения теории: завершено только {completed_lessons_ratio * 100:.0f}% уроков, "
                f"при этом уже есть {failed_attempts_count} неуспешных попыток."
            )
        if learning_state == "unstable" or (stability_index is not None and stability_index < 0.55):
            return "Результаты по теме заметно колеблются между попытками, поэтому знания пока нестабильны."
        return "По теме сохраняются риски: результат пока недостаточно устойчив и требует повторения материала."

    def determine_strong_topic_reason(self, topic_result: dict) -> str:
        attempts_count = topic_result["completed_attempts_count"]
        average_percentage = topic_result["average_percentage"]
        progress_delta = topic_result["progress_delta"]
        stability_index = topic_result["stability_index"]
        completed_lessons_ratio = topic_result["completed_lessons_ratio"]
        learning_state = topic_result["learning_state"]

        if attempts_count == 0:
            return "По теме пока нет завершенных попыток, поэтому уверенно сильной ее считать рано."
        if learning_state == "mastered":
            return (
                f"Тема уверенно закреплена: средний результат {average_percentage:.2f}%, "
                f"теория завершена на {completed_lessons_ratio * 100:.0f}%."
            )
        if topic_result["trend"] == "improving":
            return (
                f"По теме виден положительный рост: средний результат {average_percentage:.2f}%, "
                f"а прирост между первой и последней попыткой составляет {progress_delta:.2f} п.п."
            )
        if topic_result["trend"] == "stable" and (stability_index is None or stability_index >= 0.7):
            return (
                f"Тема показывает стабильно высокий результат: средний балл {average_percentage:.2f}%, "
                "без заметных просадок между попытками."
            )
        return "Тема демонстрирует высокий и достаточно устойчивый результат, поэтому ее можно считать сильной."

    def build_topic_tags(self, topic_result: dict) -> list[str]:
        tags: list[str] = []
        if self._is_weak_topic(topic_result):
            tags.append("нуждается в пересмотре")
        if self._is_unstable_topic(topic_result):
            tags.append("нестабильный результат")
        if self._is_improving_topic(topic_result):
            tags.append("улучшение")
        if topic_result["risk_level"] == "high":
            tags.append("высокий риск")
        if topic_result["completed_lessons_ratio"] < 0.75:
            tags.append("теория не завершена")
        if self._is_strong_topic(topic_result):
            tags.append("освоен")
        if self._is_topic_without_enough_data(topic_result):
            tags.append("недостаточно данных")
        return tags

    def prepare_analytics_data(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> dict:
        source_topics = self._get_topics(user_id, course_id=course_id, module_id=module_id)
        topics = [self._attach_analytics_reason(topic) for topic in source_topics]
        weak_topics = self.sort_topics_by_problem_severity(
            [self._decorate_topic(topic, "weak") for topic in source_topics if self._is_weak_topic(topic)]
        )
        strong_topics = self.sort_topics_by_success(
            [self._decorate_topic(topic, "strong") for topic in source_topics if self._is_strong_topic(topic)]
        )
        unstable_topics = self.sort_topics_by_instability(
            [self._decorate_topic(topic, "unstable") for topic in source_topics if self._is_unstable_topic(topic)]
        )
        improving_topics = self.sort_topics_by_growth(
            [self._decorate_topic(topic, "improving") for topic in source_topics if self._is_improving_topic(topic)]
        )
        topics_without_enough_data = self.sort_topics_with_limited_data(
            [
                self._decorate_topic(topic, "not_enough_data")
                for topic in source_topics
                if self._is_topic_without_enough_data(topic)
            ]
        )
        return {
            "topic_results": topics,
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "best_topics": strong_topics,
            "unstable_topics": unstable_topics,
            "improving_topics": improving_topics,
            "topics_without_enough_data": topics_without_enough_data,
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
            item["tags"] = self.build_topic_tags(item)
            item["reason"] = (
                self.determine_weak_topic_reason(item)
                if item["is_weak_topic"]
                else self.determine_strong_topic_reason(item)
                if item["is_strong_topic"]
                else self._determine_topic_reason(item, "neutral")
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
        completed_attempts_count = topic_result["completed_attempts_count"]
        if completed_attempts_count == 0:
            return include_not_enough_data

        low_average = topic_result["average_percentage"] < 60
        no_progress_after_many_attempts = (
            completed_attempts_count >= 3
            and topic_result["progress_delta"] < 5
            and topic_result["trend"] != "improving"
        )
        unfinished_theory_with_failures = (
            topic_result["completed_lessons_ratio"] < 0.5
            and topic_result["failed_attempts_count"] > 0
        )
        unstable_with_failures = (
            topic_result["learning_state"] == "unstable"
            and topic_result["failed_attempts_count"] >= 2
        )
        return (
            low_average
            or no_progress_after_many_attempts
            or unfinished_theory_with_failures
            or unstable_with_failures
        )

    def _is_strong_topic(self, topic_result: dict) -> bool:
        completed_attempts_count = topic_result["completed_attempts_count"]
        if completed_attempts_count < 2:
            return False

        stability_index = topic_result["stability_index"]
        stable_result = stability_index is None or stability_index >= 0.7
        positive_or_stable_dynamics = (
            topic_result["trend"] in {"improving", "stable"}
            and topic_result["progress_delta"] >= -2
        )
        low_failure_rate = topic_result["failed_attempts_count"] / completed_attempts_count <= 0.2
        return (
            topic_result["average_percentage"] >= 85
            and stable_result
            and positive_or_stable_dynamics
            and topic_result["completed_lessons_ratio"] >= 0.7
            and topic_result["learning_state"] != "unstable"
            and low_failure_rate
        )

    def _is_unstable_topic(self, topic_result: dict) -> bool:
        if topic_result["completed_attempts_count"] < 2:
            return False
        stability_index = topic_result["stability_index"]
        return topic_result["learning_state"] == "unstable" or (
            stability_index is not None and stability_index < 0.55
        )

    def _is_improving_topic(self, topic_result: dict) -> bool:
        if topic_result["completed_attempts_count"] < 2:
            return False
        return topic_result["trend"] == "improving" or topic_result["progress_delta"] >= 10

    def _is_topic_without_enough_data(self, topic_result: dict) -> bool:
        return topic_result["completed_attempts_count"] < 2

    def _decorate_topic(self, topic_result: dict, category: str) -> dict:
        item = dict(topic_result)
        item["tags"] = self.build_topic_tags(item)
        item["reason"] = self._determine_topic_reason(item, category)
        item["category"] = category
        return item

    def _determine_topic_reason(self, topic_result: dict, category: str) -> str:
        if category == "weak":
            return self.determine_weak_topic_reason(topic_result)
        if category == "strong":
            return self.determine_strong_topic_reason(topic_result)
        if category == "unstable":
            return "Результаты по теме нестабильны: между попытками есть заметные колебания, поэтому знания пока не закрепились."
        if category == "improving":
            return "По теме наблюдается улучшение: последние попытки показывают положительную динамику."
        if category == "not_enough_data":
            return "По теме пока недостаточно завершенных попыток, чтобы делать уверенные выводы о качестве усвоения."
        return f"Тема находится в промежуточной зоне: средний результат {topic_result['average_percentage']:.2f}%."

    def _attach_analytics_reason(self, topic_result: dict) -> dict:
        if self._is_topic_without_enough_data(topic_result):
            return self._decorate_topic(topic_result, "not_enough_data")
        if self._is_weak_topic(topic_result):
            return self._decorate_topic(topic_result, "weak")
        if self._is_unstable_topic(topic_result):
            return self._decorate_topic(topic_result, "unstable")
        if self._is_improving_topic(topic_result):
            return self._decorate_topic(topic_result, "improving")
        if self._is_strong_topic(topic_result):
            return self._decorate_topic(topic_result, "strong")
        return self._decorate_topic(topic_result, "neutral")
