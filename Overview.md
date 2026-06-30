# Overview

## 1. Назначение проекта

Проект представляет собой учебную платформу, в которой:

- студент проходит курсы, модули и уроки;
- выполняет задания и сдаёт тесты;
- получает персональную аналитику, рекомендации и историю прогресса;
- преподаватель и администратор могут публиковать учебный контент, управлять доступом и смотреть агрегированную аналитику.

Архитектурно проект состоит из трёх основных частей:

- `backend/` — FastAPI API, ORM-модели, правила доступа, bootstrap и миграция данных;
- `frontend/` — Angular SPA с маршрутами, страницами и сервисами доступа к API;
- `analytics/` — вычислительный слой, который строит прогресс, результаты по темам, рекомендации и расширенную аналитику.

Сейчас основная БД проекта — `PostgreSQL`, запускаемая через `Docker Compose`. Рабочие данные хранятся в Docker volume, а не в `*.db` внутри репозитория.

## 2. Архитектура и поток данных

### 2.1. Компоненты

- `frontend` — Angular-клиент, публикуется через `nginx`;
- `backend` — FastAPI-приложение с SQLAlchemy;
- `postgres` — PostgreSQL 16 как основная БД;
- `data/` — demo-seed для пустой БД;
- `postman/` — коллекция API-запросов.

### 2.2. Сценарий работы

1. Пользователь открывает `http://localhost:4200`.
2. `nginx` отдаёт статику Angular-приложения.
3. Все запросы на `/api/...` проксируются во `FastAPI`.
4. Backend выполняет проверку доступа, читает/изменяет данные в PostgreSQL.
5. Слой `analytics/` строит вычисляемые метрики по фактическим данным: попыткам тестов, прогрессу уроков, завершённым действиям.

### 2.3. Инициализация БД

При старте backend:

1. создаёт таблицы через `Base.metadata.create_all(...)`;
2. если БД пустая и задан `MIGRATE_SQLITE_PATH`, переносит legacy SQLite в PostgreSQL;
3. если БД пустая и включён `SEED_ON_STARTUP`, загружает demo-данные из `data/`;
4. синхронизирует вводный курс и его контент.

## 3. Backend

### 3.1. Стек backend

- `FastAPI` — HTTP API;
- `SQLAlchemy 2.x` — ORM и слой доступа к данным;
- `PyJWT` — JWT-аутентификация;
- `psycopg` — PostgreSQL driver;
- `backend/services/course_access.py` — правила доступа к курсам;
- `backend/services/analytics.py` — адаптер между API и сервисами аналитики;
- `backend/attempt_metrics.py` — вычисление процента, статуса и факта прохождения попытки.

### 3.2. Роли и права доступа

#### `student`

- может зарегистрироваться и войти;
- видит опубликованные курсы;
- может сам зачислиться на открытый опубликованный курс;
- получает доступ к контенту только после зачисления на курс;
- проходит уроки и тесты;
- видит только собственные рекомендации, прогресс и аналитику.

#### `teacher`

- имеет прямой доступ ко всем опубликованным курсам без обязательного enrollment;
- может создавать, редактировать и удалять курсы, модули, уроки, задания, тесты, вопросы, варианты ответов и рекомендации;
- может вручную зачислять студентов на курсы;
- может искать студентов по справочнику;
- может смотреть групповые и агрегированные analytics-срезы.

#### `admin`

- имеет те же права, что и `teacher`;
- дополнительно выступает как административная роль проекта;
- в текущем коде по набору разрешений эквивалентен преподавателю.

### 3.3. Правила доступа к курсам

Логика доступа сосредоточена в `backend/services/course_access.py`.

- неопубликованный курс скрывается как `404`;
- `teacher` и `admin` проходят проверку доступа автоматически;
- `student` получает доступ только если:
  - уже зачислен на курс;
  - либо курс открытый, но даже в этом случае для доступа к материалам нужно сначала выполнить enrollment;
- для закрытого курса студенту возвращается `403` с предложением обратиться к преподавателю или администратору.

### 3.4. Таблицы БД

Ниже перечислены основные таблицы, их поля и ограничения.

#### `users`

Назначение: учётные записи пользователей платформы.

Поля:

- `id: Integer` — PK, indexed.
- `username: String(100)` — обязательное поле, `UNIQUE`, indexed.
- `password_hash: String(255)` — обязательное поле.
- `email: String(255) | null` — `UNIQUE`, nullable.
- `first_name: String(100) | null` — nullable.
- `last_name: String(100) | null` — nullable.
- `role: Enum(UserRole)` — обязательное enum-поле со значениями `student`, `teacher`, `admin`, default `student`.
- `university: String(255) | null` — nullable.
- `group: String(100) | null` — nullable.
- `course_year: Integer | null` — nullable.
- `created_at: DateTime(timezone=True)` — default `utcnow`.

Ограничения и замечания:

- уникальность `username`;
- уникальность `email`, если он указан;
- enum ограничен значениями `UserRole`;
- на уровне API `course_year` валидируется в диапазоне `1..6`.

#### `courses`

Назначение: верхний уровень учебной структуры.

Поля:

- `id: Integer` — PK, indexed.
- `title: String(255)` — обязательное поле, indexed.
- `description: Text | null` — nullable.
- `author_id: Integer | null` — FK -> `users.id`, nullable.
- `difficulty: Integer` — default `1`.
- `is_published: Boolean` — default `False`.
- `is_open: Boolean` — default `True`.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Ограничения и замечания:

- курс может быть опубликованным или скрытым;
- `is_open=True` разрешает self-enrollment;
- на уровне API `difficulty` валидируется в диапазоне `1..10`.

#### `course_enrollments`

Назначение: факт зачисления пользователя на курс.

Поля:

- `id: Integer` — PK, indexed.
- `user_id: Integer` — FK -> `users.id`, indexed.
- `course_id: Integer` — FK -> `courses.id`, indexed.
- `assigned_by_id: Integer | null` — FK -> `users.id`, nullable.
- `created_at: DateTime(timezone=True)` — default `utcnow`.

Ограничения:

- `UNIQUE(user_id, course_id)` — один студент не может быть зачислен на один и тот же курс повторно.

Замечания:

- `assigned_by_id` используется, когда доступ выдал `teacher` или `admin`;
- при self-enrollment поле остаётся `null`.

#### `modules`

Назначение: тематические разделы внутри курса.

Поля:

- `id: Integer` — PK, indexed.
- `course_id: Integer` — FK -> `courses.id`, indexed.
- `title: String(255)` — обязательное поле.
- `description: Text | null` — nullable.
- `order: Integer` — default `0`.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Ограничения:

- каждый модуль должен принадлежать существующему курсу.

#### `lessons`

Назначение: теоретические единицы внутри модуля.

Поля:

- `id: Integer` — PK, indexed.
- `module_id: Integer` — FK -> `modules.id`, indexed.
- `title: String(255)` — обязательное поле.
- `content_blocks: Text | null` — сериализованные блоки контента урока.
- `video_url: String(500) | null` — nullable.
- `external_url: String(500) | null` — nullable.
- `order: Integer` — default `0`.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Замечания:

- legacy-поле `content` в БД больше не хранится;
- backend умеет строить `content_blocks` из старого plain text контента.

#### `lesson_progress`

Назначение: фиксация завершения урока пользователем.

Поля:

- `id: Integer` — PK, indexed.
- `user_id: Integer` — FK -> `users.id`, indexed.
- `lesson_id: Integer` — FK -> `lessons.id`, indexed.
- `is_completed: Boolean` — default `False`.
- `completed_at: DateTime(timezone=True) | null` — nullable.

Ограничения:

- `UNIQUE(user_id, lesson_id)` — у пользователя одна запись прогресса на урок.

#### `tasks`

Назначение: практические задания модуля.

Поля:

- `id: Integer` — PK, indexed.
- `module_id: Integer` — FK -> `modules.id`, indexed.
- `title: String(255)` — обязательное поле.
- `description: Text` — обязательное поле.
- `max_score: Float` — default `0`.
- `order: Integer` — default `0`.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

#### `tests`

Назначение: тесты по курсу или модулю.

Поля:

- `id: Integer` — PK, indexed.
- `course_id: Integer` — FK -> `courses.id`, indexed.
- `module_id: Integer | null` — FK -> `modules.id`, nullable.
- `title: String(255)` — обязательное поле.
- `description: Text | null` — nullable.
- `time_limit: Integer | null` — nullable.
- `passing_score: Float` — default `60`.
- `attempts_allowed: Integer` — default `1`.
- `is_active: Boolean` — default `True`.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Замечания:

- `module_id=null` допускает course-level test;
- бизнес-логика ограничивает число попыток через `attempts_allowed`;
- в публичной выдаче студенту доступны только активные тесты модуля.

#### `questions`

Назначение: вопросы тестов.

Поля:

- `id: Integer` — PK, indexed.
- `test_id: Integer` — FK -> `tests.id`, indexed.
- `text: Text` — обязательное поле.
- `question_type: Enum(QuestionType)` — обязательное enum-поле, default `single_choice`.
- `difficulty_level: String(50) | null` — nullable.
- `score: Float` — default `1`.
- `order: Integer` — default `0`.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Enum `QuestionType`:

- `single_choice`
- `multiple_choice`
- `text`

#### `answer_options`

Назначение: варианты ответов для вопросов.

Поля:

- `id: Integer` — PK, indexed.
- `question_id: Integer` — FK -> `questions.id`, indexed.
- `text: Text` — обязательное поле.
- `is_correct: Boolean` — default `False`.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Замечания:

- для `text`-вопросов правильные формулировки тоже хранятся здесь;
- у `multiple_choice` проверка идёт по совпадению множества выбранных верных options.

#### `test_attempts`

Назначение: попытки прохождения тестов.

Поля:

- `id: Integer` — PK, indexed.
- `user_id: Integer` — FK -> `users.id`, indexed.
- `test_id: Integer` — FK -> `tests.id`, indexed.
- `started_at: DateTime(timezone=True)` — default `utcnow`.
- `finished_at: DateTime(timezone=True) | null` — nullable.
- `score: Float` — default `0`.
- `max_score: Float` — default `0`.

Вычисляемые свойства ORM:

- `percentage` — процент выполнения попытки;
- `is_passed` — факт прохождения с учётом `tests.passing_score` и `finished_at`.

Бизнес-ограничения:

- одновременно у студента должна быть только одна незавершённая попытка на тест;
- новое прохождение запрещается, если исчерпан `attempts_allowed`.

#### `user_answers`

Назначение: ответы пользователя на вопросы в рамках одной попытки.

Поля:

