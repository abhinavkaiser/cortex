from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.learning import CurriculumRefresh, CurriculumSignal, LearningUnit, PracticeAttempt
from app.models.module import Module
from app.models.user import User
from app.services.learning import attempt_result, best_attempt, public_unit, unit_status, ready
from app.services.education_curriculum import effective_unit
from app.services.education_queue import enqueue
from app.services.education_grading import practice_payload

router = APIRouter(prefix="/api/learning", tags=["learning"])


class PracticeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=64)
    answers: list[StrictInt] = Field(min_length=1, max_length=20)
    reflection: str = Field(min_length=40, max_length=5000)


def visible_lesson(db, lesson_id, user):
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson.module or not lesson.module.course:
        raise HTTPException(404, "Lesson not found")
    course = lesson.module.course
    if not course.is_published and course.instructor_id != user.id and user.role.value != "admin":
        raise HTTPException(404, "Lesson not found")
    return lesson


@router.get("/path")
def path(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    units = db.query(LearningUnit).order_by(LearningUnit.position).all()
    result = []
    for unit in units:
        lesson = db.get(Lesson, unit.lesson_id)
        if not lesson or not lesson.module or not lesson.module.course.is_published:
            continue
        current = effective_unit(db, unit)
        attempt = best_attempt(db, user.id, current)
        result.append({"lesson_id": lesson.id, "title": lesson.title, "stage": unit.stage,
                       "objective": unit.objective, "minutes": lesson.estimated_minutes,
                       "course_slug": lesson.module.course.slug,
                       "status": unit_status(unit, lesson),
                       "assessed": ready(db, user.id, unit),
                       "practice_score": attempt.score if attempt else None})
    return result


@router.get("/lessons/{lesson_id}")
def detail(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = visible_lesson(db, lesson_id, user)
    unit = db.query(LearningUnit).filter_by(lesson_id=lesson_id).first()
    return public_unit(unit, lesson, db, user.id) if unit else None


@router.post("/lessons/{lesson_id}/practice")
def submit(lesson_id: int, body: PracticeSubmission, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = visible_lesson(db, lesson_id, user)
    unit = db.query(LearningUnit).filter_by(lesson_id=lesson_id).first()
    if not unit:
        raise HTTPException(404, "No practice published for this lesson")
    unit = effective_unit(db, unit)
    if body.version != unit.version or unit_status(unit, lesson) == "changed_since_review":
        raise HTTPException(409, "This lesson changed. Reload it before submitting practice.")
    questions = unit.exercise["questions"]
    if len(body.answers) != len(questions) or any(a < 0 or a >= len(q["choices"]) for a, q in zip(body.answers, questions)):
        raise HTTPException(422, "Select one valid answer for each task")
    if len(body.reflection.strip()) < 40:
        raise HTTPException(422, "Explain your decision in at least 40 characters")
    from app.models.education import EducationJob
    if db.query(EducationJob).filter(EducationJob.user_id == user.id, EducationJob.status.in_(['queued', 'running'])).count() >= 5:
        raise HTTPException(429, 'Five assessments are pending. Wait for feedback before submitting more work.')
    score = round(100 * sum(a == q["correct_index"] for a, q in zip(body.answers, questions)) / len(questions))
    attempt = PracticeAttempt(user_id=user.id, lesson_id=lesson_id, version=unit.version,
                              answers=body.answers, reflection=body.reflection.strip(), score=score)
    db.add(attempt)
    db.flush()
    enqueue(db,key=f'practice:{attempt.id}',kind='practice',user_id=user.id,subject_id=attempt.id,version=unit.version,
            payload=practice_payload(attempt,lesson,unit.exercise))
    db.commit()
    db.refresh(attempt)
    return attempt_result(attempt, unit, db)


@router.get("/lessons/{lesson_id}/updates")
def updates(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = visible_lesson(db, lesson_id, user)
    signals = (db.query(CurriculumSignal).filter(CurriculumSignal.published_at >= datetime.utcnow() - timedelta(days=30))
               .order_by(CurriculumSignal.published_at.desc()).limit(200).all())
    return [{"title": s.title, "url": s.url, "summary": s.summary, "source": s.source,
             "published_at": s.published_at} for s in signals if lesson.slug in s.lesson_slugs][:3]


@router.get("/lab-pack")
def lab_pack():
    """Public synthetic teaching materials; contains no learner or server data."""
    import io
    import zipfile
    from pathlib import Path
    from fastapi.responses import Response
    buffer = io.BytesIO()
    root = Path(__file__).resolve().parents[3] / "content/labs"
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.iterdir()):
            if path.suffix in {".py", ".json", ".md"}:
                archive.writestr("cortex-labs/" + path.name, path.read_bytes())
    return Response(buffer.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="cortex-learning-labs.zip"'})


@router.get("/updates/status")
def update_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    status = db.get(CurriculumRefresh, 1)
    return status.result if status else None
