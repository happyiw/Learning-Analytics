from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.analytics import router as analytics_router
from backend.api.auth import router as auth_router
from backend.api.courses import router as courses_router
from backend.api.lessons import router as lessons_router
from backend.api.modules import router as modules_router
from backend.api.recommendations import router as recommendations_router
from backend.api.tasks import router as tasks_router
from backend.api.tests import router as tests_router
from backend.bootstrap import initialize_database
from backend.core.config import settings
from backend.db import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    initialize_database(engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(modules_router)
app.include_router(lessons_router)
app.include_router(tasks_router)
app.include_router(tests_router)
app.include_router(recommendations_router)
app.include_router(analytics_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Learning Analytics API is running."}
