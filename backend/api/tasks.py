from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_current_user, get_db, require_teacher_or_admin
from backend.models import Course, Module, Task, User
from backend.schemas import MessageRead, TaskAdminRead, TaskCreate, TaskRead, TaskUpdate
from backend.services.course_access import ensure_course_access

router = APIRouter(tags=["tasks"])


def get_module_or_404(module_id: int, db: Session) -> Module:
    module = db.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    return module


def get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


def ensure_module_is_public(module: Module, db: Session) -> None:
    course = db.get(Course, module.course_id)
    if course is None or not course.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")


@router.get("/api/modules/{module_id}/tasks/", response_model=list[TaskRead])
def list_module_tasks(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Task]:
    module = get_module_or_404(module_id, db)
    ensure_module_is_public(module, db)
    course = db.get(Course, module.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    ensure_course_access(db, course, current_user)
    return list(
        db.scalars(select(Task).where(Task.module_id == module_id).order_by(Task.order, Task.id))
    )


@router.get("/api/tasks/{task_id}/", response_model=TaskRead)
def retrieve_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = get_task_or_404(task_id, db)
    module = get_module_or_404(task.module_id, db)
    ensure_module_is_public(module, db)
    course = db.get(Course, module.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    ensure_course_access(db, course, current_user)
    return task


@router.post("/api/tasks/", response_model=TaskAdminRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Task:
    _ = current_user
    if db.get(Module, payload.module_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/api/tasks/{task_id}/", response_model=TaskAdminRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> Task:
    _ = current_user
    task = get_task_or_404(task_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "module_id" in data and db.get(Module, data["module_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not found.")

    for field, value in data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/api/tasks/{task_id}/", response_model=MessageRead)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
) -> MessageRead:
    _ = current_user
    task = get_task_or_404(task_id, db)
    db.delete(task)
    db.commit()
    return MessageRead(message="Task deleted.")
