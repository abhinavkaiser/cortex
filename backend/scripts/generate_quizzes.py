#!/usr/bin/env python
"""One-off authoring script: generates a real 5-question multiple-choice
quiz for every chapter (Module) that has lessons but no Quiz yet -- grounded
in that chapter's actual lesson content, not generic questions. Mirrors
generate_lesson_content.py's own real-Claude-CLI, retry-on-bad-JSON pattern.

Run once: `python scripts/generate_quizzes.py`
Regenerate just one chapter: `python scripts/generate_quizzes.py "Module 1: ..."`
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.lesson_blocks import blocks_to_plain_text
from app.core.db import SessionLocal
from app.models.course import Quiz
from app.models.module import Module
from app.services import claude_client

PASSING_SCORE = 70


def module_content(module: Module) -> str:
    parts = []
    for lesson in sorted(module.lessons, key=lambda l: l.order_index):
        text = blocks_to_plain_text(lesson.content_blocks) if lesson.content_blocks else lesson.content_markdown
        parts.append(f"## {lesson.title}\n\n{text}")
    return "\n\n---\n\n".join(parts)


QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "choices": {"type": "array", "items": {"type": "string"}},
                    "correct_index": {"type": "integer"},
                },
                "required": ["question", "choices", "correct_index"],
            },
        },
    },
    "required": ["title", "questions"],
}


def build_prompt(module: Module) -> str:
    content = module_content(module)
    return f"""Write a 5-question multiple-choice quiz testing real understanding of this chapter's actual content, not trivia or vague generalities. Every question and every wrong answer must be something a careful reader could only get right/wrong based on what's actually written below -- no outside knowledge required, no "which of these sounds most professional" filler.

Chapter: "{module.title}"
Objective: {module.objective}

Content:
{content[:12000]}

Rules:
- Each question has exactly 4 choices, exactly one correct (correct_index 0-3).
- Wrong choices should be plausible (a real misreading or common mistake), not obviously silly.
- Vary what's being tested across the 5 questions -- don't ask 5 variations of the same fact.
- title: a short chapter quiz title, max 8 words."""


def generate_one(db, module: Module) -> int:
    prompt = build_prompt(module)
    result = claude_client.generate(prompt, response_schema=QUIZ_SCHEMA)
    parsed = json.loads(result.text) if isinstance(result.text, str) else result.text
    questions = parsed.get("questions") or []
    if len(questions) < 3:
        raise ValueError(f"Only {len(questions)} questions returned, need at least 3")

    quiz = Quiz(
        module_id=module.id,
        title=parsed.get("title") or f"{module.title} Quiz",
        passing_score=PASSING_SCORE,
        questions=questions,
    )
    db.add(quiz)
    db.commit()
    return len(questions)


def main():
    only_title = sys.argv[1] if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        query = db.query(Module)
        if only_title:
            modules = [m for m in query.all() if m.title == only_title]
        else:
            modules = [m for m in query.all() if m.lessons and not m.quiz]

        if not modules:
            print("Nothing to do." if not only_title else f"No module titled {only_title!r} found (or it already has a quiz).")
            return

        succeeded, failed = 0, []
        for module in modules:
            print(f"Generating quiz: {module.title} ({module.course.slug if module.course else 'no course'})...")
            try:
                n = generate_one(db, module)
                succeeded += 1
                print(f"  -> {n} question(s) written.")
            except Exception as err:  # noqa: BLE001
                db.rollback()
                failed.append(module.title)
                print(f"  -> FAILED: {err}")

        print(f"\nDone. {succeeded} succeeded, {len(failed)} failed.")
        if failed:
            print("Failed:", failed)
    finally:
        db.close()


if __name__ == "__main__":
    main()
