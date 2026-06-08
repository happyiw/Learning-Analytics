# Overview

## 1. Назначение проекта

Проект представляет собой учебную платформу с аналитикой обучения. Пользователь проходит курсы, модули, уроки, задания и тесты, а система:

- хранит учебный контент и результаты работы;
- отслеживает прогресс по урокам и тестам;
- формирует аналитику по попыткам и темам;
- показывает персональные рекомендации по повторению материала.

Архитектурно проект состоит из трех основных частей:

- `backend/` — FastAPI-приложение, ORM-модели, API, bootstrap-логика и сервисы;
- `frontend/` — Angular-клиент;
- `analytics/` — отдельный слой аналитических классов, который используется backend-ом.

---

## 2. Backend

### 2.1. Технологический стек и запуск

Backend построен на:

- `FastAPI` — HTTP API;
- `SQLAlchemy 2.x` — ORM и работа с БД;
- `SQLite` — текущая база данных (`app.db`);
- JWT-аутентификации — авторизация пользователей.

Точка входа backend-а: `backend/main.py`.

При запуске приложения:

1. создаются отсутствующие таблицы через `Base.metadata.create_all(...)`;
2. выполняется `initialize_database(engine)` из `backend/bootstrap.py`;
3. для SQLite при необходимости выполняется очистка/перестройка схемы;
4. синхронизируется демонстрационный вводный контент.

### 2.2. Роли пользователей

Система поддерживает три роли:

- `student` — проходит курсы, уроки и тесты;
- `teacher` — управляет учебным контентом и доступом студентов;
- `admin` — обладает теми же возможностями, что и преподаватель, плюс административный доступ.

### 2.3. Таблицы и поля

Ниже перечислены все основные таблицы backend-а в их текущем состоянии.

#### `users`

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

#### `courses`

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

#### `course_enrollments`

Назначение: факты зачисления студентов на курсы.

Поля:

- `id`
- `user_id`
- `course_id`
- `assigned_by_id`
- `created_at`

Особенность:

- уникальность пары `user_id + course_id`.

#### `modules`

Назначение: тематические разделы внутри курса.

Поля:

- `id`
- `course_id`
- `title`
- `description`
- `order`
- `created_at`
- `updated_at`

#### `lessons`

Назначение: теоретический контент модуля.

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

- в таблице больше нет поля `content`;
- в API поле `content` продолжает возвращаться как краткая производная сводка из `content_blocks`.

#### `tasks`

Назначение: практические задания внутри модуля.

Поля:

- `id`
- `module_id`
- `title`
- `description`
- `max_score`
- `order`
- `created_at`
- `updated_at`

#### `tests`

Назначение: тесты по курсу или модулю.

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

#### `questions`

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

#### `answer_options`

Назначение: варианты ответов для вопросов тестов.

Поля:

- `id`
- `question_id`
- `text`
- `is_correct`
- `created_at`
- `updated_at`

#### `test_attempts`

Назначение: факты прохождения тестов.

Поля:

- `id`
- `user_id`
- `test_id`
- `started_at`
- `finished_at`
- `score`
- `max_score`

Примечание:

- в таблице больше не хранятся `percentage` и `is_passed`;
- `percentage` вычисляется как `score / max_score * 100`;
- `is_passed` вычисляется на основе `tests.passing_score`.

#### `user_answers`

Назначение: ответы пользователя на вопросы внутри конкретной попытки.

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

- уникальность пары `attempt_id + question_id`.

#### `user_answer_option_selections`

Назначение: связь ответа пользователя с несколькими выбранными вариантами.

Поля:

- `user_answer_id`
- `answer_option_id`

Особенность:

- используется для вопросов типа `multiple_choice`.

#### `lesson_progress`

Назначение: факты завершения уроков пользователями.

Поля:

- `id`
- `user_id`
- `lesson_id`
- `is_completed`
- `completed_at`

Особенность:

- уникальность пары `user_id + lesson_id`.

#### `topic_results`

Назначение: легкий кэш результата пользователя по модулю.

Поля:

- `id`
- `user_id`
- `module_id`
- `last_attempt_at`
- `updated_at`

Примечание:

