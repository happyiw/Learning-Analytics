# Backend Updates

## Версия `1.2.0`

## Что изменилось

- Уроки переведены на структурированный формат `content_blocks`
- Backend теперь поддерживает блоки уроков с типами:
  - `rich_text`
  - `callout`
  - `bullets`
  - `checklist`
  - `table`
  - `chart`
  - `image`
  - `stat_grid`
- В `Lesson` добавлено поле `content_blocks`, при этом `content` сохраняется как краткое текстовое summary
- В `Course` поле сложности переведено на числовой формат `difficulty: 1..10`
- При старте backend автоматически выполняется bootstrap схемы SQLite:
  - добавляются новые колонки
  - синхронизируются timestamps
  - обновляется вводный курс
- Для учебного контента унифицированы timestamps `created_at` / `updated_at`

## Актуальные зависимости

- `fastapi>=0.115,<1.0`
- `uvicorn>=0.30,<1.0`
- `sqlalchemy>=2.0,<3.0`
- `PyJWT>=2.8,<3.0`

## Ключевые модели

### `Course`

- `id: int`
- `title: str`
- `description: str | None`
- `author_id: int | None`
- `difficulty: int` — значение от `1` до `10`
- `is_published: bool`
- `created_at: datetime`
- `updated_at: datetime`

### `Module`

- `id: int`
- `course_id: int`
- `title: str`
- `description: str | None`
- `order: int`
- `created_at: datetime`
- `updated_at: datetime`

### `Lesson`

- `id: int`
- `module_id: int`
- `title: str`
- `content: str` — краткое summary для списка и предпросмотра
- `content_blocks: str | None` — JSON с блоками урока
- `video_url: str | None`
- `external_url: str | None`
- `order: int`
- `created_at: datetime`
- `updated_at: datetime`

### `Task`

- `id: int`
- `module_id: int`
- `title: str`
- `description: str`
- `task_type: str | None`
- `difficulty_level: str | None`
- `explanation: str | None`
- `max_score: float`
- `order: int`
- `created_at: datetime`
- `updated_at: datetime`

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
- `created_at: datetime`
- `updated_at: datetime`

### `Question`

- `id: int`
- `test_id: int`
- `text: str`
- `question_type: str`
- `difficulty_level: str | None`
- `score: float`
- `order: int`
- `created_at: datetime`
- `updated_at: datetime`

### `AnswerOption`

- `id: int`
- `question_id: int`
- `text: str`
- `is_correct: bool`
- `created_at: datetime`
- `updated_at: datetime`

### `Recommendation`

- `id: int`
- `module_id: int`
- `title: str`
- `description: str`
- `resource_url: str | None`
- `trigger_score_threshold: float`
- `created_at: datetime`
- `updated_at: datetime`

## Изменения API

### Курсы

- `GET /api/courses/`
- `GET /api/courses/{course_id}/`
- `POST /api/courses/`
- `PATCH /api/courses/{course_id}/`

Во всех контрактах курса используется поле `difficulty`, а не `difficulty_level`.

### Уроки

- `GET /api/lessons/{lesson_id}/`
- `POST /api/lessons/`
- `PATCH /api/lessons/{lesson_id}/`
- `POST /api/lessons/{lesson_id}/complete/`

`GET /api/lessons/{lesson_id}/` теперь возвращает:

- `content` — summary урока
- `content_blocks` — массив структурированных блоков
- `next_lesson_id`
- `next_lesson_title`

### Модули

- `GET /api/modules/{module_id}/lessons/`

Теперь список уроков модуля также возвращает `content_blocks`, `created_at` и `updated_at`.

## Поведение миграций

При запуске `backend.main:app` приложение:

1. Создаёт отсутствующие таблицы через `Base.metadata.create_all(...)`
2. Выполняет SQLite-bootstrap для актуализации колонок
3. Мигрирует сложность курса в новое поле `difficulty`
4. Обогащает вводные уроки блоковым контентом

## Точка входа

- `backend/main.py`

## Запуск

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```
