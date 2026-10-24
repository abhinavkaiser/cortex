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
    """Latest published item per track; dates and stale flags remain explicit."""
    from sqlalchemy import func
    latest = (db.query(DailyPulse.track_id, func.max(DailyPulse.pulse_date).label("day"))
              .filter(DailyPulse.status == PulseStatus.PUBLISHED, DailyPulse.pulse_date <= date.today())
              .group_by(DailyPulse.track_id).subquery())
    candidates = (db.query(DailyPulse).join(latest, (DailyPulse.track_id == latest.c.track_id) & (DailyPulse.pulse_date == latest.c.day))
                  .filter(DailyPulse.status == PulseStatus.PUBLISHED).order_by(DailyPulse.track_id, DailyPulse.id.desc()).all())
    pulses, seen = [], set()
    for pulse in candidates:
        if pulse.track_id not in seen:
            pulses.append(pulse)
            seen.add(pulse.track_id)

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
            is_latest_from_earlier_day=p.pulse_date < date.today(),
        )
        for p in pulses
    ]


@router.post("/answer", response_model=QuizAnswerResult)
def answer_quiz(body: QuizAnswerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pulse = db.get(DailyPulse, body.pulse_id)
    if not pulse or pulse.status != PulseStatus.PUBLISHED:
        raise HTTPException(404, "Pulse not found")
    return QuizAnswerResult(correct=body.selected_index == pulse.quiz_correct_index, correct_index=pulse.quiz_correct_index)
