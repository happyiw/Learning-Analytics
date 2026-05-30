# Backend Updates

## Текущая версия

- Версия бекенда: `1.0.0`
- Стек: `FastAPI` + `SQLAlchemy` + `Pydantic` + `JWT`
- База данных по умолчанию: `SQLite` (`app.db`)
- Инициализация таблиц: автоматически при старте приложения через `Base.metadata.create_all(...)`
- Точка входа: `backend/main.py`

## Текущие модели данных

Ниже перечислены все текущие ORM-модели из `backend/models.py` и их поля.

### 1. `User`

- `id: int` - первичный ключ
- `username: str` - уникальный логин
- `password_hash: str` - хеш пароля
- `email: str | None` - уникальный email
- `first_name: str | None` - имя
- `last_name: str | None` - фамилия
- `role: str` - роль пользователя, по умолчанию `student`
- `university: str | None` - университет
- `group: str | None` - учебная группа
- `course_year: int | None` - курс обучения
- `created_at: datetime` - дата создания

### 2. `Course`

- `id: int` - первичный ключ
- `title: str` - название курса
- `description: str | None` - описание курса
- `author_id: int | None` - ссылка на автора (`users.id`)
- `difficulty_level: str | None` - уровень сложности
- `is_published: bool` - опубликован ли курс
- `created_at: datetime` - дата создания
- `updated_at: datetime` - дата последнего обновления

### 3. `Module`

- `id: int` - первичный ключ
- `course_id: int` - ссылка на курс (`courses.id`)
- `title: str` - название модуля
- `description: str | None` - описание модуля
- `order: int` - порядок внутри курса

### 4. `Lesson`

- `id: int` - первичный ключ
- `module_id: int` - ссылка на модуль (`modules.id`)
- `title: str` - название урока
- `content: str` - содержимое урока
- `video_url: str | None` - ссылка на видео
- `external_url: str | None` - внешняя ссылка
- `order: int` - порядок внутри модуля
- `created_at: datetime` - дата создания

### 5. `Task`

- `id: int` - первичный ключ
- `module_id: int` - ссылка на модуль (`modules.id`)
- `title: str` - название задания
- `description: str` - описание задания
- `task_type: str | None` - тип задания
- `difficulty_level: str | None` - уровень сложности
- `correct_answer: str | None` - правильный ответ
- `explanation: str | None` - пояснение
- `max_score: float` - максимальный балл
- `order: int` - порядок внутри модуля

Схемы API:

- `TaskCreate` - входная схема для создания задания
- `TaskUpdate` - частичное обновление задания
- `TaskRead` - публичная выдача задания без поля `correct_answer`
- `TaskAdminRead` - служебная выдача для `teacher` и `admin`, включает `correct_answer`

### 6. `Test`

- `id: int` - первичный ключ
- `course_id: int` - ссылка на курс (`courses.id`)
- `module_id: int | None` - ссылка на модуль (`modules.id`)
- `title: str` - название теста
- `description: str | None` - описание теста
- `time_limit: int | None` - лимит времени
- `passing_score: float` - проходной процент
- `attempts_allowed: int` - число доступных попыток
- `is_active: bool` - активен ли тест

### 7. `Question`

- `id: int` - первичный ключ
- `test_id: int` - ссылка на тест (`tests.id`)
- `text: str` - текст вопроса
- `question_type: str` - тип вопроса, по умолчанию `single_choice`
- `difficulty_level: str | None` - уровень сложности
- `score: float` - балл за вопрос
- `order: int` - порядок в тесте

### 8. `AnswerOption`

- `id: int` - первичный ключ
- `question_id: int` - ссылка на вопрос (`questions.id`)
- `text: str` - текст варианта ответа
- `is_correct: bool` - является ли вариант правильным

### 9. `TestAttempt`

- `id: int` - первичный ключ
- `user_id: int` - ссылка на пользователя (`users.id`)
- `test_id: int` - ссылка на тест (`tests.id`)
- `started_at: datetime` - время начала попытки
- `finished_at: datetime | None` - время завершения попытки
- `score: float` - набранный балл
- `max_score: float` - максимальный возможный балл
- `percentage: float` - процент результата
- `is_passed: bool` - пройдена ли попытка

### 10. `UserAnswer`

- `id: int` - первичный ключ
- `attempt_id: int` - ссылка на попытку (`test_attempts.id`)
- `question_id: int` - ссылка на вопрос (`questions.id`)
- `selected_option_id: int | None` - выбранный вариант ответа (`answer_options.id`)
- `text_answer: str | None` - текстовый ответ
- `is_correct: bool` - корректность ответа
- `score_received: float` - полученный балл
- `answered_at: datetime` - время ответа

