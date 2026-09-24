"""Quiz-taking: fetch a chapter's quiz (without answers), submit answers for
server-side grading, and view your own attempt history. Grading always
happens here, never trusted from the client -- see submit_attempt. Also
carries the instructor-facing short_answer grading queue (pending-attempts +
grade), since both live on the same Quiz/QuizAttempt models."""

import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Quiz, QuizAttempt
from app.models.user import User, UserRole
from app.schemas.course import (
    GradeAttemptRequest,
    GradeAttemptResult,
    PendingAttemptOut,
    QuestionResult,
    QuizAttemptOut,
    QuizAttemptRequest,
    QuizAttemptResult,
    QuizQuestionTakeOut,
    QuizTakeOut,
)
from app.services.course_progress import check_and_issue_certificate

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
# Separate prefix/resource (an attempt, not a quiz) -- kept in this same
# file rather than a new route module since grading is a small extension of
# the quiz-taking flow right above it, not a separate feature area.
quiz_attempts_router = APIRouter(prefix="/api/quiz-attempts", tags=["quizzes"])


def _question_type(question: dict) -> str:
    # Absent "type" means multiple_choice -- see models/course.py's Quiz
    # docstring for why (keeps every pre-existing quiz working unchanged).
    return question.get("type", "multiple_choice")


def _require_quiz_owner_or_admin(quiz: Quiz, user: User) -> None:
    course = quiz.module.course if quiz.module else None
    if not course or (course.instructor_id != user.id and user.role != UserRole.ADMIN):
        raise HTTPException(403, "Only the owning instructor or an admin can do this")


