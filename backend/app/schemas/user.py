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


class LessonOut(BaseModel):
    """One row in the lesson list the Common Core / track pages actually
    render and let the user click into -- distinct from LessonProgressOut,
    which only covers already-completed lessons. module_id/module_title are
    None for lessons that aren't part of a named module (all of Common
    Core, and any track lesson predating the Module concept) -- the
    frontend groups by module_id when present, falls back to a flat list
    when not."""

    id: int
    title: str
    estimated_minutes: int
    order_index: int
    completed: bool
    module_id: int | None
    module_title: str | None


class UserProgressOut(BaseModel):
    """Response for GET /api/users/{id}/progress -- everything the frontend
    needs to decide what to render: onboarding vs. Common Core vs. track
    curriculum, plus the actual lesson list (not just completed ones) to
    render and act on, plus a completion percentage for a progress bar."""

    user_id: int
    email: EmailStr
    role: str  # "learner" | "instructor" | "admin" -- the frontend's only source for role-gating nav/pages (see UserRole)
    track: TrackOut | None
    common_core_completed: bool
    common_core_completed_at: datetime | None

    common_core_lessons_total: int
    common_core_lessons_completed: int
    track_lessons_total: int
    track_lessons_completed: int

    common_core_lessons: list[LessonOut]
    track_lessons: list[LessonOut]
    completed_lessons: list[LessonProgressOut]


class OnboardingRequest(BaseModel):
    track_slug: str  # "leader" | "practitioner" | "developer"


class CompleteLessonRequest(BaseModel):
    lesson_id: int
