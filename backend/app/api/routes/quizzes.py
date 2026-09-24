"""Quiz-taking: fetch a chapter's quiz (without answers), submit answers for
server-side grading, and view your own attempt history. Grading always
happens here, never trusted from the client -- see submit_attempt."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Quiz, QuizAttempt
from app.models.user import User
from app.schemas.course import (
    QuestionResult,
    QuizAttemptOut,
    QuizAttemptRequest,
    QuizAttemptResult,
    QuizQuestionTakeOut,
    QuizTakeOut,
)
from app.services.course_progress import check_and_issue_certificate

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@router.get("/{quiz_id}", response_model=QuizTakeOut)
def get_quiz(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Quiz content for someone about to take it -- correct_index is
    deliberately stripped from every question here; grading happens
    server-side in submit_attempt so the answer key never reaches the
    client before it's submitted."""
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    return QuizTakeOut(
        id=quiz.id,
        title=quiz.title,
        passing_score=quiz.passing_score,
        questions=[QuizQuestionTakeOut(question=q["question"], choices=q["choices"]) for q in quiz.questions],
    )


@router.post("/{quiz_id}/attempt", response_model=QuizAttemptResult)
def submit_attempt(quiz_id: int, body: QuizAttemptRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    if len(body.answers) != len(quiz.questions):
        raise HTTPException(400, f"Expected {len(quiz.questions)} answers, got {len(body.answers)}")

    results: list[QuestionResult] = []
    correct_count = 0
    for question, selected in zip(quiz.questions, body.answers):
        correct_index = question["correct_index"]
        is_correct = selected == correct_index
        if is_correct:
            correct_count += 1
        results.append(QuestionResult(correct=is_correct, correct_index=correct_index, selected_index=selected))

    score = round(100 * correct_count / len(quiz.questions)) if quiz.questions else 0
    passed = score >= quiz.passing_score

    db.add(QuizAttempt(user_id=user.id, quiz_id=quiz.id, answers=body.answers, score=score, passed=passed))
    # SessionLocal is autoflush=False (see core/db.py) -- without an
    # explicit flush, check_and_issue_certificate's own query for a passing
    # attempt wouldn't see the one just added above, since it isn't sent to
    # the DB yet.
    db.flush()

    # A passing attempt can be the thing that clears the course's
    # completion bar (every lesson done + every chapter quiz passed) --
    # check_and_issue_certificate is idempotent, so this is safe to call on
    # every passing attempt, not just the first.
    course_completed = False
    course_id = quiz.module.course_id if quiz.module else None
    if passed and course_id:
        course_completed = check_and_issue_certificate(db, user.id, course_id) is not None

    db.commit()

    return QuizAttemptResult(score=score, passed=passed, passing_score=quiz.passing_score, results=results, course_completed=course_completed)


@router.get("/{quiz_id}/attempts", response_model=list[QuizAttemptOut])
def get_my_attempts(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.attempted_at.desc())
        .all()
    )
    return [QuizAttemptOut(id=a.id, score=a.score, passed=a.passed, attempted_at=a.attempted_at) for a in attempts]
