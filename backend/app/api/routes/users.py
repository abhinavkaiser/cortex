from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.lesson import Lesson, UserLessonProgress
from app.models.track import Track
from app.models.user import User
from app.schemas.user import CompleteLessonRequest, LessonProgressOut, OnboardingRequest, TrackOut, UserProgressOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/onboarding")
def complete_onboarding(body: OnboardingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Assigns the user's track. Common Core is unaffected by this -- a
    user can be assigned a track immediately and still see Common Core
    content until common_core_completed_at is set (see /progress)."""
    track = db.query(Track).filter(Track.slug == body.track_slug).first()
    if not track:
        raise HTTPException(404, f"Unknown track: {body.track_slug}")
    user.track_id = track.id
    db.commit()
    return {"ok": True, "track": TrackOut.model_validate(track)}


@router.post("/lessons/complete")
def complete_lesson(body: CompleteLessonRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.get(Lesson, body.lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    already = (
        db.query(UserLessonProgress)
        .filter(UserLessonProgress.user_id == user.id, UserLessonProgress.lesson_id == lesson.id)
        .first()
    )
    if not already:
        db.add(UserLessonProgress(user_id=user.id, lesson_id=lesson.id))

    # If this was the last Common Core lesson, flip the gate that unlocks
    # the track curriculum in the frontend.
    if lesson.track_id is None and user.common_core_completed_at is None:
        common_core_total = db.query(Lesson).filter(Lesson.track_id.is_(None)).count()
        completed_ids = {
            p.lesson_id
            for p in db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user.id)
        }
        completed_ids.add(lesson.id)
        common_core_completed = db.query(Lesson).filter(Lesson.track_id.is_(None), Lesson.id.in_(completed_ids)).count()
        if common_core_completed >= common_core_total:
            user.common_core_completed_at = datetime.utcnow()

    db.commit()
    return {"ok": True, "common_core_completed": user.common_core_completed_at is not None}


@router.get("/{user_id}/progress", response_model=UserProgressOut)
def get_progress(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.id != user_id and user.role.value != "admin":
        raise HTTPException(403, "Cannot view another user's progress")

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    progress_rows = db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user_id).all()
    completed_lesson_ids = {p.lesson_id for p in progress_rows}

    common_core_lessons = db.query(Lesson).filter(Lesson.track_id.is_(None)).all()
    track_lessons = db.query(Lesson).filter(Lesson.track_id == target.track_id).all() if target.track_id else []

    lessons_by_id = {l.id: l for l in common_core_lessons + track_lessons}

    return UserProgressOut(
        user_id=target.id,
        email=target.email,
        track=TrackOut.model_validate(target.track) if target.track else None,
        common_core_completed=target.common_core_completed_at is not None,
        common_core_completed_at=target.common_core_completed_at,
        common_core_lessons_total=len(common_core_lessons),
        common_core_lessons_completed=sum(1 for l in common_core_lessons if l.id in completed_lesson_ids),
        track_lessons_total=len(track_lessons),
        track_lessons_completed=sum(1 for l in track_lessons if l.id in completed_lesson_ids),
        completed_lessons=[
            LessonProgressOut(lesson_id=p.lesson_id, lesson_title=lessons_by_id[p.lesson_id].title, completed_at=p.completed_at)
            for p in progress_rows
            if p.lesson_id in lessons_by_id
        ],
    )
