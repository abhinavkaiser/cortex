from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.daily_pulse import DailyPulse, PulseStatus
from app.models.user import User
from app.schemas.daily_pulse import DailyPulseOut, QuizAnswerRequest, QuizAnswerResult

router = APIRouter(prefix="/api/daily-pulse", tags=["daily-pulse"])


@router.get("/today", response_model=DailyPulseOut)
def get_today_pulse(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Serves the JSON payload the frontend's Daily Pulse card renders --
    only ever a PUBLISHED pulse (one that cleared evals), scoped to the
    user's track. A user with no track yet (still in Common Core) gets the
    track_id IS NULL pulse if one exists, else a 404 telling the frontend
    there's nothing to show today."""
    pulse = (
        db.query(DailyPulse)
        .filter(
            DailyPulse.pulse_date == date.today(),
            DailyPulse.track_id == user.track_id,
            DailyPulse.status == PulseStatus.PUBLISHED,
        )
        .first()
    )
    if not pulse:
        raise HTTPException(404, "No published pulse for today yet -- check back after the daily generation job runs.")

    return DailyPulseOut(
        id=pulse.id,
        pulse_date=pulse.pulse_date,
        track_slug=pulse.track.slug if pulse.track else None,
        summary=pulse.summary,
        sandbox_exercise=pulse.sandbox_exercise,
        quiz_question=pulse.quiz_question,
        quiz_choices=pulse.quiz_choices,
        source_urls=pulse.source_urls,
        created_at=pulse.created_at,
    )


@router.post("/answer", response_model=QuizAnswerResult)
def answer_quiz(body: QuizAnswerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pulse = db.get(DailyPulse, body.pulse_id)
    if not pulse:
        raise HTTPException(404, "Pulse not found")
    return QuizAnswerResult(correct=body.selected_index == pulse.quiz_correct_index, correct_index=pulse.quiz_correct_index)
