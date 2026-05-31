from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


def _default_database_url() -> str:
    return f"sqlite:///{(BASE_DIR / 'app.db').as_posix()}"


class Settings:
    app_name: str = os.getenv("APP_NAME", "Learning Analytics API")
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-key")
    algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    )
    database_url: str = os.getenv("DATABASE_URL", _default_database_url())


settings = Settings()
