from pydantic import BaseModel, EmailStr


class UserProgressOut(BaseModel):
    """Response for GET /api/users/{id}/progress -- despite the route name
    (kept as-is to avoid a frontend churn for what's now a small payload),
    this is really just "who am I" identity info: the frontend's only
    source for role-gating nav/pages (see UserRole). Per-course progress
    now lives at GET /api/users/{id}/courses and GET /api/courses/{slug}
    instead -- there's no longer a single track-scoped "my progress" view,
    since a learner can be enrolled in any number of courses at once."""

    user_id: int
    email: EmailStr
    role: str  # "learner" | "instructor" | "admin"


class CompleteLessonRequest(BaseModel):
    lesson_id: int