- `attempts_count`, `average_percentage`, `best_percentage` и `weakness_level` не хранятся в таблице;
- они рассчитываются на лету в `TopicResultService`.

#### `recommendations`

Назначение: контент рекомендаций, привязанный к модулю.

Поля:

- `id`
- `module_id`
- `title`
- `description`
- `resource_url`
- `created_at`
- `updated_at`

Примечание:

- поле `trigger_score_threshold` удалено из схемы;
- логика показа рекомендаций реализована в `RecommendationService`.

### 2.4. Основные backend endpoints

Ниже перечислены текущие endpoint-ы по группам.

#### Корневой endpoint

- `GET /` — проверка, что API запущен.

#### Аутентификация: `backend/api/auth.py`

- `POST /api/auth/register/` — регистрация пользователя;
- `POST /api/auth/login/` — вход и получение JWT;
- `GET /api/auth/me/` — текущий авторизованный пользователь.

#### Курсы: `backend/api/courses.py`

- `GET /api/courses/` — список опубликованных курсов;
- `GET /api/courses/my/enrollments/` — курсы, на которые записан текущий пользователь;
- `POST /api/courses/{course_id}/enroll/my/` — самозапись на открытый курс;
- `GET /api/courses/{course_id}/enrollments/` — список зачисленных на курс студентов;
- `POST /api/courses/{course_id}/enrollments/` — добавить студента на курс;
- `GET /api/courses/students/search/` — поиск студентов для назначения на курс;
- `GET /api/courses/{course_id}/` — карточка курса;
- `GET /api/courses/{course_id}/modules/` — модули курса;
- `GET /api/courses/{course_id}/progress/my/` — прогресс по курсу;
- `GET /api/courses/{course_id}/topic-results/my/` — результаты по темам курса;
- `GET /api/courses/{course_id}/recommendations/my/` — рекомендации по курсу;
- `POST /api/courses/` — создать курс;
- `PATCH /api/courses/{course_id}/` — обновить курс;
- `DELETE /api/courses/{course_id}/` — удалить курс.

#### Модули: `backend/api/modules.py`

- `GET /api/modules/{module_id}/lessons/` — уроки модуля;
- `GET /api/modules/{module_id}/tests/` — тесты модуля;
- `GET /api/modules/{module_id}/` — карточка модуля;
- `GET /api/modules/{module_id}/progress/my/` — прогресс по модулю;
- `GET /api/modules/{module_id}/topic-results/my/` — результаты по теме модуля;
- `GET /api/modules/{module_id}/recommendations/my/` — рекомендации по модулю;
- `POST /api/modules/` — создать модуль;
- `PATCH /api/modules/{module_id}/` — обновить модуль;
- `DELETE /api/modules/{module_id}/` — удалить модуль.

#### Уроки: `backend/api/lessons.py`

- `GET /api/lessons/{lesson_id}/` — получить урок с деталями и признаком завершения;
- `POST /api/lessons/{lesson_id}/complete/` — отметить урок завершенным;
- `POST /api/lessons/` — создать урок;
- `PATCH /api/lessons/{lesson_id}/` — обновить урок;
- `DELETE /api/lessons/{lesson_id}/` — удалить урок.

#### Задания: `backend/api/tasks.py`

- `GET /api/modules/{module_id}/tasks/` — список заданий модуля;
- `GET /api/tasks/{task_id}/` — карточка задания;
- `POST /api/tasks/` — создать задание;
- `PATCH /api/tasks/{task_id}/` — обновить задание;
- `DELETE /api/tasks/{task_id}/` — удалить задание.

#### Рекомендации: `backend/api/recommendations.py`

- `GET /api/recommendations/my/` — персональные рекомендации текущего пользователя;
- `GET /api/recommendations/` — список всех рекомендаций для преподавателя/админа;
- `POST /api/recommendations/` — создать рекомендацию;
- `GET /api/recommendations/{recommendation_id}/` — получить рекомендацию;
- `PATCH /api/recommendations/{recommendation_id}/` — обновить рекомендацию;
- `DELETE /api/recommendations/{recommendation_id}/` — удалить рекомендацию.

#### Тесты, попытки, вопросы и варианты ответов: `backend/api/tests.py`

Тесты и попытки:

