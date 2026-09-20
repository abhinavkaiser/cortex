# Import order matters for SQLAlchemy relationship() string-reference
# resolution -- every model must be imported somewhere before
# Base.metadata.create_all() (or Alembic autogenerate) runs, otherwise a
# relationship like Track.users -> "User" fails to resolve at mapper
# configuration time.
from app.models.user import User, UserRole  # noqa: F401
from app.models.track import Track  # noqa: F401
from app.models.lesson import Lesson, UserLessonProgress  # noqa: F401
from app.models.daily_pulse import DailyPulse, PulseStatus  # noqa: F401
from app.models.prompt_attempt import PromptAttempt  # noqa: F401
from app.models.semantic_cache import SemanticCacheEntry  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "Track",
    "Lesson",
    "UserLessonProgress",
    "DailyPulse",
    "PulseStatus",
    "PromptAttempt",
    "SemanticCacheEntry",
]
