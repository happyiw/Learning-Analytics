from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.db import SessionLocal
from backend.lesson_content import (
    build_legacy_blocks,
    build_intro_svg_data_url,
    serialize_lesson_blocks,
)
from backend.enums import QuestionType
from backend.models import AnswerOption, Course, Lesson, Question, Test
from backend.schemas import LessonContentBlock, LessonStatItem


def initialize_database(engine: Engine) -> None:
    if engine.url.get_backend_name() == "sqlite":
        run_sqlite_migrations(engine)

    with SessionLocal() as db:
        sync_intro_course_content(db)


def run_sqlite_migrations(engine: Engine) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_answer_option_selections (
                    user_answer_id INTEGER NOT NULL,
                    answer_option_id INTEGER NOT NULL,
                    PRIMARY KEY (user_answer_id, answer_option_id),
                    FOREIGN KEY(user_answer_id) REFERENCES user_answers (id),
                    FOREIGN KEY(answer_option_id) REFERENCES answer_options (id)
                )
                """
            )
        )
        _ensure_column(connection, "courses", "difficulty", "INTEGER")
        _ensure_column(connection, "courses", "is_open", "BOOLEAN")
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
        _ensure_column(connection, "topic_results", "updated_at", "DATETIME")

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
                    ELSE 1
                END
                WHERE difficulty IS NULL OR difficulty < 1 OR difficulty > 10
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE questions
                SET question_type = CASE
                    WHEN LOWER(TRIM(COALESCE(question_type, ''))) IN ('single_choice', 'choice') THEN 'single_choice'
                    WHEN LOWER(TRIM(COALESCE(question_type, ''))) = 'multiple_choice' THEN 'multiple_choice'
                    WHEN LOWER(TRIM(COALESCE(question_type, ''))) = 'text' THEN 'text'
                    ELSE 'single_choice'
                END
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO user_answer_option_selections (user_answer_id, answer_option_id)
                SELECT id, selected_option_id
                FROM user_answers
                WHERE selected_option_id IS NOT NULL
                """
            )
        )
        connection.execute(text("UPDATE courses SET is_open = COALESCE(is_open, 1)"))
        _backfill_lesson_blocks_from_content(connection)
        _rebuild_lessons_table(connection)
        _rebuild_tasks_table(connection)
        _rebuild_test_attempts_table(connection)
        _rebuild_topic_results_table(connection)
        _rebuild_recommendations_table(connection)


def sync_intro_course_content(db: Session) -> None:
    course = db.query(Course).filter(Course.id == 1).first()
    if course is None:
        return

    course.difficulty = 1
    course.is_open = True

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

    intro_test = db.query(Test).filter(Test.id == 1).first()
    if intro_test is not None:
        intro_test.passing_score = 0
        intro_test.time_limit = None
        intro_test.attempts_allowed = 1

        intro_questions = list(
            db.query(Question).filter(Question.test_id == intro_test.id).all()
        )
        flat_question_ids = [question.id for question in intro_questions]
        question_types = {question.id: question.question_type for question in intro_questions}
        if flat_question_ids:
            for option in db.query(AnswerOption).filter(AnswerOption.question_id.in_(flat_question_ids)):
                if question_types.get(option.question_id) == QuestionType.MULTIPLE_CHOICE:
                    continue
                option.is_correct = True

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
        fallback_column = "created_at" if "created_at" in columns else "NULL"
        connection.execute(
            text(
                f"UPDATE {table_name} SET updated_at = COALESCE(updated_at, {fallback_column}, :now)"
            ),
            {"now": now},
        )


def _backfill_lesson_blocks_from_content(connection) -> None:
    columns = {
        row[1] for row in connection.execute(text("PRAGMA table_info(lessons)")).fetchall()
    }
    if "content" not in columns or "content_blocks" not in columns:
        return

    rows = connection.execute(
        text(
            """
            SELECT id, content, content_blocks
            FROM lessons
            """
        )
    ).fetchall()
    for lesson_id, content, content_blocks in rows:
        if content_blocks:
            continue
        serialized_blocks = serialize_lesson_blocks(build_legacy_blocks(content))
        connection.execute(
            text(
                """
                UPDATE lessons
                SET content_blocks = :content_blocks
                WHERE id = :lesson_id
                """
            ),
            {
                "lesson_id": lesson_id,
                "content_blocks": serialized_blocks,
            },
        )


def _rebuild_lessons_table(connection) -> None:
    expected_columns = {
        "id",
        "module_id",
        "title",
        "content_blocks",
        "video_url",
        "external_url",
        "order",
        "created_at",
        "updated_at",
    }
    _rebuild_table(
        connection,
        table_name="lessons",
        expected_columns=expected_columns,
        create_sql="""
            CREATE TABLE lessons__new (
                id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                content_blocks TEXT,
                video_url VARCHAR(500),
                external_url VARCHAR(500),
                "order" INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(module_id) REFERENCES modules (id)
            )
        """,
        insert_sql="""
            INSERT INTO lessons__new (
                id, module_id, title, content_blocks, video_url, external_url, "order", created_at, updated_at
            )
            SELECT
                id, module_id, title, content_blocks, video_url, external_url, "order", created_at, updated_at
            FROM lessons
        """,
        index_sql=[
            "CREATE INDEX ix_lessons_module_id ON lessons (module_id)",
        ],
    )


