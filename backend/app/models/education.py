"""Versioned assessment, curriculum amendments, and learning evidence."""
from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class EducationJob(Base):
    __tablename__ = 'education_jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    request_key: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    subject_id: Mapped[int]
    version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default='queued', index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProjectSubmission(Base):
    __tablename__ = 'project_submissions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    project_slug: Mapped[str] = mapped_column(String(150), index=True)
    milestone: Mapped[int]
    version: Mapped[str] = mapped_column(String(64))
    artifact: Mapped[dict] = mapped_column(JSON)
    report: Mapped[str] = mapped_column(Text)
    benchmark: Mapped[dict] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LessonAmendment(Base):
    __tablename__ = 'lesson_amendments'
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey('lessons.id'), index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey('curriculum_signals.id'))
    job_id: Mapped[int] = mapped_column(ForeignKey('education_jobs.id'), unique=True)
    base_version: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300))
    markdown: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON)
    question: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default='published')
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvidenceAttempt(Base):
    __tablename__ = 'evidence_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    skill: Mapped[str] = mapped_column(String(80), index=True)
    phase: Mapped[str] = mapped_column(String(30))
    variant: Mapped[int]
    answers: Mapped[list] = mapped_column(JSON)
    score: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'skill', 'phase', name='uq_evidence_phase'),)


class LearningEvent(Base):
    __tablename__ = 'learning_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey('lessons.id'), index=True)
    day: Mapped[str] = mapped_column(String(10))
    active_seconds: Mapped[int] = mapped_column(default=0)
    __table_args__ = (UniqueConstraint('user_id','lesson_id','day', name='uq_active_day'),)


class EducationWorker(Base):
    __tablename__ = 'education_worker'
    id: Mapped[int] = mapped_column(primary_key=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime)
    current_job: Mapped[int | None] = mapped_column(nullable=True)


class AssessmentAppeal(Base):
    __tablename__ = 'assessment_appeals'
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('education_jobs.id'), unique=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default='open')
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    resolution: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GraderCalibration(Base):
    __tablename__ = 'grader_calibration'
    id: Mapped[int] = mapped_column(primary_key=True)
    model_ids: Mapped[list] = mapped_column(JSON)
    checked_at: Mapped[datetime] = mapped_column(DateTime)
    passed: Mapped[bool] = mapped_column(Boolean)
    results: Mapped[list] = mapped_column(JSON)
