from __future__ import annotations

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session, selectinload

from backend.attempt_metrics import calculate_attempt_is_passed
from analytics.progress_service import ProgressService
from analytics.topic_result_service import WeakTopicDetector
from backend.models import LessonProgress, Test, TestAttempt


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


class StudentSummaryService:
    def __init__(self, db: Session):
        self.db = db
        self.progress_service = ProgressService(db)
        self.weak_topic_detector = WeakTopicDetector(db)

    def get_summary(self, user_id: int) -> dict:
        attempts = list(
            self.db.scalars(
                select(TestAttempt)
                .where(TestAttempt.user_id == user_id)
                .options(selectinload(TestAttempt.test))
            )
        )
        completed_attempts = [attempt for attempt in attempts if attempt.finished_at is not None]
        passed_attempts = [
            attempt
            for attempt in completed_attempts
            if calculate_attempt_is_passed(
                attempt.score,
                attempt.max_score,
                attempt.test.passing_score if attempt.test is not None else 0.0,
                attempt.finished_at,
            )
        ]
        lessons_completed = len(
            list(
                self.db.scalars(
                    select(LessonProgress.id).where(
                        LessonProgress.user_id == user_id,
                        LessonProgress.is_completed.is_(True),
                    )
                )
            )
        )
        unique_courses_started = len(
            list(
                self.db.scalars(
                    select(distinct(Test.course_id))
                    .join(TestAttempt, TestAttempt.test_id == Test.id)
                    .where(TestAttempt.user_id == user_id)
                )
            )
        )
        return {
            "total_attempts": len(attempts),
            "completed_attempts": len(completed_attempts),
            "passed_attempts": len(passed_attempts),
            "average_score": average([attempt.score for attempt in completed_attempts]),
            "average_percentage": average([attempt.percentage for attempt in completed_attempts]),
            "lessons_completed": lessons_completed,
            "unique_courses_started": unique_courses_started,
        }

    def get_dynamics(self, user_id: int) -> list[dict]:
        attempts = list(
            self.db.scalars(
                select(TestAttempt)
                .join(Test, Test.id == TestAttempt.test_id)
                .where(
                    TestAttempt.user_id == user_id,
                    TestAttempt.finished_at.is_not(None),
                )
                .order_by(TestAttempt.finished_at, TestAttempt.id)
            )
        )
        points: list[dict] = []
        for attempt in attempts:
            module = attempt.test.module
            points.append(
                {
                    "attempt_id": attempt.id,
                    "date": attempt.finished_at or attempt.started_at,
                    "test_id": attempt.test_id,
                    "test_title": attempt.test.title,
                    "module_id": module.id if module else None,
                    "module_title": module.title if module else None,
                    "percentage": attempt.percentage,
                    "is_passed": attempt.is_passed,
                }
            )
        return points

    def build_analytics_snapshot(self, user_id: int) -> dict:
        analytics_data = self.weak_topic_detector.prepare_analytics_data(user_id)
        return {
            "progress": self.progress_service.get_overall_progress(user_id),
            "summary": self.get_summary(user_id),
            "topicResults": analytics_data["topic_results"],
            "weakTopics": analytics_data["weak_topics"],
            "strongTopics": analytics_data["strong_topics"],
            "bestTopics": analytics_data["best_topics"],
            "unstableTopics": analytics_data["unstable_topics"],
            "improvingTopics": analytics_data["improving_topics"],
            "topicsWithoutEnoughData": analytics_data["topics_without_enough_data"],
            "dynamics": self.get_dynamics(user_id),
        }
