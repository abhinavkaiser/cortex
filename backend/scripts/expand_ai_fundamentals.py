"""One-off authoring script: brings AI Fundamentals up to the shape of the
other compact courses.

AI Fundamentals shipped as a single "Foundations" chapter of 3 lessons
(~2,600 words total) while every other course on the platform runs 3-6
chapters and 10,000-46,000 words -- a real gap for what is meant to be the
entry-point course. This adds two chapters of three lessons each, taking it
to 3 chapters / 9 lessons, matching prompt-engineering-for-teams and
building-ai-powered-products.

Chapter topics deliberately stay at beginner depth rather than duplicating
AI Practitioner (which covers day-to-day tool use for working professionals
at much greater depth) -- this course's job is "I have never really used
this; what is it and what should I watch out for".

Idempotent: checks for existing titles before inserting, safe to re-run.
Leaves content_blocks empty on every new lesson -- run
scripts/generate_lesson_content.py --course ai-fundamentals afterward to
fill them in, then scripts/generate_quizzes.py for the new chapters.

Run once: `python scripts/expand_ai_fundamentals.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module

COURSE_SLUG = "ai-fundamentals"

NEW_CHAPTERS = [
    {
        "title": "Using AI Day to Day",
        "objective": (
            "Turn a general understanding of what AI tools are into practical, repeatable "
            "everyday use -- knowing which tasks to hand over, how to ask well, and how to "
            "work with the output rather than just accepting it."
        ),
        "lessons": [
            ("What AI Is Actually Good At (and What It Isn't)",
             "what-ai-is-good-at-and-what-it-isnt", 18),
            ("Writing a Prompt That Gets a Useful Answer",
             "writing-a-prompt-that-gets-a-useful-answer", 20),
            ("Working With the Output: Edit, Verify, Reuse",
             "working-with-the-output-edit-verify-reuse", 18),
        ],
    },
    {
        "title": "Judgement, Risk and Responsibility",
        "objective": (
            "Build the habits that separate someone who uses AI safely from someone who gets "
            "burned by it -- spotting confident errors, knowing what should never be pasted "
            "into a chatbot, and understanding where responsibility sits when AI gets it wrong."
        ),
        "lessons": [
            ("Spotting Confident Nonsense: Verifying What AI Tells You",
             "spotting-confident-nonsense-verifying-ai", 20),
            ("Privacy, Confidentiality and What Not to Paste",
             "privacy-confidentiality-what-not-to-paste", 18),
            ("Who Is Responsible When AI Gets It Wrong?",
             "who-is-responsible-when-ai-gets-it-wrong", 18),
        ],
    },
]


def _add_module(db, course: Course, title: str, objective: str, order_index: int) -> tuple[Module, bool]:
    existing = next((m for m in course.modules if m.title == title), None)
    if existing:
        return existing, False
    module = Module(course_id=course.id, title=title, objective=objective, order_index=order_index)
    db.add(module)
    db.flush()
    return module, True


def _add_lesson(db, module: Module, title: str, slug: str, minutes: int, order_index: int) -> bool:
    if any(l.title == title for l in module.lessons):
        return False
    db.add(Lesson(
        module_id=module.id,
        slug=slug,
        title=title,
        content_markdown="",
        content_blocks=[],
        estimated_minutes=minutes,
        order_index=order_index,
    ))
    db.flush()
    return True


def main():
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.slug == COURSE_SLUG).first()
        if not course:
            print(f"Course '{COURSE_SLUG}' not found -- nothing to do.")
            return

        # Append after whatever chapters already exist rather than assuming
        # the original "Foundations" chapter is the only one (re-runs, or a
        # partially-applied earlier run, must not collide on order_index).
        next_order = max((m.order_index for m in course.modules), default=0) + 1

        chapters_created = lessons_created = 0
        for spec in NEW_CHAPTERS:
            module, is_new = _add_module(db, course, spec["title"], spec["objective"], next_order)
            if is_new:
                chapters_created += 1
                next_order += 1
                print(f"+ chapter: {spec['title']}")
            else:
                print(f"= chapter exists: {spec['title']}")

            for i, (title, slug, minutes) in enumerate(spec["lessons"], start=1):
                if _add_lesson(db, module, title, slug, minutes, i):
                    lessons_created += 1
                    print(f"    + lesson: {title}")
                else:
                    print(f"    = lesson exists: {title}")

        db.commit()
        print(f"\nDone. {chapters_created} chapter(s), {lessons_created} lesson(s) created.")
        if lessons_created:
            print("Next: scripts/generate_lesson_content.py --course ai-fundamentals")
            print("Then: scripts/generate_quizzes.py")
    finally:
        db.close()


if __name__ == "__main__":
    main()
