from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Track(Base):
    """The three specialization tracks -- AI Leader / AI Practitioner / AI
    Developer. Common Core content is NOT a Track row; it's modeled as
    Lesson rows with track_id = NULL (see Lesson), since Common Core is a
    prerequisite everyone shares, not a branch a user is assigned to."""

    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # "leader" | "practitioner" | "developer"
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "AI Leader"
    description: Mapped[str] = mapped_column(Text, default="")

    users: Mapped[list["User"]] = relationship(back_populates="track")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="track")
    daily_pulses: Mapped[list["DailyPulse"]] = relationship(back_populates="track")
