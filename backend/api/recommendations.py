from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.models import Course, Module, Recommendation, User
from backend.schemas import (
    MessageRead,
    PersonalRecommendationRead,
    RecommendationCreate,
    RecommendationRead,
    RecommendationUpdate,
)
from backend.services.analytics import build_personal_recommendations
from backend.services.course_access import ensure_course_access

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def get_recommendation_or_404(recommendation_id: int, db: Session) -> Recommendation:
    recommendation = db.get(Recommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    return recommendation


@router.get("/my/", response_model=list[PersonalRecommendationRead])
def get_my_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PersonalRecommendationRead]:
    return build_personal_recommendations(db, current_user.id)


@router.get("/", response_model=list[RecommendationRead])
def list_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> list[Recommendation]:
    _ = current_user
    return list(db.scalars(select(Recommendation).order_by(Recommendation.id)))


@router.post("/", response_model=RecommendationRead, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    payload: RecommendationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Recommendation:
    _ = current_user
    if db.get(Module, payload.module_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")
    recommendation = Recommendation(**payload.model_dump())
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.get("/{recommendation_id}/", response_model=RecommendationRead)
def retrieve_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Recommendation:
    _ = current_user
    return get_recommendation_or_404(recommendation_id, db)


@router.patch("/{recommendation_id}/", response_model=RecommendationRead)
def update_recommendation(
    recommendation_id: int,
    payload: RecommendationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Recommendation:
    _ = current_user
    recommendation = get_recommendation_or_404(recommendation_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "module_id" in data and db.get(Module, data["module_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")
    for field, value in data.items():
        setattr(recommendation, field, value)
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.delete("/{recommendation_id}/", response_model=MessageRead)
def delete_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    _ = current_user
    recommendation = get_recommendation_or_404(recommendation_id, db)
    db.delete(recommendation)
    db.commit()
    return MessageRead(message="Recommendation deleted.")
