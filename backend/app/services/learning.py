"""Deterministic practice feedback. Reflection is saved, never called AI-graded."""
import hashlib
import json
from datetime import date

from sqlalchemy.orm import Session

from app.models.learning import LearningUnit, PracticeAttempt


def content_hash(lesson):
    return hashlib.sha256(json.dumps([lesson.title, lesson.content_markdown, lesson.content_blocks], sort_keys=True).encode()).hexdigest()


def best_attempt(db: Session, user_id: int, unit: LearningUnit):
    from app.services.education_curriculum import effective_unit
    unit = effective_unit(db, unit)
    return (db.query(PracticeAttempt)
            .filter_by(user_id=user_id, lesson_id=unit.lesson_id, version=unit.version)
            .order_by(PracticeAttempt.score.desc(), PracticeAttempt.id.desc()).first())


def ready(db: Session, user_id: int, unit: LearningUnit):
    from app.services.education_curriculum import effective_unit
    from app.models.education import EducationJob
    unit = effective_unit(db, unit)
    return (db.query(PracticeAttempt).join(EducationJob, (EducationJob.subject_id == PracticeAttempt.id) & (EducationJob.kind == 'practice'))
            .filter(PracticeAttempt.user_id == user_id, PracticeAttempt.lesson_id == unit.lesson_id,
                    PracticeAttempt.version == unit.version, PracticeAttempt.score == 100,
                    EducationJob.user_id == user_id, EducationJob.version == unit.version,
                    EducationJob.status == 'graded', EducationJob.passed.is_(True)).first()) is not None


def unit_status(unit, lesson):
    if content_hash(lesson) != unit.content_hash:
        return "changed_since_review"
    return "review_due" if date.today() > unit.review_due else "reviewed"


def public_unit(unit, lesson, db, user_id):
    from app.services.education_curriculum import effective_unit
    unit = effective_unit(db, unit)
    attempt = best_attempt(db, user_id, unit)
    latest = (db.query(PracticeAttempt).filter_by(user_id=user_id, lesson_id=lesson.id, version=unit.version)
              .order_by(PracticeAttempt.id.desc()).first())
    # Do not send answer keys or reference solutions before a submission.
    exercise = unit.exercise
    return {
        "version": unit.version, "objective": unit.objective, "prerequisites": unit.prerequisites,
        "sources": unit.sources, "reviewed_on": unit.reviewed_on, "review_due": unit.review_due,
        "status": unit_status(unit, lesson), "stage": unit.stage,
        "exercise": {"title": exercise["title"], "scenario": exercise["scenario"],
                     "questions": [{"question": q["question"], "choices": q["choices"]} for q in exercise["questions"]],
                     "reflection_prompt": exercise["reflection_prompt"]},
        "mastered": ready(db, user_id, unit),
        "best_score": attempt.score if attempt else None,
        "latest_attempt": attempt_result(latest, unit, db) if latest else None,
    }


def attempt_result(attempt, unit, db=None):
    from app.models.education import EducationJob
    from app.services.education_queue import public_job
    job = db.query(EducationJob).filter_by(kind='practice',subject_id=attempt.id,user_id=attempt.user_id).first() if db else None
    questions = unit.exercise["questions"]
    return {"id": attempt.id, "assessment": public_job(job), "score": attempt.score, "answers": attempt.answers, "reflection": attempt.reflection,
            "submitted_at": attempt.submitted_at,
            "feedback": [{"correct": answer == q["correct_index"], "explanation": q["feedback"][answer]}
                         for answer, q in zip(attempt.answers, questions)],
            "reference": unit.exercise["reference"], "rubric": unit.exercise["rubric"],
            "practice_complete": attempt.score == 100 and bool(job and job.status == "graded" and job.passed)}
