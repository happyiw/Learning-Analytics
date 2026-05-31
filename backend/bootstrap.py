from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.db import SessionLocal
from backend.lesson_content import (
    build_intro_svg_data_url,
    serialize_lesson_blocks,
    summarize_lesson_content,
)
from backend.models import Course, Lesson, Test
from backend.schemas import LessonContentBlock, LessonStatItem


def initialize_database(engine: Engine) -> None:
    if engine.url.get_backend_name() == "sqlite":
        run_sqlite_migrations(engine)

    with SessionLocal() as db:
        sync_intro_course_content(db)


def run_sqlite_migrations(engine: Engine) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        _ensure_column(connection, "courses", "difficulty", "INTEGER")
        _ensure_column(connection, "modules", "created_at", "DATETIME")
        _ensure_column(connection, "modules", "updated_at", "DATETIME")
        _ensure_column(connection, "lessons", "content_blocks", "TEXT")
        _ensure_column(connection, "lessons", "updated_at", "DATETIME")
        _ensure_column(connection, "tasks", "created_at", "DATETIME")
        _ensure_column(connection, "tasks", "updated_at", "DATETIME")
        _ensure_column(connection, "tests", "created_at", "DATETIME")
        _ensure_column(connection, "tests", "updated_at", "DATETIME")
        _ensure_column(connection, "questions", "created_at", "DATETIME")
        _ensure_column(connection, "questions", "updated_at", "DATETIME")
        _ensure_column(connection, "answer_options", "created_at", "DATETIME")
        _ensure_column(connection, "answer_options", "updated_at", "DATETIME")
        _ensure_column(connection, "recommendations", "created_at", "DATETIME")
        _ensure_column(connection, "recommendations", "updated_at", "DATETIME")
        _ensure_column(connection, "topic_results", "created_at", "DATETIME")

        _fill_timestamp(connection, "modules", now)
        _fill_timestamp(connection, "lessons", now)
        _fill_timestamp(connection, "tasks", now)
        _fill_timestamp(connection, "tests", now)
        _fill_timestamp(connection, "questions", now)
        _fill_timestamp(connection, "answer_options", now)
        _fill_timestamp(connection, "recommendations", now)
        _fill_timestamp(connection, "topic_results", now)

        connection.execute(
            text(
                """
                UPDATE courses
                SET difficulty = CASE
                    WHEN difficulty BETWEEN 1 AND 10 THEN difficulty
                    WHEN TRIM(COALESCE(difficulty_level, '')) = '' THEN 1
                    WHEN LOWER(TRIM(COALESCE(difficulty_level, ''))) IN ('начальный', 'легкий', 'лёгкий', 'basic', 'beginner', 'easy') THEN 2
                    WHEN LOWER(TRIM(COALESCE(difficulty_level, ''))) IN ('средний', 'intermediate', 'medium') THEN 5
                    WHEN LOWER(TRIM(COALESCE(difficulty_level, ''))) IN ('продвинутый', 'advanced', 'hard') THEN 8
                    WHEN CAST(TRIM(COALESCE(difficulty_level, '')) AS INTEGER) BETWEEN 1 AND 10 THEN CAST(TRIM(COALESCE(difficulty_level, '')) AS INTEGER)
                    ELSE 1
                END
                WHERE difficulty IS NULL OR difficulty < 1 OR difficulty > 10
                """
            )
        )