- `id: Integer` — PK, indexed.
- `attempt_id: Integer` — FK -> `test_attempts.id`, indexed.
- `question_id: Integer` — FK -> `questions.id`, indexed.
- `selected_option_id: Integer | null` — FK -> `answer_options.id`, nullable.
- `text_answer: Text | null` — nullable.
- `is_correct: Boolean` — default `False`.
- `score_received: Float` — default `0`.
- `answered_at: DateTime(timezone=True)` — default `utcnow`.

Ограничения:

- `UNIQUE(attempt_id, question_id)` — один ответ на один вопрос внутри одной попытки.

Замечания:

- для `single_choice` используется `selected_option_id`;
- для `multiple_choice` фактическое множество хранится в связующей таблице `user_answer_option_selections`;
- свойство `selected_option_ids` в модели объединяет оба механизма в единый список.

#### `user_answer_option_selections`

Назначение: связь ответа пользователя с несколькими выбранными вариантами.

Поля:

- `user_answer_id: Integer` — FK -> `user_answers.id`, часть composite PK.
- `answer_option_id: Integer` — FK -> `answer_options.id`, часть composite PK.

Ограничения:

- composite PK `(user_answer_id, answer_option_id)`;
- дополнительный `UNIQUE(user_answer_id, answer_option_id)`.

#### `topic_results`

Назначение: минимальный кэш по теме/модулю для пользователя.

Поля:

- `id: Integer` — PK, indexed.
- `user_id: Integer` — FK -> `users.id`, indexed.
- `module_id: Integer` — FK -> `modules.id`, indexed.
- `last_attempt_at: DateTime(timezone=True) | null` — nullable.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Ограничения:

- `UNIQUE(user_id, module_id)`.

Замечания:

- большинство аналитических метрик здесь не хранится постоянно;
- они пересчитываются на лету сервисом `TopicResultService`.

#### `recommendations`

Назначение: библиотека рекомендаций, привязанных к модулю.

Поля:

- `id: Integer` — PK, indexed.
- `module_id: Integer` — FK -> `modules.id`, indexed.
- `title: String(255)` — обязательное поле.
- `description: Text` — обязательное поле.
- `resource_url: String(500) | null` — nullable.
- `created_at: DateTime(timezone=True)` — default `utcnow`.
- `updated_at: DateTime(timezone=True)` — default `utcnow`, auto-update.

Замечания:

- таблица хранит сам контент рекомендаций;
- правило показа рекомендации выбирается не в БД, а в `RecommendationService`.

### 3.5. Backend-модули и эндпоинты

#### `backend/main.py`

Назначение:

- создаёт FastAPI-приложение;
- подключает роутеры;
- на старте инициирует схему БД, bootstrap и seed/migration.

#### `backend/api/auth.py`

Назначение:

- регистрация;
- вход по username/password;
- выдача JWT;
- получение профиля текущего пользователя.

Эндпоинты:

- `POST /api/auth/register/`
  - роль: гость;
  - создаёт пользователя с ролью `student`;
  - проверяет уникальность `username` и `email`.
- `POST /api/auth/login/`
  - роль: гость;
  - возвращает `access_token`.
- `GET /api/auth/me/`
  - роль: любой авторизованный пользователь;
  - возвращает профиль текущего пользователя.

#### `backend/api/courses.py`

Назначение:

- выдача списка курсов;
- enrollment и управление доступом;
- курс как точка входа в модули, прогресс, topic results и рекомендации;
- CRUD курсов.

Эндпоинты:

- `GET /api/courses/`
  - публичный;
  - возвращает опубликованные курсы.
- `GET /api/courses/my/enrollments/`
  - роль: авторизованный пользователь;
  - возвращает список собственных enrollment-записей.
- `POST /api/courses/{course_id}/enroll/my/`
  - роль: авторизованный пользователь;
  - self-enrollment на открытый опубликованный курс.
- `GET /api/courses/{course_id}/enrollments/`
  - роль: `teacher`, `admin`;
  - возвращает список студентов курса.
- `POST /api/courses/{course_id}/enrollments/`
  - роль: `teacher`, `admin`;
  - вручную зачисляет студента.
- `GET /api/courses/students/search/`
  - роль: `teacher`, `admin`;
  - поиск студентов по `username`, `email`, имени, фамилии, группе, вузу.
- `GET /api/courses/{course_id}/`
  - роль: авторизованный пользователь с доступом к курсу;
  - карточка курса.
- `GET /api/courses/{course_id}/modules/`
  - роль: авторизованный пользователь с доступом к курсу;
  - список модулей курса.
- `GET /api/courses/{course_id}/progress/my/`
  - роль: авторизованный пользователь с доступом к курсу;
  - собственный прогресс по курсу.
- `GET /api/courses/{course_id}/topic-results/my/`
  - роль: авторизованный пользователь с доступом к курсу;
  - собственные результаты по темам курса.
- `GET /api/courses/{course_id}/recommendations/my/`
  - роль: авторизованный пользователь с доступом к курсу;
  - персональные рекомендации по курсу.
- `POST /api/courses/`
  - роль: `teacher`, `admin`;
  - создаёт курс.
- `PATCH /api/courses/{course_id}/`
  - роль: `teacher`, `admin`;
  - обновляет поля курса.
- `DELETE /api/courses/{course_id}/`
  - роль: `teacher`, `admin`;
  - удаляет курс каскадно вместе с дочерними сущностями.

#### `backend/api/modules.py`

Назначение:

- выдача модуля и его содержимого;
- доступ к урокам, тестам, прогрессу, topic results и рекомендациям на уровне модуля;
- CRUD модулей.

