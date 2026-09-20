#!/usr/bin/env python
"""Cron entrypoint -- run once daily, e.g. via crontab:

    0 6 * * * cd /path/to/backend && .venv/bin/python scripts/run_daily_pulse.py

Generates one Daily Pulse per track. A failure on one track (bad LLM
response, RSS feed down) is logged and does not stop the other tracks from
generating -- this is meant to run unattended, so partial success beats an
all-or-nothing failure.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.daily_pulse_agent import generate_and_evaluate
from app.core.db import SessionLocal
from app.models.track import Track

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily_pulse")


def main() -> int:
    db = SessionLocal()
    exit_code = 0
    try:
        tracks = db.query(Track).all()
        if not tracks:
            log.error("No Track rows in the database -- run the seed script first.")
            return 1

        for track in tracks:
            try:
                pulse = generate_and_evaluate(db, track_slug=track.slug)
                log.info("track=%s status=%s eval_score=%s pulse_id=%s", track.slug, pulse.status.value, pulse.eval_score, pulse.id)
                if pulse.status.value == "flagged":
                    # A real deployment would page/alert here (Slack webhook,
                    # PagerDuty, etc.) -- flagged means a human needs to look
                    # at it before it reaches users.
                    log.warning("Pulse for %s FLAGGED for review: %s", track.slug, pulse.eval_notes)
            except Exception:
                log.exception("Pulse generation failed for track=%s", track.slug)
                exit_code = 1
    finally:
        db.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
