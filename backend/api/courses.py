from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.models import Course, Module, User
from backend.schemas import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    MessageRead,
    ModuleRead,
    PersonalRecommendationRead,
    ProgressRead,
    TopicResultRead,
)
from backend.services.analytics import (
    build_personal_recommendations,
    build_progress,
    compute_topic_results,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])


def get_course_or_404(course_id: int, db: Session) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return course


@router.get("/", response_model=list[CourseRead])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return list(
        db.scalars(select(Course).where(Course.is_published.is_(True)).order_by(Course.created_at.desc()))
    )


@router.get("/{course_id}/", response_model=CourseRead)
def retrieve_course(course_id: int, db: Session = Depends(get_db)) -> Course:
    course = get_course_or_404(course_id, db)
    if not course.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return course


@router.get("/{course_id}/modules/", response_model=list[ModuleRead])
def list_course_modules(course_id: int, db: Session = Depends(get_db)) -> list[Module]:
    course = get_course_or_404(course_id, db)
    if not course.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return list(
        db.scalars(select(Module).where(Module.course_id == course_id).order_by(Module.order, Module.id))
    )


@router.get("/{course_id}/progress/my/", response_model=ProgressRead)
def get_course_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressRead:
    _ = get_course_or_404(course_id, db)
    return build_progress(db, current_user.id, course_id=course_id)


@router.get("/{course_id}/topic-results/my/", response_model=list[TopicResultRead])
def get_course_topic_results(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicResultRead]:
    _ = get_course_or_404(course_id, db)
    return compute_topic_results(db, current_user.id, course_id=course_id)


@router.get("/{course_id}/recommendations/my/", response_model=list[PersonalRecommendationRead])
def get_course_recommendations(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PersonalRecommendationRead]:
    _ = get_course_or_404(course_id, db)
    return build_personal_recommendations(db, current_user.id, course_id=course_id)


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Course:
    author_id = payload.author_id or current_user.id
    if db.get(User, author_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Author not found.")

    course = Course(
        title=payload.title,
        description=payload.description,
        author_id=author_id,
        difficulty_level=payload.difficulty_level,
        is_published=payload.is_published,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.patch("/{course_id}/", response_model=CourseRead)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Course:
    course = get_course_or_404(course_id, db)
    _ = current_user
    data = payload.model_dump(exclude_unset=True)
    if "author_id" in data and data["author_id"] is not None and db.get(User, data["author_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Author not found.")

    for field, value in data.items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}/", response_model=MessageRead)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    course = get_course_or_404(course_id, db)
    _ = current_user
    db.delete(course)
    db.commit()
    return MessageRead(message="Course deleted.")
