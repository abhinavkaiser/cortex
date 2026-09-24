#!/usr/bin/env python
"""Generates real, interactive lesson content (a sequence of typed blocks --
text, diagrams, inline knowledge checks, callouts, calculators; see
app/agents/lesson_blocks.py) for every Lesson row that doesn't have any
blocks yet. Run once after seeding, or after adding new lessons, or to
upgrade a lesson still on the old plain-markdown-only format:
`python scripts/generate_lesson_content.py`

Pass a lesson title as an argument to (re)generate just that one lesson:
`python scripts/generate_lesson_content.py "The AI Taxonomy for Executives"`

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

from app.agents.lesson_blocks import BLOCK_SCHEMA, blocks_to_plain_text, estimate_reading_words, validate_and_clean_blocks
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


def build_prompt(lesson: Lesson) -> str:
    track_slug = lesson.track.slug if lesson.track else None
    framing = TRACK_FRAMING.get(track_slug, TRACK_FRAMING["practitioner"])
    module_context = ""
    if lesson.module:
        module_context = f'\n\nThis lesson is part of "{lesson.module.title}". That module\'s objective: {lesson.module.objective}'

    is_final_project = lesson.title.startswith("Final Certification Project")
    brief = CAPSTONE_BRIEFS.get(lesson.title)

    if brief:
        target = "50-60 minutes, 20-26 blocks" if is_final_project else "30-40 minutes, 16-22 blocks"
        base = (
            f'Build the interactive content for a capstone exercise titled "{lesson.title}"{module_context}\n\n'
            f"The exercise is specified as: {brief}\n\n"
            f"This needs real depth -- target {target}. This is a scenario the reader works through step by "
            "step, not a single question: build the situation up across several 'text' blocks (real-sounding "
            "numbers, department names, specific constraints and complications, not \"Company X\"), introduce a "
            "complication partway through that forces the reader to revise their thinking, include a 'calculator' "
            "block if the exercise genuinely involves computing something (most of these do -- ROI, cost, a "
            "score), a 'diagram' block if a framework or comparison helps the reader structure their decision, "
            "and multiple 'check' blocks at different decision points (not one trivia question at the end) that "
            "test whether the reader reached a defensible conclusion at each stage, with explanations that teach "
            "the reasoning, not just confirm the answer."
        )
    else:
        base = (
            f'Build the interactive content for a lesson titled "{lesson.title}"{module_context}\n\n'
            f"This is for {framing}\n\n"
            "This needs real depth -- target 20-25 minutes of genuine engagement, not a summary. Build the idea "
            "up in stages from something the reader already understands: motivate it with a concrete scenario "
            "specific to this audience's actual job, explain the mechanism, then get into the nuance, exceptions, "
            "and failure modes that separate a real practitioner from someone who skimmed a blog post. Use 2-3 "
            "diagrams to visualize different facets of the lesson's structure -- pick whichever shape actually "
            "fits each one (a 2x2 matrix if weighing two dimensions, tiers if it's a hierarchy/spectrum, a "
            "comparison if evaluating options, a cycle if it's a repeating process) -- don't force the same shape "
            "twice if a different one fits better. Place 'check' blocks right after the section they test, spread "
            "across the whole lesson, not bunched at the end. Be honest about nuance/limitations rather than "
            "oversimplifying."
        )
    return base + "\n\nDo not restate the title as an opening sentence. Do not pad with filler -- depth means more real substance, not repeating the same point in different words."


def generate_one(db, lesson: Lesson) -> int:
    """Returns the number of blocks written.

    validate_and_clean_blocks only checks that each individual block is
    structurally sound -- it says nothing about whether the *set* of blocks
    actually satisfies the brief (e.g. "at least one diagram", "real depth
    not a summary"). Real generations came back with zero diagram blocks,
    and separately with the whole course landing at ~5 hours against a
    10-hour target, despite both being asked for in the prompt -- and
    passed validation cleanly because every block that WAS returned was
    individually well-formed. This enforces both requirements with a
    retry, the same pattern already proven for shape-mismatch retries in
    claude_client.generate() itself."""
    is_capstone = lesson.title in CAPSTONE_BRIEFS
    is_final_project = lesson.title.startswith("Final Certification Project")
    min_blocks = 14 if is_final_project else 10 if is_capstone else 12

    prompt = build_prompt(lesson)
    blocks: list[dict] = []

    for attempt in range(3):
        result = claude_client.generate(prompt, response_schema=BLOCK_SCHEMA)
        parsed = json.loads(result.text)
        blocks = validate_and_clean_blocks(parsed.get("blocks", []))
        if not blocks:
            raise ValueError("model returned no usable blocks after validation")

        has_diagram = any(b.get("type") == "diagram" for b in blocks)
        deep_enough = len(blocks) >= min_blocks
        missing = []
        if not (is_capstone or has_diagram):
            missing.append(
                "zero 'diagram' blocks -- include at least one visualizing the lesson's core structure "
                "(tiers/matrix/comparison/cycle, whichever fits)"
            )
        if not deep_enough:
            missing.append(f"only {len(blocks)} blocks -- this needs at least {min_blocks}, with real substance in each, not padding")
        if not missing:
            break
        prompt = f"{prompt}\n\nYour previous attempt fell short: {'; '.join(missing)}. Do better this time."
    else:
        raise ValueError(f"model did not meet the depth/diagram requirements after 3 attempts (last: {len(blocks)} blocks)")

    # A real estimate from the actual generated content, not a fixed seed-
    # time guess: reading pace over EVERY block's real content (including
    # diagram item labels/descriptions -- estimate_reading_words walks the
    # actual structure, unlike blocks_to_plain_text's short placeholders,
    # which silently undercounted every diagram-heavy lesson) plus a
    # couple minutes per interactive block for the time actually spent
    # engaging with it (answering a check, working through a calculator),
    # not just scrolling past it.
    word_count = estimate_reading_words(blocks)
    interactive_count = sum(1 for b in blocks if b.get("type") in ("check", "calculator"))
    lesson.estimated_minutes = max(5, round(word_count / 200) + interactive_count * 2)

    lesson.content_blocks = blocks
    lesson.content_markdown = blocks_to_plain_text(blocks)
    db.commit()
    return len(blocks)


def main():
    only_title = None
    force_track = None
    args = sys.argv[1:]
    if args and args[0] == "--track" and len(args) > 1:
        force_track = args[1]
    elif args:
        only_title = args[0]

    db = SessionLocal()
    try:
        if only_title:
            lessons = db.query(Lesson).filter(Lesson.title == only_title).all()
        elif force_track:
            # Force-regenerate every lesson in a track regardless of
            # whether it already has content -- for upgrading existing
            # lessons to a new depth/quality bar, not just filling gaps.
            from app.models.track import Track

            track = db.query(Track).filter(Track.slug == force_track).first()
            if not track:
                print(f"No track {force_track!r}.")
                return
            lessons = db.query(Lesson).filter(Lesson.track_id == track.id).order_by(Lesson.order_index).all()
        else:
            # JSON-column equality against a Python list isn't reliable across
            # backends at the SQL level -- filter in Python instead.
            lessons = [l for l in db.query(Lesson).all() if not l.content_blocks]

        if not lessons:
            print("Nothing to do." if not only_title else f"No lesson titled {only_title!r} found.")
            return

        succeeded, failed = 0, []
        for lesson in lessons:
            label = lesson.module.title if lesson.module else ("Common Core" if not lesson.track_id else lesson.track.slug)
            print(f"Generating: {lesson.title} ({label})...")
            try:
                n = generate_one(db, lesson)
                succeeded += 1
                print(f"  -> {n} block(s) written.")
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
