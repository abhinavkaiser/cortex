#!/usr/bin/env python
"""Seeds the three tracks and a handful of Common Core + track lessons.
Run once against a fresh database: `python scripts/seed.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import Base, SessionLocal, engine
from app.models.lesson import Lesson
from app.models.track import Track

TRACKS = [
    {"slug": "leader", "name": "AI Leader", "description": "Strategic and organizational AI literacy for execs and managers."},
    {"slug": "practitioner", "name": "AI Practitioner", "description": "Practical, workflow-level AI skills for people using AI tools day-to-day."},
    {"slug": "developer", "name": "AI Developer", "description": "Technical depth for people building with AI/ML."},
]

COMMON_CORE_LESSONS = [
    {"slug": "what-is-a-language-model", "title": "What a Language Model Actually Does", "order_index": 1, "estimated_minutes": 8},
    {"slug": "prompting-fundamentals", "title": "Prompting Fundamentals", "order_index": 2, "estimated_minutes": 10},
    {"slug": "ai-risk-and-limitations", "title": "Where AI Breaks: Hallucination, Bias, and Limits", "order_index": 3, "estimated_minutes": 10},
]

TRACK_LESSONS = {
    "leader": [{"slug": "ai-roi-and-org-design", "title": "Evaluating AI ROI and Org Design", "order_index": 1, "estimated_minutes": 12}],
    "practitioner": [{"slug": "ai-augmented-workflows", "title": "Redesigning Your Workflow Around AI", "order_index": 1, "estimated_minutes": 12}],
    "developer": [{"slug": "building-with-llm-apis", "title": "Building Production Features on LLM APIs", "order_index": 1, "estimated_minutes": 15}],
}


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        track_by_slug = {}
        for t in TRACKS:
            existing = db.query(Track).filter(Track.slug == t["slug"]).first()
            if existing:
                track_by_slug[t["slug"]] = existing
                continue
            track = Track(**t)
            db.add(track)
            db.flush()
            track_by_slug[t["slug"]] = track

        for lesson_data in COMMON_CORE_LESSONS:
            if not db.query(Lesson).filter(Lesson.slug == lesson_data["slug"]).first():
                db.add(Lesson(track_id=None, content_markdown="", **lesson_data))

        for slug, lessons in TRACK_LESSONS.items():
            for lesson_data in lessons:
                if not db.query(Lesson).filter(Lesson.slug == lesson_data["slug"]).first():
                    db.add(Lesson(track_id=track_by_slug[slug].id, content_markdown="", **lesson_data))

        db.commit()
        print(f"Seeded {len(TRACKS)} tracks, {len(COMMON_CORE_LESSONS)} common-core lessons, {sum(len(v) for v in TRACK_LESSONS.values())} track lessons.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
