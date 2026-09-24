from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Enrollment
from app.models.lesson import Lesson, UserLessonProgress
from app.models.user import User
from app.schemas.course import UserCourseOut
from app.schemas.user import CompleteLessonRequest, UserProgressOut
from app.services.course_progress import check_and_issue_certificate, course_progress_pct

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/lessons/complete")
def complete_lesson(body: CompleteLessonRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every lesson lives under some Course's Module now (see
    scripts/migrate_tracks_to_courses.py -- even the old Common Core
    lessons got a real Module/Course of their own), so completion is a
    single, uniform path: record the progress row, then let
    check_and_issue_certificate figure out whether that just cleared the
    owning course's completion bar. There's no separate "Common Core gate"
    or "track curriculum" branch anymore -- those were removed along with
    User.track_id/common_core_completed_at."""
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
        # SessionLocal is autoflush=False (see core/db.py) -- the
        # course-completion check below runs a fresh query for completed
        # lessons, which wouldn't see the row just added above without this.
        db.flush()

    course_completed = False
    if lesson.course_id:
        course_completed = check_and_issue_certificate(db, user.id, lesson.course_id) is not None

    db.commit()
    return {"ok": True, "course_completed": course_completed}


@router.get("/{user_id}/progress", response_model=UserProgressOut)
def get_progress(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Identity/role lookup -- see UserProgressOut's docstring for why this
    is no longer a track/Common-Core progress payload."""
    if user.id != user_id and user.role.value != "admin":
        raise HTTPException(403, "Cannot view another user's progress")

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    return UserProgressOut(user_id=target.id, email=target.email, role=target.role.value)


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
