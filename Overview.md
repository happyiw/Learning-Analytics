# Overview

## Backend

### Общая архитектура

- Backend построен на `FastAPI`.
- Основной входной файл: `backend/main.py`.
- Все таблицы SQLAlchemy создаются при старте приложения.
- Авторизация выполнена через `Bearer` JWT-токен.
- Роли пользователей: `student`, `teacher`, `admin`.
- Доступ к части API ограничен зависимостями:
  - `get_current_user` — нужен валидный токен.
  - `require_teacher_or_admin` — доступ только для `teacher` и `admin`.

### Модели

#### 1. `User`
Таблица: `users`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `username` | `String(100)` | уникальный логин, индекс |
| `password_hash` | `String(255)` | хеш пароля |
| `email` | `String(255) \| null` | уникальный email, необязательный |
| `first_name` | `String(100) \| null` | имя |
| `last_name` | `String(100) \| null` | фамилия |
| `role` | `Enum(UserRole)` | роль пользователя, по умолчанию `student` |
| `university` | `String(255) \| null` | университет |
| `group` | `String(100) \| null` | учебная группа |
| `course_year` | `Integer \| null` | курс обучения |
| `created_at` | `DateTime(timezone=True)` | дата создания |

Связи:

- `authored_courses` -> `Course[]`
- `test_attempts` -> `TestAttempt[]`
- `lesson_progress_entries` -> `LessonProgress[]`
- `topic_results` -> `TopicResult[]`

Особенности и ограничения:

- При регистрации роль всегда создаётся как `student`.
- В API `course_year` ограничен диапазоном `1..6`.
- `username` и `email` не могут повторяться.

#### 2. `Course`
Таблица: `courses`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `title` | `String(255)` | название курса |
| `description` | `Text \| null` | описание |
| `author_id` | `ForeignKey(users.id) \| null` | автор курса |
| `difficulty` | `Integer` | сложность, по умолчанию `1` |
| `is_published` | `Boolean` | опубликован ли курс |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `author` -> `User`
- `modules` -> `Module[]`
- `tests` -> `Test[]`

Особенности и ограничения:

- В API `difficulty` ограничен диапазоном `1..10`.
- Для студентов и публичных списков доступны только опубликованные курсы.

#### 3. `Module`
Таблица: `modules`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `course_id` | `ForeignKey(courses.id)` | курс |
| `title` | `String(255)` | название модуля |
| `description` | `Text \| null` | описание |
| `order` | `Integer` | порядок внутри курса |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `course` -> `Course`
- `lessons` -> `Lesson[]`
- `tasks` -> `Task[]`
- `tests` -> `Test[]`
- `topic_results` -> `TopicResult[]`
- `recommendations` -> `Recommendation[]`

Особенности и ограничения:

- Публичная выдача модуля, уроков, задач и тестов завязана на публикацию родительского курса.

#### 4. `Lesson`
Таблица: `lessons`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `module_id` | `ForeignKey(modules.id)` | модуль |
| `title` | `String(255)` | название урока |
| `content` | `Text` | краткое/основное текстовое содержимое |
| `content_blocks` | `Text \| null` | JSON с блоками контента |
| `video_url` | `String(500) \| null` | ссылка на видео |
| `external_url` | `String(500) \| null` | внешняя ссылка |
| `order` | `Integer` | порядок внутри модуля |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `module` -> `Module`
- `progress_entries` -> `LessonProgress[]`

Особенности и ограничения:

- При создании урока обязательно должно быть либо `content`, либо `content_blocks`.
- `content_blocks` поддерживает типы: `rich_text`, `callout`, `bullets`, `checklist`, `table`, `chart`, `image`, `stat_grid`.
- При сохранении `content_blocks` сериализуются в JSON.

#### 5. `Task`
Таблица: `tasks`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `module_id` | `ForeignKey(modules.id)` | модуль |
| `title` | `String(255)` | название задания |
| `description` | `Text` | описание задания |
| `task_type` | `String(50) \| null` | тип задания |
| `difficulty_level` | `String(50) \| null` | уровень сложности |
| `correct_answer` | `Text \| null` | правильный ответ |
| `explanation` | `Text \| null` | пояснение |
| `max_score` | `Float` | максимальный балл |
| `order` | `Integer` | порядок внутри модуля |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `module` -> `Module`

