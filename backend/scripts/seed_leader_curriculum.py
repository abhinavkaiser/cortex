#!/usr/bin/env python
"""Seeds the real AI Leader curriculum (6 modules, each with 3 sub-topics +
a capstone exercise, plus a final certification project) -- replaces the
single placeholder "leader" lesson from scripts/seed.py's original stub
data. Run once: `python scripts/seed_leader_curriculum.py`

Lesson content itself isn't written here -- run
scripts/generate_lesson_content.py afterward to fill in real instructional
text for every lesson this creates.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import Base, SessionLocal, engine
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.track import Track

# (module title, objective, [(lesson title, minutes), ...])
CURRICULUM = [
    (
        "Module 1: The Enterprise AI Landscape & Strategic Value",
        "Calibrate expectations, demystify the technology without code, and identify where AI actually creates value versus where it introduces unnecessary risk.",
        [
            ("The AI Taxonomy for Executives", 12),
            ("Hype vs. Reality: The Capability Matrix", 10),
            ("The 10-20-70 Rule of AI Implementation", 10),
            ("Capstone: Use Case Value Matrix", 15),
        ],
    ),
    (
        "Module 2: The Economics of AI & Vendor Strategy",
        "Architect profitable scaling models, understand cost structures, and avoid getting locked into a single provider.",
        [
            ("Build vs. Buy vs. Partner", 12),
            ("Tokenomics and Inference Costs", 12),
            ("Mitigating Vendor Lock-in", 10),
            ("Capstone: The ROI & API Cost Simulator", 15),
        ],
    ),
    (
        "Module 3: Governance, Risk, and Compliance (GRC)",
        "Deploy AI safely, ensuring data privacy, ethical usage, and regulatory compliance.",
        [
            ("Data Privacy & Enterprise Agreements", 12),
            ("Managing Hallucinations and Liability", 12),
            ("Ethical AI and Bias Mitigation", 12),
            ("Capstone: Policy Red-Teaming", 15),
        ],
    ),
    (
        "Module 4: Data Strategy & Infrastructure Readiness",
        "Understand that a company's AI strategy is only as strong as its data strategy.",
        [
            ("Data as a Strategic Asset", 10),
            ("Introduction to RAG for Non-Technical Leaders", 12),
            ("Assessing Technical Debt", 10),
            ("Capstone: Data Readiness Audit", 15),
        ],
    ),
    (
        "Module 5: Organizational Design & Change Management",
        "Restructure teams for human-AI orchestration and drive workforce adoption.",
        [
            ("The Center of Excellence (CoE)", 10),
            ("Role Evolution & Upskilling", 12),
            ("Empathy & Trust in Leadership", 10),
            ("Capstone: Change Management Scenario", 15),
        ],
    ),
    (
        "Module 6: Execution & Measuring Success",
        "Move from pilots to systemic enterprise adoption.",
        [
            ("The Phased Rollout", 10),
            ("Defining KPIs for AI", 10),
            ("Building a Resilient AI Roadmap", 12),
            ("Final Certification Project: 12-Month AI Deployment Playbook", 30),
        ],
    ),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        track = db.query(Track).filter(Track.slug == "leader").first()
        if not track:
            print("No 'leader' track found -- run scripts/seed.py first.")
            return

        # Replace the original single placeholder lesson from seed.py, now
        # superseded by this real curriculum -- not deleting any user
        # progress rows tied to it beyond what naturally follows from the
        # lesson itself no longer existing (fine here: nobody's real
        # progress data depends on this in a fresh dev DB).
        old = db.query(Lesson).filter(Lesson.slug == "ai-roi-and-org-design", Lesson.module_id.is_(None)).first()
        if old:
            db.delete(old)
            db.flush()

        lesson_order = 0
        module_count = 0
        lesson_count = 0
        for module_index, (module_title, objective, lessons) in enumerate(CURRICULUM, start=1):
            existing_module = db.query(Module).filter(Module.track_id == track.id, Module.title == module_title).first()
            if existing_module:
                continue  # idempotent re-run: skip modules already seeded

            module = Module(track_id=track.id, title=module_title, objective=objective, order_index=module_index)
            db.add(module)
            db.flush()
            module_count += 1

            for lesson_title, minutes in lessons:
                lesson_order += 1
                slug = f"leader-{module_index}-{lesson_order}-" + "".join(c if c.isalnum() else "-" for c in lesson_title.lower())[:60]
                db.add(
                    Lesson(
                        track_id=track.id,
                        module_id=module.id,
                        slug=slug,
                        title=lesson_title,
                        content_markdown="",
                        order_index=lesson_order,
                        estimated_minutes=minutes,
                    )
                )
                lesson_count += 1

        db.commit()
        print(f"Seeded {module_count} module(s), {lesson_count} lesson(s) for the AI Leader track.")
        print("Run `python scripts/generate_lesson_content.py` next to generate real content for them.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
