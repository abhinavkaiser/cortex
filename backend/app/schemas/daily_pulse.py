from datetime import date, datetime

from pydantic import BaseModel


class DailyPulseOut(BaseModel):
    id: int
    pulse_date: date
    track_slug: str | None
    # Learners no longer have an assigned track (see users.py's removed
    # track_id) -- GET /api/daily-pulse/today now returns every track's
    # pulse for today rather than one scoped to "the user's track", so the
    # frontend needs a human label per pulse to tell them apart.
    track_name: str | None
    summary: str
    sandbox_exercise: str
    quiz_question: str
    quiz_choices: list[str]
    # quiz_correct_index intentionally omitted -- the frontend shouldn't
    # receive the answer alongside the question. See routes/daily_pulse.py's
    # separate answer-check endpoint.
    source_urls: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class QuizAnswerRequest(BaseModel):
    pulse_id: int
    selected_index: int


class QuizAnswerResult(BaseModel):
    correct: bool
    correct_index: int
