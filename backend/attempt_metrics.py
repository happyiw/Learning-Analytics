from __future__ import annotations

from datetime import datetime

from sqlalchemy import case


def calculate_attempt_percentage(score: float, max_score: float) -> float:
    if max_score <= 0:
        return 0.0
    return round((score / max_score) * 100, 2)


def calculate_attempt_is_passed(
    score: float,
    max_score: float,
    passing_score: float,
    finished_at: datetime | None,
) -> bool:
    if finished_at is None:
        return False
    return calculate_attempt_percentage(score, max_score) >= passing_score


def calculate_attempt_status(
    finished_at: datetime | None,
    is_passed: bool,
) -> str:
    if finished_at is None:
        return "in_progress"
    return "passed" if is_passed else "failed"


def build_attempt_percentage_expression(score_column, max_score_column):
    return case(
        (max_score_column > 0, (score_column * 100.0) / max_score_column),
        else_=0.0,
    )
