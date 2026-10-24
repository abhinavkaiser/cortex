"""Additive learning tables: published revisions and private, versioned practice."""
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LearningUnit(Base):
    __tablename__ = "learning_units"
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    objective: Mapped[str] = mapped_column(Text)
    prerequisites: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON)
    reviewed_on: Mapped[date] = mapped_column(Date)
    review_due: Mapped[date] = mapped_column(Date)
    position: Mapped[int]
    stage: Mapped[str] = mapped_column(String(100))
    exercise: Mapped[dict] = mapped_column(JSON)


class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    version: Mapped[str] = mapped_column(String(64))
    answers: Mapped[list] = mapped_column(JSON)
    reflection: Mapped[str] = mapped_column(Text)
    score: Mapped[int]
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CurriculumSignal(Base):
    __tablename__ = "curriculum_signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2000), unique=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200))
    published_at: Mapped[datetime] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    lesson_slugs: Mapped[list] = mapped_column(JSON)


class LearningRevision(Base):
    __tablename__ = "learning_revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    version: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CurriculumRefresh(Base):
    __tablename__ = "curriculum_refresh"
    id: Mapped[int] = mapped_column(primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime)
    result: Mapped[dict] = mapped_column(JSON)


class LearningQuizPublication(Base):
    __tablename__ = "learning_quiz_publications"
    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), unique=True)
    version: Mapped[str] = mapped_column(String(64))
    original: Mapped[dict] = mapped_column(JSON)


class LearningQuizAttempt(Base):
    __tablename__ = "learning_quiz_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("quiz_attempts.id"), unique=True)
    version: Mapped[str] = mapped_column(String(64))
