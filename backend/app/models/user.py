import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class UserRole(str, enum.Enum):
    """RBAC role -- learner/instructor/admin. Unrelated to course content
    (which course(s) a user is enrolled in/teaches is Enrollment/
    Course.instructor_id, not this)."""

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

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lesson_progress: Mapped[list["UserLessonProgress"]] = relationship(back_populates="user")
    prompt_attempts: Mapped[list["PromptAttempt"]] = relationship(back_populates="user")

    # Course-system relationships (see models/course.py) -- a user can be a
    # learner (enrollments/quiz_attempts/certificates) and/or an instructor
    # (Course.instructor_id) at once; role gates which routes accept which,
    # not the schema.
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="user")
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="user")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="user")
