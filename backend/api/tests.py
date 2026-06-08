from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.enums import QuestionType, UserRole
from backend.models import (
    AnswerOption,
    Course,
    Module,
    Question,
    Test,
    TestAttempt,
    User,
    UserAnswer,
    UserAnswerOptionSelection,
)
from backend.schemas import (
    AnswerOptionCreate,
    AnswerOptionRead,
    AnswerOptionUpdate,
    AttemptResultRead,
    MessageRead,
    PublicQuestionRead,
    QuestionCreate,
    QuestionRead,
    QuestionUpdate,
    TestAnalyticsRead,
    TestAttemptRead,
    TestCreate,
    TestRead,
    TestUpdate,
    UnfinishedAttemptRead,
    UserAnswerCreate,
    UserAnswerRead,
)
from backend.services.analytics import upsert_topic_result
from backend.services.analytics import build_test_analytics
from backend.services.course_access import ensure_course_access

router = APIRouter(tags=["tests"])


def get_test_or_404(test_id: int, db: Session) -> Test:
    test = db.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    return test


def get_question_or_404(question_id: int, db: Session) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    return question


def get_answer_option_or_404(option_id: int, db: Session) -> AnswerOption:
    option = db.get(AnswerOption, option_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer option not found.")
    return option


def get_attempt_or_404(attempt_id: int, db: Session) -> TestAttempt:
    attempt = db.scalar(
        select(TestAttempt)
        .where(TestAttempt.id == attempt_id)
        .options(
            selectinload(TestAttempt.test),
            selectinload(TestAttempt.answers).selectinload(UserAnswer.selected_option_links),
        )
    )
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test attempt not found."
        )
    return attempt


def ensure_attempt_access(attempt: TestAttempt, current_user: User) -> None:
    if attempt.user_id != current_user.id and current_user.role not in {UserRole.TEACHER, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def ensure_test_is_published(test: Test, db: Session, current_user: User) -> None:
    course = db.get(Course, test.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    ensure_course_access(db, course, current_user)


def normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def normalize_selected_option_ids(
    selected_option_id: int | None,
    selected_option_ids: list[int] | None,
) -> list[int]:
    normalized_ids: list[int] = []
    seen: set[int] = set()
    for option_id in [selected_option_id, *(selected_option_ids or [])]:
        if option_id is None or option_id in seen:
            continue
        normalized_ids.append(option_id)
        seen.add(option_id)
    return normalized_ids


def get_selected_options(question: Question, selected_option_ids: list[int]) -> list[AnswerOption]:
    option_map = {option.id: option for option in question.answer_options}
    selected_options: list[AnswerOption] = []
    for option_id in selected_option_ids:
        option = option_map.get(option_id)
        if option is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Answer option does not belong to the question.",
            )
        selected_options.append(option)
    return selected_options


def prepare_answer_input(
    question: Question,
    selected_option_id: int | None,
    selected_option_ids: list[int] | None,
    text_answer: str | None,
) -> tuple[int | None, list[int], str | None]:
    normalized_option_ids = normalize_selected_option_ids(selected_option_id, selected_option_ids)
    normalized_text_answer = text_answer.strip() if text_answer and text_answer.strip() else None

    if question.question_type == QuestionType.SINGLE_CHOICE:
        if not normalized_option_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="selected_option_id is required for single_choice questions.",
            )
        if len(normalized_option_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="single_choice questions accept exactly one selected option.",
            )
        return normalized_option_ids[0], normalized_option_ids, None

    if question.question_type == QuestionType.MULTIPLE_CHOICE:
        if not normalized_option_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="selected_option_ids is required for multiple_choice questions.",
            )
        return None, normalized_option_ids, None

    return None, [], normalized_text_answer


