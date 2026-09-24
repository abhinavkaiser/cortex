from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.lesson import Lesson, UserLessonProgress
from app.models.user import User

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


class LessonDetailOut(BaseModel):
    id: int
    title: str
    content_markdown: str
    content_blocks: list[dict[str, Any]]
    estimated_minutes: int
    completed: bool
    module_title: str | None


@router.get("/{lesson_id}", response_model=LessonDetailOut)
def get_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Full lesson content -- deliberately a separate endpoint from
    /users/{id}/progress, which only returns list-view metadata (id, title,
    completed). Fetching every lesson's full body on every progress check
    would bloat that response for no reason; this loads on demand when a
    user actually opens one lesson to read it."""
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    completed = (
        db.query(UserLessonProgress)
        .filter(UserLessonProgress.user_id == user.id, UserLessonProgress.lesson_id == lesson_id)
        .first()
        is not None
    )

    return LessonDetailOut(
        id=lesson.id,
        title=lesson.title,
        content_markdown=lesson.content_markdown,
        content_blocks=lesson.content_blocks or [],
        estimated_minutes=lesson.estimated_minutes,
        completed=completed,
        module_title=lesson.module.title if lesson.module else None,
    )
