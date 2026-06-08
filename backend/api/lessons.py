from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.lesson_content import (
    build_legacy_blocks,
    build_lesson_detail,
    build_lesson_read,
    serialize_lesson_blocks,
)
from backend.models import Course, Lesson, LessonProgress, Module, User
from backend.schemas import (
    LessonCreate,
    LessonDetailRead,
    LessonProgressRead,
    LessonRead,
    LessonUpdate,
    MessageRead,
)
from backend.services.course_access import ensure_course_access

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
    module = db.get(Module, lesson.module_id)
    course = db.get(Course, module.course_id) if module else None
    if module is None or course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    ensure_course_access(db, course, current_user)
    ordered_lessons = list(
        db.scalars(
            select(Lesson)
            .where(Lesson.module_id == lesson.module_id)
            .order_by(Lesson.order, Lesson.id)
        )
    )
    next_lesson = None
    for index, module_lesson in enumerate(ordered_lessons):
        if module_lesson.id == lesson.id and index + 1 < len(ordered_lessons):
            next_lesson = ordered_lessons[index + 1]
            break

    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.user_id == current_user.id,
            LessonProgress.is_completed.is_(True),
        )
    )
    return build_lesson_detail(
        lesson,
        is_completed=progress is not None,
        next_lesson_id=next_lesson.id if next_lesson else None,
        next_lesson_title=next_lesson.title if next_lesson else None,
    )


@router.post("/{lesson_id}/complete/", response_model=LessonProgressRead)
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressRead:
    lesson = get_lesson_or_404(lesson_id, db)
    module = db.get(Module, lesson.module_id)
    course = db.get(Course, module.course_id) if module else None
    if module is None or course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    ensure_course_access(db, course, current_user)
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
) -> LessonRead:
    _ = current_user
    if db.get(Module, payload.module_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")

    blocks = payload.content_blocks or build_legacy_blocks(payload.content)
    lesson = Lesson(
        module_id=payload.module_id,
        title=payload.title,
        content_blocks=serialize_lesson_blocks(blocks),
        video_url=payload.video_url,
        external_url=payload.external_url,
        order=payload.order,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return build_lesson_read(lesson)


@router.patch("/{lesson_id}/", response_model=LessonRead)
def update_lesson(
    lesson_id: int,
    payload: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> LessonRead:
    _ = current_user
    lesson = get_lesson_or_404(lesson_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "module_id" in data and db.get(Module, data["module_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")

    content = data.pop("content", None)
    content_blocks = data.pop("content_blocks", None)

    for field, value in data.items():
        setattr(lesson, field, value)

    if content_blocks is not None:
        lesson.content_blocks = serialize_lesson_blocks(content_blocks)
    elif "content" in payload.model_fields_set:
        lesson.content_blocks = serialize_lesson_blocks(build_legacy_blocks(content))

    db.commit()
    db.refresh(lesson)
    return build_lesson_read(lesson)


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
