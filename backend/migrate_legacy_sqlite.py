from __future__ import annotations

from backend.bootstrap import initialize_database
from backend.core.config import settings
from backend.db import Base, engine


def main() -> None:
    if settings.migrate_sqlite_path is None:
        raise SystemExit(
            "Set MIGRATE_SQLITE_PATH to the legacy SQLite file before running the migration."
        )

    Base.metadata.create_all(bind=engine)
    initialize_database(engine)
    print("Legacy SQLite migration completed.")


if __name__ == "__main__":
    main()
