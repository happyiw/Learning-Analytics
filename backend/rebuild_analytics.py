from backend.db import SessionLocal
from backend.services.analytics_materialization import refresh_all_student_module_metrics


def main() -> None:
    with SessionLocal() as db:
        count = refresh_all_student_module_metrics(db)
    print(f"Rebuilt {count} student-module analytics rows.")


if __name__ == "__main__":
    main()
