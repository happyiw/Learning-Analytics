# Overview

## 1. Назначение проекта

Проект представляет собой учебную веб-платформу, в которой пользователь проходит курсы, изучает уроки, выполняет задания, сдает тесты и получает персональную аналитику.  
Система не хранит лишние агрегаты в базе, а строит большую часть аналитики на лету по фактическим данным: попыткам тестов, прогрессу по урокам, ответам на вопросы и зачислениям на курсы.

Ключевые задачи проекта:

- управление учебным контентом: курсы, модули, уроки, задания, тесты, вопросы;
- прохождение обучения студентом;
- отслеживание прогресса по урокам и тестам;
- расчет результатов по темам;
- формирование персональных рекомендаций;
- построение аналитики по темам, тестам, попыткам и вопросам.

Архитектурно проект состоит из трех основных частей:

- `backend/` — FastAPI-приложение, ORM-модели, API, DTO, bootstrap и адаптерный слой;
- `frontend/` — Angular-клиент с маршрутами, страницами и сервисами доступа к API;
- `analytics/` — слой вычислительных сервисов, который собирает и интерпретирует учебные данные.

---

## 2. Backend

## 2.1. Технологии и общая структура

Backend построен на:

- `FastAPI` — HTTP API;
- `SQLAlchemy 2.x` — ORM и доступ к данным;
- `SQLite` — текущая база данных `app.db`;
- `Pydantic` — схемы входных и выходных DTO;
- JWT-аутентификации — защита приватных endpoint-ов.

Ключевые backend-модули:

- `backend/main.py` — точка входа, регистрация роутеров;
- `backend/models.py` — SQLAlchemy-модели таблиц;
- `backend/schemas.py` — DTO и схемы API;
- `backend/bootstrap.py` — инициализация и миграционная логика для локальной БД;
- `backend/deps.py` — зависимости FastAPI, текущий пользователь, проверка прав;
- `backend/services/analytics.py` — адаптер между аналитическими сервисами и API;
- `backend/services/course_access.py` — проверка доступа к курсам и тестам;
- `backend/attempt_metrics.py` — расчет `percentage`, `is_passed`, `status` для попыток.

## 2.2. Роли пользователей

Система поддерживает три роли:

- `student` — проходит обучение и видит персональную аналитику;
- `teacher` — управляет учебным контентом и видит преподавательскую аналитику;
- `admin` — имеет административный доступ к тем же данным и операциям.

## 2.3. Таблицы и поля

Ниже перечислены основные таблицы в актуальной схеме проекта.

### `users`

Назначение: учетные записи пользователей.

Поля:

- `id`
- `username`
- `password_hash`
- `email`
- `first_name`
- `last_name`
- `role`
- `university`
- `group`
- `course_year`
- `created_at`

### `courses`

Назначение: верхний уровень учебной структуры.

Поля:

- `id`
- `title`
- `description`
- `author_id`
- `difficulty`
- `is_published`
- `is_open`
- `created_at`
- `updated_at`

### `course_enrollments`

Назначение: факты зачисления пользователей на курсы.

Поля:

- `id`
- `user_id`
- `course_id`
- `assigned_by_id`
- `created_at`

Особенность:

- уникальная связка `user_id + course_id`.

### `modules`

Назначение: модули внутри курса.

Поля:

- `id`
- `course_id`
- `title`
- `description`
- `order`
- `created_at`
- `updated_at`

### `lessons`

Назначение: теоретические материалы модуля.

Поля:

- `id`
- `module_id`
- `title`
- `content_blocks`
- `video_url`
- `external_url`
- `order`
- `created_at`
- `updated_at`

Примечание:

- поле `content` удалено из БД;
- в API краткая текстовая сводка все еще может формироваться из `content_blocks`.

### `tasks`

Назначение: практические задания модуля.

Поля:

- `id`
- `module_id`
- `title`
- `description`
- `max_score`
- `order`
- `created_at`
- `updated_at`

### `tests`

Назначение: тесты курса или конкретного модуля.

Поля:

