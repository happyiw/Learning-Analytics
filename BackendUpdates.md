# Backend Updates

## Текущая версия

- Версия backend: `1.1.0`
- Стек: `FastAPI`, `SQLAlchemy`, `Pydantic`, `JWT`
- База данных по умолчанию: `SQLite` (`app.db`)
- Точка входа: `backend/main.py`

## Изменения версии 1.1.0

- Регистрация через `POST /api/auth/register/` больше не принимает поле `role`.
- Любой новый пользователь автоматически создаётся только с ролью `student`.
- Роль пользователя ограничена перечислением `student`, `teacher`, `admin`.
- Для `course_year` в регистрации добавлена backend-валидация: допускаются только значения от `1` до `6`.
- Для прямого доступа к тестам добавлена проверка публикации курса:
  - `GET /api/tests/{test_id}/`
  - `GET /api/tests/{test_id}/questions/`
  - `POST /api/tests/{test_id}/start/`
- Пользователи с ролями `teacher` и `admin` сохраняют служебный доступ к неопубликованным материалам через защищённые сценарии.

## Политика ролей

- `student` - публичная регистрация
- `teacher` - доверенное назначение
- `admin` - доверенное назначение

Публичная регистрация больше не используется для создания преподавателей и администраторов.

## Основные модели

### `User`

- `id: int` - первичный ключ
- `username: str` - уникальный логин
- `password_hash: str` - хеш пароля
- `email: str | None` - уникальный email
- `first_name: str | None`
- `last_name: str | None`
- `role: UserRole` - одно из значений `student | teacher | admin`
- `university: str | None`
- `group: str | None`
- `course_year: int | None` - от `1` до `6`
- `created_at: datetime`

### `Course`

- `id: int`
- `title: str`
- `description: str | None`
- `author_id: int | None`
- `difficulty_level: str | None`
- `is_published: bool`
- `created_at: datetime`
- `updated_at: datetime`

### `Module`

- `id: int`
- `course_id: int`
- `title: str`
- `description: str | None`
- `order: int`

### `Lesson`

- `id: int`
- `module_id: int`
- `title: str`
- `content: str`
- `video_url: str | None`
- `external_url: str | None`
- `order: int`
- `created_at: datetime`

### `Task`

- `id: int`
- `module_id: int`
- `title: str`
- `description: str`
- `task_type: str | None`
- `difficulty_level: str | None`
- `correct_answer: str | None`
- `explanation: str | None`
- `max_score: float`
- `order: int`

### `Test`

- `id: int`
- `course_id: int`
- `module_id: int | None`
- `title: str`
- `description: str | None`
- `time_limit: int | None`
- `passing_score: float`
- `attempts_allowed: int`
- `is_active: bool`

### `Question`

- `id: int`
- `test_id: int`
- `text: str`
- `question_type: str`
- `difficulty_level: str | None`
- `score: float`
- `order: int`

### `AnswerOption`

- `id: int`
- `question_id: int`
- `text: str`
- `is_correct: bool`

### `TestAttempt`

- `id: int`
- `user_id: int`
- `test_id: int`
- `started_at: datetime`
- `finished_at: datetime | None`
- `score: float`
- `max_score: float`
- `percentage: float`
- `is_passed: bool`

### `UserAnswer`

- `id: int`
- `attempt_id: int`
- `question_id: int`
- `selected_option_id: int | None`
- `text_answer: str | None`
- `is_correct: bool`
- `score_received: float`
- `answered_at: datetime`

### `LessonProgress`

- `id: int`
- `user_id: int`
- `lesson_id: int`
- `is_completed: bool`
- `completed_at: datetime | None`

### `TopicResult`

- `id: int`
- `user_id: int`
- `module_id: int`
- `attempts_count: int`
- `average_percentage: float`
- `best_percentage: float`
- `weakness_level: str`
- `last_attempt_at: datetime | None`
- `updated_at: datetime`

### `Recommendation`

