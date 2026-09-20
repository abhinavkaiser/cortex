"""The Daily Pulse pipeline: ingest AI news -> extract signal via Claude,
tailored per learning track -> evaluate quality -> persist as
draft/published/flagged.

Run for all three tracks by scripts/run_daily_pulse.py (the cron entrypoint).
Each track gets its own generation call, not one call reused three ways --
"tailored to the user's specific track" means the actual framing/depth
differs (a Leader pulse emphasizes strategic/organizational impact, a
Developer pulse emphasizes implementation detail), which only works if the
model is told which track it's writing for up front.
"""

import json
from datetime import date

from sqlalchemy.orm import Session

from app.agents import evals
from app.agents.news_ingest import RawArticle, fetch_recent_articles
from app.models.daily_pulse import DailyPulse, PulseStatus
from app.models.track import Track
from app.services import claude_client
from app.core.config import get_settings

settings = get_settings()

PULSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "A ~2-minute-read summary (roughly 250-350 words) of the most important AI development(s) today, written for this specific track's audience."},
        "sandbox_exercise": {"type": "string", "description": "A concrete, doable-in-10-minutes practical exercise related to the summary -- a prompt to try, a small experiment, a real decision to think through. Not generic busywork."},
        "quiz_question": {"type": "string", "description": "One multiple-choice question testing real understanding of the summary, not trivia."},
        "quiz_choices": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "quiz_correct_index": {"type": "integer", "description": "0-based index into quiz_choices of the correct answer."},
    },
    "required": ["summary", "sandbox_exercise", "quiz_question", "quiz_choices", "quiz_correct_index"],
}

TRACK_FRAMING = {
    "leader": "an AI Leader (exec/manager) who needs to understand strategic and organizational implications, ROI, and risk -- not implementation detail.",
    "practitioner": "an AI Practitioner (product/ops person using AI tools day-to-day) who needs practical, workflow-level understanding -- how this changes what they can actually do.",
    "developer": "an AI Developer (builds with AI/ML) who needs technical substance -- architecture, APIs, tradeoffs, what they'd actually need to implement or evaluate this.",
}


def _build_prompt(articles: list[RawArticle], track_slug: str) -> str:
    framing = TRACK_FRAMING.get(track_slug, TRACK_FRAMING["practitioner"])
    articles_block = "\n\n".join(f"[{i + 1}] {a.title} ({a.source})\n{a.summary}\nURL: {a.url}" for i, a in enumerate(articles))
    return f"""You are the editorial engine for a daily AI micro-learning digest. Today's reader is {framing}

Read these {len(articles)} recent AI news items and identify the single most important, genuinely learnable development among them -- not just the flashiest headline. Extract signal from noise: skip pure hype, funding announcements with no substance, or anything you can't actually explain clearly.

ARTICLES:
{articles_block}

Produce the daily pulse content for this reader, grounded ONLY in the articles above -- do not introduce facts not present in them."""


def _source_articles_text(articles: list[RawArticle]) -> str:
    return "\n\n".join(f"{a.title} ({a.source}): {a.summary}" for a in articles)


def generate_and_evaluate(db: Session, track_slug: str, pulse_date: date | None = None) -> DailyPulse:
    pulse_date = pulse_date or date.today()

    track = db.query(Track).filter(Track.slug == track_slug).first()
    if not track:
        raise ValueError(f"Unknown track slug: {track_slug}")

    articles = fetch_recent_articles()
    if not articles:
        raise RuntimeError("No articles could be fetched from any configured RSS feed -- nothing to generate a pulse from.")

    generation = claude_client.generate(
        _build_prompt(articles, track_slug),
        temperature=0.4,  # low-ish: this is factual digest content, not creative writing
        response_schema=PULSE_SCHEMA,
    )
    parsed = json.loads(generation.text)

    det_failure = evals.deterministic_checks(
        parsed["summary"], parsed["sandbox_exercise"], parsed["quiz_question"], parsed["quiz_choices"], parsed["quiz_correct_index"]
    )

    if det_failure:
        status, eval_score, eval_notes = PulseStatus.FLAGGED, 0.0, f"Deterministic check failed: {det_failure}"
    else:
        judged = evals.score_with_llm_judge(
            _source_articles_text(articles), track.name, parsed["summary"], parsed["sandbox_exercise"], parsed["quiz_question"], parsed["quiz_choices"]
        )
        status = PulseStatus.PUBLISHED if judged.passed else PulseStatus.FLAGGED
        eval_score, eval_notes = judged.score, judged.notes

    pulse = DailyPulse(
        pulse_date=pulse_date,
        track_id=track.id,
        summary=parsed["summary"],
        sandbox_exercise=parsed["sandbox_exercise"],
        quiz_question=parsed["quiz_question"],
        quiz_choices=parsed["quiz_choices"],
        quiz_correct_index=parsed["quiz_correct_index"],
        source_urls=[a.url for a in articles],
        status=status,
        eval_score=eval_score,
        eval_notes=eval_notes,
        generation_model=settings.claude_model,
    )
    db.add(pulse)
    db.commit()
    db.refresh(pulse)
    return pulse
