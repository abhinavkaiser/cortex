from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)

    # NULL = Common Core (shown to every user regardless of track, before
    # their track curriculum unlocks). Non-null = belongs to that track.
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    track: Mapped["Track | None"] = relationship(back_populates="lessons")

    # Optional grouping within a track's curriculum (e.g. AI Leader's
    # "Module 2: The Economics of AI & Vendor Strategy") -- NULL for
    # Common Core and for any track lesson that isn't part of a named
    # module (the original flat single-lesson-per-track seed data).
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id"), nullable=True)
    module: Mapped["Module | None"] = relationship(back_populates="lessons")

    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Legacy/fallback: a plain-text render of the lesson, kept in sync
    # whenever content_blocks is generated (see generate_lesson_content.py)
    # so anything that only knows how to read plain text (the TTS
    # "Listen" button, a future export-to-PDF, search indexing) has a
    # single flattened string to work with instead of re-implementing
    # block-walking logic in N different places.
    content_markdown: Mapped[str] = mapped_column(Text, default="")

    # The real lesson content: an ordered list of typed blocks --
    # {"type": "text", "markdown": "..."}
    # {"type": "diagram", "title": "...", "svg": "<svg>...</svg>", "caption": "..."}
    # {"type": "callout", "style": "insight"|"warning", "markdown": "..."}
    # {"type": "check", "question": "...", "choices": [...], "correct_index": N, "explanation": "..."}
    # {"type": "calculator", "title": "...", "description": "...",
    #   "inputs": [{"key","label","default","min","max","step","unit"}],
    #   "formula": "safe arithmetic expression over input keys",
    #   "output_label": "...", "output_format": "currency"|"number"|"percent"}
    # See scripts/generate_lesson_content.py's BLOCK_SCHEMA for the
    # authoritative shape, and frontend/components/lesson-blocks/ for
    # rendering. Empty list = not yet generated in block form (falls back
    # to content_markdown in the UI).
    content_blocks: Mapped[list[dict]] = mapped_column(JSON, default=list)

    order_index: Mapped[int] = mapped_column(Integer, default=0)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=10)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    progress: Mapped[list["UserLessonProgress"]] = relationship(back_populates="lesson")

    @property
    def course_id(self) -> int | None:
        """A lesson's course affiliation is derived, not stored -- always
        via its module (lesson.module.course_id) -- so there's no separate
        column to keep in sync with Module.course_id. None for Common
        Core, any Track lesson, or a moduleless lesson."""
        return self.module.course_id if self.module else None


class UserLessonProgress(Base):
    """Not one of the five named models in the spec, but required to
    actually serve 'GET /users/{id}/progress' with real data -- otherwise
    there is nowhere to record which lessons a user has completed."""

    __tablename__ = "user_lesson_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="lesson_progress")
    lesson: Mapped["Lesson"] = relationship(back_populates="progress")