- `GET /api/tests/{test_id}/` — карточка теста;
- `GET /api/tests/{test_id}/active-attempt/` — активная незавершенная попытка по тесту;
- `GET /api/tests/{test_id}/analytics/my/` — аналитика по тесту для текущего пользователя;
- `GET /api/test-attempts/my/unfinished/` — список незавершенных попыток;
- `GET /api/tests/{test_id}/questions/` — вопросы теста для прохождения;
- `POST /api/tests/{test_id}/start/` — начать попытку;
- `POST /api/test-attempts/{attempt_id}/answers/` — сохранить ответ в попытке;
- `POST /api/test-attempts/{attempt_id}/finish/` — завершить попытку;
- `GET /api/test-attempts/{attempt_id}/result/` — получить результат завершенной попытки.

CRUD тестов:

- `POST /api/tests/`
- `PATCH /api/tests/{test_id}/`
- `DELETE /api/tests/{test_id}/`

CRUD вопросов:

- `POST /api/questions/`
- `PATCH /api/questions/{question_id}/`
- `DELETE /api/questions/{question_id}/`

CRUD вариантов ответов:

- `POST /api/answer-options/`
- `PATCH /api/answer-options/{option_id}/`
- `DELETE /api/answer-options/{option_id}/`

#### Аналитика: `backend/api/analytics.py`

Персональная аналитика:

- `GET /api/progress/my/` — общий прогресс по доступным материалам;
- `GET /api/topic-results/my/` — результаты по темам по всем доступным модулям;
- `GET /api/analytics/my/snapshot/` — единый аналитический снимок;
- `GET /api/analytics/my/summary/` — краткая сводка по обучению;
- `GET /api/analytics/my/weak-topics/` — слабые темы;
- `GET /api/analytics/my/best-topics/` — сильные темы;
- `GET /api/analytics/my/dynamics/` — динамика попыток во времени.

Агрегированная аналитика для преподавателя/админа:

- `GET /api/analytics/groups/{group_id}/topic-results/` — тема по группе;
- `GET /api/analytics/courses/{course_id}/topic-results/` — тема по курсу;
- `GET /api/analytics/modules/{module_id}/topic-results/` — тема по модулю.

### 2.5. Внутренние backend-сервисы

Помимо роутеров, в `backend/services/analytics.py` есть слой адаптации аналитики для API. Он:

- вызывает классы из `analytics/`;
- преобразует их payload в DTO из `backend/schemas.py`;
- собирает сводные ответы для endpoint-ов аналитики, рекомендаций и topic results.

Также в `backend/attempt_metrics.py` вынесены функции для вычисления:

- процента выполнения попытки;
- признака прохождения попытки;
- статуса попытки;
- SQL-выражения для процента в аналитических запросах.

---

## 3. Frontend

### 3.1. Общая структура

Frontend реализован на `Angular`.

Главные элементы:

- `frontend/src/app/app.routes.ts` — маршруты приложения;
- `frontend/src/app/app.html` — общий shell с header, footer и `router-outlet`;
- `frontend/src/app/core/services/` — сервисы работы с API;
- `frontend/src/app/core/models/` — интерфейсы DTO;
- `frontend/src/app/features/` — страницы приложения.

### 3.2. Основная навигация

В шапке приложения:

- гость видит ссылки на главную, вход и регистрацию;
- авторизованный пользователь видит ссылки на:
  - главную;
  - курсы;
  - аналитику;
  - рекомендации;
  - незавершенные попытки;
  - профиль.

### 3.3. Страницы и их назначение

#### `/` и `/dashboard` — `DashboardPageComponent`

Где используется:

- главная страница для гостя;
- главная рабочая сводка для авторизованного пользователя.

Содержимое:

- для гостя — landing screen с описанием платформы и переходами к входу/регистрации;
- для авторизованного пользователя — краткая сводка по обучению.

Что показывает:

- общий прогресс;
- число доступных курсов;
- число завершенных уроков;
- средний результат тестов;
- количество рекомендаций;
- короткие инсайты по попыткам и курсам.

#### `/login` — `LoginPageComponent`

Где используется:

- точка входа для уже зарегистрированного пользователя.