- `id`
- `course_id`
- `module_id`
- `title`
- `description`
- `time_limit`
- `passing_score`
- `attempts_allowed`
- `is_active`
- `created_at`
- `updated_at`

### `questions`

Назначение: вопросы тестов.

Поля:

- `id`
- `test_id`
- `text`
- `question_type`
- `difficulty_level`
- `score`
- `order`
- `created_at`
- `updated_at`

### `answer_options`

Назначение: варианты ответов для вопросов.

Поля:

- `id`
- `question_id`
- `text`
- `is_correct`
- `created_at`
- `updated_at`

### `test_attempts`

Назначение: факты прохождения тестов пользователями.

Поля:

- `id`
- `user_id`
- `test_id`
- `started_at`
- `finished_at`
- `score`
- `max_score`

Примечание:

- поля `percentage` и `is_passed` не хранятся;
- они вычисляются по данным попытки и `tests.passing_score`.

### `user_answers`

Назначение: ответы пользователя в рамках конкретной попытки.

Поля:

- `id`
- `attempt_id`
- `question_id`
- `selected_option_id`
- `text_answer`
- `is_correct`
- `score_received`
- `answered_at`

Особенность:

- уникальная связка `attempt_id + question_id`.

### `user_answer_option_selections`

Назначение: связь ответа с несколькими выбранными вариантами.

Поля:

- `user_answer_id`
- `answer_option_id`

### `lesson_progress`

Назначение: факты прохождения уроков.

Поля:

- `id`
- `user_id`
- `lesson_id`
- `is_completed`
- `completed_at`

Особенность:

- уникальная связка `user_id + lesson_id`.

### `topic_results`

Назначение: легкий кэш результата пользователя по теме.

Поля:

- `id`
- `user_id`
- `module_id`
- `last_attempt_at`
- `updated_at`

Примечание:

- в таблице не хранятся аналитические метрики темы;
- `TopicResultService` собирает их на лету из `test_attempts` и `lesson_progress`.

### `recommendations`

Назначение: библиотека контента рекомендаций, привязанная к модулям.

Поля:

- `id`
- `module_id`
- `title`
- `description`
- `resource_url`
- `created_at`
- `updated_at`

Примечание:

- поле `trigger_score_threshold` удалено;
- логика выбора рекомендаций теперь находится в `RecommendationService`.

## 2.4. Backend-модули и endpoint-ы

Ниже перечислены основные backend-роутеры и их назначение.

### `backend/api/auth.py`

Назначение:

- регистрация;
- вход;
- получение текущего пользователя.

