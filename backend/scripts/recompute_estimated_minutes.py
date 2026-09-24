#!/usr/bin/env python
"""Recomputes Lesson.estimated_minutes from already-stored content_blocks,
using estimate_reading_words (see app/agents/lesson_blocks.py) instead of
whatever formula generated it originally. No LLM call -- pure local
recomputation, safe to rerun any time the estimate formula changes.
`python scripts/recompute_estimated_minutes.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.lesson_blocks import estimate_reading_words
from app.core.db import SessionLocal
from app.models.lesson import Lesson


def main():
    db = SessionLocal()
    try:
        lessons = [l for l in db.query(Lesson).all() if l.content_blocks]
        changed = 0
        for l in lessons:
            interactive_count = sum(1 for b in l.content_blocks if b.get("type") in ("check", "calculator"))
            new_estimate = max(5, round(estimate_reading_words(l.content_blocks) / 200) + interactive_count * 2)
            if new_estimate != l.estimated_minutes:
                print(f"  {l.title}: {l.estimated_minutes} -> {new_estimate} min")
                l.estimated_minutes = new_estimate
                changed += 1
        db.commit()
        print(f"\nRecomputed {len(lessons)} lesson(s), {changed} changed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