Содержимое:

- форма входа по `username` и `password`.

#### `/register` — `RegisterPageComponent`

Где используется:

- точка регистрации нового пользователя.

Содержимое:

- форма регистрации;
- базовые поля профиля студента;
- выбор курса обучения (`course_year`).

#### `/courses` — `CoursesPageComponent`

Где используется:

- основная точка входа в каталог курсов;
- переход сюда идет из верхнего меню.

Содержимое:

- список опубликованных курсов;
- карточки с названием, описанием, сложностью и статусом доступа;
- кнопки старта/продолжения курса;
- для преподавателя и администратора — переход в управление доступом к закрытому курсу.

#### `/courses/:courseId` — `CoursePageComponent`

Где используется:

- открывается из каталога курсов.

Содержимое:

- карточка курса;
- список модулей;
- прогресс по курсу;
- результаты по темам внутри курса;
- персональные рекомендации по курсу.

#### `/courses/:courseId/manage` — `CourseAccessPageComponent`

Где используется:

- доступна преподавателю и администратору из карточки закрытого курса.

Содержимое:

- информация о курсе;
- текущие зачисления;
- поиск студентов;
- добавление студента на курс.

#### `/modules/:moduleId` — `ModulePageComponent`

Где используется:

- открывается из страницы курса.

Содержимое:

- карточка модуля;
- список уроков;
- список заданий;
- список тестов;
- прогресс по модулю;
- topic result по модулю;
- рекомендации по модулю.

#### `/lessons/:lessonId` — `LessonPageComponent`

Где используется:

- открывается из страницы модуля.

Содержимое:

- название урока;
- краткая сводка;
- `content_blocks` с поддержкой нескольких типов блоков;
- видео и внешние ссылки;
- кнопка завершения урока;
- переход к следующему уроку.

#### `/tasks/:taskId` — `TaskPageComponent`

Где используется:

- открывается из страницы модуля.

Содержимое:

- заголовок задания;
- описание;
- максимальный балл;
- порядок задания внутри модуля.

Это информационная карточка задания, без отдельного интерфейса сдачи.

#### `/tests/:testId` — `TestPageComponent`

Где используется:

- открывается из страницы модуля.

Содержимое:

- карточка теста;
- описание;
- лимит времени;
- проходной процент;
- число доступных попыток;
- информация об активной попытке;
- кнопка старта теста;
- переход к списку незавершенных попыток.

#### `/tests/:testId/attempt/:attemptId` — `TestAttemptPageComponent`

Где используется:

- открывается после старта теста или возврата к незавершенной попытке.

Содержимое:

- интерфейс прохождения теста;
- текущий вопрос;
- навигация между вопросами;
- автосохранение ответов;
- таймер при наличии ограничения;
- завершение попытки с переходом на страницу результата.

#### `/tests/:testId/attempt/:attemptId/result` — `TestAttemptResultPageComponent`

Где используется:

- открывается после завершения тестовой попытки.

Содержимое:

- итог попытки;
- статус прохождения;
- набранные баллы;
- процент результата;
- длительность попытки;
- разбор ответов по каждому вопросу;
- кнопка перехода к рекомендациям.

#### `/recommendations` — `RecommendationsPageComponent`

Где используется:

- отдельная страница рекомендаций из верхнего меню;
- также сюда можно перейти со страницы результата теста.

Содержимое:

- список персональных рекомендаций;
- фильтр по всему набору данных, по курсу или по модулю;
- модуль, текущий результат, приоритет и текстовое объяснение причины показа рекомендации.

#### `/analytics` — `AnalyticsPageComponent`

Где используется:

- отдельная аналитическая страница из верхнего меню.

Содержимое:

- общий снимок аналитики пользователя;
- summary-метрики;
- график динамики результатов;
- слабые темы;
- сильные темы;
- полная таблица результатов по темам.

#### `/attempts` — `UnfinishedAttemptsPageComponent`

Где используется:

- отдельная страница из верхнего меню;
- дополнительная точка возврата к незавершенным тестам.

Содержимое:

- список незавершенных попыток;
- курс и модуль;
- время последней активности;
- число отвеченных вопросов;
- лимит времени;
- ссылка на продолжение попытки.

