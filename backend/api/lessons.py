from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.models import Lesson, LessonProgress, Module, User
from backend.schemas import (
    LessonCreate,
    LessonDetailRead,
    LessonProgressRead,
    LessonRead,
    LessonUpdate,
    MessageRead,
)

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def get_lesson_or_404(lesson_id: int, db: Session) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    return lesson


@router.get("/{lesson_id}/", response_model=LessonDetailRead)
def retrieve_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonDetailRead:
    lesson = get_lesson_or_404(lesson_id, db)
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.user_id == current_user.id,
            LessonProgress.is_completed.is_(True),
        )
    )
    return LessonDetailRead(**LessonRead.model_validate(lesson).model_dump(), is_completed=progress is not None)


@router.post("/{lesson_id}/complete/", response_model=LessonProgressRead)
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressRead:
    lesson = get_lesson_or_404(lesson_id, db)
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.lesson_id == lesson.id,
            LessonProgress.user_id == current_user.id,
        )
    )
    if progress is None:
        progress = LessonProgress(user_id=current_user.id, lesson_id=lesson.id)
        db.add(progress)

    progress.is_completed = True
    progress.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(progress)
    return LessonProgressRead(
        lesson_id=lesson.id,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
    )


@router.post("/", response_model=LessonRead, status_code=status.HTTP_201_CREATED)
def create_lesson(
    payload: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Lesson:
    _ = current_user
    if db.get(Module, payload.module_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")
    lesson = Lesson(**payload.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.patch("/{lesson_id}/", response_model=LessonRead)
def update_lesson(
    lesson_id: int,
    payload: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Lesson:
    _ = current_user
    lesson = get_lesson_or_404(lesson_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "module_id" in data and db.get(Module, data["module_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")

    for field, value in data.items():
        setattr(lesson, field, value)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/{lesson_id}/", response_model=MessageRead)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    _ = current_user
    lesson = get_lesson_or_404(lesson_id, db)
    db.delete(lesson)
    db.commit()
    return MessageRead(message="Lesson deleted.")