Эндпоинты:

- `GET /api/modules/{module_id}/`
  - роль: авторизованный пользователь с доступом к курсу модуля.
- `GET /api/modules/{module_id}/lessons/`
  - роль: авторизованный пользователь с доступом к курсу модуля;
  - список уроков модуля.
- `GET /api/modules/{module_id}/tests/`
  - роль: авторизованный пользователь с доступом к курсу модуля;
  - список активных тестов модуля.
- `GET /api/modules/{module_id}/progress/my/`
  - роль: авторизованный пользователь;
  - прогресс по модулю.
- `GET /api/modules/{module_id}/topic-results/my/`
  - роль: авторизованный пользователь;
  - результаты по теме/модулю.
- `GET /api/modules/{module_id}/recommendations/my/`
  - роль: авторизованный пользователь;
  - персональные рекомендации по модулю.
- `POST /api/modules/`
  - роль: `teacher`, `admin`;
  - создаёт модуль.
- `PATCH /api/modules/{module_id}/`
  - роль: `teacher`, `admin`;
  - редактирует модуль.
- `DELETE /api/modules/{module_id}/`
  - роль: `teacher`, `admin`;
  - удаляет модуль каскадно.

#### `backend/api/lessons.py`

Назначение:

- просмотр содержимого урока;
- завершение урока пользователем;
- CRUD уроков.

Эндпоинты:

- `GET /api/lessons/{lesson_id}/`
  - роль: авторизованный пользователь с доступом к курсу;
  - возвращает урок, признак завершения и данные о следующем уроке.
- `POST /api/lessons/{lesson_id}/complete/`
  - роль: авторизованный пользователь;
  - создаёт или обновляет `lesson_progress`.
- `POST /api/lessons/`
  - роль: `teacher`, `admin`;
  - создаёт урок, сериализуя `content_blocks`.
- `PATCH /api/lessons/{lesson_id}/`
  - роль: `teacher`, `admin`;
  - обновляет урок;
  - может пересобрать `content_blocks` из legacy `content`.
- `DELETE /api/lessons/{lesson_id}/`
  - роль: `teacher`, `admin`.

#### `backend/api/tasks.py`

Назначение:

- выдача заданий модуля;
- просмотр одного задания;
- CRUD заданий.

Эндпоинты:

- `GET /api/modules/{module_id}/tasks/`
  - роль: авторизованный пользователь с доступом к курсу;
  - список заданий модуля.
- `GET /api/tasks/{task_id}/`
  - роль: авторизованный пользователь с доступом к курсу.
- `POST /api/tasks/`
  - роль: `teacher`, `admin`.
- `PATCH /api/tasks/{task_id}/`
  - роль: `teacher`, `admin`.
- `DELETE /api/tasks/{task_id}/`
  - роль: `teacher`, `admin`.

#### `backend/api/tests.py`

Назначение:

- выдача тестов и вопросов;
- старт, продолжение и завершение попыток;
- автосохранение ответов;
- CRUD тестов, вопросов и answer options.

Эндпоинты чтения и прохождения:

- `GET /api/tests/{test_id}/`
  - роль: авторизованный пользователь с доступом к курсу.
- `GET /api/tests/{test_id}/active-attempt/`
  - роль: авторизованный пользователь;
  - текущая незавершённая попытка по тесту.
- `GET /api/tests/{test_id}/analytics/my/`
  - роль: авторизованный пользователь;
  - аналитика собственных попыток по тесту.
- `GET /api/test-attempts/my/unfinished/`
  - роль: авторизованный пользователь;
  - список всех незавершённых попыток.
- `GET /api/tests/{test_id}/questions/`
  - роль: авторизованный пользователь;
  - вопросы теста с публичными answer options.
- `POST /api/tests/{test_id}/start/`
  - роль: авторизованный пользователь;
  - стартует новую попытку или возвращает существующую незавершённую;
  - блокирует старт при исчерпанном лимите попыток.
- `POST /api/test-attempts/{attempt_id}/answers/`
  - роль: владелец попытки, а также `teacher`/`admin`;
  - сохраняет или обновляет ответ;
  - поддерживает `single_choice`, `multiple_choice`, `text`;
  - автоматически считает `is_correct` и `score_received`.
- `POST /api/test-attempts/{attempt_id}/finish/`
  - роль: владелец попытки, а также `teacher`/`admin`;
  - закрывает попытку, пересчитывает `score`, `max_score`, обновляет topic result.
- `GET /api/test-attempts/{attempt_id}/result/`
  - роль: владелец попытки, а также `teacher`/`admin`;
  - возвращает attempt + ответы.

Эндпоинты администрирования тестов:

- `POST /api/tests/`
- `PATCH /api/tests/{test_id}/`
- `DELETE /api/tests/{test_id}/`

Роль для всех трёх: `teacher`, `admin`.

Эндпоинты администрирования вопросов:

- `POST /api/questions/`
- `PATCH /api/questions/{question_id}/`
- `DELETE /api/questions/{question_id}/`

Роль: `teacher`, `admin`.

Эндпоинты администрирования вариантов ответов:

- `POST /api/answer-options/`
- `PATCH /api/answer-options/{option_id}/`
- `DELETE /api/answer-options/{option_id}/`

Роль: `teacher`, `admin`.

#### `backend/api/recommendations.py`

Назначение:

