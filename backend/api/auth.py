from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.core.security import create_access_token, hash_password, verify_password
from backend.deps import get_current_user, get_db
from backend.enums import UserRole
from backend.models import User
from backend.schemas import TokenRead, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    conditions = [User.username == payload.username]
    if payload.email:
        conditions.append(User.email == payload.email)

    existing_user = db.scalar(select(User).where(or_(*conditions)))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exists.",
        )

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=UserRole.STUDENT,
        university=payload.university,
        group=payload.group,
        course_year=payload.course_year,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login/", response_model=TokenRead)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> TokenRead:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    return TokenRead(access_token=create_access_token(str(user.id)))


@router.get("/me/", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