Ограничение:

- уникальная пара `attempt_id + question_id`

### 11. `LessonProgress`

- `id: int` - первичный ключ
- `user_id: int` - ссылка на пользователя (`users.id`)
- `lesson_id: int` - ссылка на урок (`lessons.id`)
- `is_completed: bool` - завершён ли урок
- `completed_at: datetime | None` - дата завершения

Ограничение:

- уникальная пара `user_id + lesson_id`

### 12. `TopicResult`

- `id: int` - первичный ключ
- `user_id: int` - ссылка на пользователя (`users.id`)
- `module_id: int` - ссылка на модуль (`modules.id`)
- `attempts_count: int` - количество завершённых попыток по теме
- `average_percentage: float` - средний процент
- `best_percentage: float` - лучший процент
- `weakness_level: str` - уровень слабости темы (`high`, `medium`, `low`)
- `last_attempt_at: datetime | None` - дата последней попытки
- `updated_at: datetime` - дата обновления записи

Ограничение:

- уникальная пара `user_id + module_id`

### 13. `Recommendation`

- `id: int` - первичный ключ
- `module_id: int` - ссылка на модуль (`modules.id`)
- `title: str` - заголовок рекомендации
- `description: str` - описание рекомендации
- `resource_url: str | None` - ссылка на ресурс
- `trigger_score_threshold: float` - порог процента, ниже или равный которому рекомендация считается актуальной

## Текущие эндпоинты

Ниже перечислены все маршруты, подключённые в `backend/main.py`.

### Системный

- `GET /` - проверочный корневой эндпоинт; возвращает сообщение, что API запущен

### Аутентификация (`/api/auth`)

- `POST /api/auth/register/` - регистрирует пользователя, проверяет уникальность `username` и `email`
- `POST /api/auth/login/` - проверяет логин и пароль, возвращает `JWT` access token
- `GET /api/auth/me/` - возвращает профиль текущего авторизованного пользователя

### Курсы (`/api/courses`)

- `GET /api/courses/` - возвращает список только опубликованных курсов
- `GET /api/courses/{course_id}/` - возвращает один опубликованный курс
- `GET /api/courses/{course_id}/modules/` - возвращает модули опубликованного курса
- `GET /api/courses/{course_id}/progress/my/` - возвращает персональный прогресс пользователя по курсу
- `GET /api/courses/{course_id}/topic-results/my/` - возвращает результаты пользователя по темам курса
- `GET /api/courses/{course_id}/recommendations/my/` - возвращает персональные рекомендации пользователя по курсу
- `POST /api/courses/` - создаёт курс; доступно `teacher` и `admin`
- `PATCH /api/courses/{course_id}/` - обновляет курс; доступно `teacher` и `admin`
- `DELETE /api/courses/{course_id}/` - удаляет курс; доступно `teacher` и `admin`

### Модули (`/api/modules`)

- `GET /api/modules/{module_id}/lessons/` - возвращает уроки модуля, если родительский курс опубликован
- `GET /api/modules/{module_id}/tests/` - возвращает активные тесты модуля, если родительский курс опубликован
- `GET /api/modules/{module_id}/tasks/` - возвращает задания модуля, если родительский курс опубликован; поле `correct_answer` скрыто
- `GET /api/modules/{module_id}/progress/my/` - возвращает персональный прогресс пользователя по модулю
- `GET /api/modules/{module_id}/topic-results/my/` - возвращает результаты пользователя по теме конкретного модуля
- `GET /api/modules/{module_id}/recommendations/my/` - возвращает персональные рекомендации пользователя по модулю
- `POST /api/modules/` - создаёт модуль; доступно `teacher` и `admin`
- `PATCH /api/modules/{module_id}/` - обновляет модуль; доступно `teacher` и `admin`
- `DELETE /api/modules/{module_id}/` - удаляет модуль; доступно `teacher` и `admin`

### Уроки (`/api/lessons`)

- `GET /api/lessons/{lesson_id}/` - возвращает урок и флаг `is_completed` для текущего пользователя
- `POST /api/lessons/{lesson_id}/complete/` - помечает урок как завершённый для текущего пользователя
- `POST /api/lessons/` - создаёт урок; доступно `teacher` и `admin`
- `PATCH /api/lessons/{lesson_id}/` - обновляет урок; доступно `teacher` и `admin`
- `DELETE /api/lessons/{lesson_id}/` - удаляет урок; доступно `teacher` и `admin`

### Задания (`/api/tasks`)

