from __future__ import annotations

import argparse
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import SessionLocal
from backend.models import StudentModuleMetric


FEATURE_COLUMNS = (
    "user_id",
    "module_id",
    "attempts_count",
    "completed_attempts_count",
    "average_percentage",
    "best_percentage",
    "last_percentage",
    "progress_delta",
    "stability_index",
    "completed_lessons_ratio",
    "failed_attempts_count",
    "failure_rate",
    "computed_at",
)


def build_feature_rows(db: Session) -> list[dict]:
    metrics = list(
        db.scalars(
            select(StudentModuleMetric).order_by(
                StudentModuleMetric.user_id,
                StudentModuleMetric.module_id,
            )
        )
    )
    rows = []
    for metric in metrics:
        failure_rate = (
            metric.failed_attempts_count / metric.completed_attempts_count
            if metric.completed_attempts_count
            else 0.0
        )
        rows.append(
            {
                "user_id": metric.user_id,
                "module_id": metric.module_id,
                "attempts_count": metric.attempts_count,
                "completed_attempts_count": metric.completed_attempts_count,
                "average_percentage": metric.average_percentage,
                "best_percentage": metric.best_percentage,
                "last_percentage": metric.last_percentage,
                "progress_delta": metric.progress_delta,
                "stability_index": metric.stability_index,
                "completed_lessons_ratio": metric.completed_lessons_ratio,
                "failed_attempts_count": metric.failed_attempts_count,
                "failure_rate": round(failure_rate, 4),
                "computed_at": metric.computed_at.isoformat(),
            }
        )
    return rows


def export_features(output: Path) -> int:
    with SessionLocal() as db:
        rows = build_feature_rows(db)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FEATURE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export an offline ML feature snapshot.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/ml_features.csv"))
    args = parser.parse_args()
    count = export_features(args.output)
    print(f"Exported {count} feature rows to {args.output}.")


if __name__ == "__main__":
    main()
