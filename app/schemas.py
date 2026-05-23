from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: str = "student"
    university: str | None = None
    group: str | None = None
    course_year: int | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(ORMModel):
    id: int
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: str
    university: str | None = None
    group: str | None = None
    course_year: int | None = None
    created_at: datetime


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CourseCreate(BaseModel):
    title: str
    description: str | None = None
    author_id: int | None = None
    difficulty_level: str | None = None
    is_published: bool = False


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    author_id: int | None = None
    difficulty_level: str | None = None
    is_published: bool | None = None


class CourseRead(ORMModel):
    id: int
    title: str
    description: str | None = None
    author_id: int | None = None
    difficulty_level: str | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime


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


class ModuleRead(ORMModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    order: int


class LessonCreate(BaseModel):
    module_id: int
    title: str
    content: str
    video_url: str | None = None
    external_url: str | None = None
    order: int = 0


class LessonUpdate(BaseModel):
    module_id: int | None = None
    title: str | None = None
    content: str | None = None
    video_url: str | None = None
    external_url: str | None = None
    order: int | None = None


class LessonRead(ORMModel):
    id: int
    module_id: int
    title: str
    content: str
    video_url: str | None = None
    external_url: str | None = None
    order: int
    created_at: datetime


class LessonDetailRead(LessonRead):
    is_completed: bool


class LessonProgressRead(BaseModel):
    lesson_id: int
    is_completed: bool
    completed_at: datetime | None = None


class TaskRead(ORMModel):
    id: int
    module_id: int
    title: str
    description: str
    task_type: str | None = None
    difficulty_level: str | None = None
    explanation: str | None = None
    max_score: float
    order: int


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


class TestRead(ORMModel):
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


class AnswerOptionRead(ORMModel):
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
    question_type: str = "single_choice"
    difficulty_level: str | None = None
    score: float = 1
    order: int = 0


class QuestionUpdate(BaseModel):
    test_id: int | None = None
    text: str | None = None
    question_type: str | None = None
    difficulty_level: str | None = None
    score: float | None = None
    order: int | None = None


class QuestionRead(ORMModel):
    id: int
    test_id: int
    text: str
    question_type: str
    difficulty_level: str | None = None
    score: float
    order: int
    answer_options: list[AnswerOptionRead] = []


class PublicQuestionRead(ORMModel):
    id: int
    test_id: int
    text: str
    question_type: str
    difficulty_level: str | None = None
    score: float
    order: int
    answer_options: list[AnswerOptionPublicRead] = []


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


class UserAnswerCreate(BaseModel):
    question_id: int
    selected_option_id: int | None = None
    text_answer: str | None = None


class UserAnswerRead(ORMModel):
    id: int
    attempt_id: int
    question_id: int
    selected_option_id: int | None = None
    text_answer: str | None = None
    is_correct: bool
    score_received: float
    answered_at: datetime


class AttemptResultRead(BaseModel):
    attempt: TestAttemptRead
    answers: list[UserAnswerRead]


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
    weakness_level: str
    last_attempt_at: datetime | None = None
    updated_at: datetime | None = None


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
    trigger_score_threshold: float = 60


class RecommendationUpdate(BaseModel):
    module_id: int | None = None
    title: str | None = None
    description: str | None = None
    resource_url: str | None = None
    trigger_score_threshold: float | None = None


class RecommendationRead(ORMModel):
    id: int
    module_id: int
    title: str
    description: str
    resource_url: str | None = None
    trigger_score_threshold: float


class PersonalRecommendationRead(BaseModel):
    id: int
    module_id: int
    module_title: str
    title: str
    description: str
    resource_url: str | None = None
    trigger_score_threshold: float
    current_percentage: float
    weakness_level: str


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


class MessageRead(BaseModel):
    message: str
