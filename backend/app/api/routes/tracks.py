"""Open-catalog browsing: list the three tracks, and browse any one track's
full curriculum regardless of which track (if any) the current user is
assigned to. Deliberately separate from /api/users/{id}/progress, which is
scoped to "my own track, gated behind Common Core" -- this route powers a
plain course catalog instead: pick any course, see its curriculum, open any
lesson. Completion checkmarks still reflect the real current user, but
nothing here is gated."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.lesson import Lesson, UserLessonProgress
from app.models.module import Module
from app.models.track import Track
from app.models.user import User
from app.schemas.user import LessonOut

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


class TrackSummary(BaseModel):
    slug: str
    name: str
    description: str
    lesson_count: int


@router.get("", response_model=list[TrackSummary])
def list_tracks(db: Session = Depends(get_db)):
    tracks = db.query(Track).order_by(Track.id).all()
    return [
        TrackSummary(slug=t.slug, name=t.name, description=t.description, lesson_count=len(t.lessons))
        for t in tracks
    ]


class ModuleOut(BaseModel):
    id: int
    title: str
    objective: str
    lessons: list[LessonOut]


class CurriculumOut(BaseModel):
    track: TrackSummary
    modules: list[ModuleOut]
    ungrouped_lessons: list[LessonOut]


@router.get("/{slug}/curriculum", response_model=CurriculumOut)
def get_curriculum(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.slug == slug).first()
    if not track:
        raise HTTPException(404, "No such track")

    completed_ids = {
        p.lesson_id for p in db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user.id).all()
    }

    def to_lesson_out(l: Lesson) -> LessonOut:
        return LessonOut(
            id=l.id,
            title=l.title,
            estimated_minutes=l.estimated_minutes,
            order_index=l.order_index,
            completed=l.id in completed_ids,
            module_id=l.module_id,
            module_title=l.module.title if l.module else None,
        )

    modules = db.query(Module).filter(Module.track_id == track.id).order_by(Module.order_index).all()
    ungrouped = (
        db.query(Lesson)
        .filter(Lesson.track_id == track.id, Lesson.module_id.is_(None))
        .order_by(Lesson.order_index)
        .all()
    )

    return CurriculumOut(
        track=TrackSummary(slug=track.slug, name=track.name, description=track.description, lesson_count=len(track.lessons)),
        modules=[ModuleOut(id=m.id, title=m.title, objective=m.objective, lessons=[to_lesson_out(l) for l in m.lessons]) for m in modules],
        ungrouped_lessons=[to_lesson_out(l) for l in ungrouped],
    )
