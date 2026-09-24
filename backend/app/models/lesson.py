from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Which chapter (Module) this lesson belongs to -- every lesson today
    # belongs to a Course via its Module (see course_id property below).
    # Nullable in the schema because a handful of pre-Module-era track
    # lessons used to be a real, flat (no-module) case -- see
    # scripts/migrate_tracks_to_courses.py, which gave every one of those a
    # real Module on migration. Kept nullable rather than tightened to
    # NOT NULL since nothing currently depends on that guarantee.
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
    # {"type": "video", "title": "...", "url": "youtube/vimeo id or URL, or a direct file URL",
    #   "transcript": "optional plain-text transcript"}
    #   -- a known-provider URL (youtube.com/youtu.be/vimeo.com) is parsed
    #   into an embed URL and rendered via <iframe>; anything else falls
    #   back to a native <video> tag. See frontend/lib/videoEmbed.ts.
    # {"type": "document", "title": "...", "url": "/static/course-uploads/...",
    #   "filename": "original-name.pdf"}
    #   -- url comes from POST /api/courses/{id}/upload (instructor/admin
    #   only), same static-file convention app/agents/image_mcp.py already
    #   uses for images. Rendered via <iframe>/<embed> with a download
    #   fallback link, not re-hosted anywhere else.
    # {"type": "link", "title": "...", "url": "https://...", "description": "..."}
    #   -- an external URL, rendered as a clearly-labeled outbound card, not
    #   auto-embedded (unlike video/document, this is content this app
    #   doesn't control or host).
    # See scripts/generate_lesson_content.py's BLOCK_SCHEMA for the
    # authoritative shape of the AI-generated block types, and
    # frontend/components/lesson-blocks/ for rendering of all of them.
    # Empty list = not yet generated in block form (falls back to
    # content_markdown in the UI).
    content_blocks: Mapped[list[dict]] = mapped_column(JSON, default=list)

    order_index: Mapped[int] = mapped_column(Integer, default=0)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=10)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    progress: Mapped[list["UserLessonProgress"]] = relationship(back_populates="lesson")

    @property
    def course_id(self) -> int | None:
        """A lesson's course affiliation is derived, not stored -- always
        via its module (lesson.module.course_id) -- so there's no separate
        column to keep in sync with Module.course_id. None only for a
        lesson with no module at all, which shouldn't happen in practice
        today (every lesson-creation path assigns a module)."""
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
