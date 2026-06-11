from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.enums import QuestionType, UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    university: str | None = None
    group: str | None = None
    course_year: int | None = Field(default=None, ge=1, le=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(ORMModel):
    id: int
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: UserRole
    university: str | None = None
    group: str | None = None
    course_year: int | None = Field(default=None, ge=1, le=6)
    created_at: datetime


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TimestampedRead(ORMModel):
    created_at: datetime
    updated_at: datetime


class CourseCreate(BaseModel):
    title: str
    description: str | None = None
    author_id: int | None = None
    difficulty: int = Field(default=1, ge=1, le=10)
    is_published: bool = False
    is_open: bool = True


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    author_id: int | None = None
    difficulty: int | None = Field(default=None, ge=1, le=10)
    is_published: bool | None = None
    is_open: bool | None = None


class CourseRead(TimestampedRead):
    id: int
    title: str
    description: str | None = None
    author_id: int | None = None
    difficulty: int
    is_published: bool
    is_open: bool


class CourseEnrollmentCreate(BaseModel):
    user_id: int


class EnrolledCourseRead(BaseModel):
    course_id: int
    enrolled_at: datetime


class CourseEnrollmentRead(BaseModel):
    id: int
    course_id: int
    user_id: int
    assigned_by_id: int | None = None
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    university: str | None = None
    group: str | None = None
    course_year: int | None = Field(default=None, ge=1, le=6)
    created_at: datetime


class StudentDirectoryItemRead(BaseModel):
    id: int
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    university: str | None = None
    group: str | None = None
    course_year: int | None = Field(default=None, ge=1, le=6)
    created_at: datetime


class ModuleCreate(BaseModel):
    course_id: int
    title: str
    description: str | None = None
    order: int = 0


class ModuleUpdate(BaseModel):
    course_id: int | None = None
    title: str | None = None
    description: str | None = None
    order: int | None = None


class ModuleRead(TimestampedRead):
    id: int
    course_id: int
    title: str
    description: str | None = None
    order: int


class LessonStatItem(BaseModel):
    label: str
    value: str
    hint: str | None = None


class LessonContentBlock(BaseModel):
    type: Literal["rich_text", "callout", "bullets", "checklist", "table", "chart", "image", "stat_grid"]
    title: str | None = None
    text: str | None = None
    tone: Literal["default", "info", "success", "warning", "accent"] | None = None
    paragraphs: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    unit: str | None = None
    src: str | None = None
    alt: str | None = None
    caption: str | None = None
    stats: list[LessonStatItem] = Field(default_factory=list)


class LessonCreate(BaseModel):
    module_id: int
    title: str
    content: str | None = None
    content_blocks: list[LessonContentBlock] = Field(default_factory=list)
    video_url: str | None = None
    external_url: str | None = None
    order: int = 0

    @model_validator(mode="after")
    def validate_content(self) -> "LessonCreate":
        if not (self.content or self.content_blocks):
            raise ValueError("Lesson content or content_blocks is required.")
        return self


class LessonUpdate(BaseModel):
    module_id: int | None = None
    title: str | None = None
    content: str | None = None
    content_blocks: list[LessonContentBlock] | None = None
    video_url: str | None = None
    external_url: str | None = None
    order: int | None = None


class LessonRead(TimestampedRead):
    id: int
    module_id: int
    title: str
    content: str
    content_blocks: list[LessonContentBlock] = Field(default_factory=list)
    video_url: str | None = None
    external_url: str | None = None
    order: int


class LessonDetailRead(LessonRead):
    is_completed: bool
    next_lesson_id: int | None = None
    next_lesson_title: str | None = None


class LessonProgressRead(BaseModel):
    lesson_id: int
    is_completed: bool
    completed_at: datetime | None = None


class TaskCreate(BaseModel):
    module_id: int
    title: str
    description: str
    max_score: float = 0
    order: int = 0


class TaskUpdate(BaseModel):
    module_id: int | None = None
    title: str | None = None
    description: str | None = None
    max_score: float | None = None
    order: int | None = None


class TaskRead(TimestampedRead):
    id: int
    module_id: int
    title: str
    description: str
    max_score: float
    order: int


class TaskAdminRead(TaskRead):
    pass


class TestCreate(BaseModel):
    course_id: int
    module_id: int | None = None
    title: str
    description: str | None = None
    time_limit: int | None = None
    passing_score: float = 60
    attempts_allowed: int = 1
    is_active: bool = True


class TestUpdate(BaseModel):
    course_id: int | None = None
    module_id: int | None = None
    title: str | None = None
    description: str | None = None
    time_limit: int | None = None
    passing_score: float | None = None
    attempts_allowed: int | None = None
    is_active: bool | None = None


class TestRead(TimestampedRead):
    id: int
    course_id: int
    module_id: int | None = None
    title: str
    description: str | None = None
    time_limit: int | None = None
    passing_score: float
    attempts_allowed: int
    is_active: bool


class AnswerOptionCreate(BaseModel):
    question_id: int
    text: str
    is_correct: bool = False


class AnswerOptionUpdate(BaseModel):
    question_id: int | None = None
    text: str | None = None
    is_correct: bool | None = None


class AnswerOptionRead(TimestampedRead):
    id: int
    question_id: int
    text: str
    is_correct: bool


class AnswerOptionPublicRead(ORMModel):
    id: int
    question_id: int
    text: str


class QuestionCreate(BaseModel):
    test_id: int
    text: str
    question_type: QuestionType = QuestionType.SINGLE_CHOICE
    difficulty_level: str | None = None
    score: float = 1
    order: int = 0


class QuestionUpdate(BaseModel):
    test_id: int | None = None
    text: str | None = None
    question_type: QuestionType | None = None
    difficulty_level: str | None = None
    score: float | None = None
    order: int | None = None


class QuestionRead(TimestampedRead):
    id: int
    test_id: int
    text: str
    question_type: QuestionType
    difficulty_level: str | None = None
    score: float
    order: int
    answer_options: list[AnswerOptionRead] = Field(default_factory=list)


class PublicQuestionRead(ORMModel):
    id: int
    test_id: int
    text: str
    question_type: QuestionType
    difficulty_level: str | None = None
    score: float
    order: int
    answer_options: list[AnswerOptionPublicRead] = Field(default_factory=list)


class TestAttemptRead(ORMModel):
    id: int
    user_id: int
    test_id: int
    started_at: datetime
    finished_at: datetime | None = None
    score: float
    max_score: float
    percentage: float
    is_passed: bool


class TestAttemptAnalyticsItemRead(BaseModel):
    attempt_id: int
    started_at: datetime
    finished_at: datetime | None = None
    completion_percentage: float
    percentage: float = 0.0
    is_passed: bool = False
    time_spent_seconds: int | None = None
    duration_seconds: int | None = None
    answered_questions_count: int = 0
    status: str


class TestAnalyticsRead(BaseModel):
    test_id: int
    attempts_count: int
    completed_attempts_count: int
    unfinished_attempts_count: int = 0
    completion_percentage: float
    best_result: float
    average_result: float
    first_result: float = 0.0
    last_result: float
    progress_delta: float = 0.0
    best_improvement: float = 0.0
    failure_streak: int = 0
    overall_trend: str = "not_enough_data"
    insight: str | None = None
    time_spent_seconds: int | None = None
    status: str
    attempts: list[TestAttemptAnalyticsItemRead] = Field(default_factory=list)


class UserAnswerCreate(BaseModel):
    question_id: int
    selected_option_id: int | None = None
    selected_option_ids: list[int] = Field(default_factory=list)
    text_answer: str | None = None


class UserAnswerRead(ORMModel):
    id: int
    attempt_id: int
    question_id: int
    selected_option_id: int | None = None
    selected_option_ids: list[int] = Field(default_factory=list)
    text_answer: str | None = None
    is_correct: bool
    score_received: float
    answered_at: datetime


class AttemptResultRead(BaseModel):
    attempt: TestAttemptRead
    answers: list[UserAnswerRead]


class UnfinishedAttemptRead(BaseModel):
    attempt_id: int
    test_id: int
    test_title: str
    course_id: int
    course_title: str
    module_id: int | None = None
    module_title: str | None = None
    started_at: datetime
    last_activity_at: datetime
    answered_questions: int
    total_questions: int
    time_limit: int | None = None


class ProgressRead(BaseModel):
    scope_type: str
    scope_id: int | None = None
    completed_lessons: int
    total_lessons: int
    passed_tests: int
    total_tests: int
    average_test_percentage: float
    completion_rate: float


class TopicResultRead(BaseModel):
    id: int | None = None
    module_id: int
    module_title: str
    attempts_count: int
    average_percentage: float
    best_percentage: float
    last_percentage: float = 0.0
    first_percentage: float = 0.0
    progress_delta: float = 0.0
    trend: str = "not_enough_data"
    stability_index: float | None = None
    completed_lessons_ratio: float = 0.0
    completed_attempts_count: int = 0
    passed_attempts_count: int = 0
    failed_attempts_count: int = 0
    weakness_level: str
    risk_level: str | None = None
    learning_state: str | None = None
    reason_code: str | None = None
    last_attempt_at: datetime | None = None
    updated_at: datetime | None = None
    reason: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class TopicResultAggregateRead(BaseModel):
    module_id: int
    module_title: str
    users_count: int
    attempts_count: int
    average_percentage: float
    best_percentage: float
    high_weakness_count: int
    medium_weakness_count: int
    low_weakness_count: int


class RecommendationCreate(BaseModel):
    module_id: int
    title: str
    description: str
    resource_url: str | None = None


class RecommendationUpdate(BaseModel):
    module_id: int | None = None
    title: str | None = None
    description: str | None = None
    resource_url: str | None = None


class RecommendationRead(TimestampedRead):
    id: int
    module_id: int
    title: str
    description: str
    resource_url: str | None = None


class PersonalRecommendationRead(BaseModel):
    id: int
    module_id: int
    module_title: str
    title: str
    description: str
    resource_url: str | None = None
    current_percentage: float
    current_result: float = 0.0
    weakness_level: str
    topic_state: str | None = None
    rule_key: str | None = None
    priority: str | None = None
    reason: str | None = None
    topic_reason: str | None = None
    progress_delta: float = 0.0
    completed_lessons_ratio: float = 0.0


class UserAnalyticsSummaryRead(BaseModel):
    total_attempts: int
    completed_attempts: int
    passed_attempts: int
    average_score: float
    average_percentage: float
    lessons_completed: int
    unique_courses_started: int


class AnalyticsDynamicsPointRead(BaseModel):
    attempt_id: int
    date: datetime
    test_id: int
    test_title: str
    module_id: int | None = None
    module_title: str | None = None
    percentage: float
    is_passed: bool


class QuestionWrongOptionRead(BaseModel):
    option_id: int
    option_text: str
    selections_count: int


class QuestionAnalyticsRead(BaseModel):
    question_id: int
    test_id: int
    module_id: int | None = None
    question_text: str
    question_type: QuestionType
    order: int
    max_score: float
    attempts_count: int
    correct_answers_count: int
    incorrect_answers_count: int
    success_rate: float
    average_score: float
    common_wrong_options: list[QuestionWrongOptionRead] = Field(default_factory=list)


class PersonalAnalyticsSnapshotRead(BaseModel):
    progress: ProgressRead
    summary: UserAnalyticsSummaryRead
    topicResults: list[TopicResultRead] = Field(default_factory=list)
    weakTopics: list[TopicResultRead] = Field(default_factory=list)
    strongTopics: list[TopicResultRead] = Field(default_factory=list)
    bestTopics: list[TopicResultRead] = Field(default_factory=list)
    unstableTopics: list[TopicResultRead] = Field(default_factory=list)
    improvingTopics: list[TopicResultRead] = Field(default_factory=list)
    topicsWithoutEnoughData: list[TopicResultRead] = Field(default_factory=list)
    dynamics: list[AnalyticsDynamicsPointRead] = Field(default_factory=list)


class MessageRead(BaseModel):
    message: str