Особенности и ограничения:

- В пользовательском `TaskRead` поле `correct_answer` не возвращается.
- `correct_answer` доступен только в admin-ответе `TaskAdminRead`.

#### 6. `Test`
Таблица: `tests`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `course_id` | `ForeignKey(courses.id)` | курс |
| `module_id` | `ForeignKey(modules.id) \| null` | модуль, если тест привязан к модулю |
| `title` | `String(255)` | название теста |
| `description` | `Text \| null` | описание |
| `time_limit` | `Integer \| null` | лимит времени в минутах |
| `passing_score` | `Float` | проходной процент, по умолчанию `60` |
| `attempts_allowed` | `Integer` | число допустимых попыток |
| `is_active` | `Boolean` | активен ли тест |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `course` -> `Course`
- `module` -> `Module`
- `questions` -> `Question[]`
- `attempts` -> `TestAttempt[]`

Особенности и ограничения:

- Студенту тест доступен только если курс опубликован.
- Старт новой попытки запрещён, если тест неактивен или исчерпан лимит `attempts_allowed`.

#### 7. `Question`
Таблица: `questions`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `test_id` | `ForeignKey(tests.id)` | тест |
| `text` | `Text` | текст вопроса |
| `question_type` | `String(50)` | тип вопроса, по умолчанию `single_choice` |
| `difficulty_level` | `String(50) \| null` | уровень сложности |
| `score` | `Float` | вес вопроса |
| `order` | `Integer` | порядок в тесте |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `test` -> `Test`
- `answer_options` -> `AnswerOption[]`
- `user_answers` -> `UserAnswer[]`

Особенности и ограничения:

- Для пользовательской выдачи используется `PublicQuestionRead`: правильность вариантов не раскрывается.

#### 8. `AnswerOption`
Таблица: `answer_options`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `question_id` | `ForeignKey(questions.id)` | вопрос |
| `text` | `Text` | текст варианта |
| `is_correct` | `Boolean` | правильный ли вариант |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `question` -> `Question`
- `user_answers` -> `UserAnswer[]`

#### 9. `TestAttempt`
Таблица: `test_attempts`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `user_id` | `ForeignKey(users.id)` | пользователь |
| `test_id` | `ForeignKey(tests.id)` | тест |
| `started_at` | `DateTime(timezone=True)` | начало попытки |
| `finished_at` | `DateTime(timezone=True) \| null` | завершение попытки |
| `score` | `Float` | набранные баллы |
| `max_score` | `Float` | максимальный балл |
| `percentage` | `Float` | процент |
| `is_passed` | `Boolean` | пройдена ли попытка |

Связи:

- `user` -> `User`
- `test` -> `Test`
- `answers` -> `UserAnswer[]`

Особенности и ограничения:

- У пользователя может быть только одна незавершённая попытка на тест; при повторном старте вернётся существующая активная попытка.
- Результат подсчитывается при завершении попытки.

#### 10. `UserAnswer`
Таблица: `user_answers`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `attempt_id` | `ForeignKey(test_attempts.id)` | попытка |
| `question_id` | `ForeignKey(questions.id)` | вопрос |
| `selected_option_id` | `ForeignKey(answer_options.id) \| null` | выбранный вариант |
| `text_answer` | `Text \| null` | текстовый ответ |
| `is_correct` | `Boolean` | корректность ответа |
| `score_received` | `Float` | полученный балл |
| `answered_at` | `DateTime(timezone=True)` | время ответа |

Связи:

- `attempt` -> `TestAttempt`
- `question` -> `Question`
- `selected_option` -> `AnswerOption`

Особенности и ограничения:

- Уникальность по паре `attempt_id + question_id`.
- Для choice-вопросов обязателен `selected_option_id`.
- Нельзя сохранить вариант ответа, который относится к другому вопросу.

