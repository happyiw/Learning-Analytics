from datetime import datetime, timezone

from backend.generate_load_dataset import COURSE_CATALOG, PROFILE, attempt_rows, event_rows


def test_medium_profile_cardinalities_are_consistent():
    assert len(COURSE_CATALOG) == PROFILE["courses"] == 20
    assert PROFILE["students"] * PROFILE["attempts_per_student"] == 500_000
    assert (
        PROFILE["students"]
        * PROFILE["attempts_per_student"]
        * PROFILE["answers_per_attempt"]
        == 2_000_000
    )


def test_attempt_generator_produces_expected_student_boundary():
    rows = attempt_rows(datetime(2026, 1, 1, tzinfo=timezone.utc))
    first = next(rows)
    for _ in range(PROFILE["attempts_per_student"] - 1):
        last_for_first_student = next(rows)
    first_for_second_student = next(rows)

    assert first[1] == last_for_first_student[1]
    assert first_for_second_student[1] == first[1] + 1
    assert first[0] + PROFILE["attempts_per_student"] == first_for_second_student[0]


def test_event_generator_has_attempt_events_first():
    rows = event_rows(datetime(2026, 1, 1, tzinfo=timezone.utc))
    first = next(rows)

    assert first[1] in {"test.attempt.started", "test.attempt.completed"}
    assert first[2] is not None
    assert first[3] is not None
    assert first[4] is not None