def score_answer(
    question: Question,
    selected_option_ids: list[int],
    text_answer: str | None,
) -> tuple[bool, float]:
    if question.question_type == QuestionType.SINGLE_CHOICE:
        option = get_selected_options(question, selected_option_ids)[0]
        return option.is_correct, question.score if option.is_correct else 0.0

    if question.question_type == QuestionType.MULTIPLE_CHOICE:
        selected_options = get_selected_options(question, selected_option_ids)
        correct_option_ids = {option.id for option in question.answer_options if option.is_correct}
        selected_option_id_set = {option.id for option in selected_options}
        if not correct_option_ids:
            is_answered = bool(selected_option_id_set)
            return is_answered, question.score if is_answered else 0.0
        is_correct = selected_option_id_set == correct_option_ids
        return is_correct, question.score if is_correct else 0.0

    correct_texts = {
        normalize_text(option.text)
        for option in question.answer_options
        if option.is_correct
    }
    normalized_answer = normalize_text(text_answer)
    if not correct_texts:
        is_answered = bool(normalized_answer)
        return is_answered, question.score if is_answered else 0.0

    is_correct = normalized_answer in correct_texts if normalized_answer else False
    return is_correct, question.score if is_correct else 0.0


@router.get("/api/tests/{test_id}/", response_model=TestRead)
def retrieve_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Test:
    test = get_test_or_404(test_id, db)
    ensure_test_is_published(test, db, current_user)
    return test


