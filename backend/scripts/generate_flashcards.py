#!/usr/bin/env python
"""One-off authoring script: generates a flashcard review deck for every
chapter (Module) that has lessons but no deck yet -- grounded in that
chapter's actual lesson content, not generic chess-of-the-topic cards.

Structurally a twin of generate_quizzes.py (same Claude-CLI call, same
retry-on-bad-shape, same default-select-what's-missing behaviour), and it
reuses that script's module_content() so both features read the same source
text rather than two slightly different concatenations drifting apart.

Run once: `python scripts/generate_flashcards.py`
Regenerate just one chapter: `python scripts/generate_flashcards.py "Module 1: ..."`
  (replaces that chapter's existing deck -- one deck per chapter)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.flashcards import FLASHCARD_SCHEMA, MIN_CARDS, validate_and_clean_cards
from app.core.db import SessionLocal
from app.models.course import FlashcardDeck
from app.models.module import Module
from app.services import claude_client

# module_content lives in the quiz generator; importing it keeps the two
# generators reading identical chapter text instead of duplicating the
# concatenation logic.
from generate_quizzes import module_content

MAX_ATTEMPTS = 3


def build_prompt(module: Module) -> str:
    content = module_content(module)
    return f"""Write a flashcard review deck for this chapter. These are for a learner revising AFTER reading it -- cards must stand alone and be answerable from the card itself.

Chapter: "{module.title}"
Objective: {module.objective}

Content:
{content[:12000]}

Write {MIN_CARDS}-15 cards covering the real substance of this chapter: the terms it defined, the distinctions it drew, the numbers and thresholds it gave, the failure modes it warned about, the frameworks it introduced.

Do not write cards about the course structure itself, and do not introduce anything the chapter above didn't actually teach."""


def generate_one(db, module: Module) -> int:
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = claude_client.generate(build_prompt(module), response_schema=FLASHCARD_SCHEMA)
            parsed = json.loads(result.text) if isinstance(result.text, str) else result.text
            cards = validate_and_clean_cards(parsed.get("cards"))
            if len(cards) < MIN_CARDS:
                raise ValueError(f"only {len(cards)} valid card(s) after cleaning, need {MIN_CARDS}")

            # One deck per chapter: replace rather than accumulate, so a
            # rerun fixes a bad deck instead of leaving both behind.
            existing = db.query(FlashcardDeck).filter(FlashcardDeck.module_id == module.id).first()
            if existing:
                existing.title = parsed.get("title") or f"{module.title} -- key terms"
                existing.cards = cards
            else:
                db.add(FlashcardDeck(
                    module_id=module.id,
                    title=parsed.get("title") or f"{module.title} -- key terms",
                    cards=cards,
                ))
            db.commit()
            return len(cards)
        except Exception as err:  # noqa: BLE001
            db.rollback()
            last_err = err
            if attempt < MAX_ATTEMPTS:
                print(f"  (attempt {attempt} failed: {err}; retrying)")
    raise last_err


def main():
    only_title = sys.argv[1] if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        all_modules = db.query(Module).all()
        if only_title:
            modules = [m for m in all_modules if m.title == only_title]
        else:
            modules = [m for m in all_modules if m.lessons and not m.flashcard_deck]

        if not modules:
            print("Nothing to do." if not only_title
                  else f"No module titled {only_title!r} found.")
            return

        succeeded, failed = 0, []
        for module in modules:
            course = module.course.slug if module.course else "no course"
            print(f"Generating flashcards: {module.title} ({course})...")
            try:
                n = generate_one(db, module)
                succeeded += 1
                print(f"  -> {n} card(s) written.")
            except Exception as err:  # noqa: BLE001
                failed.append(module.title)
                print(f"  -> FAILED: {err}")

        print(f"\nDone. {succeeded} succeeded, {len(failed)} failed.")
        if failed:
            print("Failed:", failed)
    finally:
        db.close()


if __name__ == "__main__":
    main()
