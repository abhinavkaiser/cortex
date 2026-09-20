#!/usr/bin/env python
"""Generates real instructional content (Markdown) for every Lesson row
that doesn't have any yet. Run once after seeding, or after adding new
lessons: `python scripts/generate_lesson_content.py`

Deliberately a one-off authoring script, not part of the Daily Pulse's
recurring pipeline -- curriculum content is written once and read many
times, not regenerated daily. No eval-gating here either (contrast with
daily_pulse_agent.py): this is long-form reference material a human is
expected to actually review before publishing to real learners, not an
unattended daily feed.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models.lesson import Lesson
from app.services import claude_client

TRACK_FRAMING = {
    None: "a general audience with no assumed background -- this is Common Core, the shared foundation everyone reads before branching into a specialized track.",
    "leader": "an AI Leader (exec/manager) who needs to make organizational and strategic decisions about AI -- budget, risk, team structure, vendor choices. Keep implementation detail light; focus on what a decision-maker needs to reason well.",
    "practitioner": "an AI Practitioner (product/ops person using AI tools day-to-day) who needs practical, workflow-level understanding they can apply this week, not academic theory.",
    "developer": "an AI Developer (builds with AI/ML) who needs technical substance -- how it actually works, real tradeoffs, what they'd need to know to implement or evaluate it correctly.",
}

# Verbatim from the original AI Leader curriculum brief -- used to ground
# capstone/certification-project generation in the exact exercise that was
# specified, rather than letting the model invent a different one.
CAPSTONE_BRIEFS = {
    "Capstone: Use Case Value Matrix": "Users rank 5 hypothetical departmental AI projects based on estimated time-to-value and technical feasibility.",
    "Capstone: The ROI & API Cost Simulator": "Users input team size, workflow volume, and labor rates to compare the operational cost of API tokens versus projected labor hours saved.",
    "Capstone: Policy Red-Teaming": 'Users review a draft "Acceptable AI Use Policy" and must identify operational loopholes that could lead to data exposure.',
    "Capstone: Data Readiness Audit": "An interactive checklist that scores a hypothetical organization's readiness to deploy an internal RAG-based knowledge assistant.",
    "Capstone: Change Management Scenario": "Users navigate a simulated crisis where a department rejects a new AI tool due to fear of job displacement, choosing the correct leadership responses to rebuild trust.",
    "Final Certification Project: 12-Month AI Deployment Playbook": "Develop a comprehensive 12-month AI deployment playbook for a specific business unit, defending the chosen architecture, governance model, and budget allocation.",
}

LESSON_SCHEMA = {
    "type": "object",
    "properties": {
        "content_markdown": {
            "type": "string",
            "description": "The full lesson body in Markdown: a short intro, 2-4 headed sections building the idea up, at least one concrete example, and a brief closing takeaway. 500-800 words. Use ## for section headers, and real Markdown formatting (bold, lists) where it helps, not as decoration.",
        }
    },
    "required": ["content_markdown"],
}


def build_prompt(lesson: Lesson) -> str:
    track_slug = lesson.track.slug if lesson.track else None
    framing = TRACK_FRAMING.get(track_slug, TRACK_FRAMING["practitioner"])
    module_context = ""
    if lesson.module:
        module_context = f'\n\nThis lesson is part of "{lesson.module.title}". That module\'s objective: {lesson.module.objective}'

    brief = CAPSTONE_BRIEFS.get(lesson.title)
    if brief:
        return f"""Write a capstone exercise for an AI leadership course. The exercise's title is: "{lesson.title}"{module_context}

The exercise is specified as: {brief}

Write the full exercise as something a reader can actually work through on paper: set up a specific, concrete scenario (real-sounding numbers, department names, constraints -- not "Company X"), state exactly what the reader needs to decide or calculate, and close with 2-3 questions that force them to defend their reasoning. This is a written exercise, not an explanation of a concept -- don't teach theory here, put the reader in the scenario."""

    return f"""Write a self-contained lesson for an AI literacy course. The lesson's title is: "{lesson.title}"{module_context}

This is for {framing}

Write it like a good technical educator would: build the idea up from something the reader already understands, use one concrete, specific example (not a generic placeholder), and be honest about nuance/limitations rather than oversimplifying. Do not pad with filler or restate the title as an opening sentence."""


def main():
    db = SessionLocal()
    try:
        lessons = db.query(Lesson).filter((Lesson.content_markdown == "") | (Lesson.content_markdown.is_(None))).all()
        if not lessons:
            print("Every lesson already has content -- nothing to do.")
            return

        succeeded, failed = 0, []
        for lesson in lessons:
            label = lesson.module.title if lesson.module else ("Common Core" if not lesson.track_id else lesson.track.slug)
            print(f"Generating: {lesson.title} ({label})...")
            try:
                result = claude_client.generate(build_prompt(lesson), response_schema=LESSON_SCHEMA)
                parsed = json.loads(result.text)
                lesson.content_markdown = parsed["content_markdown"]
                db.commit()
                succeeded += 1
                print(f"  -> {len(parsed['content_markdown'])} chars written.")
            except Exception as err:  # noqa: BLE001 -- one lesson failing (even after generate()'s own retries) shouldn't abandon the rest of the batch
                db.rollback()
                failed.append(lesson.title)
                print(f"  -> FAILED: {err}. Skipping -- rerun this script to retry just the lessons still missing content.")

        print(f"\nDone -- generated content for {succeeded}/{len(lessons)} lesson(s).")
        if failed:
            print(f"Failed ({len(failed)}): {', '.join(failed)} -- rerun this script to retry them.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