@router.get("/api/tests/{test_id}/active-attempt/", response_model=TestAttemptRead)
def get_active_test_attempt(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestAttempt:
    test = get_test_or_404(test_id, db)
    ensure_test_is_published(test, db, current_user)
    attempt = db.scalar(
        select(TestAttempt)
        .where(
            TestAttempt.user_id == current_user.id,
            TestAttempt.test_id == test_id,
            TestAttempt.finished_at.is_(None),
        )
        .order_by(TestAttempt.started_at.desc(), TestAttempt.id.desc())
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active attempt not found.")
    return attempt


@router.get("/api/tests/{test_id}/analytics/my/", response_model=TestAnalyticsRead)
def get_my_test_analytics(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestAnalyticsRead:
    test = get_test_or_404(test_id, db)
    ensure_test_is_published(test, db, current_user)
    return build_test_analytics(db, current_user.id, test_id)


@router.get("/api/test-attempts/my/unfinished/", response_model=list[UnfinishedAttemptRead])
def list_unfinished_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UnfinishedAttemptRead]:
    attempts = list(
        db.scalars(
            select(TestAttempt)
            .where(
                TestAttempt.user_id == current_user.id,
                TestAttempt.finished_at.is_(None),
            )
            .options(
                selectinload(TestAttempt.test).selectinload(Test.course),
                selectinload(TestAttempt.test).selectinload(Test.module),
                selectinload(TestAttempt.answers),
            )
            .order_by(TestAttempt.started_at.desc(), TestAttempt.id.desc())
        )
    )

    items: list[UnfinishedAttemptRead] = []
    for attempt in attempts:
        test = attempt.test
        if test is None:
            continue

        if current_user.role not in {UserRole.TEACHER, UserRole.ADMIN}:
            course = test.course
            if course is None or not course.is_published:
                continue

        total_questions = len(
            list(db.scalars(select(Question.id).where(Question.test_id == test.id)))
        )
        last_activity_candidates = [attempt.started_at] + [
            answer.answered_at for answer in attempt.answers if answer.answered_at is not None
        ]
        last_activity_at = max(last_activity_candidates)
        items.append(
            UnfinishedAttemptRead(
                attempt_id=attempt.id,
                test_id=test.id,
                test_title=test.title,
                course_id=test.course_id,
                course_title=test.course.title if test.course else "Курс",
                module_id=test.module_id,
                module_title=test.module.title if test.module else None,
                started_at=attempt.started_at,
                last_activity_at=last_activity_at,
                answered_questions=len(attempt.answers),
                total_questions=total_questions,
                time_limit=test.time_limit,
            )
        )

    return items


@router.get("/api/tests/{test_id}/questions/", response_model=list[PublicQuestionRead])
def list_test_questions(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Question]:
    test = get_test_or_404(test_id, db)
    ensure_test_is_published(test, db, current_user)
    return list(
        db.scalars(
            select(Question)
            .where(Question.test_id == test.id)
            .options(selectinload(Question.answer_options))
            .order_by(Question.order, Question.id)
        )
    )


@router.post("/api/tests/{test_id}/start/", response_model=TestAttemptRead, status_code=status.HTTP_201_CREATED)
def start_test_attempt(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestAttempt:
    test = get_test_or_404(test_id, db)
    ensure_test_is_published(test, db, current_user)
    if not test.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test is inactive.")

    existing_attempt = db.scalar(
        select(TestAttempt)
        .where(
            TestAttempt.user_id == current_user.id,
            TestAttempt.test_id == test_id,
            TestAttempt.finished_at.is_(None),
        )
        .order_by(TestAttempt.started_at.desc(), TestAttempt.id.desc())
    )
    if existing_attempt is not None:
        return existing_attempt

    total_attempts = len(
        list(
            db.scalars(
                select(TestAttempt.id).where(
                    TestAttempt.user_id == current_user.id,
                    TestAttempt.test_id == test_id,
                )
            )
        )
    )

    if total_attempts >= test.attempts_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No attempts left for this test.",
        )

    max_score = sum(
        db.scalars(select(Question.score).where(Question.test_id == test_id)).all()
    )
    attempt = TestAttempt(user_id=current_user.id, test_id=test_id, max_score=max_score)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.post("/api/test-attempts/{attempt_id}/answers/", response_model=UserAnswerRead)
def submit_answer(
    attempt_id: int,
    payload: UserAnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAnswer:
    attempt = get_attempt_or_404(attempt_id, db)
    ensure_attempt_access(attempt, current_user)
    if attempt.finished_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempt is already finished.",
        )

    question = db.scalar(
        select(Question)
        .where(Question.id == payload.question_id, Question.test_id == attempt.test_id)
        .options(selectinload(Question.answer_options))
    )
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question does not belong to the test.",
        )

    user_answer = db.scalar(
        select(UserAnswer)
        .where(
            UserAnswer.attempt_id == attempt_id,
            UserAnswer.question_id == payload.question_id,
        )
        .options(selectinload(UserAnswer.selected_option_links))
    )
    if user_answer is None:
        user_answer = UserAnswer(
            attempt_id=attempt_id,
            question_id=payload.question_id,
        )
        db.add(user_answer)

    selected_option_id, selected_option_ids, text_answer = prepare_answer_input(
        question=question,
        selected_option_id=payload.selected_option_id,
        selected_option_ids=payload.selected_option_ids,
        text_answer=payload.text_answer,
    )
    is_correct, score_received = score_answer(
        question=question,
        selected_option_ids=selected_option_ids,
        text_answer=text_answer,
    )

    user_answer.selected_option_id = selected_option_id
    user_answer.text_answer = text_answer
    user_answer.is_correct = is_correct
    user_answer.score_received = score_received
    user_answer.answered_at = datetime.now(timezone.utc)
    user_answer.selected_option_links.clear()
    for option in get_selected_options(question, selected_option_ids):
        user_answer.selected_option_links.append(
            UserAnswerOptionSelection(answer_option_id=option.id)
        )

    db.commit()
    return db.scalar(
        select(UserAnswer)
        .where(UserAnswer.id == user_answer.id)
        .options(selectinload(UserAnswer.selected_option_links))
    )


@router.post("/api/test-attempts/{attempt_id}/finish/", response_model=TestAttemptRead)
def finish_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestAttempt:
    attempt = get_attempt_or_404(attempt_id, db)
    ensure_attempt_access(attempt, current_user)
    if attempt.finished_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempt is already finished.",
        )

    questions = list(db.scalars(select(Question).where(Question.test_id == attempt.test_id)))
    max_score = sum(question.score for question in questions)
    answers = list(db.scalars(select(UserAnswer).where(UserAnswer.attempt_id == attempt_id)))
    score = sum(answer.score_received for answer in answers)
    attempt.score = score
    attempt.max_score = max_score
    attempt.finished_at = datetime.now(timezone.utc)
    if attempt.test.module_id is not None:
        upsert_topic_result(db, attempt.user_id, attempt.test.module_id)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/api/test-attempts/{attempt_id}/result/", response_model=AttemptResultRead)
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttemptResultRead:
    attempt = get_attempt_or_404(attempt_id, db)
    ensure_attempt_access(attempt, current_user)
    answers = list(
        db.scalars(
            select(UserAnswer)
            .where(UserAnswer.attempt_id == attempt_id)
            .options(selectinload(UserAnswer.selected_option_links))
            .order_by(UserAnswer.id)
        )
    )
    return AttemptResultRead(
        attempt=TestAttemptRead.model_validate(attempt),
        answers=[UserAnswerRead.model_validate(answer) for answer in answers],
    )


