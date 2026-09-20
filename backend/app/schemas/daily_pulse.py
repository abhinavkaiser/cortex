from datetime import date, datetime

from pydantic import BaseModel


class DailyPulseOut(BaseModel):
    id: int
    pulse_date: date
    track_slug: str | None
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
