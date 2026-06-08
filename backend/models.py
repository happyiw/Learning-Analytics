from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.attempt_metrics import calculate_attempt_is_passed, calculate_attempt_percentage
from backend.db import Base
from backend.enums import QuestionType, UserRole


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class User(CreatedAtMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [role.value for role in enum_cls],
        ),
        default=UserRole.STUDENT,
    )
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    course_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    authored_courses: Mapped[list["Course"]] = relationship(back_populates="author")
    course_enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="user",
        foreign_keys="CourseEnrollment.user_id",
        cascade="all, delete-orphan",
    )
    assigned_course_enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="assigned_by",
        foreign_keys="CourseEnrollment.assigned_by_id",
    )
    test_attempts: Mapped[list["TestAttempt"]] = relationship(back_populates="user")
    lesson_progress_entries: Mapped[list["LessonProgress"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    topic_results: Mapped[list["TopicResult"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    author: Mapped[User | None] = relationship(back_populates="authored_courses")
    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )
    modules: Mapped[list["Module"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )
    tests: Mapped[list["Test"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )


class Module(TimestampMixin, Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped[Course] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
    )
    tests: Mapped[list["Test"]] = relationship(back_populates="module")
    topic_results: Mapped[list["TopicResult"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
    )


class Lesson(TimestampMixin, Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content_blocks: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    module: Mapped[Module] = relationship(back_populates="lessons")
    progress_entries: Mapped[list["LessonProgress"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    max_score: Mapped[float] = mapped_column(Float, default=0)
    order: Mapped[int] = mapped_column(Integer, default=0)

    module: Mapped[Module] = relationship(back_populates="tasks")


class Test(TimestampMixin, Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passing_score: Mapped[float] = mapped_column(Float, default=60)
    attempts_allowed: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    course: Mapped[Course] = relationship(back_populates="tests")
    module: Mapped[Module | None] = relationship(back_populates="tests")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
    )
    attempts: Mapped[list["TestAttempt"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
    )


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [question_type.value for question_type in enum_cls],
        ),
        default=QuestionType.SINGLE_CHOICE,
    )
    difficulty_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=1)
    order: Mapped[int] = mapped_column(Integer, default=0)

    test: Mapped[Test] = relationship(back_populates="questions")
    answer_options: Mapped[list["AnswerOption"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )
    user_answers: Mapped[list["UserAnswer"]] = relationship(back_populates="question")


class AnswerOption(TimestampMixin, Base):
    __tablename__ = "answer_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped[Question] = relationship(back_populates="answer_options")
    user_answers: Mapped[list["UserAnswer"]] = relationship(back_populates="selected_option")
    user_answer_links: Mapped[list["UserAnswerOptionSelection"]] = relationship(
        back_populates="answer_option",
        cascade="all, delete-orphan",
    )


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    max_score: Mapped[float] = mapped_column(Float, default=0)

    user: Mapped[User] = relationship(back_populates="test_attempts")
    test: Mapped[Test] = relationship(back_populates="attempts")
    answers: Mapped[list["UserAnswer"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
    )

    @property
    def percentage(self) -> float:
        return calculate_attempt_percentage(self.score, self.max_score)

    @property
    def is_passed(self) -> bool:
        passing_score = self.test.passing_score if self.test is not None else 0.0
        return calculate_attempt_is_passed(
            self.score,
            self.max_score,
            passing_score,
            self.finished_at,
        )


class CourseEnrollment(CreatedAtMixin, Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    assigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    user: Mapped[User] = relationship(
        back_populates="course_enrollments",
        foreign_keys=[user_id],
    )
    course: Mapped[Course] = relationship(back_populates="enrollments")
    assigned_by: Mapped[User | None] = relationship(
        back_populates="assigned_course_enrollments",
        foreign_keys=[assigned_by_id],
    )


class UserAnswer(Base):
    __tablename__ = "user_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("test_attempts.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    selected_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("answer_options.id"),
        nullable=True,
    )
    text_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    score_received: Mapped[float] = mapped_column(Float, default=0)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    attempt: Mapped[TestAttempt] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship(back_populates="user_answers")
    selected_option: Mapped[AnswerOption | None] = relationship(back_populates="user_answers")
    selected_option_links: Mapped[list["UserAnswerOptionSelection"]] = relationship(
        back_populates="user_answer",
        cascade="all, delete-orphan",
    )

    @property
    def selected_option_ids(self) -> list[int]:
        option_ids = [link.answer_option_id for link in self.selected_option_links]
        if self.selected_option_id is not None and self.selected_option_id not in option_ids:
            option_ids.append(self.selected_option_id)
        return sorted(set(option_ids))


class UserAnswerOptionSelection(Base):
    __tablename__ = "user_answer_option_selections"
    __table_args__ = (UniqueConstraint("user_answer_id", "answer_option_id"),)

    user_answer_id: Mapped[int] = mapped_column(ForeignKey("user_answers.id"), primary_key=True)
    answer_option_id: Mapped[int] = mapped_column(ForeignKey("answer_options.id"), primary_key=True)

    user_answer: Mapped[UserAnswer] = relationship(back_populates="selected_option_links")
    answer_option: Mapped[AnswerOption] = relationship(back_populates="user_answer_links")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="lesson_progress_entries")
    lesson: Mapped[Lesson] = relationship(back_populates="progress_entries")


class TopicResult(Base):
    __tablename__ = "topic_results"
    __table_args__ = (UniqueConstraint("user_id", "module_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), index=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    user: Mapped[User] = relationship(back_populates="topic_results")
    module: Mapped[Module] = relationship(back_populates="topic_results")


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    resource_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    module: Mapped[Module] = relationship(back_populates="recommendations")
