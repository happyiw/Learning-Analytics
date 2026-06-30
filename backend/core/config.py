from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _default_database_url() -> str:
    postgres_user = os.getenv("POSTGRES_USER", "learning_user")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "learning_password")
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "learning_analytics")
    return (
        f"postgresql+psycopg://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    )


class Settings:
    app_name: str = os.getenv("APP_NAME", "Learning Analytics API")
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-key")
    algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    )
    database_url: str = os.getenv("DATABASE_URL", _default_database_url())
    seed_on_startup: bool = _env_flag("SEED_ON_STARTUP", True)
    seed_data_dir: Path = Path(os.getenv("SEED_DATA_DIR", str(DATA_DIR)))
    migrate_sqlite_path: Path | None = (
        Path(raw_path)
        if (raw_path := os.getenv("MIGRATE_SQLITE_PATH"))
        else None
    )


settings = Settings()
