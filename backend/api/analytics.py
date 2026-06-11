from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.models import Course, Module, Question, Test, User
from backend.schemas import (
    AnalyticsDynamicsPointRead,
    PersonalAnalyticsSnapshotRead,
    ProgressRead,
    QuestionAnalyticsRead,
    TopicResultAggregateRead,
    TopicResultRead,
    UserAnalyticsSummaryRead,
)
from backend.services.analytics import (
    build_best_topics,
    build_dynamics,
    build_hardest_questions_for_module,
    build_hardest_questions_for_test,
    build_module_question_analytics,
    build_most_missed_questions_for_test,
    build_personal_analytics_snapshot,
    build_progress,
    build_question_snapshot,
    build_summary,
    build_test_question_analytics,
    build_topic_result_aggregates,
    build_weak_topics,
    compute_topic_results,
)

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/progress/my/", response_model=ProgressRead)
def get_my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressRead:
    return build_progress(db, current_user.id)


@router.get("/topic-results/my/", response_model=list[TopicResultRead])
def get_my_topic_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicResultRead]:
    return compute_topic_results(db, current_user.id)


@router.get("/analytics/my/snapshot/", response_model=PersonalAnalyticsSnapshotRead)
def get_my_analytics_snapshot(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PersonalAnalyticsSnapshotRead:
    return build_personal_analytics_snapshot(db, current_user.id)


@router.get("/analytics/my/summary/", response_model=UserAnalyticsSummaryRead)
def get_my_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAnalyticsSummaryRead:
    return build_summary(db, current_user.id)


@router.get("/analytics/my/weak-topics/", response_model=list[TopicResultRead])
def get_my_weak_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicResultRead]:
    return build_weak_topics(db, current_user.id)


@router.get("/analytics/my/best-topics/", response_model=list[TopicResultRead])
def get_my_best_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicResultRead]:
    return build_best_topics(db, current_user.id)


@router.get("/analytics/my/dynamics/", response_model=list[AnalyticsDynamicsPointRead])
def get_my_dynamics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnalyticsDynamicsPointRead]:
    return build_dynamics(db, current_user.id)


@router.get("/analytics/groups/{group_id}/topic-results/", response_model=list[TopicResultAggregateRead])
def get_group_topic_results(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[TopicResultAggregateRead]:
    _ = current_user
    students = list(result for result in db.query(User).filter(User.group == group_id))
    if not students:
        raise HTTPException(status_code=404, detail="Group not found.")
    return build_topic_result_aggregates(db, group_id=group_id)


@router.get("/analytics/courses/{course_id}/topic-results/", response_model=list[TopicResultAggregateRead])
def get_course_topic_result_analytics(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[TopicResultAggregateRead]:
    _ = current_user
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    return build_topic_result_aggregates(db, course_id=course_id)


@router.get("/analytics/modules/{module_id}/topic-results/", response_model=list[TopicResultAggregateRead])
def get_module_topic_result_analytics(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[TopicResultAggregateRead]:
    _ = current_user
    if db.get(Module, module_id) is None:
        raise HTTPException(status_code=404, detail="Module not found.")
    return build_topic_result_aggregates(db, module_id=module_id)


@router.get("/analytics/questions/{question_id}/", response_model=QuestionAnalyticsRead)
def get_question_analytics_snapshot(
    question_id: int,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> QuestionAnalyticsRead:
    _ = current_user
    if db.get(Question, question_id) is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    return build_question_snapshot(db, question_id, user_id=user_id)


@router.get("/analytics/tests/{test_id}/questions/", response_model=list[QuestionAnalyticsRead])
def get_test_question_analytics(
    test_id: int,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[QuestionAnalyticsRead]:
    _ = current_user
    if db.get(Test, test_id) is None:
        raise HTTPException(status_code=404, detail="Test not found.")
    return build_test_question_analytics(db, test_id, user_id=user_id)


@router.get("/analytics/tests/{test_id}/questions/hardest/", response_model=list[QuestionAnalyticsRead])
def get_hardest_questions_by_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[QuestionAnalyticsRead]:
    _ = current_user
    if db.get(Test, test_id) is None:
        raise HTTPException(status_code=404, detail="Test not found.")
    return build_hardest_questions_for_test(db, test_id)


@router.get("/analytics/tests/{test_id}/questions/most-missed/", response_model=list[QuestionAnalyticsRead])
def get_most_missed_questions_by_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[QuestionAnalyticsRead]:
    _ = current_user
    if db.get(Test, test_id) is None:
        raise HTTPException(status_code=404, detail="Test not found.")
    return build_most_missed_questions_for_test(db, test_id)


@router.get("/analytics/modules/{module_id}/questions/", response_model=list[QuestionAnalyticsRead])
def get_module_question_analytics(
    module_id: int,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[QuestionAnalyticsRead]:
    _ = current_user
    if db.get(Module, module_id) is None:
        raise HTTPException(status_code=404, detail="Module not found.")
    return build_module_question_analytics(db, module_id, user_id=user_id)


@router.get("/analytics/modules/{module_id}/questions/hardest/", response_model=list[QuestionAnalyticsRead])
def get_hardest_questions_by_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[QuestionAnalyticsRead]:
    _ = current_user
    if db.get(Module, module_id) is None:
        raise HTTPException(status_code=404, detail="Module not found.")
    return build_hardest_questions_for_module(db, module_id)