#### 11. `LessonProgress`
Таблица: `lesson_progress`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `user_id` | `ForeignKey(users.id)` | пользователь |
| `lesson_id` | `ForeignKey(lessons.id)` | урок |
| `is_completed` | `Boolean` | завершён ли урок |
| `completed_at` | `DateTime(timezone=True) \| null` | время завершения |

Связи:

- `user` -> `User`
- `lesson` -> `Lesson`

Особенности и ограничения:

- Уникальность по паре `user_id + lesson_id`.

#### 12. `TopicResult`
Таблица: `topic_results`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `user_id` | `ForeignKey(users.id)` | пользователь |
| `module_id` | `ForeignKey(modules.id)` | модуль/тема |
| `attempts_count` | `Integer` | число попыток |
| `average_percentage` | `Float` | средний процент |
| `best_percentage` | `Float` | лучший процент |
| `weakness_level` | `String(50)` | уровень слабости, по умолчанию `high` |
| `last_attempt_at` | `DateTime(timezone=True) \| null` | дата последней попытки |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `user` -> `User`
- `module` -> `Module`

Особенности и ограничения:

- Уникальность по паре `user_id + module_id`.
- Обновляется после завершения теста, если тест привязан к модулю.

#### 13. `Recommendation`
Таблица: `recommendations`

Поля:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | `Integer` | PK, индекс |
| `module_id` | `ForeignKey(modules.id)` | модуль, к которому относится рекомендация |
| `title` | `String(255)` | заголовок |
| `description` | `Text` | описание |
| `resource_url` | `String(500) \| null` | ссылка на материал |
| `trigger_score_threshold` | `Float` | порог, ниже которого рекомендация считается актуальной |
| `created_at` | `DateTime(timezone=True)` | дата создания |
| `updated_at` | `DateTime(timezone=True)` | дата обновления |

Связи:

- `module` -> `Module`

### Эндпоинты

#### Служебный

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/` | Проверка, что API запущен | Без авторизации |

#### Auth

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register/` | Регистрация пользователя | `username` и `email` должны быть уникальны; роль всегда `student`; `course_year` 1..6 |
| `POST` | `/api/auth/login/` | Получение JWT-токена | Неверные логин/пароль -> `401` |
| `GET` | `/api/auth/me/` | Возврат текущего пользователя | Нужен Bearer-токен |

#### Courses

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/api/courses/` | Список опубликованных курсов | Возвращаются только `is_published = true` |
| `GET` | `/api/courses/{course_id}/` | Карточка курса | Неопубликованный курс скрывается как `404` |
| `GET` | `/api/courses/{course_id}/modules/` | Модули курса | Только для опубликованного курса |
| `GET` | `/api/courses/{course_id}/progress/my/` | Личный прогресс по курсу | Нужен токен |
| `GET` | `/api/courses/{course_id}/topic-results/my/` | Результаты по темам курса | Нужен токен |
| `GET` | `/api/courses/{course_id}/recommendations/my/` | Личные рекомендации по курсу | Нужен токен |
| `POST` | `/api/courses/` | Создание курса | Только `teacher/admin`; `author_id` должен существовать; `difficulty` 1..10 |
| `PATCH` | `/api/courses/{course_id}/` | Обновление курса | Только `teacher/admin`; новый `author_id` должен существовать |
| `DELETE` | `/api/courses/{course_id}/` | Удаление курса | Только `teacher/admin` |

#### Modules

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/api/modules/{module_id}/` | Карточка модуля | Доступен только если родительский курс опубликован |
| `GET` | `/api/modules/{module_id}/lessons/` | Список уроков модуля | Только для модуля опубликованного курса |
| `GET` | `/api/modules/{module_id}/tests/` | Список активных тестов модуля | Только `is_active = true`, только для опубликованного курса |
| `GET` | `/api/modules/{module_id}/progress/my/` | Личный прогресс по модулю | Нужен токен |
| `GET` | `/api/modules/{module_id}/topic-results/my/` | Результаты по теме модуля | Нужен токен |
| `GET` | `/api/modules/{module_id}/recommendations/my/` | Личные рекомендации по модулю | Нужен токен |
| `POST` | `/api/modules/` | Создание модуля | Только `teacher/admin`; `course_id` должен существовать |
| `PATCH` | `/api/modules/{module_id}/` | Обновление модуля | Только `teacher/admin`; новый `course_id` должен существовать |
| `DELETE` | `/api/modules/{module_id}/` | Удаление модуля | Только `teacher/admin` |

