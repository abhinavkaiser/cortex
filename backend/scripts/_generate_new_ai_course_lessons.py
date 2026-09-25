"""Throwaway, one-off companion to expand_ai_courses.py -- generates content
for exactly the lessons that script just added (empty content_blocks AND
belonging to ai-leader/ai-practitioner/ai-developer), skipping the two demo
courses (Prompt Engineering for Teams, Building AI-Powered Products), which
are deliberately plain-markdown-authored and must not be swept up by the
generic "any lesson with empty content_blocks" default in
generate_lesson_content.py. Not meant to be reused after this run -- delete
once done."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_lesson_content import generate_one
from app.core.db import SessionLocal
from app.models.course import Course
from app.models.lesson import Lesson

TARGET_COURSES = {"ai-leader", "ai-practitioner", "ai-developer"}


def main():
    db = SessionLocal()
    try:
        lessons = [
            l
            for l in db.query(Lesson).all()
            if not l.content_blocks and l.module and l.module.course and l.module.course.slug in TARGET_COURSES
        ]
        lessons.sort(key=lambda l: (l.module.course.slug, l.module.order_index, l.order_index))
        print(f"{len(lessons)} lessons to generate.")

        succeeded, failed = 0, []
        for lesson in lessons:
            print(f"Generating: {lesson.title} ({lesson.module.course.slug} / {lesson.module.title})...")
            try:
                n = generate_one(db, lesson)
                succeeded += 1
                print(f"  -> {n} block(s) written.")
            except Exception as err:  # noqa: BLE001
                db.rollback()
                failed.append(lesson.title)
                print(f"  -> FAILED: {err}")

        print(f"\nDone. {succeeded} succeeded, {len(failed)} failed.")
        if failed:
            print("Failed:", failed)
    finally:
        db.close()


if __name__ == "__main__":
    main()