- выдача персональных рекомендаций текущему пользователю;
- CRUD библиотеки рекомендаций.

Эндпоинты:

- `GET /api/recommendations/my/`
  - роль: авторизованный пользователь;
  - персональные рекомендации по всем доступным темам.
- `GET /api/recommendations/`
  - роль: `teacher`, `admin`;
  - полный список рекомендаций.
- `GET /api/recommendations/{recommendation_id}/`
  - роль: `teacher`, `admin`.
- `POST /api/recommendations/`
  - роль: `teacher`, `admin`.
- `PATCH /api/recommendations/{recommendation_id}/`
  - роль: `teacher`, `admin`.
- `DELETE /api/recommendations/{recommendation_id}/`
  - роль: `teacher`, `admin`.

#### `backend/api/analytics.py`

Назначение:

- выдача персональной analytics-сводки;
- выдача weak/best topics и dynamics;
- teacher/admin analytics по группе, курсу, модулю, тестам и вопросам.

Персональные эндпоинты:

- `GET /api/progress/my/`
  - роль: авторизованный пользователь;
  - глобальный прогресс.
- `GET /api/topic-results/my/`
  - роль: авторизованный пользователь;
  - результаты по темам по всем доступным курсам.
- `GET /api/analytics/my/snapshot/`
  - роль: авторизованный пользователь;
  - полный analytics snapshot.
- `GET /api/analytics/my/summary/`
  - роль: авторизованный пользователь;
  - краткая агрегированная сводка.
- `GET /api/analytics/my/weak-topics/`
  - роль: авторизованный пользователь.
- `GET /api/analytics/my/best-topics/`
  - роль: авторизованный пользователь.
- `GET /api/analytics/my/dynamics/`
  - роль: авторизованный пользователь.

Teacher/Admin эндпоинты:

- `GET /api/analytics/groups/{group_id}/topic-results/`
  - агрегаты по учебной группе.
- `GET /api/analytics/courses/{course_id}/topic-results/`
  - агрегаты по курсу.
- `GET /api/analytics/modules/{module_id}/topic-results/`
  - агрегаты по модулю.
- `GET /api/analytics/questions/{question_id}/`
  - analytics snapshot по одному вопросу;
  - optional `user_id` для фильтра по конкретному пользователю.
- `GET /api/analytics/tests/{test_id}/questions/`
  - analytics по всем вопросам теста;
  - optional `user_id`.
- `GET /api/analytics/tests/{test_id}/questions/hardest/`
  - самые трудные вопросы теста.
- `GET /api/analytics/tests/{test_id}/questions/most-missed/`
  - наиболее часто проваливаемые вопросы теста.
- `GET /api/analytics/modules/{module_id}/questions/`
  - analytics по вопросам всех тестов модуля;
  - optional `user_id`.
- `GET /api/analytics/modules/{module_id}/questions/hardest/`
  - самые трудные вопросы модуля.

Роль для всех teacher/admin analytics-эндпоинтов: `teacher`, `admin`.

## 4. Frontend

### 4.1. Общая роль frontend

Frontend — это Angular SPA, которая:

- управляет маршрутизацией пользователя между учебными сущностями;
- хранит JWT в `localStorage`;
- вызывает backend по относительным путям `/api/...`;
- защищает приватные страницы через `authGuard`;
- закрывает страницы логина и регистрации для уже авторизованного пользователя через `guestGuard`.

### 4.2. Маршруты и страницы

#### `/` и `/dashboard` — `DashboardPageComponent`

Назначение:

- главная страница платформы;
- показывает общую учебную сводку, персональные рекомендации и доступные курсы.

Доступ:

- публичный маршрут, но фактический контент зависит от состояния авторизации.

#### `/login` — `LoginPageComponent`

Назначение:

- форма входа;
- получение JWT и загрузка профиля.

Guard:

- `guestGuard`.

#### `/register` — `RegisterPageComponent`

Назначение:

- регистрация нового пользователя;
- после регистрации инициирует вход.

Guard:

- `guestGuard`.

#### `/courses` — `CoursesPageComponent`

Назначение:

- каталог опубликованных курсов;
- точка входа в enrolment и обучение.

Доступ:

- публичный маршрут.

#### `/courses/:courseId` — `CoursePageComponent`

Назначение:

- детальная страница курса;
- показывает описание, модули, курс-level progress, topic results и рекомендации.

Guard:

- `authGuard`.

#### `/courses/:courseId/manage` — `CourseAccessPageComponent`

Назначение:

- управление доступом к курсу;
- просмотр зачисленных пользователей;
- поиск студентов и ручное назначение enrollment.

Guard:

- `authGuard`.

Замечание:

- реальная авторизация на teacher/admin проверяется backend.

#### `/modules/:moduleId` — `ModulePageComponent`

Назначение:

- детальная страница модуля;
- список уроков, заданий, тестов, прогресс и рекомендации по модулю.

Guard:

- `authGuard`.

#### `/lessons/:lessonId` — `LessonPageComponent`

Назначение:

- просмотр конкретного урока;
- отметка завершения урока;
- переход к следующему уроку.

Guard:

- `authGuard`.

#### `/tasks/:taskId` — `TaskPageComponent`

Назначение:

- просмотр карточки практического задания.

Guard:

- `authGuard`.

#### `/tests/:testId` — `TestPageComponent`

Назначение:

- просмотр описания теста;
- вход в активную попытку или старт новой.

Guard:

- `authGuard`.