- `id: int`
- `module_id: int`
- `title: str`
- `description: str`
- `resource_url: str | None`
- `trigger_score_threshold: float`

## Эндпоинты

### Системные

- `GET /` - проверка доступности API

### Аутентификация

- `POST /api/auth/register/` - регистрирует нового пользователя со строго фиксированной ролью `student`
- `POST /api/auth/login/` - возвращает JWT access token
- `GET /api/auth/me/` - возвращает профиль текущего пользователя

### Курсы и контент

- `GET /api/courses/` - список опубликованных курсов
- `GET /api/courses/{course_id}/` - опубликованный курс
- `GET /api/courses/{course_id}/modules/` - модули опубликованного курса
- `GET /api/modules/{module_id}/lessons/` - уроки модуля опубликованного курса
- `GET /api/modules/{module_id}/tests/` - активные тесты модуля опубликованного курса
- `GET /api/modules/{module_id}/tasks/` - задания модуля опубликованного курса

### Прогресс и аналитика

- `GET /api/progress/my/`
- `GET /api/courses/{course_id}/progress/my/`
- `GET /api/modules/{module_id}/progress/my/`
- `GET /api/topic-results/my/`
- `GET /api/courses/{course_id}/topic-results/my/`
- `GET /api/modules/{module_id}/topic-results/my/`
- `GET /api/recommendations/my/`
- `GET /api/courses/{course_id}/recommendations/my/`
- `GET /api/modules/{module_id}/recommendations/my/`
- `GET /api/analytics/my/summary/`
- `GET /api/analytics/my/weak-topics/`
- `GET /api/analytics/my/best-topics/`
- `GET /api/analytics/my/dynamics/`

### Тесты и попытки

- `GET /api/tests/{test_id}/` - возвращает тест только если его курс опубликован, либо если запрос выполняет `teacher/admin`
- `GET /api/tests/{test_id}/questions/` - возвращает вопросы теста по тем же правилам доступа
- `POST /api/tests/{test_id}/start/` - создаёт попытку только для теста опубликованного курса и только если тест активен
- `POST /api/test-attempts/{attempt_id}/answers/` - сохраняет ответ пользователя
- `POST /api/test-attempts/{attempt_id}/finish/` - завершает попытку и пересчитывает результат
- `GET /api/test-attempts/{attempt_id}/result/` - возвращает результат попытки

### Служебные маршруты для `teacher` и `admin`

- `POST /api/courses/`
- `PATCH /api/courses/{course_id}/`
- `DELETE /api/courses/{course_id}/`
- `POST /api/modules/`
- `PATCH /api/modules/{module_id}/`
- `DELETE /api/modules/{module_id}/`
- `POST /api/lessons/`
- `PATCH /api/lessons/{lesson_id}/`
- `DELETE /api/lessons/{lesson_id}/`
- `POST /api/tasks/`
- `PATCH /api/tasks/{task_id}/`
- `DELETE /api/tasks/{task_id}/`
- `POST /api/tests/`
- `PATCH /api/tests/{test_id}/`
- `DELETE /api/tests/{test_id}/`
- `POST /api/questions/`
- `PATCH /api/questions/{question_id}/`
- `DELETE /api/questions/{question_id}/`
- `POST /api/answer-options/`
- `PATCH /api/answer-options/{option_id}/`
- `DELETE /api/answer-options/{option_id}/`
- `GET /api/recommendations/`
- `POST /api/recommendations/`
- `GET /api/recommendations/{recommendation_id}/`
- `PATCH /api/recommendations/{recommendation_id}/`
- `DELETE /api/recommendations/{recommendation_id}/`
- `GET /api/analytics/groups/{group_id}/topic-results/`
- `GET /api/analytics/courses/{course_id}/topic-results/`
- `GET /api/analytics/modules/{module_id}/topic-results/`

## Важные ограничения

- Публичный доступ к учебному контенту завязан на `course.is_published`.
- Проверка повышенных прав выполняется через `require_teacher_or_admin`.
- Публичная регистрация больше не предназначена для выдачи повышенных ролей.
