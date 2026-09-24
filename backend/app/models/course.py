import secrets
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Course(Base):
    """An instructor-authored course -- arbitrary content, unlike the three
    fixed Tracks (Leader/Practitioner/Developer), which are the platform's
    own curated curriculum. Deliberately built from the same Module/Lesson
    tables a Track uses (see Module.course_id) rather than a parallel
    chapter/lesson schema, so lesson rendering, content_blocks, and
    progress tracking are all the same code paths a Track lesson already
    goes through -- only the top-level container (Course vs. Track) and
    who can author it differ."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # Free text, not a fixed enum/lookup table -- there's no
    # category-management UI in this scope, just a label shown on the
    # catalog card and usable for a future filter.
    category: Mapped[str] = mapped_column(String(100), default="")

    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    instructor: Mapped["User"] = relationship(foreign_keys=[instructor_id])

    # Draft courses (False) are visible only to their instructor and admins
    # -- GET /api/courses filters these out of the public catalog for
    # everyone else. No review/approval workflow: the owning
    # instructor's own toggle is the only gate.
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    modules: Mapped[list["Module"]] = relationship(back_populates="course", order_by="Module.order_index")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="course")


class Enrollment(Base):
    """A learner's membership in a course. due_at is a real, simple 'typical
    LMS' feature -- an optional target-completion date a learner can see on
    their dashboard -- deliberately NOT wired to any reminder/notification
    system (no email/cron infra for that here; see README Scoping notes).
    completed_at is set once, automatically, by the completion-check in
    users.py's complete_lesson -- there's no manual 'mark course complete'
    action."""

    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)

    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")


class Quiz(Base):
    """One quiz per chapter (Module). module_id isn't DB-unique -- the API
    always upserts by module_id (POST .../quiz replaces the existing quiz
    rather than adding a second one), which is simpler than a DB constraint
    plus explicit "replace" logic for a feature that only ever needs one
    active quiz per chapter today.

    questions mirrors DailyPulse.quiz_choices/quiz_correct_index's shape --
    one question there, a list of the same per-question shape here -- for
    consistency rather than inventing a new question schema:
    [{"question": "...", "choices": [...], "correct_index": N}, ...]
    """

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    module: Mapped["Module"] = relationship(back_populates="quiz")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    passing_score: Mapped[int] = mapped_column(Integer, default=70)  # percent, 0-100
    questions: Mapped[list[dict]] = mapped_column(JSON, default=list)

    attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="quiz")


class QuizAttempt(Base):
    """Multiple attempts per user are allowed (a learner can retake) --
    course-completion logic (see users.py's complete_lesson) checks for the
    user's BEST attempt meeting passing_score, not just the most recent, so
    a later failed retake can't un-clear a chapter that was already
    passed."""

    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)

    answers: Mapped[list[int]] = mapped_column(JSON, default=list)  # chosen choice index per question, in question order
    score: Mapped[int] = mapped_column(Integer, default=0)  # percent, 0-100
    passed: Mapped[bool] = mapped_column(Boolean, default=False)

    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="quiz_attempts")
    quiz: Mapped["Quiz"] = relationship(back_populates="attempts")


class Certificate(Base):
    """Auto-issued the moment a course's completion bar clears (see
    users.py's complete_lesson) -- one per (user, course), never
    re-issued/duplicated on repeat triggers (e.g. re-completing an already
    -passed quiz). certificate_code is the public, unguessable lookup key
    for the no-auth verification page (GET /api/certificates/verify/{code})
    -- deliberately not the numeric id, so a certificate URL can't be
    enumerated to fish for other learners' certificates."""

    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)

    certificate_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(24))
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="certificates")
    course: Mapped["Course"] = relationship(back_populates="certificates")