#### `/tests/:testId/attempt/:attemptId` — `TestAttemptPageComponent`

Назначение:

- непосредственное прохождение теста;
- автосохранение ответов;
- завершение попытки.

Guard:

- `authGuard`.

#### `/tests/:testId/attempt/:attemptId/result` — `TestAttemptResultPageComponent`

Назначение:

- просмотр результата завершённой попытки;
- вывод оценивания и сохранённых ответов.

Guard:

- `authGuard`.

#### `/attempts` — `UnfinishedAttemptsPageComponent`

Назначение:

- список незавершённых попыток;
- быстрый возврат к прерванному тесту.

Guard:

- `authGuard`.

#### `/recommendations` — `RecommendationsPageComponent`

Назначение:

- единая лента персональных рекомендаций;
- отображение причин рекомендаций, приоритета и ссылки на материал.

Guard:

- `authGuard`.

#### `/analytics` — `AnalyticsPageComponent`

Назначение:

- персональная аналитическая страница;
- progress, summary, weak/best topics, instability, improving topics и dynamics.

Guard:

- `authGuard`.

#### `/profile` — `ProfilePageComponent`

Назначение:

- личный профиль пользователя;
- отображение роли, вуза, группы и базовых персональных данных.

Guard:

- `authGuard`.

#### `**`

Назначение:

- fallback-маршрут;
- перенаправляет пользователя на `/`.

## 5. Analytics

Папка `analytics/` содержит вычислительный слой, который строит вторичные аналитические объекты по фактическим данным БД.

### 5.1. `ProgressService` — `analytics/progress_service.py`

Назначение:

- считает учебный прогресс пользователя;
- умеет работать в трёх scope: глобально, по курсу и по модулю;
- учитывает только доступные пользователю курсы.

Основные методы:

- `get_accessible_course_ids(user_id) -> list[int]`
  - возвращает список course id, доступных пользователю;
  - `teacher`/`admin` видят все опубликованные курсы;
  - `student` видит только опубликованные курсы с enrollment.
- `get_overall_progress(user_id) -> ProgressRead`
  - возвращает глобальный прогресс.
- `get_course_progress(user_id, course_id) -> ProgressRead`
  - прогресс внутри одного курса.
- `get_module_progress(user_id, module_id) -> ProgressRead`
  - прогресс внутри одного модуля.
- `get_completed_lessons_percentage(...) -> float`
  - процент завершённых уроков.
- `get_completed_modules_percentage(...) -> float`
  - процент полностью завершённых модулей.
- `get_modules_for_scope(...) -> list[Module]`
  - возвращает набор модулей выбранного scope.
- `get_scope_lesson_ids(...) -> list[int]`
  - возвращает lesson ids выбранного scope.
- `get_scope_test_ids(...) -> list[int]`
  - возвращает test ids выбранного scope.
- `_build_progress(...) -> ProgressRead`
  - собирает итоговый DTO с:
    - `completed_lessons`
    - `total_lessons`
    - `passed_tests`
    - `total_tests`
    - `average_test_percentage`
    - `completion_rate`

Возвращаемый результат:

- `ProgressRead`.

### 5.2. `TopicResultService` — `analytics/topic_result_service.py`

Назначение:

- считает аналитический результат пользователя по теме;
- тема в текущей архитектуре эквивалентна модулю;
- опирается на попытки тестов и завершённость уроков.

Основные методы:

- `update_topic_result_after_attempt(user_id, module_id) -> dict`
  - пересчитывает topic result после завершения попытки;
  - обновляет `last_attempt_at` в `topic_results`.
- `get_or_create_topic_result(user_id, module_id) -> TopicResult`
  - возвращает существующую строку или создаёт новую.
- `get_user_topic_results(user_id) -> list[dict]`
  - результаты по всем доступным темам.
- `get_course_topic_results(user_id, course_id) -> list[dict]`
  - результаты по темам курса.
- `get_module_topic_results(user_id, module_id) -> list[dict]`
  - результат по одной теме/модулю.
- `calculate_topic_state(...) -> dict`
  - определяет:
    - `weakness_level`
    - `risk_level`
    - `learning_state`
    - `reason_code`
- `calculate_weakness_level(...) -> str`
  - возвращает категорию слабости по среднему результату.
- `_calculate_topic_result_values(...) -> dict`
  - считает:
    - число попыток;
    - средний, лучший, первый, последний процент;
    - прогресс между первой и последней попыткой;
    - число успешных и неуспешных завершённых попыток;
    - долю завершённых уроков;
    - тренд;
    - индекс стабильности.
- `_calculate_progress_trend(percentages) -> str`
  - `improving`, `declining`, `stable`, `not_enough_data`.
- `_calculate_stability_index(percentages) -> float | None`
  - индекс устойчивости результата.
- `_get_module_lesson_completion_ratio(user_id, module_id) -> float`
  - доля завершённых уроков модуля.
- `_serialize_topic_result(...) -> dict`
  - формирует payload для API.

Возвращаемый результат:

- `dict`, который затем приводится к `TopicResultRead`.

### 5.3. `WeakTopicDetector` — `analytics/topic_result_service.py`

Назначение:

- интерпретирует сырые topic results;
- классифицирует темы по категориям;
- формирует причины, теги и сортировки для UI и recommendation engine.

Основные методы:

- `get_weak_topics(...) -> list[dict]`
  - слабые темы пользователя.
- `get_strong_topics(...) -> list[dict]`
  - сильные темы.
