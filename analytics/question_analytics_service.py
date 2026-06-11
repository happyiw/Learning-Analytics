from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models import Question, Test, TestAttempt, UserAnswer


class QuestionAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_question_attempts(self, question_id: int, user_id: int | None = None) -> list[UserAnswer]:
        stmt = (
            select(UserAnswer)
            .join(TestAttempt, TestAttempt.id == UserAnswer.attempt_id)
            .where(UserAnswer.question_id == question_id)
            .options(
                selectinload(UserAnswer.question).selectinload(Question.answer_options),
                selectinload(UserAnswer.attempt).selectinload(TestAttempt.test),
                selectinload(UserAnswer.selected_option_links),
            )
            .order_by(UserAnswer.answered_at, UserAnswer.id)
        )
        if user_id is not None:
            stmt = stmt.where(TestAttempt.user_id == user_id)
        return list(self.db.scalars(stmt))

    def calculate_question_success_rate(self, question_id: int, user_id: int | None = None) -> float:
        answers = self.get_question_attempts(question_id, user_id=user_id)
        if not answers:
            return 0.0
        correct_answers_count = len([answer for answer in answers if answer.is_correct])
        return round((correct_answers_count / len(answers)) * 100, 2)

    def calculate_question_average_score(self, question_id: int, user_id: int | None = None) -> float:
        answers = self.get_question_attempts(question_id, user_id=user_id)
        if not answers:
            return 0.0
        return round(sum(answer.score_received for answer in answers) / len(answers), 2)

    def get_common_wrong_options(self, question_id: int, user_id: int | None = None) -> list[dict]:
        question = self.db.get(Question, question_id)
        if question is None:
            return []

        option_map = {option.id: option for option in question.answer_options}
        counter: Counter[int] = Counter()
        for answer in self.get_question_attempts(question_id, user_id=user_id):
            if answer.is_correct:
                continue
            for option_id in answer.selected_option_ids:
                option = option_map.get(option_id)
                if option is None or option.is_correct:
                    continue
                counter[option_id] += 1

        return [
            {
                "option_id": option_id,
                "option_text": option_map[option_id].text,
                "selections_count": selections_count,
            }
            for option_id, selections_count in counter.most_common(5)
            if option_id in option_map
        ]

    def build_question_snapshot(self, question_id: int, user_id: int | None = None) -> dict:
        question = self.db.scalar(
            select(Question)
            .where(Question.id == question_id)
            .options(
                selectinload(Question.answer_options),
                selectinload(Question.test),
            )
        )
        if question is None:
            return {}

        answers = self.get_question_attempts(question_id, user_id=user_id)
        correct_answers_count = len([answer for answer in answers if answer.is_correct])
        incorrect_answers_count = len(answers) - correct_answers_count
        return {
            "question_id": question.id,
            "test_id": question.test_id,
            "module_id": question.test.module_id if question.test is not None else None,
            "question_text": question.text,
            "question_type": question.question_type,
            "order": question.order,
            "max_score": question.score,
            "attempts_count": len(answers),
            "correct_answers_count": correct_answers_count,
            "incorrect_answers_count": incorrect_answers_count,
            "success_rate": self.calculate_question_success_rate(question_id, user_id=user_id),
            "average_score": self.calculate_question_average_score(question_id, user_id=user_id),
            "common_wrong_options": self.get_common_wrong_options(question_id, user_id=user_id),
        }

    def get_test_question_analytics(self, test_id: int, user_id: int | None = None) -> list[dict]:
        question_ids = list(
            self.db.scalars(
                select(Question.id).where(Question.test_id == test_id).order_by(Question.order, Question.id)
            )
        )
        return [self.build_question_snapshot(question_id, user_id=user_id) for question_id in question_ids]

    def get_hardest_questions_for_test(self, test_id: int) -> list[dict]:
        snapshots = self.get_test_question_analytics(test_id)
        return sorted(
            snapshots,
            key=lambda item: (
                item["success_rate"],
                item["average_score"],
                -item["incorrect_answers_count"],
                item["order"],
            ),
        )

    def get_most_missed_questions_for_test(self, test_id: int) -> list[dict]:
        snapshots = self.get_test_question_analytics(test_id)
        return sorted(
            snapshots,
            key=lambda item: (
                -item["incorrect_answers_count"],
                item["success_rate"],
                item["order"],
            ),
        )

    def get_module_question_analytics(self, module_id: int, user_id: int | None = None) -> list[dict]:
        question_ids = list(
            self.db.scalars(
                select(Question.id)
                .join(Test, Test.id == Question.test_id)
                .where(Test.module_id == module_id)
                .order_by(Question.order, Question.id)
            )
        )
        return [self.build_question_snapshot(question_id, user_id=user_id) for question_id in question_ids]

    def get_hardest_questions_for_module(self, module_id: int) -> list[dict]:
        snapshots = self.get_module_question_analytics(module_id)
        return sorted(
            snapshots,
            key=lambda item: (
                item["success_rate"],
                item["average_score"],
                -item["incorrect_answers_count"],
                item["order"],
            ),
        )
