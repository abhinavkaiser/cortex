import enum
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import JSON, Date, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PulseStatus(str, enum.Enum):
    """Evals gate publication -- see agents/evals.py. A pulse is generated as
    DRAFT, scored, and only flips to PUBLISHED (visible to users) if it
    clears the quality bar; otherwise it's FLAGGED for human review rather
    than silently shipped or silently dropped."""

    DRAFT = "draft"
    PUBLISHED = "published"
    FLAGGED = "flagged"


class DailyPulse(Base):
    __tablename__ = "daily_pulses"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(primary_key=True)
    pulse_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    # A pulse is generated per-track (summary/exercise/quiz are tailored to
    # the reader's track), so (pulse_date, track_id) is the natural identity
    # -- enforced at the query/generation layer, not a DB unique constraint,
    # since SQLite's handling of NULL in composite uniques is inconsistent
    # and Common-Core-wide pulses (track_id NULL) are a real, valid case too.
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    track: Mapped["Track | None"] = relationship(back_populates="daily_pulses")

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sandbox_exercise: Mapped[str] = mapped_column(Text, nullable=False)

    quiz_question: Mapped[str] = mapped_column(Text, nullable=False)
    quiz_choices: Mapped[list[str]] = mapped_column(JSON, default=list)
    quiz_correct_index: Mapped[int] = mapped_column(default=0)

    source_urls: Mapped[list[str]] = mapped_column(JSON, default=list)

    status: Mapped[PulseStatus] = mapped_column(Enum(PulseStatus), default=PulseStatus.DRAFT)
    eval_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_notes: Mapped[str] = mapped_column(Text, default="")

    generation_model: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