- `get_unstable_topics(...) -> list[dict]`
  - темы с нестабильным результатом.
- `get_improving_topics(...) -> list[dict]`
  - темы с заметным ростом.
- `get_topics_without_enough_data(...) -> list[dict]`
  - темы, по которым ещё мало завершённых попыток.
- `prepare_analytics_data(...) -> dict`
  - собирает полный набор списков для analytics snapshot:
    - `topic_results`
    - `weak_topics`
    - `strong_topics`
    - `best_topics`
    - `unstable_topics`
    - `improving_topics`
    - `topics_without_enough_data`
- `prepare_recommendation_data(...) -> list[dict]`
  - подготавливает enriched topic contexts для recommendation engine.
- `determine_weak_topic_reason(topic_result) -> str`
  - человекочитаемая причина слабости темы.
- `determine_strong_topic_reason(topic_result) -> str`
  - объяснение, почему тема сильная.
- `build_topic_tags(topic_result) -> list[str]`
  - возвращает теги вроде:
    - слабая тема;
    - высокий риск;
    - нестабильность;
    - теория не завершена;
    - освоена;
    - недостаточно данных.

Ключевые критерии:

- слабая тема — низкий средний результат, отсутствие прогресса, незавершённая теория с ошибками или нестабильность с провалами;
- сильная тема — высокий средний результат, стабильность, низкая доля провалов, завершённая теория;
- нестабильная тема — низкий stability index или `learning_state == "unstable"`;
- improving — положительный тренд или заметный `progress_delta`.

Возвращаемый результат:

- списки `dict`, которые далее приводятся к `TopicResultRead`.

### 5.4. `RecommendationService` — `analytics/recommendation_service.py`

Назначение:

- сопоставляет контент рекомендаций с проблемными темами пользователя;
- определяет правила показа, приоритет и текст объяснения.

Используемые правила:

- `high_failure_streak`
- `low_average_score`
- `unfinished_theory`
- `no_progress_after_retries`
- `unstable_mastery`
- `improving_but_not_mastered`

Основные методы:

- `get_personal_recommendations(user_id) -> list[dict]`
- `get_course_recommendations(user_id, course_id) -> list[dict]`
- `get_module_recommendations(user_id, module_id) -> list[dict]`
- `match_topic_results_with_recommendations(...) -> list[dict]`
  - соединяет аналитический контекст темы и библиотеку `recommendations`.
- `determine_priority(context, rule_key) -> str`
  - возвращает `high`, `medium` или `low`.
- `build_reason_explanation(context, rule_key) -> str`
  - строит текст причины, который видит пользователь.
- `to_frontend_payload(recommendation, context, rule_key) -> dict`
  - формирует payload для `PersonalRecommendationRead`.
- `_build_contexts(user_id, topic_results) -> dict[int, dict]`
  - расширяет тему данными о streak, unfinished lessons и текущем состоянии.
- `_get_failed_attempt_metrics(...) -> dict[int, dict]`
  - считает число провалов и failure streak по модулю.
- `_get_unfinished_lessons_count(...) -> dict[int, int]`
  - считает число незавершённых уроков в модуле.
- `_get_matching_rules(context) -> list[RecommendationRule]`
  - определяет, какие правила применимы к теме.
- `_get_recommendation_entities(module_ids) -> dict[int, list[Recommendation]]`
  - подтягивает контент рекомендаций из БД.

Возвращаемый результат:

- список `dict`, далее приводимый к `PersonalRecommendationRead`.

### 5.5. `TestAnalyticsService` — `analytics/test_analytics_service.py`

Назначение:

- строит аналитику прохождения одного теста пользователем;
- учитывает завершённые и незавершённые попытки;
- формирует snapshot по каждой попытке и агрегаты по тесту.

Основные методы:

- `get_test_attempts(user_id, test_id, include_unfinished=True) -> list[TestAttempt]`
  - возвращает историю попыток пользователя по тесту.
- `calculate_completion_percentage(attempt) -> float`
  - процент выполнения попытки;
  - для незавершённой попытки использует текущую сумму баллов по сохранённым ответам.
- `calculate_attempts_count(attempts) -> int`
- `calculate_best_result(attempts) -> float`
- `calculate_average_result(attempts) -> float`
- `calculate_first_result(attempts) -> float`
- `calculate_last_result(attempts) -> float`
- `calculate_progress_delta(attempts) -> float`
- `calculate_best_improvement(attempts) -> float`
- `calculate_unfinished_attempts_count(attempts) -> int`
- `calculate_failure_streak(attempts) -> int`
  - сколько последних завершённых попыток подряд были неуспешными.
- `calculate_test_trend(attempts) -> str`
  - `improving`, `declining`, `stable`, `not_enough_data`.
- `build_test_insight(attempts) -> str`
  - человекочитаемый вывод по тесту.
- `calculate_time_spent_seconds(attempt) -> int | None`
- `calculate_answered_questions_count(attempt) -> int`
- `calculate_status(attempt) -> str`
  - использует `calculate_attempt_status(...)`.
- `build_attempt_snapshot(attempt) -> dict`
  - строит payload отдельной попытки.
- `build_test_analytics(user_id, test_id) -> dict`
  - итоговая аналитика теста.

Возвращаемый результат:

- `dict`, далее приводимый к `TestAnalyticsRead`.

### 5.6. `QuestionAnalyticsService` — `analytics/question_analytics_service.py`

Назначение:

