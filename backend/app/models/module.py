from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Module(Base):
    """A named, ordered group of lessons -- a chapter in an instructor
    -authored Course (e.g. "Module 2: The Economics of AI & Vendor
    Strategy" in the migrated AI Leader course). Added once a real
    multi-module curriculum existed to organize (the original
    single-flat-lesson-list seed didn't need this yet).

    Used to also (mutually exclusively) belong to a fixed Track instead of
    a Course, back when the 3 specialization Tracks were a separate,
    learner-facing concept from the general Course system -- see
    scripts/migrate_tracks_to_courses.py, which repointed every Track
    -owned Module to a Course and nulled out the now-removed track_id
    column. Every Module belongs to exactly one Course now."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)

    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    course: Mapped["Course | None"] = relationship(back_populates="modules")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(String(500), default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", order_by="Lesson.order_index")
    # A chapter's quiz, if it has one -- see models/course.py's Quiz.
    quiz: Mapped["Quiz | None"] = relationship(back_populates="module", uselist=False)