def sync_intro_course_content(db: Session) -> None:
    course = db.query(Course).filter(Course.id == 1).first()
    if course is None:
        return

    course.difficulty = 1

    illustrations = {
        1: build_intro_svg_data_url("Добро пожаловать", "Карта платформы и первые шаги", "#c2410c", "#0f766e"),
        2: build_intro_svg_data_url("Маршрут обучения", "Как курс делится на модули и уроки", "#0f766e", "#1d4ed8"),
        3: build_intro_svg_data_url("Прогресс и рекомендации", "Как данные помогают двигаться дальше", "#7c2d12", "#2563eb"),
        4: build_intro_svg_data_url("Тесты без стресса", "Попытки, автосохранение и возврат", "#1d4ed8", "#c2410c"),
    }

    lesson_blocks = {
        1: [
            LessonContentBlock(
                type="callout",
                title="Что вас ждёт",
                text="Платформа собирает курсы, уроки, задания, тесты и личную аналитику в одном понятном маршруте.",
                tone="accent",
            ),
            LessonContentBlock(
                type="rich_text",
                title="Как ориентироваться",
                paragraphs=[
                    "Главная страница показывает ваш текущий прогресс, завершённые уроки и краткую учебную сводку.",
                    "Из карточки курса вы переходите в модули, затем в уроки, задания и тесты, не теряя общий контекст обучения.",
                ],
            ),
            LessonContentBlock(
                type="stat_grid",
                title="Ключевые разделы",
                stats=[
                    LessonStatItem(label="Главная", value="Сводка", hint="Краткий обзор вашей траектории"),
                    LessonStatItem(label="Курсы", value="Маршрут", hint="Все доступные учебные программы"),
                    LessonStatItem(label="Аналитика", value="Прогресс", hint="Результаты, динамика и темы"),
                    LessonStatItem(label="Рекомендации", value="Подсказки", hint="Материалы для усиления слабых мест"),
                ],
            ),
            LessonContentBlock(
                type="image",
                title="Визуальная карта платформы",
                src=illustrations[1],
                alt="Схема разделов учебной платформы",
                caption="Каждый раздел помогает быстро понять, где вы сейчас и что делать дальше.",
            ),
        ],
        2: [
            LessonContentBlock(
                type="rich_text",
                title="От курса к конкретному действию",
                paragraphs=[
                    "Курс задаёт общую тему обучения. Внутри него находятся модули, а внутри модулей — уроки, задания и тесты.",
                    "Такая структура делает обучение последовательным: сначала изучение материала, затем практика и только потом проверка результата.",
                ],
            ),
            LessonContentBlock(
                type="table",
                title="Из чего состоит маршрут",
                columns=["Уровень", "Что хранит", "Для чего нужен"],
                rows=[
                    ["Курс", "Общую тему и набор модулей", "Показывает большую картину обучения"],
                    ["Модуль", "Уроки, задания, тесты", "Фокусирует на одной подтеме"],
                    ["Урок", "Контент и вложения", "Помогает изучить материал"],
                    ["Тест", "Вопросы и попытки", "Показывает, как усвоена тема"],
                ],
            ),
            LessonContentBlock(
                type="chart",
                title="Типичный ритм прохождения",
                labels=["Изучение", "Практика", "Проверка", "Повторение"],
                values=[80, 55, 40, 65],
                unit="%",
                caption="Чем ровнее вы проходите шаги, тем стабильнее становится прогресс.",
            ),
            LessonContentBlock(
                type="image",
                title="Как выглядит учебная траектория",
                src=illustrations[2],
                alt="Иллюстрация маршрута от курса к урокам",
            ),
        ],
        3: [
            LessonContentBlock(
                type="callout",
                title="Аналитика не ради отчёта",
                text="Она нужна, чтобы быстро увидеть сильные стороны, слабые темы и понять, где стоит задержаться чуть дольше.",
                tone="info",
            ),
            LessonContentBlock(
                type="rich_text",
                title="Что вы увидите в аналитике",
                paragraphs=[
                    "Платформа агрегирует завершённые уроки, результаты тестов и средний процент по темам.",
                    "Если по какой-то теме результат ниже ожидаемого, в рекомендациях появляются дополнительные материалы и подсказки.",
                ],
            ),
            LessonContentBlock(
                type="chart",
                title="Пример динамики обучения",
                labels=["Первая попытка", "После повторения", "После рекомендаций"],
                values=[42, 68, 84],
                unit="%",
                caption="Даже простое повторение и одна рекомендация часто заметно улучшают результат.",
            ),
            LessonContentBlock(
                type="bullets",
                title="Когда стоит открыть рекомендации",
                items=[
                    "Если по теме несколько попыток подряд дают низкий результат.",
                    "Если вы давно не возвращались к модулю и хотите быстро освежить материал.",
                    "Если нужно подобрать внешний материал для повторения перед тестом.",
                ],
            ),
            LessonContentBlock(
                type="image",
                title="Как аналитика помогает учиться",
                src=illustrations[3],
                alt="Иллюстрация аналитики и рекомендаций",
            ),
        ],
        4: [
            LessonContentBlock(
                type="rich_text",
                title="Что важно знать о тестах",
                paragraphs=[
                    "Перед стартом теста обратите внимание на лимит времени, проходной процент и количество попыток.",
                    "Во время прохождения ответы автоматически сохраняются, поэтому вы можете безопасно вернуться к незавершённой попытке позже.",
                ],
            ),
            LessonContentBlock(
                type="table",
                title="Как ведёт себя система",
                columns=["Ситуация", "Что произойдёт"],
                rows=[
                    ["Вы ответили на вопрос", "Ответ сохранится как черновик и будет доступен при возврате"],
                    ["Вы закрыли вкладку", "Попытка останется незавершённой и доступной для продолжения"],
                    ["Время закончилось", "Система автоматически завершит тест"],
                    ["Попытки кончились", "Новый старт будет недоступен до изменения лимита"],
                ],
            ),
            LessonContentBlock(
                type="checklist",
                title="Мини-чеклист перед стартом",
                items=[
                    "Проверьте, что у вас достаточно времени.",
                    "Откройте урок ещё раз, если хотите быстро повторить материал.",
                    "Сохраняйте ответы по ходу прохождения, если сомневаетесь.",
                ],
            ),
            LessonContentBlock(
                type="image",
                title="Спокойный сценарий прохождения",
                src=illustrations[4],
                alt="Схема прохождения теста с возвратом к попытке",
            ),
        ],
    }

    for lesson_id, blocks in lesson_blocks.items():
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if lesson is None:
            continue
        lesson.content_blocks = serialize_lesson_blocks(blocks)
        lesson.content = summarize_lesson_content("", blocks)

    intro_test = db.query(Test).filter(Test.id == 1).first()
    if intro_test is not None:
        intro_test.passing_score = 0

    db.commit()


def _ensure_column(connection, table_name: str, column_name: str, column_type: str) -> None:
    existing_columns = {
        row[1] for row in connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    }
    if column_name in existing_columns:
        return
    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def _fill_timestamp(connection, table_name: str, now: str) -> None:
    columns = {
        row[1] for row in connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    }
    if "created_at" in columns:
        connection.execute(
            text(f"UPDATE {table_name} SET created_at = COALESCE(created_at, :now)"),
            {"now": now},
        )
    if "updated_at" in columns:
        connection.execute(
            text(
                f"UPDATE {table_name} SET updated_at = COALESCE(updated_at, created_at, :now)"
            ),
            {"now": now},
        )
