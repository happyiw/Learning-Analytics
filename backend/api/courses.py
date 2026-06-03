from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.enums import UserRole
from backend.models import Course, CourseEnrollment, Module, User
from backend.schemas import (
    CourseCreate,
    CourseEnrollmentCreate,
    CourseEnrollmentRead,
    CourseRead,
    CourseUpdate,
    EnrolledCourseRead,
    MessageRead,
    ModuleRead,
    PersonalRecommendationRead,
    ProgressRead,
    StudentDirectoryItemRead,
    TopicResultRead,
)
from backend.services.analytics import (
    build_personal_recommendations,
    build_progress,
    compute_topic_results,
)
from backend.services.course_access import (
    create_or_get_course_enrollment,
    ensure_course_access,
    ensure_course_is_published,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])


def get_course_or_404(course_id: int, db: Session) -> Course:
    course = db.scalar(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.enrollments).selectinload(CourseEnrollment.user))
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return course


def build_enrollment_read(
    enrollment_id: int,
    course_id: int,
    assigned_by_id: int | None,
    created_at: datetime,
    user: User,
) -> CourseEnrollmentRead:
    return CourseEnrollmentRead(
        id=enrollment_id,
        course_id=course_id,
        user_id=user.id,
        assigned_by_id=assigned_by_id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        university=user.university,
        group=user.group,
        course_year=user.course_year,
        created_at=created_at,
    )


@router.get("/", response_model=list[CourseRead])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return list(
        db.scalars(select(Course).where(Course.is_published.is_(True)).order_by(Course.created_at.desc()))
    )


@router.get("/my/enrollments/", response_model=list[EnrolledCourseRead])
def list_my_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EnrolledCourseRead]:
    enrollments = list(
        db.scalars(
            select(CourseEnrollment)
            .where(CourseEnrollment.user_id == current_user.id)
            .order_by(CourseEnrollment.created_at.desc(), CourseEnrollment.id.desc())
        )
    )
    return [
        EnrolledCourseRead(course_id=enrollment.course_id, enrolled_at=enrollment.created_at)
        for enrollment in enrollments
    ]


@router.post("/{course_id}/enroll/my/", response_model=CourseEnrollmentRead, status_code=status.HTTP_201_CREATED)
def enroll_myself(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseEnrollmentRead:
    course = get_course_or_404(course_id, db)
    ensure_course_is_published(course)
    if not course.is_open:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This course is closed. Ask a teacher or admin for access.",
        )

    enrollment = create_or_get_course_enrollment(db, course, current_user)
    return build_enrollment_read(
        enrollment.id,
        course.id,
        enrollment.assigned_by_id,
        enrollment.created_at,
        current_user,
    )


@router.get("/{course_id}/enrollments/", response_model=list[CourseEnrollmentRead])
def list_course_enrollments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[CourseEnrollmentRead]:
    _ = current_user
    course = get_course_or_404(course_id, db)
    ensure_course_is_published(course)
    items = [
        build_enrollment_read(
            enrollment.id,
            enrollment.course_id,
            enrollment.assigned_by_id,
            enrollment.created_at,
            enrollment.user,
        )
        for enrollment in course.enrollments
    ]
    return sorted(items, key=lambda item: (item.last_name or "", item.first_name or "", item.username))


@router.post("/{course_id}/enrollments/", response_model=CourseEnrollmentRead, status_code=status.HTTP_201_CREATED)
def enroll_student_to_course(
    course_id: int,
    payload: CourseEnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> CourseEnrollmentRead:
    course = get_course_or_404(course_id, db)
    ensure_course_is_published(course)
    target_user = db.get(User, payload.user_id)
    if target_user is None or target_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student not found.")

    enrollment = create_or_get_course_enrollment(db, course, target_user, assigned_by_id=current_user.id)
    return build_enrollment_read(
        enrollment.id,
        course.id,
        enrollment.assigned_by_id,
        enrollment.created_at,
        target_user,
    )


@router.get("/students/search/", response_model=list[StudentDirectoryItemRead])
def search_students(
    q: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[StudentDirectoryItemRead]:
    _ = current_user
    stmt = select(User).where(User.role == UserRole.STUDENT)
    query = q.strip()
    if query:
        stmt = stmt.where(
            or_(
                User.username.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.first_name.ilike(f"%{query}%"),
                User.last_name.ilike(f"%{query}%"),
                User.group.ilike(f"%{query}%"),
                User.university.ilike(f"%{query}%"),
            )
        )
    students = list(db.scalars(stmt.order_by(User.username).limit(30)))
    return [
        StudentDirectoryItemRead(
            id=student.id,
            username=student.username,
            email=student.email,
            first_name=student.first_name,
            last_name=student.last_name,
            university=student.university,
            group=student.group,
            course_year=student.course_year,
            created_at=student.created_at,
        )
        for student in students
    ]


@router.get("/{course_id}/", response_model=CourseRead)
def retrieve_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    course = get_course_or_404(course_id, db)
    ensure_course_access(db, course, current_user)
    return course


@router.get("/{course_id}/modules/", response_model=list[ModuleRead])
def list_course_modules(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Module]:
    course = get_course_or_404(course_id, db)
    ensure_course_access(db, course, current_user)
    return list(
        db.scalars(select(Module).where(Module.course_id == course_id).order_by(Module.order, Module.id))
    )


@router.get("/{course_id}/progress/my/", response_model=ProgressRead)
def get_course_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressRead:
    course = get_course_or_404(course_id, db)
    ensure_course_access(db, course, current_user)
    return build_progress(db, current_user.id, course_id=course_id)


@router.get("/{course_id}/topic-results/my/", response_model=list[TopicResultRead])
def get_course_topic_results(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicResultRead]:
    course = get_course_or_404(course_id, db)
    ensure_course_access(db, course, current_user)
    return compute_topic_results(db, current_user.id, course_id=course_id)


@router.get("/{course_id}/recommendations/my/", response_model=list[PersonalRecommendationRead])
def get_course_recommendations(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PersonalRecommendationRead]:
    course = get_course_or_404(course_id, db)
    ensure_course_access(db, course, current_user)
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
        difficulty=payload.difficulty,
        is_published=payload.is_published,
        is_open=payload.is_open,
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
    _ = current_user
    course = get_course_or_404(course_id, db)
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
    _ = current_user
    course = get_course_or_404(course_id, db)
    db.delete(course)
    db.commit()
    return MessageRead(message="Course deleted.")
