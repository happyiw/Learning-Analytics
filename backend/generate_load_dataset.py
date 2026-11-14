from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Iterator

import psycopg

from backend.core.config import settings
from backend.core.security import hash_password


PROFILE = {
    "students": 5_000,
    "courses": 20,
    "modules_per_course": 15,
    "lessons_per_module": 6,
    "tasks_per_module": 2,
    "tests_per_module": 2,
    "questions_per_test": 4,
    "attempts_per_student": 100,
    "answers_per_attempt": 4,
    "events": 2_000_000,
}

BASE = {
    "user": 100_000,
    "course": 10_000,
    "enrollment": 100_000,
    "module": 100_000,
    "lesson": 1_000_000,
    "lesson_progress": 1_000_000,
    "task": 2_000_000,
    "test": 100_000,
    "question": 1_000_000,
    "option": 10_000_000,
    "recommendation": 100_000,
    "attempt": 1_000_000,
    "answer": 10_000_000,
    "event": 10_000_000,
}

COURSE_CATALOG = (
    ("Безопасность веб-приложений и OWASP", "контроль доступа", "инъекции", "безопасная конфигурация"),
    ("Сетевая безопасность и защита инфраструктуры", "сегментация", "межсетевые экраны", "сетевой мониторинг"),
    ("Прикладная криптография и PKI", "шифрование", "электронная подпись", "управление ключами"),
    ("SOC, SIEM и мониторинг событий", "нормализация журналов", "корреляция", "триаж событий"),
    ("Реагирование на инциденты и цифровая криминалистика", "подготовка", "локализация", "сбор доказательств"),
    ("Threat Intelligence и MITRE ATT&CK", "тактики ATT&CK", "техники противника", "защитное картирование"),
    ("Безопасность облачных платформ", "shared responsibility", "облачные IAM", "защита данных"),
    ("Безопасность контейнеров и Kubernetes", "образы контейнеров", "политики кластера", "runtime-защита"),
    ("DevSecOps и безопасность цепочки поставок", "SAST и DAST", "SBOM", "защита CI/CD"),
    ("Управление идентификацией и Zero Trust", "аутентификация", "авторизация", "минимальные привилегии"),
    ("Защита Linux-систем", "hardening", "контроль доступа", "аудит Linux"),
    ("Защита Windows и Active Directory", "Kerberos", "групповые политики", "защита привилегий"),
    ("Анализ вредоносного программного обеспечения", "статический анализ", "динамический анализ", "поведенческие индикаторы"),
    ("Тестирование на проникновение и этический хакинг", "разведка", "валидация уязвимостей", "отчётность"),
    ("Безопасность API и мобильных приложений", "API authorization", "защита токенов", "мобильное хранение"),
    ("Безопасность баз данных и защита информации", "классификация данных", "разграничение доступа", "аудит запросов"),
    ("Управление киберрисками и соответствием", "оценка риска", "контроли", "непрерывность"),
    ("Безопасность промышленных систем и OT", "архитектура ICS", "сегментация OT", "безопасность процессов"),
    ("Безопасность ИИ и LLM-приложений", "угрозы моделям", "защита данных", "безопасный inference"),
    ("Киберустойчивость и восстановление", "устойчивые архитектуры", "резервирование", "восстановление после атак"),
)

MODULE_PATTERNS = (
    "Основы и терминология: {focus}",
    "Активы и модель угроз: {focus}",
    "Архитектура и границы доверия: {focus}",
    "Идентификация поверхности атаки: {focus}",
    "Управление доступом: {focus}",
    "Безопасная конфигурация: {focus}",
    "Уязвимости и методы проверки: {focus}",
    "Мониторинг и журналирование: {focus}",
    "Обнаружение атак: {focus}",
    "Реагирование на инциденты: {focus}",
    "Восстановление и устойчивость: {focus}",
    "Практикум по теме: {focus}",
    "Разбор типовых ошибок: {focus}",
    "Анализ инцидентов: {focus}",
    "Итоговый сценарий: {focus}",
)

LESSON_PATTERNS = (
    "Концепции и область применения",
    "Угрозы и сценарии атак",
    "Защитные меры и конфигурация",
    "Мониторинг и признаки компрометации",
    "Практическая лабораторная работа",
    "Контрольный список и разбор инцидента",
)