#### `/profile` — `ProfilePageComponent`

Где используется:

- личный кабинет пользователя из верхнего меню.

Содержимое:

- ФИО;
- username;
- email;
- университет;
- группа;
- курс обучения;
- дата создания аккаунта;
- роль;
- кнопка выхода.

### 3.4. Как страницы связаны между собой

Типовой пользовательский маршрут выглядит так:

1. пользователь входит в систему;
2. открывает `/courses`;
3. выбирает `/courses/:courseId`;
4. переходит в `/modules/:moduleId`;
5. открывает урок `/lessons/:lessonId`, задание `/tasks/:taskId` или тест `/tests/:testId`;
6. при прохождении теста переходит на `/tests/:testId/attempt/:attemptId`;
7. после завершения получает `/tests/:testId/attempt/:attemptId/result`;
8. затем может открыть `/recommendations` и `/analytics`.

---

## 4. Analytics

Пакет `analytics/` содержит все основные аналитические классы проекта.

### 4.1. `ProgressService`

Файл: `analytics/progress_service.py`

Назначение:

- считает прогресс пользователя по всем доступным материалам;
- умеет работать в трех скоупах: глобально, по курсу, по модулю.

Основные методы:

- `get_accessible_course_ids(user_id)` — определяет курсы, доступные пользователю с учетом роли и зачислений;
- `get_overall_progress(user_id)` — общий прогресс;
- `get_course_progress(user_id, course_id)` — прогресс по курсу;
- `get_module_progress(user_id, module_id)` — прогресс по модулю;
- `get_completed_lessons_percentage(...)` — процент завершенных уроков;
- `get_completed_modules_percentage(...)` — процент полностью завершенных модулей;
- `get_modules_for_scope(...)` — список модулей для указанного скоупа;
- `get_scope_lesson_ids(...)` — ID уроков для скоупа;
- `get_scope_test_ids(...)` — ID тестов для скоупа;
- `_build_progress(...)` — собирает итоговый `ProgressRead`.

На чем основаны расчеты:

- `course_enrollments`;
- `lesson_progress`;
- `test_attempts`;
- `tests.passing_score`.

### 4.2. `TopicResultService`

Файл: `analytics/topic_result_service.py`

Назначение:

- строит результаты пользователя по модулям;
- использует `topic_results` только как легкий кэш времени последней попытки и идентичности строки;
- считает все метрики напрямую из `test_attempts`.

Основные методы:

- `update_topic_result_after_attempt(user_id, module_id)` — обновляет кэш после завершения попытки;
- `get_or_create_topic_result(user_id, module_id)` — возвращает или создает строку `topic_results`;
- `calculate_weakness_level(average_percentage, attempts_count)` — определяет уровень слабости темы;
- `get_user_topic_results(user_id)` — результаты по всем доступным модулям;
- `get_course_topic_results(user_id, course_id)` — результаты в рамках курса;
- `get_module_topic_results(user_id, module_id)` — результаты по одному модулю;
- `_get_scope_topic_results(...)` — общая логика выборки для разных скоупов;
- `_build_topic_result_payload(user_id, module)` — собирает payload по модулю;
- `_calculate_topic_result_values(user_id, module_id)` — считает число попыток, средний и лучший результат, слабость и дату последней попытки;
- `_serialize_topic_result(...)` — готовит итоговый словарь для DTO.

### 4.3. `WeakTopicDetector`

Файл: `analytics/topic_result_service.py`

Назначение:

- работает поверх `TopicResultService`;
- делит темы на слабые, сильные и промежуточные;
- формирует текстовые объяснения для аналитики и рекомендаций.

Основные методы:

- `get_weak_topics(...)` — возвращает слабые темы;
- `get_strong_topics(...)` — возвращает сильные темы;
- `sort_topics_by_problem_severity(topics)` — сортировка слабых тем;
- `sort_topics_by_success(topics)` — сортировка сильных тем;
- `determine_weak_topic_reason(topic_result)` — объяснение, почему тема считается слабой;
- `determine_strong_topic_reason(topic_result)` — объяснение, почему тема считается сильной;
- `prepare_analytics_data(...)` — полный набор данных для аналитической страницы;
- `prepare_recommendation_data(...)` — подготовка темы к дальнейшему правилу рекомендаций;
- `_is_weak_topic(...)` — признак слабой темы;
- `_is_strong_topic(...)` — признак сильной темы;
- `_attach_weak_reason(...)`, `_attach_strong_reason(...)`, `_attach_analytics_reason(...)` — добавляют объяснения в payload.