def _rebuild_tasks_table(connection) -> None:
    expected_columns = {
        "id",
        "module_id",
        "title",
        "description",
        "max_score",
        "order",
        "created_at",
        "updated_at",
    }
    _rebuild_table(
        connection,
        table_name="tasks",
        expected_columns=expected_columns,
        create_sql="""
            CREATE TABLE tasks__new (
                id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                max_score FLOAT NOT NULL,
                "order" INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(module_id) REFERENCES modules (id)
            )
        """,
        insert_sql="""
            INSERT INTO tasks__new (
                id, module_id, title, description, max_score, "order", created_at, updated_at
            )
            SELECT
                id, module_id, title, description, max_score, "order", created_at, updated_at
            FROM tasks
        """,
        index_sql=[
            "CREATE INDEX ix_tasks_module_id ON tasks (module_id)",
        ],
    )


def _rebuild_test_attempts_table(connection) -> None:
    expected_columns = {
        "id",
        "user_id",
        "test_id",
        "started_at",
        "finished_at",
        "score",
        "max_score",
    }
    _rebuild_table(
        connection,
        table_name="test_attempts",
        expected_columns=expected_columns,
        create_sql="""
            CREATE TABLE test_attempts__new (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                test_id INTEGER NOT NULL,
                started_at DATETIME NOT NULL,
                finished_at DATETIME,
                score FLOAT NOT NULL,
                max_score FLOAT NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(test_id) REFERENCES tests (id)
            )
        """,
        insert_sql="""
            INSERT INTO test_attempts__new (
                id, user_id, test_id, started_at, finished_at, score, max_score
            )
            SELECT
                id, user_id, test_id, started_at, finished_at, score, max_score
            FROM test_attempts
        """,
        index_sql=[
            "CREATE INDEX ix_test_attempts_user_id ON test_attempts (user_id)",
            "CREATE INDEX ix_test_attempts_test_id ON test_attempts (test_id)",
        ],
    )


def _rebuild_topic_results_table(connection) -> None:
    expected_columns = {
        "id",
        "user_id",
        "module_id",
        "last_attempt_at",
        "updated_at",
    }
    _rebuild_table(
        connection,
        table_name="topic_results",
        expected_columns=expected_columns,
        create_sql="""
            CREATE TABLE topic_results__new (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                last_attempt_at DATETIME,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                UNIQUE (user_id, module_id),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(module_id) REFERENCES modules (id)
            )
        """,
        insert_sql="""
            INSERT INTO topic_results__new (
                id, user_id, module_id, last_attempt_at, updated_at
            )
            SELECT
                id,
                user_id,
                module_id,
                last_attempt_at,
                COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM topic_results
        """,
        index_sql=[
            "CREATE INDEX ix_topic_results_user_id ON topic_results (user_id)",
            "CREATE INDEX ix_topic_results_module_id ON topic_results (module_id)",
        ],
    )


def _rebuild_recommendations_table(connection) -> None:
    expected_columns = {
        "id",
        "module_id",
        "title",
        "description",
        "resource_url",
        "created_at",
        "updated_at",
    }
    _rebuild_table(
        connection,
        table_name="recommendations",
        expected_columns=expected_columns,
        create_sql="""
            CREATE TABLE recommendations__new (
                id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                resource_url VARCHAR(500),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(module_id) REFERENCES modules (id)
            )
        """,
        insert_sql="""
            INSERT INTO recommendations__new (
                id, module_id, title, description, resource_url, created_at, updated_at
            )
            SELECT
                id, module_id, title, description, resource_url, created_at, updated_at
            FROM recommendations
        """,
        index_sql=[
            "CREATE INDEX ix_recommendations_module_id ON recommendations (module_id)",
        ],
    )


def _rebuild_table(
    connection,
    *,
    table_name: str,
    expected_columns: set[str],
    create_sql: str,
    insert_sql: str,
    index_sql: list[str],
) -> None:
    current_columns = {
        row[1] for row in connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    }
    if current_columns == expected_columns:
        return

    connection.execute(text("PRAGMA foreign_keys = OFF"))
    connection.execute(text(f"DROP TABLE IF EXISTS {table_name}__new"))
    connection.execute(text(create_sql))
    connection.execute(text(insert_sql))
    connection.execute(text(f"DROP TABLE {table_name}"))
    connection.execute(text(f"ALTER TABLE {table_name}__new RENAME TO {table_name}"))
    for statement in index_sql:
        connection.execute(text(statement))
    connection.execute(text("PRAGMA foreign_keys = ON"))
