from datetime import datetime

from pydantic import BaseModel, EmailStr


class TrackOut(BaseModel):
    id: int
    slug: str
    name: str

    class Config:
        from_attributes = True


class LessonProgressOut(BaseModel):
    lesson_id: int
    lesson_title: str
    completed_at: datetime


class UserProgressOut(BaseModel):
    """Response for GET /api/users/{id}/progress -- everything the frontend
    needs to decide what to render: onboarding vs. Common Core vs. track
    curriculum, plus a completion percentage for a progress bar."""

    user_id: int
    email: EmailStr
    track: TrackOut | None
    common_core_completed: bool
    common_core_completed_at: datetime | None

    common_core_lessons_total: int
    common_core_lessons_completed: int
    track_lessons_total: int
    track_lessons_completed: int

    completed_lessons: list[LessonProgressOut]


class OnboardingRequest(BaseModel):
    track_slug: str  # "leader" | "practitioner" | "developer"


class CompleteLessonRequest(BaseModel):
    lesson_id: int
