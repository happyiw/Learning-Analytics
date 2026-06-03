from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.enums import UserRole
from backend.models import Course, CourseEnrollment, User


def is_privileged_user(user: User) -> bool:
    return user.role in {UserRole.TEACHER, UserRole.ADMIN}


def get_course_enrollment(
    db: Session,
    user_id: int,
    course_id: int,
) -> CourseEnrollment | None:
    return db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
        )
    )


def is_user_enrolled(
    db: Session,
    user_id: int,
    course_id: int,
) -> bool:
    return get_course_enrollment(db, user_id, course_id) is not None


def ensure_course_is_published(course: Course) -> None:
    if not course.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")


def ensure_course_access(
    db: Session,
    course: Course,
    current_user: User,
) -> None:
    ensure_course_is_published(course)

    if is_privileged_user(current_user):
        return

    if is_user_enrolled(db, current_user.id, course.id):
        return

    if course.is_open:
        detail = "Enroll in this course to access its materials."
    else:
        detail = "This course is closed. Ask a teacher or admin for access."

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def create_or_get_course_enrollment(
    db: Session,
    course: Course,
    user: User,
    assigned_by_id: int | None = None,
) -> CourseEnrollment:
    enrollment = get_course_enrollment(db, user.id, course.id)
    if enrollment is not None:
        return enrollment

    enrollment = CourseEnrollment(
        user_id=user.id,
        course_id=course.id,
        assigned_by_id=assigned_by_id,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment
