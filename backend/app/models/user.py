import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class UserRole(str, enum.Enum):
    """RBAC role -- separate from `track`, which is the learning-content
    track (Leader/Practitioner/Developer), not an authorization level."""

    LEARNER = "learner"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.LEARNER, nullable=False)

    # Nullable until onboarding assigns one -- the frontend routes to the
    # onboarding flow whenever this is NULL, matching the "assigns users to
    # one of three tracks" requirement.
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    track: Mapped["Track | None"] = relationship(back_populates="users")

    # NULL = has not finished Common Core yet -- this is the single flag the
    # frontend checks to decide "show Common Core" vs "show track curriculum".
    common_core_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lesson_progress: Mapped[list["UserLessonProgress"]] = relationship(back_populates="user")
    prompt_attempts: Mapped[list["PromptAttempt"]] = relationship(back_populates="user")
