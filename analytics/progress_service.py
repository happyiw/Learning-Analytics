from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from backend.attempt_metrics import build_attempt_percentage_expression
from backend.enums import UserRole
from backend.models import Course, CourseEnrollment, Lesson, LessonProgress, Module, Test, TestAttempt, User
from backend.schemas import ProgressRead


@dataclass(slots=True)
class ProgressSnapshot:
    scope_type: str
    scope_id: int | None
    completed_lessons: int
    total_lessons: int
    passed_tests: int
    total_tests: int
    average_test_percentage: float
    completion_rate: float


class ProgressService:
    def __init__(self, db: Session):
        self.db = db

    def get_accessible_course_ids(self, user_id: int) -> list[int]:
        user = self.db.get(User, user_id)
        if user is None:
            return []

        if user.role in {UserRole.TEACHER, UserRole.ADMIN}:
            return list(
                self.db.scalars(
                    select(Course.id)
                    .where(Course.is_published.is_(True))
                    .order_by(Course.created_at.desc(), Course.id.desc())
                )
            )

        return list(
            self.db.scalars(
                select(CourseEnrollment.course_id)
                .join(Course, Course.id == CourseEnrollment.course_id)
                .where(
                    CourseEnrollment.user_id == user_id,
                    Course.is_published.is_(True),
                )
                .order_by(Course.id)
            )
        )

    def get_overall_progress(self, user_id: int) -> ProgressRead:
        return self._build_progress(user_id=user_id)

    def get_course_progress(self, user_id: int, course_id: int) -> ProgressRead:
        return self._build_progress(user_id=user_id, course_id=course_id)

    def get_module_progress(self, user_id: int, module_id: int) -> ProgressRead:
        return self._build_progress(user_id=user_id, module_id=module_id)

    def get_completed_lessons_percentage(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> float:
        lesson_ids = self.get_scope_lesson_ids(user_id, course_id=course_id, module_id=module_id)
        if not lesson_ids:
            return 0.0

        completed_lessons = len(
            list(
                self.db.scalars(
                    select(LessonProgress.id).where(
                        LessonProgress.user_id == user_id,
                        LessonProgress.is_completed.is_(True),
                        LessonProgress.lesson_id.in_(lesson_ids),
                    )
                )
            )
        )
        return round((completed_lessons / len(lesson_ids)) * 100, 2)

    def get_completed_modules_percentage(
        self,
        user_id: int,
        course_id: int | None = None,
    ) -> float:
        modules = self.get_modules_for_scope(user_id=user_id, course_id=course_id)
        if not modules:
            return 0.0

        completed_modules = 0
        for module in modules:
            lesson_ids = self.get_scope_lesson_ids(user_id, module_id=module.id)
            if not lesson_ids:
                continue

            completed_lesson_ids = set(
                self.db.scalars(
                    select(LessonProgress.lesson_id).where(
                        LessonProgress.user_id == user_id,
                        LessonProgress.is_completed.is_(True),
                        LessonProgress.lesson_id.in_(lesson_ids),
                    )
                )
            )
            if len(completed_lesson_ids) == len(lesson_ids):
                completed_modules += 1

        return round((completed_modules / len(modules)) * 100, 2)

    def get_modules_for_scope(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[Module]:
        if module_id is not None:
            module = self.db.get(Module, module_id)
            return [module] if module else []

        stmt = select(Module)
        if course_id is not None:
            stmt = stmt.where(Module.course_id == course_id)
        else:
            accessible_course_ids = self.get_accessible_course_ids(user_id)
            if not accessible_course_ids:
                return []
            stmt = stmt.where(Module.course_id.in_(accessible_course_ids))

        return list(self.db.scalars(stmt.order_by(Module.order, Module.id)))

    def get_scope_lesson_ids(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> list[int]:
        stmt = select(Lesson.id).join(Module, Module.id == Lesson.module_id)
        if module_id is not None:
            stmt = stmt.where(Lesson.module_id == module_id)
        elif course_id is not None:
            stmt = stmt.where(Module.course_id == course_id)
        else:
            accessible_course_ids = self.get_accessible_course_ids(user_id)
            if not accessible_course_ids:
                return []
            stmt = stmt.where(Module.course_id.in_(accessible_course_ids))

        return list(self.db.scalars(stmt))

    def get_scope_test_ids(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
        only_active: bool = False,
    ) -> list[int]:
        stmt = select(Test.id)
        if only_active:
            stmt = stmt.where(Test.is_active.is_(True))
        if module_id is not None:
            stmt = stmt.where(Test.module_id == module_id)
        elif course_id is not None:
            stmt = stmt.where(Test.course_id == course_id)
        else:
            accessible_course_ids = self.get_accessible_course_ids(user_id)
            if not accessible_course_ids:
                return []
            stmt = stmt.where(Test.course_id.in_(accessible_course_ids))

        return list(self.db.scalars(stmt))

    def _build_progress(
        self,
        user_id: int,
        course_id: int | None = None,
        module_id: int | None = None,
    ) -> ProgressRead:
        lesson_ids = self.get_scope_lesson_ids(user_id, course_id=course_id, module_id=module_id)
        test_ids = self.get_scope_test_ids(
            user_id,
            course_id=course_id,
            module_id=module_id,
            only_active=True,
        )

        completed_lessons = (
            len(
                list(
                    self.db.scalars(
                        select(LessonProgress.id).where(
                            LessonProgress.user_id == user_id,
                            LessonProgress.is_completed.is_(True),
                            LessonProgress.lesson_id.in_(lesson_ids),
                        )
                    )
                )
            )
            if lesson_ids
            else 0
        )
        percentage_expr = build_attempt_percentage_expression(
            TestAttempt.score,
            TestAttempt.max_score,
        )
        passed_tests = (
            len(
                list(
                    self.db.scalars(
                        select(distinct(TestAttempt.test_id))
                        .join(Test, Test.id == TestAttempt.test_id)
                        .where(
                            TestAttempt.user_id == user_id,
                            TestAttempt.finished_at.is_not(None),
                            TestAttempt.test_id.in_(test_ids),
                            percentage_expr >= Test.passing_score,
                        )
                    )
                )
            )
            if test_ids
            else 0
        )
        percentages = (
            list(
                self.db.scalars(
                    select(percentage_expr)
                    .where(
                        TestAttempt.user_id == user_id,
                        TestAttempt.finished_at.is_not(None),
                        TestAttempt.test_id.in_(test_ids),
                    )
                )
            )
            if test_ids
            else []
        )

        total_lessons = len(lesson_ids)
        total_tests = len(test_ids)
        denominator = total_lessons + total_tests
        completion_rate = round(((completed_lessons + passed_tests) / denominator) * 100, 2) if denominator else 0.0
        average_test_percentage = round(sum(percentages) / len(percentages), 2) if percentages else 0.0

        if module_id is not None:
            scope_type = "module"
            scope_id = module_id
        elif course_id is not None:
            scope_type = "course"
            scope_id = course_id
        else:
            scope_type = "global"
            scope_id = None

        return ProgressRead(
            scope_type=scope_type,
            scope_id=scope_id,
            completed_lessons=completed_lessons,
            total_lessons=total_lessons,
            passed_tests=passed_tests,
            total_tests=total_tests,
            average_test_percentage=average_test_percentage,
            completion_rate=completion_rate,
        )