@router.get("/{quiz_id}", response_model=QuizTakeOut)
def get_quiz(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Quiz content for someone about to take it -- correct_index/
    correct_indices are deliberately stripped from every question here;
    grading happens server-side in submit_attempt so the answer key never
    reaches the client before it's submitted.

    When randomize_questions is set, question ORDER is shuffled fresh on
    every fetch (answer-choice order within a question is never touched) --
    each question carries its original_index so the client can echo the
    order back on submit (see QuizAttemptRequest.question_order)."""
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    indices = list(range(len(quiz.questions)))
    if quiz.randomize_questions:
        random.shuffle(indices)

    questions_out = [
        QuizQuestionTakeOut(
            original_index=idx,
            type=_question_type(quiz.questions[idx]),
            question=quiz.questions[idx]["question"],
            choices=quiz.questions[idx].get("choices") or [],
        )
        for idx in indices
    ]

    attempts_used = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user.id).count()

    return QuizTakeOut(
        id=quiz.id,
        title=quiz.title,
        passing_score=quiz.passing_score,
        max_attempts=quiz.max_attempts,
        attempts_used=attempts_used,
        questions=questions_out,
    )


@router.post("/{quiz_id}/attempt", response_model=QuizAttemptResult)
def submit_attempt(quiz_id: int, body: QuizAttemptRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    if len(body.answers) != len(quiz.questions):
        raise HTTPException(400, f"Expected {len(quiz.questions)} answers, got {len(body.answers)}")

    if quiz.max_attempts is not None:
        attempts_so_far = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == user.id).count()
        if attempts_so_far >= quiz.max_attempts:
            raise HTTPException(403, f"Maximum attempts ({quiz.max_attempts}) reached for this quiz.")

    # question_order maps each answer's position to the question's real
    # index in quiz.questions -- required to grade correctly when the quiz
    # was fetched randomized (see get_quiz). A client that didn't randomize
    # (or an older one) omits it, so sequential order is assumed.
    order = body.question_order if body.question_order is not None else list(range(len(quiz.questions)))
    if len(order) != len(body.answers) or set(order) != set(range(len(quiz.questions))):
        raise HTTPException(400, "question_order must be a permutation of every question index, matching answers in length")

    # Stored/returned per-question data always keyed by the question's
    # ORIGINAL index, not presentation order -- so attempt history and the
    # grading queue read consistently regardless of which shuffle a given
    # attempt happened to get.
    canonical_answers: list = [None] * len(quiz.questions)
    results_by_original: dict[int, QuestionResult] = {}
    correct_count = 0
    gradable_count = 0
    has_pending = False

    for position, original_index in enumerate(order):
        question = quiz.questions[original_index]
        qtype = _question_type(question)
        selected = body.answers[position]
        canonical_answers[original_index] = selected

        if qtype == "multi_select":
            correct_indices = question.get("correct_indices") or []
            selected_list = selected if isinstance(selected, list) else []
            is_correct = set(selected_list) == set(correct_indices)
            gradable_count += 1
            correct_count += int(is_correct)
            results_by_original[original_index] = QuestionResult(type=qtype, correct=is_correct, selected=selected, correct_indices=correct_indices)
        elif qtype == "short_answer":
            has_pending = True
            results_by_original[original_index] = QuestionResult(type=qtype, correct=None, selected=selected)
        else:  # multiple_choice, true_false, and any unrecognized type -- graded the same way as today's multiple_choice
            correct_index = question.get("correct_index")
            is_correct = selected == correct_index
            gradable_count += 1
            correct_count += int(is_correct)
            results_by_original[original_index] = QuestionResult(type=qtype, correct=is_correct, selected=selected, correct_index=correct_index)

    score = round(100 * correct_count / gradable_count) if gradable_count else 0
    status = "pending" if has_pending else "graded"
    passed = (not has_pending) and score >= quiz.passing_score

    attempt = QuizAttempt(
        user_id=user.id,
        quiz_id=quiz.id,
        answers=canonical_answers,
        score=score,
        passed=passed,
        status=status,
        graded_at=None if has_pending else datetime.utcnow(),
    )
    db.add(attempt)
    # SessionLocal is autoflush=False (see core/db.py) -- without an
    # explicit flush, check_and_issue_certificate's own query for a passing
    # attempt wouldn't see the one just added above, since it isn't sent to
    # the DB yet.
    db.flush()

    # A passing attempt can be the thing that clears the course's
    # completion bar (every lesson done + every chapter quiz passed) --
    # check_and_issue_certificate is idempotent, so this is safe to call on
    # every passing attempt, not just the first. Never true for a pending
    # attempt (passed is forced False above until an instructor grades it).
    course_completed = False
    course_id = quiz.module.course_id if quiz.module else None
    if passed and course_id:
        course_completed = check_and_issue_certificate(db, user.id, course_id) is not None

    db.commit()

    # Results returned in PRESENTATION order (matching what the client just
    # displayed), not original-index order -- results_by_original[idx] for
    # idx in `order` reproduces that.
    results = [results_by_original[idx] for idx in order]

    return QuizAttemptResult(score=score, passed=passed, status=status, passing_score=quiz.passing_score, results=results, course_completed=course_completed)


@router.get("/{quiz_id}/attempts", response_model=list[QuizAttemptOut])
def get_my_attempts(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.attempted_at.desc())
        .all()
    )
    return [QuizAttemptOut(id=a.id, score=a.score, passed=a.passed, status=a.status, attempted_at=a.attempted_at) for a in attempts]


@router.get("/{quiz_id}/pending-attempts", response_model=list[PendingAttemptOut])
def get_pending_attempts(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The instructor's grading queue for one quiz -- every attempt still
    awaiting a human call on its short_answer question(s). Owning
    instructor or admin only, same gate as the rest of course authoring."""
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    _require_quiz_owner_or_admin(quiz, user)

    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == "pending")
        .order_by(QuizAttempt.attempted_at)
        .all()
    )

    # Questions are sent alongside each attempt (not fetched separately)
    # so the grading UI can render "question -> this learner's answer"
    # without a second round trip -- sample_answer only travels for
    # short_answer questions, since that's the only type an instructor
    # actually needs a reference answer for here.
    questions_payload = [
        {"type": _question_type(q), "question": q["question"], **({"sample_answer": q.get("sample_answer", "")} if _question_type(q) == "short_answer" else {})}
        for q in quiz.questions
    ]

    return [
        PendingAttemptOut(
            id=a.id,
            user_id=a.user_id,
            user_email=a.user.email,
            user_full_name=a.user.full_name,
            attempted_at=a.attempted_at,
            questions=questions_payload,
            answers=a.answers,
        )
        for a in attempts
    ]


@quiz_attempts_router.post("/{attempt_id}/grade", response_model=GradeAttemptResult)
def grade_attempt(attempt_id: int, body: GradeAttemptRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Finalizes a pending (short_answer-containing) attempt -- the
    instructor supplies score/passed directly (short_answer can't be
    auto-scored), and a pass triggers the exact same course-completion
    check (check_and_issue_certificate) an auto-graded passing attempt
    does, so a short_answer chapter quiz can clear the course bar and issue
    a certificate the same way any other chapter quiz can."""
    attempt = db.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    quiz = attempt.quiz
    _require_quiz_owner_or_admin(quiz, user)

    attempt.score = body.score
    attempt.passed = body.passed
    attempt.status = "graded"
    attempt.graded_at = datetime.utcnow()
    db.flush()

    course_completed = False
    course_id = quiz.module.course_id if quiz.module else None
    if body.passed and course_id:
        course_completed = check_and_issue_certificate(db, attempt.user_id, course_id) is not None

    db.commit()
    return GradeAttemptResult(id=attempt.id, score=attempt.score, passed=attempt.passed, status=attempt.status, course_completed=course_completed)
