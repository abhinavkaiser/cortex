"""Shared course-completion logic -- used by both the lesson-completion path
(users.py's complete_lesson) and the quiz-attempt path (quizzes.py), since
either one can be the action that clears a course's completion bar. Kept
here rather than duplicated in both route modules, and rather than living on
the Enrollment model itself, since progress % is deliberately NOT a stored
column (see models/course.py's Enrollment docstring) -- it's always computed
live from UserLessonProgress/QuizAttempt rows, so route code and this module
are the only places that need to agree on how."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.course import Certificate, Enrollment, Quiz, QuizAttempt
from app.models.lesson import Lesson, UserLessonProgress
from app.models.module import Module


def course_lesson_ids(db: Session, course_id: int) -> list[int]:
    return [
        lid
        for (lid,) in db.query(Lesson.id).join(Module, Lesson.module_id == Module.id).filter(Module.course_id == course_id).all()
    ]


def course_progress_pct(db: Session, user_id: int, course_id: int) -> int:
    """Percent of the course's lessons this user has completed. 0 for a
    course with no lessons yet, rather than dividing by zero."""
    lesson_ids = course_lesson_ids(db, course_id)
    if not lesson_ids:
        return 0
    completed = (
        db.query(UserLessonProgress)
        .filter(UserLessonProgress.user_id == user_id, UserLessonProgress.lesson_id.in_(lesson_ids))
        .count()
    )
    return round(100 * completed / len(lesson_ids))


def quizzes_all_passed(db: Session, user_id: int, course_id: int) -> bool:
    """True if every chapter quiz in the course has a passing best attempt
    from this user -- vacuously true for a course with no quizzes."""
    quizzes = db.query(Quiz).join(Module, Quiz.module_id == Module.id).filter(Module.course_id == course_id).all()
    for quiz in quizzes:
        passed_once = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz.id, QuizAttempt.passed.is_(True))
            .first()
        )
        if not passed_once:
            return False
    return True


def check_and_issue_certificate(db: Session, user_id: int, course_id: int) -> Certificate | None:
    """Call after a course lesson is completed or a quiz is submitted --
    either can be the thing that clears the bar. If the user is enrolled,
    has completed every lesson in the course, and has passed every chapter
    quiz (if any), marks the Enrollment complete and auto-issues a
    Certificate.

    Idempotent by design: never issues a second certificate for the same
    (user, course) -- returns the existing one instead -- and does nothing
    for a user who was never enrolled (completing a course's lessons via
    the generic /api/lessons/{id} endpoint without enrolling first doesn't
    silently grant a certificate; enroll is the explicit "I'm taking this
    course" signal).

    Does not commit -- caller's existing transaction commits once, same
    pattern as complete_lesson's own db.commit() at the end.
    """
    enrollment = db.query(Enrollment).filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id).first()
    if not enrollment:
        return None

    lesson_ids = course_lesson_ids(db, course_id)
    if not lesson_ids:
        return None

    if course_progress_pct(db, user_id, course_id) < 100 or not quizzes_all_passed(db, user_id, course_id):
        return None

    if enrollment.completed_at is None:
        enrollment.completed_at = datetime.utcnow()

    existing = db.query(Certificate).filter(Certificate.user_id == user_id, Certificate.course_id == course_id).first()
    if existing:
        return existing

    cert = Certificate(user_id=user_id, course_id=course_id)
    db.add(cert)
    db.flush()
    return cert
