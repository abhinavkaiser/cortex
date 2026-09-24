# Import order matters for SQLAlchemy relationship() string-reference
# resolution -- every model must be imported somewhere before
# Base.metadata.create_all() (or Alembic autogenerate) runs, otherwise a
# relationship like Track.users -> "User" fails to resolve at mapper
# configuration time.
from app.models.user import User, UserRole  # noqa: F401
from app.models.track import Track  # noqa: F401
# Course (and its Enrollment/Quiz/QuizAttempt/Certificate siblings) before
# Module -- Module.course_id relationship references "Course" by string.
from app.models.course import Certificate, Course, Enrollment, Quiz, QuizAttempt  # noqa: F401
from app.models.module import Module  # noqa: F401
from app.models.lesson import Lesson, UserLessonProgress  # noqa: F401
from app.models.daily_pulse import DailyPulse, PulseStatus  # noqa: F401
from app.models.prompt_attempt import PromptAttempt  # noqa: F401
from app.models.semantic_cache import SemanticCacheEntry  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "Track",
    "Course",
    "Enrollment",
    "Quiz",
    "QuizAttempt",
    "Certificate",
    "Module",
    "Lesson",
    "UserLessonProgress",
    "DailyPulse",
    "PulseStatus",
    "PromptAttempt",
    "SemanticCacheEntry",
]