#### Lessons

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/api/lessons/{lesson_id}/` | Полный урок с флагом завершения и ссылкой на следующий урок | Нужен токен |
| `POST` | `/api/lessons/{lesson_id}/complete/` | Отметить урок завершённым | Нужен токен; запись прогресса создаётся/обновляется по текущему пользователю |
| `POST` | `/api/lessons/` | Создание урока | Только `teacher/admin`; `module_id` должен существовать; нужен `content` или `content_blocks` |
| `PATCH` | `/api/lessons/{lesson_id}/` | Обновление урока | Только `teacher/admin`; при смене `module_id` модуль должен существовать |
| `DELETE` | `/api/lessons/{lesson_id}/` | Удаление урока | Только `teacher/admin` |

#### Tasks

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/api/modules/{module_id}/tasks/` | Список задач модуля | Только для опубликованного курса |
| `GET` | `/api/tasks/{task_id}/` | Получение одной задачи | Только для опубликованного курса |
| `POST` | `/api/tasks/` | Создание задачи | Только `teacher/admin`; `module_id` должен существовать |
| `PATCH` | `/api/tasks/{task_id}/` | Обновление задачи | Только `teacher/admin`; при смене `module_id` модуль должен существовать |
| `DELETE` | `/api/tasks/{task_id}/` | Удаление задачи | Только `teacher/admin` |

Примечание:

- Пользовательские ответы по задачам в текущем backend не реализованы.
- Публичное чтение не возвращает `correct_answer`.

#### Tests, Questions, Answer Options, Attempts

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/api/tests/{test_id}/` | Карточка теста | Нужен токен; студент видит только тесты опубликованных курсов |
| `GET` | `/api/tests/{test_id}/active-attempt/` | Текущая незавершённая попытка пользователя | Нужен токен; `404`, если активной попытки нет |
| `GET` | `/api/tests/{test_id}/questions/` | Вопросы теста без признака правильности вариантов | Нужен токен |
| `POST` | `/api/tests/{test_id}/start/` | Начать попытку теста | Нужен токен; тест должен быть активным; больше `attempts_allowed` нельзя; если активная попытка уже есть, вернётся она |
| `POST` | `/api/test-attempts/{attempt_id}/answers/` | Сохранить/обновить ответ на вопрос | Нужен токен; попытка должна быть незавершённой; нельзя отвечать на вопрос другого теста |
| `POST` | `/api/test-attempts/{attempt_id}/finish/` | Завершить попытку и подсчитать результат | Нужен токен; повторно завершить нельзя |
| `GET` | `/api/test-attempts/{attempt_id}/result/` | Получить результат попытки и список ответов | Нужен токен; доступ только владельцу или `teacher/admin` |
| `POST` | `/api/tests/` | Создание теста | Только `teacher/admin`; `course_id` обязателен и должен существовать; `module_id`, если передан, тоже должен существовать |
| `PATCH` | `/api/tests/{test_id}/` | Обновление теста | Только `teacher/admin` |
| `DELETE` | `/api/tests/{test_id}/` | Удаление теста | Только `teacher/admin` |
| `POST` | `/api/questions/` | Создание вопроса | Только `teacher/admin`; `test_id` должен существовать |
| `PATCH` | `/api/questions/{question_id}/` | Обновление вопроса | Только `teacher/admin`; новый `test_id` должен существовать |
| `DELETE` | `/api/questions/{question_id}/` | Удаление вопроса | Только `teacher/admin` |
| `POST` | `/api/answer-options/` | Создание варианта ответа | Только `teacher/admin`; `question_id` должен существовать |
| `PATCH` | `/api/answer-options/{option_id}/` | Обновление варианта ответа | Только `teacher/admin`; новый `question_id` должен существовать |
| `DELETE` | `/api/answer-options/{option_id}/` | Удаление варианта ответа | Только `teacher/admin` |

Дополнительные ограничения логики тестирования:

- Для типов `single_choice`, `choice`, `multiple_choice` обязателен `selected_option_id`.
- Если выбранный вариант не относится к вопросу, возвращается `400`.
- Для текстовых вопросов сравнение выполняется по нормализованному тексту.
- Если у текстового вопроса нет правильных вариантов, любой непустой ответ считается зачтённым.

#### Recommendations

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/api/recommendations/my/` | Все персональные рекомендации пользователя | Нужен токен |
| `GET` | `/api/recommendations/` | Список всех рекомендаций | Только `teacher/admin` |
| `POST` | `/api/recommendations/` | Создание рекомендации | Только `teacher/admin`; `module_id` должен существовать |
| `GET` | `/api/recommendations/{recommendation_id}/` | Получить рекомендацию | Только `teacher/admin` |
| `PATCH` | `/api/recommendations/{recommendation_id}/` | Обновить рекомендацию | Только `teacher/admin`; новый `module_id` должен существовать |
| `DELETE` | `/api/recommendations/{recommendation_id}/` | Удалить рекомендацию | Только `teacher/admin` |