- строит аналитику по отдельным вопросам, по тесту и по модулю;
- показывает успешность, средний балл и типичные ошибки.

Основные методы:

- `get_question_attempts(question_id, user_id=None) -> list[UserAnswer]`
  - возвращает ответы по вопросу;
  - optional фильтр по конкретному пользователю.
- `calculate_question_success_rate(question_id, user_id=None) -> float`
  - доля правильных ответов.
- `calculate_question_average_score(question_id, user_id=None) -> float`
  - средний балл по вопросу.
- `get_common_wrong_options(question_id, user_id=None) -> list[dict]`
  - топ наиболее часто выбираемых неправильных вариантов.
- `build_question_snapshot(question_id, user_id=None) -> dict`
  - формирует полный payload вопроса:
    - `attempts_count`
    - `correct_answers_count`
    - `incorrect_answers_count`
    - `success_rate`
    - `average_score`
    - `common_wrong_options`
- `get_test_question_analytics(test_id, user_id=None) -> list[dict]`
  - analytics по всем вопросам теста.
- `get_hardest_questions_for_test(test_id) -> list[dict]`
  - сортировка по трудности.
- `get_most_missed_questions_for_test(test_id) -> list[dict]`
  - сортировка по числу ошибок.
- `get_module_question_analytics(module_id, user_id=None) -> list[dict]`
  - analytics по вопросам всех тестов модуля.
- `get_hardest_questions_for_module(module_id) -> list[dict]`
  - самые трудные вопросы модуля.

Возвращаемый результат:

- `dict` или `list[dict]`, далее приводимые к `QuestionAnalyticsRead`.

### 5.7. `StudentSummaryService` — `analytics/student_summary.py`

Назначение:

- собирает персональную сводку по пользователю;
- объединяет прогресс, результаты по темам и временную динамику попыток.

Основные методы:

- `get_summary(user_id) -> dict`
  - возвращает:
    - `total_attempts`
    - `completed_attempts`
    - `passed_attempts`
    - `average_score`
    - `average_percentage`
    - `lessons_completed`
    - `unique_courses_started`
- `get_dynamics(user_id) -> list[dict]`
  - временной ряд завершённых попыток:
    - дата;
    - test id и title;
    - module id и title;
    - percentage;
    - `is_passed`.
- `build_analytics_snapshot(user_id) -> dict`
  - собирает полный payload персональной аналитики:
    - `progress`
    - `summary`
    - `topicResults`
    - `weakTopics`
    - `strongTopics`
    - `bestTopics`
    - `unstableTopics`
    - `improvingTopics`
    - `topicsWithoutEnoughData`
    - `dynamics`

Возвращаемый результат:

- `dict`, который в backend приводится к `PersonalAnalyticsSnapshotRead`.

### 5.8. `backend/services/analytics.py`

Назначение:

- адаптерный слой между роутерами FastAPI и сервисами `analytics/`;
- приводит внутренние `dict`-payload'ы к Pydantic DTO;
- скрывает от роутеров детали вычислительной реализации.

Основные функции:

- `build_progress(...) -> ProgressRead`
- `compute_topic_results(...) -> list[TopicResultRead]`
- `upsert_topic_result(...) -> TopicResult | None`
- `build_test_analytics(...) -> TestAnalyticsRead`
- `build_summary(...) -> UserAnalyticsSummaryRead`
- `build_dynamics(...) -> list[AnalyticsDynamicsPointRead]`
- `build_personal_analytics_snapshot(...) -> PersonalAnalyticsSnapshotRead`
- `build_weak_topics(...) -> list[TopicResultRead]`
- `build_best_topics(...) -> list[TopicResultRead]`
- `build_personal_recommendations(...) -> list[PersonalRecommendationRead]`
- `build_question_snapshot(...) -> QuestionAnalyticsRead`
- `build_test_question_analytics(...) -> list[QuestionAnalyticsRead]`
- `build_hardest_questions_for_test(...) -> list[QuestionAnalyticsRead]`
- `build_most_missed_questions_for_test(...) -> list[QuestionAnalyticsRead]`
- `build_module_question_analytics(...) -> list[QuestionAnalyticsRead]`
- `build_hardest_questions_for_module(...) -> list[QuestionAnalyticsRead]`
- `build_topic_result_aggregates(...) -> list[TopicResultAggregateRead]`

### 5.9. Какие данные получает frontend из analytics

Frontend использует analytics-слой для получения:

- `ProgressRead` — общий или scoped progress;
- `TopicResultRead` — результат по теме;
- `PersonalRecommendationRead` — персональная рекомендация с причиной;
- `TestAnalyticsRead` — аналитика одного теста;
- `QuestionAnalyticsRead` — аналитика вопроса;
- `UserAnalyticsSummaryRead` — краткая summary по пользователю;
- `PersonalAnalyticsSnapshotRead` — полный снимок аналитики;
- `TopicResultAggregateRead` — агрегаты для teacher/admin views.

## 6. Итоговая картина проекта

В текущем виде проект устроен так:

- backend хранит пользователей, учебный контент и факты обучения;
- frontend проводит пользователя по маршруту от курса к уроку, тесту и аналитике;
- слой `analytics/` не дублирует лишние агрегаты в БД, а пересчитывает их по фактическим данным;
- роли `student`, `teacher`, `admin` управляют доступом к контенту, аналитике и административным операциям;
- документация, схема запуска и модель данных согласованы с текущей PostgreSQL-архитектурой.
