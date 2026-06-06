from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models import TestAttempt


@dataclass(slots=True)
class AttemptAnalyticsSnapshot:
    attempt_id: int
    started_at: datetime
    finished_at: datetime | None
    completion_percentage: float
    time_spent_seconds: int | None
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
            .options(selectinload(TestAttempt.answers))
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
        return round(attempt.percentage, 2)

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

    def calculate_last_result(self, attempts: list[TestAttempt]) -> float:
        if not attempts:
            return 0.0
        return self.calculate_completion_percentage(attempts[-1])

    def calculate_time_spent_seconds(self, attempt: TestAttempt | None) -> int | None:
        if attempt is None or attempt.finished_at is None:
            return None
        return max(int((attempt.finished_at - attempt.started_at).total_seconds()), 0)

    def calculate_status(self, attempt: TestAttempt | None) -> str:
        if attempt is None:
            return "not_started"
        if attempt.finished_at is None:
            return "in_progress"
        return "passed" if attempt.is_passed else "failed"

    def build_attempt_snapshot(self, attempt: TestAttempt) -> dict:
        snapshot = AttemptAnalyticsSnapshot(
            attempt_id=attempt.id,
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
            completion_percentage=self.calculate_completion_percentage(attempt),
            time_spent_seconds=self.calculate_time_spent_seconds(attempt),
            status=self.calculate_status(attempt),
        )
        return asdict(snapshot)

    def build_test_analytics(self, user_id: int, test_id: int) -> dict:
        attempts = self.get_test_attempts(user_id, test_id, include_unfinished=True)
        finished_attempts = [attempt for attempt in attempts if attempt.finished_at is not None]

        last_attempt = attempts[-1] if attempts else None
        last_finished_attempt = finished_attempts[-1] if finished_attempts else None

        return {
            "test_id": test_id,
            "attempts_count": self.calculate_attempts_count(attempts),
            "completed_attempts_count": self.calculate_attempts_count(finished_attempts),
            "completion_percentage": self.calculate_completion_percentage(last_attempt),
            "best_result": self.calculate_best_result(finished_attempts),
            "average_result": self.calculate_average_result(finished_attempts),
            "last_result": self.calculate_last_result(finished_attempts),
            "time_spent_seconds": self.calculate_time_spent_seconds(last_attempt),
            "status": self.calculate_status(last_attempt),
            "attempts": [self.build_attempt_snapshot(attempt) for attempt in attempts],
        }