RECOMMENDATIONS = (
    "Разобрать серию неуспешных попыток",
    "Повторить ключевые понятия темы",
    "Завершить теоретические материалы",
    "Изменить стратегию повторения",
    "Закрепить знания на практическом сценарии",
    "Довести тему до уверенного уровня",
)


def database_dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def copy_rows(
    connection: psycopg.Connection,
    table: str,
    columns: tuple[str, ...],
    rows: Iterable[tuple],
    expected: int,
) -> None:
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    statement = f'COPY "{table}" ({quoted_columns}) FROM STDIN'
    started = datetime.now(timezone.utc)
    count = 0
    with connection.cursor() as cursor, cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)
            count += 1
            if count % 100_000 == 0:
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                print(f"{table}: {count:,}/{expected:,} rows ({elapsed:.1f}s)", flush=True)
    connection.commit()
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    print(f"{table}: completed {count:,} rows in {elapsed:.1f}s", flush=True)


def ensure_target_is_empty(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM users WHERE id >= %s LIMIT 1", (BASE["user"],))
        if cursor.fetchone() is not None:
            raise RuntimeError("Medium dataset already exists. Use --replace to regenerate it.")


def remove_generated_data(connection: psycopg.Connection) -> None:
    statements = (
        ("DELETE FROM user_answer_option_selections WHERE user_answer_id >= %s", BASE["answer"]),
        ("DELETE FROM user_answers WHERE id >= %s", BASE["answer"]),
        ("DELETE FROM learning_events WHERE id >= %s", BASE["event"]),
        ("DELETE FROM student_module_metrics WHERE user_id >= %s", BASE["user"]),
        ("DELETE FROM topic_results WHERE user_id >= %s", BASE["user"]),
        ("DELETE FROM test_attempts WHERE id >= %s", BASE["attempt"]),
        ("DELETE FROM lesson_progress WHERE id >= %s", BASE["lesson_progress"]),
        ("DELETE FROM course_enrollments WHERE id >= %s", BASE["enrollment"]),
        ("DELETE FROM answer_options WHERE id >= %s", BASE["option"]),
        ("DELETE FROM questions WHERE id >= %s", BASE["question"]),
        ("DELETE FROM tests WHERE id >= %s", BASE["test"]),
        ("DELETE FROM tasks WHERE id >= %s", BASE["task"]),
        ("DELETE FROM lesson_progress WHERE lesson_id >= %s", BASE["lesson"]),
        ("DELETE FROM lessons WHERE id >= %s", BASE["lesson"]),
        ("DELETE FROM recommendations WHERE id >= %s", BASE["recommendation"]),
        ("DELETE FROM modules WHERE id >= %s", BASE["module"]),
        ("DELETE FROM courses WHERE id >= %s", BASE["course"]),
        ("DELETE FROM users WHERE id >= %s", BASE["user"]),
    )
    with connection.cursor() as cursor:
        for statement, threshold in statements:
            cursor.execute(statement, (threshold,))
    connection.commit()
    print("Previous Medium dataset removed.", flush=True)


def user_rows(password_hash: str, now: datetime) -> Iterator[tuple]:
    for index in range(PROFILE["students"]):
        user_id = BASE["user"] + index
        yield (
            user_id,
            f"load_medium_{index + 1:05d}",
            password_hash,
            f"load-medium-{index + 1:05d}@example.test",
            f"Студент{index + 1}",
            "Нагрузочный",
            "student",
            "Synthetic Cybersecurity University",
            f"LOAD-{index // 50 + 1:03d}",
            index % 4 + 1,
            now,
        )


def course_rows(now: datetime) -> Iterator[tuple]:
    for index, (title, *focuses) in enumerate(COURSE_CATALOG):
        yield (
            BASE["course"] + index,
            title,
            "[LOAD-MEDIUM] Синтетический курс для нагрузочного тестирования. "
            f"Практические области: {', '.join(focuses)}.",
            2,
            index % 5 + 1,
            True,
            False,
            now,
            now,
        )


def enrollment_rows(now: datetime) -> Iterator[tuple]:
    for index in range(PROFILE["students"]):
        yield (
            BASE["enrollment"] + index,
            BASE["user"] + index,
            BASE["course"] + index % PROFILE["courses"],
            2,
            now,
        )


def module_rows(now: datetime) -> Iterator[tuple]:
    for course_index, (_, *focuses) in enumerate(COURSE_CATALOG):
        for module_index, pattern in enumerate(MODULE_PATTERNS):
            focus = focuses[module_index % len(focuses)]
            yield (
                BASE["module"] + course_index * 15 + module_index,
                BASE["course"] + course_index,
                pattern.format(focus=focus),
                f"Синтетический модуль по теме «{focus}» с теорией, практикой и контролем.",
                module_index + 1,
                now,
                now,
            )


def lesson_rows(now: datetime) -> Iterator[tuple]:
    for module_offset in range(300):
        course_index = module_offset // 15
        module_index = module_offset % 15
        focuses = COURSE_CATALOG[course_index][1:]
        focus = focuses[module_index % len(focuses)]
        for lesson_index, lesson_title in enumerate(LESSON_PATTERNS):
            lesson_id = BASE["lesson"] + module_offset * 6 + lesson_index
            blocks = json.dumps(
                [
                    {
                        "type": "text",
                        "title": lesson_title,
                        "content": (
                            f"Учебный материал по направлению «{focus}». Рассматриваются активы, "
                            "угрозы, защитные меры, мониторинг и проверяемые результаты обучения."
                        ),
                    }
                ],
                ensure_ascii=False,
            )
            yield (
                lesson_id,
                BASE["module"] + module_offset,
                f"{lesson_index + 1}. {lesson_title}",
                blocks,
                None,
                None,
                lesson_index + 1,
                now,
                now,
            )


def task_rows(now: datetime) -> Iterator[tuple]:
    for module_offset in range(300):
        for task_index in range(2):
            yield (
                BASE["task"] + module_offset * 2 + task_index,
                BASE["module"] + module_offset,
                f"Практическое задание {task_index + 1}",
                "Проанализируйте сценарий угроз, предложите защитные меры и критерии проверки.",
                10.0,
                task_index + 1,
                now,
                now,
            )


def test_rows(now: datetime) -> Iterator[tuple]:
    for module_offset in range(300):
        course_index = module_offset // 15
        for test_index in range(2):
            yield (
                BASE["test"] + module_offset * 2 + test_index,
                BASE["course"] + course_index,
                BASE["module"] + module_offset,
                f"Контроль по модулю — вариант {test_index + 1}",
                "Проверка понимания угроз, защитных мер и порядка реагирования.",
                30,
                60.0,
                6,
                True,
                now,
                now,
            )


def question_rows(now: datetime) -> Iterator[tuple]:
    for test_offset in range(600):
        module_offset = test_offset // 2
        course_index = module_offset // 15
        focuses = COURSE_CATALOG[course_index][1:]
        focus = focuses[(module_offset % 15) % len(focuses)]
        for question_index in range(4):
            yield (
                BASE["question"] + test_offset * 4 + question_index,
                BASE["test"] + test_offset,
                f"Какое действие наиболее корректно для темы «{focus}» в сценарии {question_index + 1}?",
                "single_choice",
                ("basic", "intermediate", "advanced")[question_index % 3],
                1.0,
                question_index + 1,
                now,
                now,
            )


def option_rows(now: datetime) -> Iterator[tuple]:
    texts = (
        "Сначала определить активы и угрозы, затем применить и проверить защитные меры",
        "Отключить журналирование и продолжить эксплуатацию без анализа",
        "Игнорировать контекст и использовать одинаковую настройку для всех систем",
        "Скрыть обнаруженный риск без документирования и контроля",
    )
    for question_offset in range(2_400):
        for option_index, text in enumerate(texts):
            yield (
                BASE["option"] + question_offset * 4 + option_index,
                BASE["question"] + question_offset,
                text,
                option_index == 0,
                now,
                now,
            )


def recommendation_rows(now: datetime) -> Iterator[tuple]:
    for module_offset in range(300):
        for recommendation_index, title in enumerate(RECOMMENDATIONS):
            yield (
                BASE["recommendation"] + module_offset * 6 + recommendation_index,
                BASE["module"] + module_offset,
                title,
                "Повторите соответствующий материал, выполните лабораторную работу и проверьте результат новым тестом.",
                None,
                now,
                now,
            )


def lesson_progress_rows(now: datetime) -> Iterator[tuple]:
    progress_id = BASE["lesson_progress"]
    for student_index in range(5_000):
        course_index = student_index % 20
        course_started = now - timedelta(days=365 - student_index % 30)
        for module_index in range(15):
            module_offset = course_index * 15 + module_index
            for lesson_index in range(4):
                completed_at = course_started + timedelta(days=module_index * 20 + lesson_index * 2)
                yield (
                    progress_id,
                    BASE["user"] + student_index,
                    BASE["lesson"] + module_offset * 6 + lesson_index,
                    True,
                    completed_at,
                )
                progress_id += 1


def iter_attempt_blueprint(now: datetime) -> Iterator[tuple[int, int, int, int, datetime, datetime | None, int]]:
    rng = random.Random(42)
    attempt_id = BASE["attempt"]
    for student_index in range(5_000):
        user_id = BASE["user"] + student_index
        course_index = student_index % 20
        ability = 0.32 + (student_index % 100) / 190
        course_started = now - timedelta(days=365 - student_index % 30)
        sequence = 0
        for course_test_index in range(30):
            test_offset = course_index * 30 + course_test_index
            repeats = 4 if course_test_index < 10 else 3
            for repeat in range(repeats):
                started_at = course_started + timedelta(
                    days=course_test_index * 10 + repeat,
                    minutes=student_index % 120,
                )
                unfinished = (attempt_id - BASE["attempt"]) % 50 == 0
                finished_at = None if unfinished else started_at + timedelta(minutes=8 + sequence % 35)
                probability = min(max(ability + repeat * 0.07 - (course_test_index % 15) * 0.006, 0.08), 0.96)
                score = sum(1 for _ in range(4) if rng.random() < probability)
                yield attempt_id, user_id, test_offset, repeat, started_at, finished_at, score
                attempt_id += 1
                sequence += 1


def attempt_rows(now: datetime) -> Iterator[tuple]:
    for attempt_id, user_id, test_offset, _, started_at, finished_at, score in iter_attempt_blueprint(now):
        yield attempt_id, user_id, BASE["test"] + test_offset, started_at, finished_at, float(score), 4.0


def answer_rows(now: datetime) -> Iterator[tuple]:
    answer_id = BASE["answer"]
    for attempt_id, _, test_offset, _, started_at, _, score in iter_attempt_blueprint(now):
        for question_index in range(4):
            question_offset = test_offset * 4 + question_index
            correct = question_index < score
            selected_option_id = BASE["option"] + question_offset * 4 + (0 if correct else 1)
            yield (
                answer_id,
                attempt_id,
                BASE["question"] + question_offset,
                selected_option_id,
                None,
                correct,
                1.0 if correct else 0.0,
                started_at + timedelta(minutes=question_index + 1),
            )
            answer_id += 1


def selection_rows() -> Iterator[tuple]:
    answer_id = BASE["answer"]
    for _, _, test_offset, _, _, _, score in iter_attempt_blueprint(datetime.now(timezone.utc)):
        for question_index in range(4):
            question_offset = test_offset * 4 + question_index
            correct = question_index < score
            option_id = BASE["option"] + question_offset * 4 + (0 if correct else 1)
            yield answer_id, option_id
            answer_id += 1


def event_rows(now: datetime) -> Iterator[tuple]:
    event_id = BASE["event"]
    for attempt_id, user_id, test_offset, _, _, finished_at, score in iter_attempt_blueprint(now):
        occurred_at = finished_at or now
        course_index = test_offset // 30
        module_offset = test_offset // 2
        yield (
            event_id,
            "test.attempt.completed" if finished_at else "test.attempt.started",
            user_id,
            BASE["course"] + course_index,
            BASE["module"] + module_offset,
            "test_attempt",
            attempt_id,
            json.dumps({"score": score, "max_score": 4}),
            occurred_at,
            occurred_at,
            occurred_at,
        )
        event_id += 1

    for student_index in range(5_000):
        user_id = BASE["user"] + student_index
        course_index = student_index % 20
        for module_index in range(15):
            module_offset = course_index * 15 + module_index
            for lesson_index in range(4):
                occurred_at = now - timedelta(days=300 - module_index * 15 - lesson_index)
                yield (
                    event_id,
                    "lesson.completed",
                    user_id,
                    BASE["course"] + course_index,
                    BASE["module"] + module_offset,
                    "lesson",
                    BASE["lesson"] + module_offset * 6 + lesson_index,
                    None,
                    occurred_at,
                    occurred_at,
                    occurred_at,
                )
                event_id += 1

    remaining = PROFILE["events"] - 800_000
    for offset in range(remaining):
        answer_id = BASE["answer"] + offset
        attempt_offset = offset // 4
        student_index = attempt_offset // 100
        course_index = student_index % 20
        test_in_course = (attempt_offset % 100) // 4
        module_index = min(test_in_course // 2, 14)
        occurred_at = now - timedelta(days=offset % 300, seconds=offset % 86_400)
        yield (
            event_id,
            "test.answer.saved",
            BASE["user"] + student_index,
            BASE["course"] + course_index,
            BASE["module"] + course_index * 15 + module_index,
            "user_answer",
            answer_id,
            None,
            occurred_at,
            occurred_at,
            occurred_at,
        )
        event_id += 1


def sync_sequences(connection: psycopg.Connection) -> None:
    tables = (
        "users", "courses", "course_enrollments", "modules", "lessons", "lesson_progress",
        "tasks", "tests", "questions", "answer_options", "recommendations", "test_attempts",
        "user_answers", "learning_events",
    )
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}), true)"
            )
    connection.commit()


