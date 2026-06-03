from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.lesson_content import build_lesson_read
from backend.models import Course, Lesson, Module, Test, User
from backend.schemas import (
    LessonRead,
    MessageRead,
    ModuleCreate,
    ModuleRead,
    ModuleUpdate,
    PersonalRecommendationRead,
    ProgressRead,
    TestRead,
    TopicResultRead,
)
from backend.services.analytics import (
    build_personal_recommendations,
    build_progress,
    compute_topic_results,
)
from backend.services.course_access import ensure_course_access

router = APIRouter(prefix="/api/modules", tags=["modules"])


def get_module_or_404(module_id: int, db: Session) -> Module:
    module = db.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    return module


@router.get("/{module_id}/lessons/", response_model=list[LessonRead])
def list_module_lessons(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LessonRead]:
    module = get_module_or_404(module_id, db)
    course = db.get(Course, module.course_id)
    if course is None or not course.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    ensure_course_access(db, course, current_user)
    lessons = list(
        db.scalars(select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.order, Lesson.id))
    )
    return [build_lesson_read(lesson) for lesson in lessons]


@router.get("/{module_id}/tests/", response_model=list[TestRead])
def list_module_tests(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Test]:
    module = get_module_or_404(module_id, db)
    course = db.get(Course, module.course_id)
    if course is None or not course.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    ensure_course_access(db, course, current_user)
    return list(
        db.scalars(
            select(Test).where(Test.module_id == module_id, Test.is_active.is_(True)).order_by(Test.id)
        )
    )


@router.get("/{module_id}/", response_model=ModuleRead)
def retrieve_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Module:
    module = get_module_or_404(module_id, db)
    course = db.get(Course, module.course_id)
    if course is None or not course.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    ensure_course_access(db, course, current_user)
    return module


@router.get("/{module_id}/progress/my/", response_model=ProgressRead)
def get_module_progress(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressRead:
    module = get_module_or_404(module_id, db)
    course = db.get(Course, module.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    ensure_course_access(db, course, current_user)
    return build_progress(db, current_user.id, module_id=module_id)


@router.get("/{module_id}/topic-results/my/", response_model=list[TopicResultRead])
def get_module_topic_results(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicResultRead]:
    module = get_module_or_404(module_id, db)
    course = db.get(Course, module.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    ensure_course_access(db, course, current_user)
    return compute_topic_results(db, current_user.id, module_id=module_id)


@router.get("/{module_id}/recommendations/my/", response_model=list[PersonalRecommendationRead])
def get_module_recommendations(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PersonalRecommendationRead]:
    module = get_module_or_404(module_id, db)
    course = db.get(Course, module.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    ensure_course_access(db, course, current_user)
    return build_personal_recommendations(db, current_user.id, module_id=module_id)


@router.post("/", response_model=ModuleRead, status_code=status.HTTP_201_CREATED)
def create_module(
    payload: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Module:
    _ = current_user
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found.")

    module = Module(**payload.model_dump())
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


@router.patch("/{module_id}/", response_model=ModuleRead)
def update_module(
    module_id: int,
    payload: ModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Module:
    _ = current_user
    module = get_module_or_404(module_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "course_id" in data and db.get(Course, data["course_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found.")

    for field, value in data.items():
        setattr(module, field, value)
    db.commit()
    db.refresh(module)
    return module


@router.delete("/{module_id}/", response_model=MessageRead)
def delete_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    _ = current_user
    module = get_module_or_404(module_id, db)
    db.delete(module)
    db.commit()
    return MessageRead(message="Module deleted.")
