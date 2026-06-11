from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.attempt_metrics import calculate_attempt_status
from backend.models import TestAttempt


@dataclass(slots=True)
class AttemptAnalyticsSnapshot:
    attempt_id: int
    started_at: datetime
    finished_at: datetime | None
    completion_percentage: float
    percentage: float
    is_passed: bool
    time_spent_seconds: int | None
    duration_seconds: int | None
    answered_questions_count: int
    status: str


class TestAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_test_attempts(
        self,
        user_id: int,
        test_id: int,
        include_unfinished: bool = True,
    ) -> list[TestAttempt]:
        stmt = (
            select(TestAttempt)
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.test_id == test_id,
            )
            .options(
                selectinload(TestAttempt.answers),
                selectinload(TestAttempt.test),
            )
            .order_by(TestAttempt.started_at, TestAttempt.id)
        )
        if not include_unfinished:
            stmt = stmt.where(TestAttempt.finished_at.is_not(None))
        return list(self.db.scalars(stmt))

    def calculate_completion_percentage(self, attempt: TestAttempt | None) -> float:
        if attempt is None:
            return 0.0
        score = attempt.score
        if attempt.finished_at is None:
            score = sum(answer.score_received for answer in attempt.answers)
        if attempt.max_score > 0:
            return round((score / attempt.max_score) * 100, 2)
        return 0.0

    def calculate_attempts_count(self, attempts: list[TestAttempt]) -> int:
        return len(attempts)

    def calculate_best_result(self, attempts: list[TestAttempt]) -> float:
        if not attempts:
            return 0.0
        return round(max(self.calculate_completion_percentage(attempt) for attempt in attempts), 2)

    def calculate_average_result(self, attempts: list[TestAttempt]) -> float:
        if not attempts:
            return 0.0
        total = sum(self.calculate_completion_percentage(attempt) for attempt in attempts)
        return round(total / len(attempts), 2)

    def calculate_first_result(self, attempts: list[TestAttempt]) -> float:
        if not attempts:
            return 0.0
        return self.calculate_completion_percentage(attempts[0])

    def calculate_last_result(self, attempts: list[TestAttempt]) -> float:
        if not attempts:
            return 0.0
        return self.calculate_completion_percentage(attempts[-1])

    def calculate_progress_delta(self, attempts: list[TestAttempt]) -> float:
        if len(attempts) < 2:
            return 0.0
        return round(self.calculate_last_result(attempts) - self.calculate_first_result(attempts), 2)

    def calculate_best_improvement(self, attempts: list[TestAttempt]) -> float:
        if len(attempts) < 2:
            return 0.0
        return round(self.calculate_best_result(attempts) - self.calculate_first_result(attempts), 2)

    def calculate_unfinished_attempts_count(self, attempts: list[TestAttempt]) -> int:
        return len([attempt for attempt in attempts if attempt.finished_at is None])

    def calculate_failure_streak(self, attempts: list[TestAttempt]) -> int:
        streak = 0
        for attempt in reversed(attempts):
            if attempt.finished_at is None:
                continue
            if attempt.is_passed:
                break
            streak += 1
        return streak

    def calculate_test_trend(self, attempts: list[TestAttempt]) -> str:
        if len(attempts) < 2:
            return "not_enough_data"

        progress_delta = self.calculate_completion_percentage(attempts[-1]) - self.calculate_completion_percentage(attempts[0])
        if progress_delta >= 5:
            return "improving"
        if progress_delta <= -5:
            return "declining"
        return "stable"

    def build_test_insight(self, attempts: list[TestAttempt]) -> str:
        if not attempts:
            return "По тесту пока нет завершенных попыток."

        overall_trend = self.calculate_test_trend(attempts)
        last_attempt = attempts[-1]
        passing_score = last_attempt.test.passing_score if last_attempt.test is not None else 0.0
        last_result = self.calculate_last_result(attempts)
        failure_streak = self.calculate_failure_streak(attempts)

        if overall_trend == "improving" and last_result < passing_score:
            return "Результат растет, но проходной порог еще не достигнут."
        if failure_streak >= 2 and last_result < passing_score:
            return "Тест несколько раз завершался без успешного результата."
        if last_result >= passing_score and overall_trend in {"stable", "improving"} and failure_streak == 0:
            return "Тест стабильно пройден."
        if overall_trend == "declining":
            return "Результаты по тесту снижаются и требуют повторного разбора."
        return "По тесту есть активность, но устойчивый вывод пока делать рано."

    def calculate_time_spent_seconds(self, attempt: TestAttempt | None) -> int | None:
        if attempt is None or attempt.finished_at is None:
            return None
        return max(int((attempt.finished_at - attempt.started_at).total_seconds()), 0)

    def calculate_answered_questions_count(self, attempt: TestAttempt | None) -> int:
        if attempt is None:
            return 0
        return len(attempt.answers)

    def calculate_status(self, attempt: TestAttempt | None) -> str:
        if attempt is None:
            return "not_started"
        return calculate_attempt_status(attempt.finished_at, attempt.is_passed)

    def build_attempt_snapshot(self, attempt: TestAttempt) -> dict:
        percentage = self.calculate_completion_percentage(attempt)
        duration_seconds = self.calculate_time_spent_seconds(attempt)
        snapshot = AttemptAnalyticsSnapshot(
            attempt_id=attempt.id,
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
            completion_percentage=percentage,
            percentage=percentage,
            is_passed=attempt.is_passed,
            time_spent_seconds=duration_seconds,
            duration_seconds=duration_seconds,
            answered_questions_count=self.calculate_answered_questions_count(attempt),
            status=self.calculate_status(attempt),
        )
        return asdict(snapshot)

    def build_test_analytics(self, user_id: int, test_id: int) -> dict:
        attempts = self.get_test_attempts(user_id, test_id, include_unfinished=True)
        finished_attempts = [attempt for attempt in attempts if attempt.finished_at is not None]

        last_attempt = attempts[-1] if attempts else None

        return {
            "test_id": test_id,
            "attempts_count": self.calculate_attempts_count(attempts),
            "completed_attempts_count": self.calculate_attempts_count(finished_attempts),
            "unfinished_attempts_count": self.calculate_unfinished_attempts_count(attempts),
            "completion_percentage": self.calculate_completion_percentage(last_attempt),
            "best_result": self.calculate_best_result(finished_attempts),
            "average_result": self.calculate_average_result(finished_attempts),
            "first_result": self.calculate_first_result(finished_attempts),
            "last_result": self.calculate_last_result(finished_attempts),
            "progress_delta": self.calculate_progress_delta(finished_attempts),
            "best_improvement": self.calculate_best_improvement(finished_attempts),
            "failure_streak": self.calculate_failure_streak(finished_attempts),
            "overall_trend": self.calculate_test_trend(finished_attempts),
            "insight": self.build_test_insight(finished_attempts),
            "time_spent_seconds": self.calculate_time_spent_seconds(last_attempt),
            "status": self.calculate_status(last_attempt),
            "attempts": [self.build_attempt_snapshot(attempt) for attempt in attempts],
        }
