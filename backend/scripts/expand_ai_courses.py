"""One-off authoring script: expands AI Leader with 5 new lessons closing
real curriculum gaps (agents, governance, security, copyright, sustainability),
and builds out AI Practitioner and AI Developer from single-lesson stubs into
full 3-module/12-lesson curricula, relocating each course's original lesson
in as that first module's capstone.

Idempotent: checks for existing titles before inserting, safe to re-run.
Leaves content_blocks empty on every new lesson -- run
scripts/generate_lesson_content.py afterward to fill them in.

Run once: `python scripts/expand_ai_courses.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module


def _find_module(db, course_slug: str, module_title: str) -> Module | None:
    course = db.query(Course).filter(Course.slug == course_slug).first()
    if not course:
        return None
    return next((m for m in course.modules if m.title == module_title), None)


def _insert_lesson_before(db, module: Module, title: str, before_title: str | None, slug: str, minutes: int = 15) -> tuple[Lesson, bool]:
    """Inserts a new empty lesson into `module`, positioned immediately
    before the lesson titled `before_title` (typically a capstone) -- or
    appended at the end if `before_title` is None. Renumbers the whole
    module's order_index afterward so it stays a clean 1..N sequence.
    Returns (lesson, was_newly_created)."""
    existing = next((l for l in module.lessons if l.title == title), None)
    if existing:
        return existing, False

    lessons = sorted(module.lessons, key=lambda l: l.order_index)
    insert_at = len(lessons)
    if before_title:
        for i, l in enumerate(lessons):
            if l.title == before_title:
                insert_at = i
                break

    lesson = Lesson(
        module_id=module.id,
        slug=slug,
        title=title,
        content_markdown="",
        content_blocks=[],
        estimated_minutes=minutes,
        order_index=insert_at,  # temporary, fixed by the renumber pass below
    )
    lessons.insert(insert_at, lesson)
    db.add(lesson)
    db.flush()
    for i, l in enumerate(lessons):
        l.order_index = i + 1
    return lesson, True


def _add_module(db, course: Course, title: str, objective: str, order_index: int) -> Module:
    existing = next((m for m in course.modules if m.title == title), None)
    if existing:
        return existing
    module = Module(course_id=course.id, title=title, objective=objective, order_index=order_index)
    db.add(module)
    db.flush()
    return module


def expand_ai_leader(db):
    additions = [
        ("Module 1: The Enterprise AI Landscape & Strategic Value", "AI Agents & Agentic Workflows", "ai-agents-and-agentic-workflows", "Capstone: Use Case Value Matrix"),
        ("Module 3: Governance, Risk, and Compliance (GRC)", "AI Governance & Regulatory Compliance", "ai-governance-and-regulatory-compliance", "Capstone: Policy Red-Teaming"),
        ("Module 3: Governance, Risk, and Compliance (GRC)", "Security & Adversarial Risk", "security-and-adversarial-risk", "Capstone: Policy Red-Teaming"),
        ("Module 3: Governance, Risk, and Compliance (GRC)", "AI Copyright & IP Exposure", "ai-copyright-and-ip-exposure", "Capstone: Policy Red-Teaming"),
        ("Module 4: Data Strategy & Infrastructure Readiness", "Sustainability & the Cost of Scale", "sustainability-and-the-cost-of-scale", "Capstone: Data Readiness Audit"),
    ]
    created = 0
    for module_title, lesson_title, slug, before in additions:
        module = _find_module(db, "ai-leader", module_title)
        if not module:
            print(f"  SKIP (module not found): {module_title}")
            continue
        _, was_new = _insert_lesson_before(db, module, lesson_title, before, slug)
        if was_new:
            created += 1
        print(f"  {'+' if was_new else '='} {lesson_title}  (in {module_title})")
    db.commit()
    print(f"AI Leader: {created} lessons added.\n")


def build_out_stub_course(db, course_slug: str, module1_title: str, module1_objective: str, capstone_title: str, capstone_slug_hint: str, module1_lessons: list[str], module2: tuple, module3: tuple):
    course = db.query(Course).filter(Course.slug == course_slug).first()
    if not course:
        print(f"  SKIP: course {course_slug!r} not found")
        return

    # The course's one pre-existing lesson becomes Module 1's capstone --
    # renamed with a "Capstone:" prefix and moved last in that module, its
    # existing generated content left untouched (already real, no need to
    # regenerate it just to fit a label). Identified by lowest id, not list
    # position/index [0] -- relationship order isn't guaranteed to match
    # order_index, and after a first run has added new (higher-id) lessons
    # to this same module, `.lessons[0]` can return one of those instead of
    # the original stub, mis-renaming it on a second run.
    stub_module = min(course.modules, key=lambda m: m.id)
    stub_lesson = min(stub_module.lessons, key=lambda l: l.id)
    if not stub_lesson.title.startswith("Capstone:"):
        stub_lesson.title = f"Capstone: {stub_lesson.title}"
    stub_module.title = module1_title
    stub_module.objective = module1_objective
    stub_module.order_index = 1

    created = 0
    for title in module1_lessons:
        slug = title.lower().replace(" ", "-").replace(",", "").replace("'", "").replace("?", "")
        _, was_new = _insert_lesson_before(db, stub_module, title, stub_lesson.title, f"{capstone_slug_hint}-{slug}"[:150])
        if was_new:
            created += 1
        print(f"  {'+' if was_new else '='} {title}  (in {module1_title})")

    for order_index, (title, objective, lessons, capstone) in enumerate([module2, module3], start=2):
        module = _add_module(db, course, title, objective, order_index)
        for lesson_title in lessons + [capstone]:
            slug = lesson_title.lower().replace(" ", "-").replace(",", "").replace("'", "").replace("?", "")
            _, was_new = _insert_lesson_before(db, module, lesson_title, None, f"{capstone_slug_hint}-{slug}"[:150])
            if was_new:
                created += 1
            print(f"  {'+' if was_new else '='} {lesson_title}  (in {title})")

    db.commit()
    print(f"{course.title}: {created} lessons added (plus 1 existing relocated as a capstone).\n")


def main():
    db = SessionLocal()
    try:
        print("=== AI Leader: adding 5 gap-closing lessons ===")
        expand_ai_leader(db)

        print("=== AI Practitioner: building out from stub ===")
        build_out_stub_course(
            db,
            "ai-practitioner",
            module1_title="Module 1: Foundations of Working with AI Tools",
            module1_objective="Build the judgment to pick the right tool, prompt it well, and verify its output before trusting it.",
            capstone_title="Capstone: Redesigning Your Workflow Around AI",
            capstone_slug_hint="practitioner-m1",
            module1_lessons=[
                "Choosing the Right Tool for the Job",
                "Prompting for Real Work, Not Demos",
                "Verifying AI Output Before You Trust It",
            ],
            module2=(
                "Module 2: AI-Augmented Daily Workflows",
                "Apply AI to the actual work of research, writing, and analysis -- and know where its limits are.",
                ["Research and Synthesis with AI", "Writing and Editing at Speed", "Data Analysis Without Writing Code"],
                "Capstone: Automate One Real Task This Week",
            ),
            module3=(
                "Module 3: Working with AI as a Team",
                "Turn individual AI skill into a team practice -- shared playbooks, real quality control, and honest limits.",
                ["Sharing Prompts and Playbooks", "Quality Control in an AI-Assisted Workflow", "When NOT to Use AI"],
                "Capstone: Team Workflow Audit",
            ),
        )

        print("=== AI Developer: building out from stub ===")
        build_out_stub_course(
            db,
            "ai-developer",
            module1_title="Module 1: Foundations for Building with LLMs",
            module1_objective="Understand enough real mechanism to reason correctly about model behavior, and ship a reliable first LLM feature.",
            capstone_title="Capstone: Building Production Features on LLM APIs",
            capstone_slug_hint="developer-m1",
            module1_lessons=[
                "How Transformers and Context Windows Actually Work",
                "Prompt Engineering for Production, Not Chat",
                "Structured Output and Function Calling",
            ],
            module2=(
                "Module 2: Retrieval, Memory, and Grounding",
                "Go from a RAG diagram to a real pipeline, and understand where retrieval actually fails in practice.",
                ["RAG Architecture Deep Dive", "Chunking, Embeddings, and Vector Search Tradeoffs", "Agentic Tool Use and Orchestration"],
                "Capstone: Design a RAG Pipeline for a Real Dataset",
            ),
            module3=(
                "Module 3: Running LLM Systems in Production",
                "Treat model failure as a design constraint: real evaluation, cost control, and guardrails.",
                ["Evaluation and Testing for Non-Deterministic Systems", "Latency, Cost, and Caching Strategies", "Guardrails, Safety, and Failure Modes"],
                "Capstone: Production Readiness Review",
            ),
        )

        total_lessons = db.query(Lesson).count()
        print(f"Done. Total lessons in DB now: {total_lessons}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