#### Analytics

| Метод | Путь | Назначение | Ограничения |
| --- | --- | --- | --- |
| `GET` | `/api/progress/my/` | Общий прогресс пользователя | Нужен токен |
| `GET` | `/api/topic-results/my/` | Все результаты пользователя по темам | Нужен токен |
| `GET` | `/api/analytics/my/summary/` | Сводная статистика пользователя | Нужен токен |
| `GET` | `/api/analytics/my/weak-topics/` | Слабые темы пользователя | Нужен токен |
| `GET` | `/api/analytics/my/best-topics/` | Сильные темы пользователя | Нужен токен |
| `GET` | `/api/analytics/my/dynamics/` | Динамика попыток по датам | Нужен токен |
| `GET` | `/api/analytics/groups/{group_id}/topic-results/` | Агрегированная аналитика по группе | Только `teacher/admin`; группа должна существовать |
| `GET` | `/api/analytics/courses/{course_id}/topic-results/` | Агрегированная аналитика по курсу | Только `teacher/admin`; курс должен существовать |
| `GET` | `/api/analytics/modules/{module_id}/topic-results/` | Агрегированная аналитика по модулю | Только `teacher/admin`; модуль должен существовать |

## Frontend

### Общая структура

- Frontend написан на `Angular`.
- Общая оболочка приложения содержит:
  - верхнюю навигацию;
  - основной контент через `router-outlet`;
  - футер.
- Для авторизованного пользователя в хедере доступны ссылки на курсы, аналитику, рекомендации и профиль.
- Для гостя доступны ссылки на вход и регистрацию.

### Страницы текущей версии

#### `/` и `/dashboard`
Компонент: `DashboardPageComponent`

Содержимое:

- Для гостя: лендинг с описанием платформы, преимуществами, кнопками входа и регистрации.
- Для авторизованного пользователя: главная сводка по обучению.
- Показываются:
  - общий прогресс;
  - число доступных курсов;
  - число завершённых уроков;
  - средний процент по тестам;
  - число рекомендаций;
  - число завершённых тестовых попыток;
  - число курсов, в которых уже была активность.

Ограничения:

- `/dashboard` открыт без guard, но фактическая аналитическая часть загружается только для авторизованного пользователя.

#### `/login`
Компонент: `LoginPageComponent`

Содержимое:

- форма входа;
- поля `username` и `password`;
- сообщения валидации и ошибки;
- ссылка на регистрацию.

Ограничения:

- Доступен только гостю (`guestGuard`).
- Авторизованный пользователь перенаправляется на `/`.

#### `/register`
Компонент: `RegisterPageComponent`

Содержимое:

- форма регистрации;
- поля `username`, `password`, `email`, `first_name`, `last_name`, `university`, `group`, `course_year`;
- валидация формы;
- ссылка на страницу входа.

Ограничения:

- Доступен только гостю (`guestGuard`).
- Пароль минимум 6 символов.
- `course_year` ограничен диапазоном `1..6`.