@router.post("/api/tests/", response_model=TestRead, status_code=status.HTTP_201_CREATED)
def create_test(
    payload: TestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Test:
    _ = current_user
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found.")
    if payload.module_id is not None and db.get(Module, payload.module_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")
    test = Test(**payload.model_dump())
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.patch("/api/tests/{test_id}/", response_model=TestRead)
def update_test(
    test_id: int,
    payload: TestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Test:
    _ = current_user
    test = get_test_or_404(test_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "course_id" in data and db.get(Course, data["course_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found.")
    if "module_id" in data and data["module_id"] is not None and db.get(Module, data["module_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")
    for field, value in data.items():
        setattr(test, field, value)
    db.commit()
    db.refresh(test)
    return test


@router.delete("/api/tests/{test_id}/", response_model=MessageRead)
def delete_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    _ = current_user
    test = get_test_or_404(test_id, db)
    db.delete(test)
    db.commit()
    return MessageRead(message="Test deleted.")


@router.post("/api/questions/", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Question:
    _ = current_user
    if db.get(Test, payload.test_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test not found.")
    question = Question(**payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return db.scalar(
        select(Question)
        .where(Question.id == question.id)
        .options(selectinload(Question.answer_options))
    )


@router.patch("/api/questions/{question_id}/", response_model=QuestionRead)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Question:
    _ = current_user
    question = get_question_or_404(question_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "test_id" in data and db.get(Test, data["test_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test not found.")
    for field, value in data.items():
        setattr(question, field, value)
    db.commit()
    return db.scalar(
        select(Question)
        .where(Question.id == question.id)
        .options(selectinload(Question.answer_options))
    )


@router.delete("/api/questions/{question_id}/", response_model=MessageRead)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    _ = current_user
    question = get_question_or_404(question_id, db)
    db.delete(question)
    db.commit()
    return MessageRead(message="Question deleted.")


@router.post("/api/answer-options/", response_model=AnswerOptionRead, status_code=status.HTTP_201_CREATED)
def create_answer_option(
    payload: AnswerOptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> AnswerOption:
    _ = current_user
    if db.get(Question, payload.question_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question not found.")
    answer_option = AnswerOption(**payload.model_dump())
    db.add(answer_option)
    db.commit()
    db.refresh(answer_option)
    return answer_option


@router.patch("/api/answer-options/{option_id}/", response_model=AnswerOptionRead)
def update_answer_option(
    option_id: int,
    payload: AnswerOptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> AnswerOption:
    _ = current_user
    answer_option = get_answer_option_or_404(option_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "question_id" in data and db.get(Question, data["question_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question not found.")
    for field, value in data.items():
        setattr(answer_option, field, value)
    db.commit()
    db.refresh(answer_option)
    return answer_option


@router.delete("/api/answer-options/{option_id}/", response_model=MessageRead)
def delete_answer_option(
    option_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    _ = current_user
    answer_option = get_answer_option_or_404(option_id, db)
    db.delete(answer_option)
    db.commit()
    return MessageRead(message="Answer option deleted.")