def generate(replace: bool) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    password_hash = hash_password("loadpass")
    with psycopg.connect(database_dsn()) as connection:
        if replace:
            remove_generated_data(connection)
        ensure_target_is_empty(connection)

        jobs: tuple[tuple[str, tuple[str, ...], Callable[[], Iterable[tuple]], int], ...] = (
            ("users", ("id", "username", "password_hash", "email", "first_name", "last_name", "role", "university", "group", "course_year", "created_at"), lambda: user_rows(password_hash, now), 5_000),
            ("courses", ("id", "title", "description", "author_id", "difficulty", "is_published", "is_open", "created_at", "updated_at"), lambda: course_rows(now), 20),
            ("course_enrollments", ("id", "user_id", "course_id", "assigned_by_id", "created_at"), lambda: enrollment_rows(now), 5_000),
            ("modules", ("id", "course_id", "title", "description", "order", "created_at", "updated_at"), lambda: module_rows(now), 300),
            ("lessons", ("id", "module_id", "title", "content_blocks", "video_url", "external_url", "order", "created_at", "updated_at"), lambda: lesson_rows(now), 1_800),
            ("tasks", ("id", "module_id", "title", "description", "max_score", "order", "created_at", "updated_at"), lambda: task_rows(now), 600),
            ("tests", ("id", "course_id", "module_id", "title", "description", "time_limit", "passing_score", "attempts_allowed", "is_active", "created_at", "updated_at"), lambda: test_rows(now), 600),
            ("questions", ("id", "test_id", "text", "question_type", "difficulty_level", "score", "order", "created_at", "updated_at"), lambda: question_rows(now), 2_400),
            ("answer_options", ("id", "question_id", "text", "is_correct", "created_at", "updated_at"), lambda: option_rows(now), 9_600),
            ("recommendations", ("id", "module_id", "title", "description", "resource_url", "created_at", "updated_at"), lambda: recommendation_rows(now), 1_800),
            ("lesson_progress", ("id", "user_id", "lesson_id", "is_completed", "completed_at"), lambda: lesson_progress_rows(now), 300_000),
            ("test_attempts", ("id", "user_id", "test_id", "started_at", "finished_at", "score", "max_score"), lambda: attempt_rows(now), 500_000),
            ("user_answers", ("id", "attempt_id", "question_id", "selected_option_id", "text_answer", "is_correct", "score_received", "answered_at"), lambda: answer_rows(now), 2_000_000),
            ("user_answer_option_selections", ("user_answer_id", "answer_option_id"), selection_rows, 2_000_000),
            ("learning_events", ("id", "event_type", "user_id", "course_id", "module_id", "entity_type", "entity_id", "payload", "occurred_at", "processed_at", "published_at"), lambda: event_rows(now), 2_000_000),
        )
        for table, columns, row_factory, expected in jobs:
            copy_rows(connection, table, columns, row_factory(), expected)
        sync_sequences(connection)

    print("Medium dataset generated successfully.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the PostgreSQL Medium load profile.")
    parser.add_argument("--replace", action="store_true", help="Delete the previous generated range first.")
    args = parser.parse_args()
    generate(args.replace)


if __name__ == "__main__":
    main()
