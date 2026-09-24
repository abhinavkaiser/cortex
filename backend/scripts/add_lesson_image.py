#!/usr/bin/env python
"""Inserts a real, already-generated image (see app/agents/image_mcp.py)
as the lead block of a lesson's content_blocks. Deliberately a separate,
manual curation step from lesson content generation -- see
app/agents/lesson_blocks.py's _clean_image for why images aren't part of
the AI-generation schema.

Usage:
  python scripts/add_lesson_image.py "<Lesson Title>" "/static/lesson-images/foo.png" "alt text" ["caption"] ["attribution"]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.lesson_blocks import blocks_to_plain_text, validate_and_clean_blocks
from app.core.db import SessionLocal
from app.models.lesson import Lesson


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    title, url, alt = sys.argv[1], sys.argv[2], sys.argv[3]
    caption = sys.argv[4] if len(sys.argv) > 4 else ""
    attribution = sys.argv[5] if len(sys.argv) > 5 else ""

    db = SessionLocal()
    try:
        lesson = db.query(Lesson).filter(Lesson.title == title).first()
        if not lesson:
            print(f"No lesson titled {title!r}.")
            sys.exit(1)

        image_block = {"type": "image", "url": url, "alt": alt, "caption": caption, "attribution": attribution}
        existing = [b for b in (lesson.content_blocks or []) if b.get("type") != "image"]
        blocks = validate_and_clean_blocks([image_block] + existing)
        if not blocks or blocks[0].get("type") != "image":
            print("Image block failed validation -- check the url starts with /static/lesson-images/ and alt text is non-empty.")
            sys.exit(1)

        lesson.content_blocks = blocks
        lesson.content_markdown = blocks_to_plain_text(blocks)
        db.commit()
        print(f"Added image to {title!r} ({len(blocks)} blocks total).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
