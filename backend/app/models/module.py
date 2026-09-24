from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Module(Base):
    """A named, ordered group of lessons -- e.g. AI Leader's "Module 2: The
    Economics of AI & Vendor Strategy", or a chapter in an instructor
    -authored Course. Added once a real multi-module curriculum existed to
    organize (the original single-flat-lesson-list seed didn't need this
    yet). NULL track_id would theoretically mean a Common-Core module,
    mirroring Lesson's own NULL-means-Common-Core convention, though Common
    Core doesn't use modules today.

    A Module now belongs to either a Track or a Course, never both -- the
    general-purpose course system (see models/course.py) reuses this same
    table as a Course's "chapter" rather than inventing a parallel
    chapter/lesson schema, so lesson rendering and progress tracking stay
    one code path. track_id and course_id are both nullable and mutually
    exclusive in practice (enforced at the route layer, not a DB
    CHECK constraint -- SQLite's support for those is limited enough that
    the existing codebase doesn't lean on them elsewhere either)."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    track: Mapped["Track | None"] = relationship(back_populates="modules")

    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    course: Mapped["Course | None"] = relationship(back_populates="modules")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(String(500), default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", order_by="Lesson.order_index")
    # A chapter's quiz, if it has one -- see models/course.py's Quiz.
    # Track modules never get one today (no route creates a Quiz for a
    # track-owned module), but nothing in the schema forbids it.
    quiz: Mapped["Quiz | None"] = relationship(back_populates="module", uselist=False)
