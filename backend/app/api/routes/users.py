from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Enrollment
from app.models.lesson import Lesson, UserLessonProgress
from app.models.module import Module
from app.models.track import Track
from app.models.user import User
from app.schemas.course import UserCourseOut
from app.schemas.user import CompleteLessonRequest, LessonOut, LessonProgressOut, OnboardingRequest, TrackOut, UserProgressOut
from app.services.course_progress import check_and_issue_certificate, course_progress_pct

router = APIRouter(prefix="/api/users", tags=["users"])


def _common_core_lessons_query(db: Session):
    """Common Core = track_id IS NULL, historically enough on its own to
    identify it. Now that the course system exists, a course lesson ALSO
    has track_id NULL (it hangs off a Module via module_id, never a Track
    -- see Module/Lesson docstrings), so track_id IS NULL alone would
    double-count every course lesson as Common Core too. Excluding any
    lesson whose module belongs to a Course closes that gap."""
    return (
        db.query(Lesson)
        .outerjoin(Module, Lesson.module_id == Module.id)
        .filter(Lesson.track_id.is_(None))
        .filter(or_(Lesson.module_id.is_(None), Module.course_id.is_(None)))
    )


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
        # SessionLocal is autoflush=False (see core/db.py) -- the course
        # -completion check below runs a fresh query for completed lessons,
        # which wouldn't see the row just added above without this.
        db.flush()

    # If this was the last Common Core lesson, flip the gate that unlocks
    # the track curriculum in the frontend. lesson.course_id is None for a
    # genuine Common Core lesson (see _common_core_lessons_query above for
    # why track_id IS NULL alone isn't enough anymore).
    if lesson.track_id is None and lesson.course_id is None and user.common_core_completed_at is None:
        common_core_total = _common_core_lessons_query(db).count()
        completed_ids = {
            p.lesson_id
            for p in db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user.id)
        }
        completed_ids.add(lesson.id)
        common_core_completed = _common_core_lessons_query(db).filter(Lesson.id.in_(completed_ids)).count()
        if common_core_completed >= common_core_total:
            user.common_core_completed_at = datetime.utcnow()

    # Course completion is a separate gate from Common Core, and orthogonal
    # to it -- a course lesson has track_id None (it's not a Track lesson)
    # so it never touches the Common Core branch above. course_id is
    # derived via lesson.module.course_id (see Lesson.course_id).
    course_completed = False
    if lesson.course_id:
        course_completed = check_and_issue_certificate(db, user.id, lesson.course_id) is not None

    db.commit()
    return {
        "ok": True,
        "common_core_completed": user.common_core_completed_at is not None,
        "course_completed": course_completed,
    }


@router.get("/{user_id}/progress", response_model=UserProgressOut)
def get_progress(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.id != user_id and user.role.value != "admin":
        raise HTTPException(403, "Cannot view another user's progress")

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    progress_rows = db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user_id).all()
    completed_lesson_ids = {p.lesson_id for p in progress_rows}

    common_core_lessons = _common_core_lessons_query(db).order_by(Lesson.order_index).all()
    track_lessons = (
        db.query(Lesson)
        .filter(Lesson.track_id == target.track_id)
        .outerjoin(Module, Lesson.module_id == Module.id)
        .order_by(Module.order_index, Lesson.order_index)
        .all()
        if target.track_id
        else []
    )

    lessons_by_id = {l.id: l for l in common_core_lessons + track_lessons}

    def to_lesson_out(l: Lesson) -> LessonOut:
        return LessonOut(
            id=l.id,
            title=l.title,
            estimated_minutes=l.estimated_minutes,
            order_index=l.order_index,
            completed=l.id in completed_lesson_ids,
            module_id=l.module_id,
            module_title=l.module.title if l.module else None,
        )

    return UserProgressOut(
        user_id=target.id,
        email=target.email,
        role=target.role.value,
        track=TrackOut.model_validate(target.track) if target.track else None,
        common_core_completed=target.common_core_completed_at is not None,
        common_core_completed_at=target.common_core_completed_at,
        common_core_lessons_total=len(common_core_lessons),
        common_core_lessons_completed=sum(1 for l in common_core_lessons if l.id in completed_lesson_ids),
        track_lessons_total=len(track_lessons),
        track_lessons_completed=sum(1 for l in track_lessons if l.id in completed_lesson_ids),
        common_core_lessons=[to_lesson_out(l) for l in common_core_lessons],
        track_lessons=[to_lesson_out(l) for l in track_lessons],
        completed_lessons=[
            LessonProgressOut(lesson_id=p.lesson_id, lesson_title=lessons_by_id[p.lesson_id].title, completed_at=p.completed_at)
            for p in progress_rows
            if p.lesson_id in lessons_by_id
        ],
    )


@router.get("/{user_id}/courses", response_model=list[UserCourseOut])
def get_user_courses(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every course this user is enrolled in, plus % complete each -- the
    learner course dashboard. Same self-or-admin access check as
    /progress above -- your own enrollments are private, not something any
    other learner (or even the course's instructor, via this endpoint --
    they'd use GET /api/courses/{id}/roster instead) can browse."""
    if user.id != user_id and user.role.value != "admin":
        raise HTTPException(403, "Cannot view another user's courses")

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    enrollments = db.query(Enrollment).filter(Enrollment.user_id == user_id).order_by(Enrollment.enrolled_at.desc()).all()
    return [
        UserCourseOut(
            course_id=e.course_id,
            slug=e.course.slug,
            title=e.course.title,
            category=e.course.category,
            progress_pct=course_progress_pct(db, user_id, e.course_id),
            enrolled_at=e.enrolled_at,
            due_at=e.due_at,
            completed_at=e.completed_at,
        )
        for e in enrollments
    ]