Endpoint-ы:

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`

### `backend/api/courses.py`

Назначение:

- работа с курсами;
- зачисления;
- курс как точка входа в обучение;
- доступ к курсовому progress, topic results и рекомендациям.

Endpoint-ы:

- `GET /api/courses/`
- `GET /api/courses/my/enrollments/`
- `POST /api/courses/{course_id}/enroll/my/`
- `GET /api/courses/{course_id}/enrollments/`
- `POST /api/courses/{course_id}/enrollments/`
- `GET /api/courses/students/search/`
- `GET /api/courses/{course_id}/`
- `GET /api/courses/{course_id}/modules/`
- `GET /api/courses/{course_id}/progress/my/`
- `GET /api/courses/{course_id}/topic-results/my/`
- `GET /api/courses/{course_id}/recommendations/my/`
- `POST /api/courses/`
- `PATCH /api/courses/{course_id}/`
- `DELETE /api/courses/{course_id}/`

### `backend/api/modules.py`

Назначение:

- работа с модулями;
- выдача содержимого модуля: уроки, задания, тесты;
- доступ к аналитике и рекомендациям в рамках модуля.

Endpoint-ы:

- `GET /api/modules/{module_id}/`
- `GET /api/modules/{module_id}/lessons/`
- `GET /api/modules/{module_id}/tasks/`
- `GET /api/modules/{module_id}/tests/`
- `GET /api/modules/{module_id}/progress/my/`
- `GET /api/modules/{module_id}/topic-results/my/`
- `GET /api/modules/{module_id}/recommendations/my/`
- `POST /api/modules/`
- `PATCH /api/modules/{module_id}/`
- `DELETE /api/modules/{module_id}/`

### `backend/api/lessons.py`

Назначение:

- создание и редактирование уроков;
- выдача страницы урока;
- отметка урока как завершенного.

Endpoint-ы:

- `GET /api/lessons/{lesson_id}/`
- `POST /api/lessons/{lesson_id}/complete/`
- `POST /api/lessons/`
- `PATCH /api/lessons/{lesson_id}/`
- `DELETE /api/lessons/{lesson_id}/`

### `backend/api/tasks.py`

Назначение:

- CRUD для заданий;
- выдача карточки задания.

Endpoint-ы:

- `GET /api/tasks/{task_id}/`
- `POST /api/tasks/`
- `PATCH /api/tasks/{task_id}/`
- `DELETE /api/tasks/{task_id}/`

### `backend/api/tests.py`

Назначение:

- CRUD для тестов, вопросов и вариантов ответов;
- прохождение тестов;
- сохранение ответов;
- завершение попыток;
- выдача test analytics и результата попытки.

Endpoint-ы для тестов и попыток:

- `GET /api/tests/{test_id}/`
- `GET /api/tests/{test_id}/questions/`
- `GET /api/tests/{test_id}/active-attempt/`
- `GET /api/tests/{test_id}/analytics/my/`
- `GET /api/test-attempts/my/unfinished/`
- `POST /api/tests/{test_id}/start/`
- `POST /api/test-attempts/{attempt_id}/answers/`
- `POST /api/test-attempts/{attempt_id}/finish/`
- `GET /api/test-attempts/{attempt_id}/result/`

Endpoint-ы для управления тестами:

- `POST /api/tests/`
- `PATCH /api/tests/{test_id}/`
- `DELETE /api/tests/{test_id}/`

Endpoint-ы для вопросов:

- `POST /api/questions/`
- `PATCH /api/questions/{question_id}/`
- `DELETE /api/questions/{question_id}/`

Endpoint-ы для вариантов ответов:

- `POST /api/answer-options/`
- `PATCH /api/answer-options/{option_id}/`
- `DELETE /api/answer-options/{option_id}/`

### `backend/api/recommendations.py`

Назначение:

- CRUD рекомендаций;
- выдача персональных рекомендаций пользователю.

Endpoint-ы:

- `GET /api/recommendations/my/`
- `GET /api/recommendations/`
- `GET /api/recommendations/{recommendation_id}/`
- `POST /api/recommendations/`
- `PATCH /api/recommendations/{recommendation_id}/`
- `DELETE /api/recommendations/{recommendation_id}/`

### `backend/api/analytics.py`

Назначение:

- персональная аналитика пользователя;
- групповые и преподавательские срезы по темам;
- аналитика по вопросам, тестам и модулям.

Персональная аналитика:

- `GET /api/progress/my/`
- `GET /api/topic-results/my/`
- `GET /api/analytics/my/snapshot/`
- `GET /api/analytics/my/summary/`
- `GET /api/analytics/my/weak-topics/`
- `GET /api/analytics/my/best-topics/`
- `GET /api/analytics/my/dynamics/`

Агрегаты по преподавательским срезам:

- `GET /api/analytics/groups/{group_id}/topic-results/`
- `GET /api/analytics/courses/{course_id}/topic-results/`
- `GET /api/analytics/modules/{module_id}/topic-results/`

Аналитика по вопросам:

- `GET /api/analytics/questions/{question_id}/`
- `GET /api/analytics/tests/{test_id}/questions/`
- `GET /api/analytics/tests/{test_id}/questions/hardest/`
- `GET /api/analytics/tests/{test_id}/questions/most-missed/`
- `GET /api/analytics/modules/{module_id}/questions/`
- `GET /api/analytics/modules/{module_id}/questions/hardest/`

## 2.5. DTO и схемы ответа

Основной файл: `backend/schemas.py`.

Ключевые схемы:

- `UserRead`, `TokenRead` — пользователь и токен;
- `CourseRead`, `ModuleRead`, `LessonRead`, `TaskRead`, `TestRead` — основные сущности контента;
- `TestAttemptRead`, `AttemptResultRead`, `UnfinishedAttemptRead` — попытки и их результат;
- `ProgressRead` — прогресс;
- `TopicResultRead` — аналитика по теме;
- `PersonalRecommendationRead` — персональная рекомендация;
- `TestAttemptAnalyticsItemRead` — расширенный snapshot попытки;
- `TestAnalyticsRead` — аналитика по тесту;
- `QuestionWrongOptionRead`, `QuestionAnalyticsRead` — аналитика по вопросу;
- `PersonalAnalyticsSnapshotRead` — полный персональный snapshot аналитики.

## 2.6. Адаптерный слой backend

Файл: `backend/services/analytics.py`.

Его роль:

- вызывать сервисы из `analytics/`;
- приводить их словари к DTO;
- собирать итоговые структуры для API;
- скрывать внутреннюю логику расчетов от роутеров.

Основные функции слоя:

- сбор progress;
- сбор topic results;
- сбор персонального snapshot;
- сбор рекомендаций;
- сбор test analytics;
- сбор question analytics;
- сбор агрегированных срезов по темам.

---

## 3. Frontend

Frontend расположен в `frontend/src/app` и построен вокруг feature-page компонентов, core-моделей и сервисов доступа к backend API.

## 3.1. Главные frontend-модули

### `app.routes.ts`

Назначение:

- задает маршруты всего приложения;
- связывает URL со страницами.

Основные маршруты:

- `/`
- `/dashboard`
- `/login`
- `/register`
- `/courses`
- `/courses/:courseId`
- `/courses/:courseId/manage`
- `/modules/:moduleId`
- `/lessons/:lessonId`
- `/tasks/:taskId`
- `/tests/:testId`
- `/tests/:testId/attempt/:attemptId`
- `/tests/:testId/attempt/:attemptId/result`
- `/recommendations`
- `/analytics`
- `/attempts`
- `/profile`

### `core/models`

Назначение:

- содержит TypeScript-интерфейсы для backend DTO;
- разделяет дашбордные и учебные модели.

Основные файлы:

- `dashboard.models.ts`
- `learning.models.ts`

### `core/services`

Назначение:

- централизованный доступ к backend API;
- инкапсуляция HTTP-запросов.

Основные сервисы:

- `AuthService` — вход, регистрация, текущий пользователь;
- `CourseService` — каталог курсов;
- `LearningService` — уроки, задания, тесты, попытки, test analytics;
- `RecommendationService` — загрузка рекомендаций в разных scope;
- `AnalyticsService` — персональный analytics snapshot;
- `DashboardService` — агрегированная загрузка данных для главной панели.

## 3.2. Страницы frontend

Ниже перечислены основные страницы, их маршрут, содержимое и место использования в пользовательском пути.

### `LoginPageComponent`

Маршрут:

- `/login`

Содержимое:

- форма авторизации;
- поля логина и пароля;
- обработка ошибок входа.

Где используется:

- стартовая точка для неавторизованного пользователя;
- переход в защищенную часть приложения.

### `RegisterPageComponent`

Маршрут:

- `/register`

Содержимое:

- форма регистрации;
- базовые поля профиля пользователя;
- создание новой учетной записи.

Где используется:

- путь входа в систему для новых пользователей.

### `DashboardPageComponent`

Маршрут:

- `/dashboard`

Содержимое:

- прогресс;
- summary;
- блок курсов;
- блок рекомендаций.

Где используется:

- главная страница после входа;
- быстрый обзор текущего состояния обучения.

### `CoursesPageComponent`

Маршрут:

- `/courses`

Содержимое:

- каталог доступных курсов;
- карточки курсов;
- ссылки на курс.

Где используется:

- отправная точка учебного маршрута;
- выбор курса для продолжения обучения.

### `CoursePageComponent`

Маршрут:

- `/courses/:courseId`

Содержимое:

- карточка курса;
- список модулей;
- progress по курсу;
- topic results по всем модулям курса;
- рекомендации в рамках курса.

Где используется:

- страница курса после выбора из каталога;
- переход дальше в конкретный модуль.

### `CourseAccessPageComponent`

Маршрут:

- `/courses/:courseId/manage`

Содержимое:

- управление доступом студентов к курсу;
- список зачисленных;
- поиск и добавление пользователей.

Где используется:

- преподавательский и административный сценарий управления курсом.

### `ModulePageComponent`

Маршрут:

- `/modules/:moduleId`

Содержимое:

- информация о модуле;
- список уроков;
- список заданий;
- список тестов;
- progress;
- аналитика темы;
- рекомендации по модулю.

Где используется:

- основная учебная страница внутри курса;
- переход в урок, задание или тест.

### `LessonPageComponent`

Маршрут:

- `/lessons/:lessonId`

Содержимое:

- блоки контента урока;
- видео и внешние ссылки;
- статус завершения;
- переход к следующему уроку.

Где используется:

- теоретический этап изучения модуля.

### `TaskPageComponent`

Маршрут:

- `/tasks/:taskId`

Содержимое:

- название задания;
- описание;
- максимальный балл;
- контекст модуля.

Где используется:

- практическая часть модуля.

### `TestPageComponent`

Маршрут:

- `/tests/:testId`

Содержимое:

- карточка теста;
- параметры теста;
- кнопка старта или продолжения попытки;
- расширенная аналитика по тесту:
  - число попыток;
  - завершенные и незавершенные попытки;
  - первая и последняя завершенные попытки;
  - тренд;
  - прирост;
  - серия неудач;
  - insight по тесту.

Где используется:

- точка входа в прохождение теста;
- предварительный обзор прогресса по конкретному тесту.

### `TestAttemptPageComponent`

Маршрут:

- `/tests/:testId/attempt/:attemptId`

Содержимое:

- вопросы теста;
- выбор ответов;
- сохранение прогресса по попытке;
- завершение теста.

Где используется:

- основной экран прохождения теста.

### `TestAttemptResultPageComponent`

Маршрут:

- `/tests/:testId/attempt/:attemptId/result`

Содержимое:

- итоговый балл;
- рассчитанный процент;
- признак прохождения;
- детализация по вопросам и ответам.

Где используется:

- финальный экран после завершения попытки.

### `RecommendationsPageComponent`

Маршрут:

- `/recommendations`

Содержимое:

- список персональных рекомендаций;
- фильтрация по всем курсам, по курсу или по модулю;
- причина рекомендации;
- приоритет;
- rule key;
- текущее состояние темы;
- текущий результат;
- прогресс по теме;
- доля завершения теории.

Где используется:

- персональная страница поддержки обучения;
- быстрый способ понять, что повторять дальше.

### `AnalyticsPageComponent`

Маршрут:

- `/analytics`

Содержимое:

- общий progress и summary;
- график динамики попыток;
- таблицы слабых и сильных тем;
- полная таблица topic results;
- дополнительные категории:
  - `unstableTopics`
  - `improvingTopics`
  - `topicsWithoutEnoughData`

Где используется:

- персональная страница аналитики;
- сводный обзор траектории обучения.

### `UnfinishedAttemptsPageComponent`

Маршрут:

- `/attempts`

Содержимое:

- список незавершенных попыток;
- курс и модуль;
- время последней активности;
- прогресс по отвеченным вопросам.

Где используется:

- возврат к незавершенным тестам;
- контроль зависших попыток.

### `ProfilePageComponent`

Маршрут:

- `/profile`

Содержимое:

- персональные данные;
- учебные атрибуты;
- роль;
- дата создания аккаунта.

Где используется:

- личный кабинет пользователя.

---

## 4. Analytics

Папка `analytics/` содержит все аналитические классы проекта. Каждый класс отвечает за свой уровень вычислений: прогресс, тема, рекомендации, тест, вопрос или пользовательская сводка.

## 4.1. `ProgressService`

Файл:

- `analytics/progress_service.py`

Назначение:

- рассчитывает прогресс пользователя по доступному контенту;
- работает только по фактам из БД;
- умеет считать progress глобально, по курсу и по модулю.

Что делает класс:

- определяет, какие курсы доступны пользователю;
- собирает модули для нужного scope;
- считает завершенные уроки;
- считает пройденные тесты;
- считает средний процент по тестам;
- формирует итоговый `ProgressRead`.

Основные методы:

- `get_accessible_course_ids(...)`
- `get_modules_for_scope(...)`
- `get_scope_lesson_ids(...)`
- `get_scope_test_ids(...)`
- `get_overall_progress(...)`
- `get_course_progress(...)`
- `get_module_progress(...)`
- `_build_progress(...)`

## 4.2. `TopicResultService`

Файл:

- `analytics/topic_result_service.py`

Назначение:

- строит результат пользователя по теме, где тема эквивалентна модулю;
- рассчитывает все метрики по попыткам тестов и прогрессу по урокам;
- использует `topic_results` только как минимальный кэш строки и времени последней попытки.

Что делает класс:

- получает все попытки по тестам модуля;
- отделяет завершенные попытки;
- считает средний, лучший, первый и последний результат;
- считает тренд, стабильность и прирост;
- считает долю завершения уроков;
- определяет состояние темы: слабость, риск, learning state и reason code;
- сериализует результат в payload, который потом использует backend API.

Основные методы:

- `update_topic_result_after_attempt(...)`
- `get_or_create_topic_result(...)`
- `get_user_topic_results(...)`
- `get_course_topic_results(...)`
- `get_module_topic_results(...)`
- `_calculate_topic_result_values(...)`
- `_calculate_progress_trend(...)`
- `_calculate_stability_index(...)`
- `_get_module_lesson_completion_ratio(...)`
- `calculate_topic_state(...)`
- `_serialize_topic_result(...)`

## 4.3. `WeakTopicDetector`

Файл:

- `analytics/topic_result_service.py`

Назначение:

- интерпретирует результат темы;
- выделяет слабые, сильные, нестабильные и улучшающиеся темы;
- формирует текстовые причины и аналитические теги.

Что делает класс:

- проверяет критерии слабой темы;
- проверяет критерии сильной темы;
- выделяет темы с нехваткой данных;
- строит списки для analytics snapshot;
- добавляет category, reason и tags к payload темы;
- подготавливает данные для recommendation engine.

Основные методы:

- `get_weak_topics(...)`
- `get_strong_topics(...)`
- `get_unstable_topics(...)`
- `get_improving_topics(...)`
- `get_topics_without_enough_data(...)`
- `determine_weak_topic_reason(...)`
- `determine_strong_topic_reason(...)`
- `build_topic_tags(...)`
- `prepare_analytics_data(...)`
- `prepare_recommendation_data(...)`

## 4.4. `RecommendationService`

Файл:

- `analytics/recommendation_service.py`

Назначение:

- выбирает, какие рекомендации показывать пользователю;
- берет контент рекомендаций из БД;
- применяет rule-based логику на основе аналитики темы.

Что делает класс:

- получает topic results из `WeakTopicDetector`;
- собирает расширенный контекст темы;
- считает неуспешные попытки и failure streak;
- сопоставляет тему с rule key;
- определяет priority;
- формирует краткое и конкретное reason explanation;
- готовит frontend payload рекомендации.

Основные методы:

- `get_personal_recommendations(...)`
- `get_course_recommendations(...)`
- `get_module_recommendations(...)`
- `match_topic_results_with_recommendations(...)`
- `determine_priority(...)`
- `build_reason_explanation(...)`
- `to_frontend_payload(...)`
- `_build_contexts(...)`
- `_get_failed_attempt_metrics(...)`
- `_get_unfinished_lessons_count(...)`
- `_get_matching_rules(...)`
- `_get_recommendation_entities(...)`

Поддерживаемые rule key:

- `low_average_score`
- `no_progress_after_retries`
- `unfinished_theory`
- `high_failure_streak`
- `unstable_mastery`
- `improving_but_not_mastered`

## 4.5. `TestAnalyticsService`

Файл:

- `analytics/test_analytics_service.py`

Назначение:

- строит расширенную аналитику по одному тесту;
- анализирует историю попыток пользователя;
- формирует итоговый инсайт по тесту.

Что делает класс:

- получает все попытки по тесту;
- считает завершенные и незавершенные попытки;
- считает средний, лучший, первый и последний результат;
- считает прогресс, лучший прирост и failure streak;
- определяет общий тренд теста;
- формирует insight;
- собирает расширенные snapshot-ы попыток.

Основные методы:

- `get_test_attempts(...)`
- `calculate_completion_percentage(...)`
- `calculate_best_result(...)`
- `calculate_average_result(...)`
- `calculate_first_result(...)`
- `calculate_last_result(...)`
- `calculate_progress_delta(...)`
- `calculate_best_improvement(...)`
- `calculate_unfinished_attempts_count(...)`
- `calculate_failure_streak(...)`
- `calculate_test_trend(...)`
- `build_test_insight(...)`
- `calculate_time_spent_seconds(...)`
- `calculate_answered_questions_count(...)`
- `calculate_status(...)`
- `build_attempt_snapshot(...)`
- `build_test_analytics(...)`

## 4.6. `QuestionAnalyticsService`

Файл:

- `analytics/question_analytics_service.py`

Назначение:

- строит аналитику по отдельным вопросам;
- показывает сложные вопросы, часто ошибочные варианты и средний успех;
- умеет работать как на уровне одного вопроса, так и на уровне теста или модуля.

Что делает класс:

- собирает ответы пользователей по вопросу;
- считает success rate;
- считает средний балл по вопросу;
- определяет самые частые неверные варианты;
- строит snapshot по вопросу;
- собирает аналитические срезы по тесту;
- собирает аналитические срезы по модулю.

Основные методы:

- `get_question_attempts(...)`
- `calculate_question_success_rate(...)`
- `calculate_question_average_score(...)`
- `get_common_wrong_options(...)`
- `build_question_snapshot(...)`
- `get_test_question_analytics(...)`
- `get_hardest_questions_for_test(...)`
- `get_most_missed_questions_for_test(...)`
- `get_module_question_analytics(...)`
- `get_hardest_questions_for_module(...)`

## 4.7. `StudentSummaryService`

Файл:

- `analytics/student_summary.py`

Назначение:

- собирает персональную общую сводку пользователя;
- объединяет progress, topic analytics и dynamics в единый snapshot.

Что делает класс:

- считает число всех попыток;
- считает число завершенных и успешных попыток;
- считает средний балл и средний процент;
- считает число завершенных уроков;
- считает число начатых курсов;
- собирает временной ряд завершенных попыток;
- строит персональный analytics snapshot.

Основные методы:

- `get_summary(...)`
- `get_dynamics(...)`
- `build_analytics_snapshot(...)`

## 4.8. Интеграция аналитики с backend

Файл:

- `backend/services/analytics.py`

Роль слоя:

- вызывать аналитические классы;
- приводить результаты к Pydantic DTO;
- отдавать данные роутерам в готовом виде.

Через этот слой в API попадают:

- progress;
- topic results;
- weak/best topic выборки;
- recommendations;
- test analytics;
- question analytics;
- персональный analytics snapshot;
- агрегаты по темам для преподавателей.

---

## 5. Итоговая картина проекта

В текущем состоянии проект — это учебная система, в которой:

- backend хранит пользователей, контент и факты обучения;
- frontend проводит пользователя по маршруту от курса до аналитики;
- аналитический слой строит прогресс, тему, тест, вопрос, рекомендации и общий snapshot напрямую из реальных данных;
- документация, API и клиентская часть опираются на одну и ту же актуальную схему проекта.
