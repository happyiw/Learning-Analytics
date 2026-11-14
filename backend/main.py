from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.analytics import router as analytics_router
from backend.api.auth import router as auth_router
from backend.api.courses import router as courses_router
from backend.api.lessons import router as lessons_router
from backend.api.modules import router as modules_router
from backend.api.recommendations import router as recommendations_router
from backend.api.tasks import router as tasks_router
from backend.api.teacher import router as teacher_router
from backend.api.tests import router as tests_router
from backend.core.config import settings
from backend.db import async_engine
from backend.deps import get_async_db
from backend.observability import configure_logging, install_observability
from backend.services.analytics_materialization import process_pending_learning_events

logger = logging.getLogger(__name__)


async def analytics_materialization_worker() -> None:
    while True:
        try:
            processed = await asyncio.to_thread(
                process_pending_learning_events,
                settings.analytics_worker_batch_size,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Analytics materialization batch failed")
            processed = 0
        if processed == 0:
            await asyncio.sleep(settings.analytics_worker_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker = asyncio.create_task(analytics_materialization_worker())
    try:
        yield
    finally:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        await async_engine.dispose()


configure_logging()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
install_observability(app)

app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(modules_router)
app.include_router(lessons_router)
app.include_router(tasks_router)
app.include_router(tests_router)
app.include_router(recommendations_router)
app.include_router(analytics_router)
app.include_router(teacher_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Learning Analytics API is running."}


@app.get("/health/ready", tags=["health"])
async def readiness(db: AsyncSession = Depends(get_async_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