#### `/courses`
Компонент: `CoursesPageComponent`

Содержимое:

- список опубликованных курсов в виде карточек;
- у карточки выводятся:
  - название;
  - описание;
  - сложность;
  - статус доступности;
  - кнопка перехода к курсу.

Ограничения:

- Страница открыта без guard.
- В API подгружаются только опубликованные курсы.

#### `/courses/:courseId`
Компонент: `CoursePageComponent`

Содержимое:

- детальная страница курса;
- шапка с названием, описанием, сложностью и общим прогрессом;
- список модулей курса;
- список результатов по темам курса;
- список персональных рекомендаций по курсу.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).

#### `/modules/:moduleId`
Компонент: `ModulePageComponent`

Содержимое:

- детальная страница модуля;
- прогресс по модулю;
- список уроков;
- список практических заданий;
- список тестов;
- карточка результата по теме;
- рекомендации по теме.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).

#### `/lessons/:lessonId`
Компонент: `LessonPageComponent`

Содержимое:

- детальная страница урока;
- статус завершения урока;
- краткое описание;
- блочный контент урока:
  - текстовые блоки;
  - callout;
  - списки;
  - таблицы;
  - графики;
  - изображения;
  - сетки со статистикой;
- встроенное видео;
- внешняя ссылка на материал;
- кнопка завершения урока;
- переход к следующему уроку.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).

#### `/tasks/:taskId`
Компонент: `TaskPageComponent`

Содержимое:

- просмотр одного практического задания;
- название и описание;
- тип задания;
- уровень сложности;
- максимальный балл;
- порядок внутри модуля.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).
- Интерфейса сдачи решения в текущей версии нет.

#### `/tests/:testId`
Компонент: `TestPageComponent`

Содержимое:

- карточка теста;
- описание теста;
- лимит времени;
- проходной процент;
- число доступных попыток;
- статус активности;
- уведомление о незавершённой попытке;
- кнопка начала или продолжения теста.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).
- При исчерпании попыток кнопка старта блокируется.

#### `/tests/:testId/attempt/:attemptId`
Компонент: `TestAttemptPageComponent`

Содержимое:

- экран прохождения теста;
- таймер;
- текущий вопрос;
- навигация по вопросам;
- варианты ответа или поле текстового ответа;
- ручное сохранение ответа;
- автосохранение черновика;
- завершение теста;
- предупреждение о незаполненных вопросах.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).
- При истечении таймера тест завершается автоматически.

#### `/recommendations`
Компонент: `RecommendationsPageComponent`

Содержимое:

- страница персональных рекомендаций;
- фильтр по области:
  - все;
  - по курсу;
  - по модулю;
- карточки рекомендаций с названием, описанием, порогом, текущим результатом и ссылкой на материал.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).
- Для фильтра по курсу и модулю пользователь вручную вводит `ID`.

#### `/analytics`
Компонент: `AnalyticsPageComponent`

Содержимое:

- персональная аналитика пользователя;
- карточки со сводными метриками;
- линейный график динамики результатов по датам;
- диаграмма результатов по модулям;
- таблица слабых тем;
- таблица сильных тем;
- полная таблица результатов по темам.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).

#### `/profile`
Компонент: `ProfilePageComponent`

Содержимое:

- страница профиля пользователя;
- ФИО;
- `username`;
- `email`;
- университет;
- группа;
- курс обучения;
- дата создания аккаунта;
- роль;
- кнопка выхода.

Ограничения:

- Доступна только авторизованному пользователю (`authGuard`).

#### `**`

- Все неизвестные маршруты перенаправляются на `/`.

### Что важно про текущую версию frontend

- В интерфейсе есть пользовательский поток для студента: регистрация, вход, просмотр курсов, прохождение уроков и тестов, просмотр аналитики и рекомендаций.
- Отдельных экранов для администрирования курсов, модулей, уроков, задач, тестов, вопросов и рекомендаций сейчас нет, хотя backend API для этого уже существует.
- Страница задач сейчас только информационная: решения и оценивание через UI не реализованы.