### 4.4. `RecommendationService`

Файл: `analytics/recommendation_service.py`

Назначение:

- выбирает, какие рекомендации показывать пользователю;
- использует контент из таблицы `recommendations`;
- применяет к нему backend-правила, а не пороги из БД.

Текущие rule-based сценарии:

- низкий средний результат по модулю;
- несколько неуспешных попыток;
- незавершенные уроки в модуле.

Основные методы:

- `get_personal_recommendations(user_id)` — рекомендации по всем доступным модулям;
- `get_course_recommendations(user_id, course_id)` — рекомендации по курсу;
- `get_module_recommendations(user_id, module_id)` — рекомендации по модулю;
- `match_topic_results_with_recommendations(...)` — сопоставляет тему, контекст и рекомендации;
- `determine_priority(context, rule_key)` — приоритет рекомендации;
- `build_reason_explanation(context, rule_key)` — текстовое объяснение;
- `to_frontend_payload(recommendation, context, rule_key)` — payload для frontend;
- `_build_contexts(user_id, topic_results)` — собирает расширенный контекст по каждой теме;
- `_get_failed_attempt_metrics(user_id, module_ids)` — число неудачных попыток и длина серии неудач;
- `_get_unfinished_lessons_count(user_id, module_ids)` — число незавершенных уроков;
- `_get_matching_rules(context)` — определяет, какие правила сработали;
- `_get_recommendation_entities(module_ids)` — получает контент рекомендаций из БД;
- `_recommendation_sort_key(item)` — сортировка выдачи.

### 4.5. `TestAnalyticsService`

Файл: `analytics/test_analytics_service.py`

Назначение:

- строит аналитику по одному тесту и всем попыткам пользователя по нему.

Основные методы:

- `get_test_attempts(user_id, test_id, include_unfinished=True)` — получает попытки по тесту;
- `calculate_completion_percentage(attempt)` — вычисляет процент выполнения;
- `calculate_attempts_count(attempts)` — число попыток;
- `calculate_best_result(attempts)` — лучший результат;
- `calculate_average_result(attempts)` — средний результат;
- `calculate_last_result(attempts)` — последний результат;
- `calculate_time_spent_seconds(attempt)` — время прохождения;
- `calculate_status(attempt)` — статус попытки;
- `build_attempt_snapshot(attempt)` — snapshot одной попытки;
- `build_test_analytics(user_id, test_id)` — итоговый payload для `TestAnalyticsRead`.

### 4.6. `StudentSummaryService`

Файл: `analytics/student_summary.py`

Назначение:

- собирает сводную аналитику по пользователю;
- формирует summary и динамику результатов;
- используется в общей аналитической странице.

Основные методы:

- `get_summary(user_id)` — общая сводка: попытки, пройденные тесты, средние результаты, завершенные уроки, число начатых курсов;
- `get_dynamics(user_id)` — временной ряд завершенных тестовых попыток;
- `build_analytics_snapshot(user_id)` — объединенный аналитический снимок пользователя.

### 4.7. Как аналитика интегрирована в backend

Backend использует эти классы через функции из `backend/services/analytics.py`.

Этот слой:

- вызывает аналитические сервисы;
- собирает DTO из `backend/schemas.py`;
- подготавливает данные для endpoint-ов:
  - прогресса;
  - snapshot-а;
  - weak/best topics;
  - рекомендаций;
  - агрегированной аналитики по группе, курсу и модулю.

---

## 5. Итоговая картина проекта

В текущем состоянии проект — это полноценная учебная веб-платформа, где:

- backend хранит пользователей, учебный контент, попытки и факты прогресса;
- frontend дает единый пользовательский маршрут от каталога курсов до аналитики и рекомендаций;
- аналитический слой считает все ключевые учебные метрики на лету из фактических данных, без лишней денормализации в БД.
