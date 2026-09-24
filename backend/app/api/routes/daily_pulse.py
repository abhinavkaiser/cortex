from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.daily_pulse import DailyPulse, PulseStatus
from app.models.user import User
from app.schemas.daily_pulse import DailyPulseOut, QuizAnswerRequest, QuizAnswerResult

router = APIRouter(prefix="/api/daily-pulse", tags=["daily-pulse"])


@router.get("/today", response_model=list[DailyPulseOut])
def list_today_pulses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Serves the JSON payloads the frontend's Daily Pulse page renders --
    only ever PUBLISHED pulses (ones that cleared evals).

    Used to be scoped to "the current user's track" (User.track_id). Now
    that Tracks are no longer a learner-facing concept (a user doesn't
    have a track -- see the User model), there's no single track left to
    scope this to. Rather than silently picking one track's pulse (which
    would arbitrarily hide the other two tracks' content every day),
    this returns every track's published pulse for today -- Daily Pulse's
    generation/framing/storage (see agents/daily_pulse_agent.py,
    scripts/run_daily_pulse.py) is completely untouched, still one pulse
    per Track, per day; only how this route *serves* that unchanged data
    to a now-track-less user changed."""
    pulses = (
        db.query(DailyPulse)
        .filter(DailyPulse.pulse_date == date.today(), DailyPulse.status == PulseStatus.PUBLISHED)
        .order_by(DailyPulse.track_id)
        .all()
    )
    if not pulses:
        raise HTTPException(404, "No published pulses for today yet -- check back after the daily generation job runs.")

    return [
        DailyPulseOut(
            id=p.id,
            pulse_date=p.pulse_date,
            track_slug=p.track.slug if p.track else None,
            track_name=p.track.name if p.track else None,
            summary=p.summary,
            sandbox_exercise=p.sandbox_exercise,
            quiz_question=p.quiz_question,
            quiz_choices=p.quiz_choices,
            source_urls=p.source_urls,
            created_at=p.created_at,
        )
        for p in pulses
    ]


@router.post("/answer", response_model=QuizAnswerResult)
def answer_quiz(body: QuizAnswerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pulse = db.get(DailyPulse, body.pulse_id)
    if not pulse:
        raise HTTPException(404, "Pulse not found")
    return QuizAnswerResult(correct=body.selected_index == pulse.quiz_correct_index, correct_index=pulse.quiz_correct_index)
