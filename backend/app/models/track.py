from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Track(Base):
    """Formerly the three learner-facing specialization tracks (AI Leader /
    AI Practitioner / AI Developer). That curriculum now lives as ordinary
    Courses (see models/course.py and scripts/migrate_tracks_to_courses.py)
    -- Tracks are no longer a user-facing concept anywhere in the app.

    This table (and model) survives purely as an internal dependency of
    Daily Pulse: DailyPulse.track_id still points here because pulses are
    generated and framed per track ("write this for an AI Leader audience"
    -- see agents/daily_pulse_agent.py's TRACK_FRAMING) independent of
    which course a learner happens to be enrolled in. Do not repurpose this
    as a learner-facing entity again without re-threading that through
    Daily Pulse's generation/serving logic."""

    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # "leader" | "practitioner" | "developer"
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "AI Leader"
    description: Mapped[str] = mapped_column(Text, default="")

    daily_pulses: Mapped[list["DailyPulse"]] = relationship(back_populates="track")
