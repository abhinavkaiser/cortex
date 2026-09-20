from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Module(Base):
    """A named, ordered group of lessons within one track -- e.g. AI
    Leader's "Module 2: The Economics of AI & Vendor Strategy". Added once a
    real multi-module curriculum existed to organize (the original
    single-flat-lesson-list seed didn't need this yet). NULL track_id would
    theoretically mean a Common-Core module, mirroring Lesson's own
    NULL-means-Common-Core convention, though Common Core doesn't use
    modules today."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    track: Mapped["Track | None"] = relationship(back_populates="modules")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(String(500), default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", order_by="Lesson.order_index")