- `GET /api/tasks/{task_id}/` - возвращает одно задание, если родительский курс опубликован; поле `correct_answer` скрыто
- `POST /api/tasks/` - создаёт задание; доступно `teacher` и `admin`
- `PATCH /api/tasks/{task_id}/` - обновляет задание; доступно `teacher` и `admin`
- `DELETE /api/tasks/{task_id}/` - удаляет задание; доступно `teacher` и `admin`

### Тесты и попытки (`/api/tests`, `/api/test-attempts`, `/api/questions`, `/api/answer-options`)

- `GET /api/tests/{test_id}/` - возвращает тест по идентификатору
- `GET /api/tests/{test_id}/questions/` - возвращает вопросы теста с публичными вариантами ответов без поля `is_correct`
- `POST /api/tests/{test_id}/start/` - создаёт новую попытку прохождения теста, если тест активен и лимит попыток не исчерпан
- `POST /api/test-attempts/{attempt_id}/answers/` - сохраняет или обновляет ответ пользователя на вопрос в рамках попытки
- `POST /api/test-attempts/{attempt_id}/finish/` - завершает попытку, считает итоговый процент и признак прохождения, обновляет `TopicResult` для модуля
- `GET /api/test-attempts/{attempt_id}/result/` - возвращает итог попытки и все ответы пользователя
- `POST /api/tests/` - создаёт тест; доступно `teacher` и `admin`
- `PATCH /api/tests/{test_id}/` - обновляет тест; доступно `teacher` и `admin`
- `DELETE /api/tests/{test_id}/` - удаляет тест; доступно `teacher` и `admin`
- `POST /api/questions/` - создаёт вопрос для теста; доступно `teacher` и `admin`
- `PATCH /api/questions/{question_id}/` - обновляет вопрос; доступно `teacher` и `admin`
- `DELETE /api/questions/{question_id}/` - удаляет вопрос; доступно `teacher` и `admin`
- `POST /api/answer-options/` - создаёт вариант ответа; доступно `teacher` и `admin`
- `PATCH /api/answer-options/{option_id}/` - обновляет вариант ответа; доступно `teacher` и `admin`
- `DELETE /api/answer-options/{option_id}/` - удаляет вариант ответа; доступно `teacher` и `admin`

### Рекомендации (`/api/recommendations`)

- `GET /api/recommendations/my/` - возвращает персональные рекомендации текущего пользователя по всем доступным темам
- `GET /api/recommendations/` - возвращает все рекомендации; доступно `teacher` и `admin`
- `POST /api/recommendations/` - создаёт рекомендацию; доступно `teacher` и `admin`
- `GET /api/recommendations/{recommendation_id}/` - возвращает одну рекомендацию; доступно `teacher` и `admin`
- `PATCH /api/recommendations/{recommendation_id}/` - обновляет рекомендацию; доступно `teacher` и `admin`
- `DELETE /api/recommendations/{recommendation_id}/` - удаляет рекомендацию; доступно `teacher` и `admin`

### Аналитика (`/api`)

- `GET /api/progress/my/` - возвращает глобальный прогресс текущего пользователя по всем курсам
- `GET /api/topic-results/my/` - возвращает глобальные результаты текущего пользователя по темам
- `GET /api/analytics/my/summary/` - возвращает краткую персональную сводку по обучению и тестам
- `GET /api/analytics/my/weak-topics/` - возвращает темы пользователя, отсортированные от наиболее слабых
- `GET /api/analytics/my/best-topics/` - возвращает темы пользователя, отсортированные от наиболее сильных
- `GET /api/analytics/my/dynamics/` - возвращает динамику прохождения тестов пользователя по завершённым попыткам
- `GET /api/analytics/groups/{group_id}/topic-results/` - возвращает агрегированную аналитику по темам для учебной группы; доступно `teacher` и `admin`
- `GET /api/analytics/courses/{course_id}/topic-results/` - возвращает агрегированную аналитику по темам курса; доступно `teacher` и `admin`
- `GET /api/analytics/modules/{module_id}/topic-results/` - возвращает агрегированную аналитику по теме конкретного модуля; доступно `teacher` и `admin`

## Что важно отметить по текущему состоянию

- Для `Task` теперь реализован отдельный CRUD-роутер с публичными маршрутами чтения и служебными маршрутами управления.
- Публичная выдача заданий разделена со служебной: `correct_answer` исключён из `TaskRead` и остаётся только в `TaskAdminRead`.
- Публичная выдача курсов и модулей завязана на `is_published` у курса.
- Для преподавателей и администраторов используется проверка роли через `require_teacher_or_admin`.
- Авторизация построена на `Bearer JWT`, `tokenUrl` настроен на `/api/auth/login/`.
