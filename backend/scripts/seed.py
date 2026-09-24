#!/usr/bin/env python
"""Seeds the three tracks and a handful of Common Core + track lessons, plus
three example instructor-authored Courses (distinct from the fixed Tracks --
see models/course.py) so the general-purpose course system is clickable
end-to-end after a fresh `python scripts/seed.py`, not just empty scaffolding.
The third course specifically exercises everything added on top of the
original course system: video/document/link lesson blocks, all four quiz
question types (including a short_answer one, with a real pending attempt
already sitting in the instructor's grading queue), and a
certificate_validity_days expiry. Run once against a fresh database.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.course import Course, Enrollment, Quiz, QuizAttempt
from app.models.lesson import Lesson, UserLessonProgress
from app.models.module import Module
from app.models.track import Track
from app.models.user import User, UserRole

STATIC_DIR = Path(__file__).resolve().parent.parent / "static" / "course-uploads"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
DEMO_PDF_NAME = "ai-media-literacy-handout-demo.pdf"

LEARNER = {"email": "learner@cortex.ai", "password": "learnerpass123", "full_name": "Jordan Lee"}


def _write_demo_pdf() -> None:
    """A real, small PDF for the seeded 'document' lesson block to point
    at -- generated with reportlab (the same library
    services/certificate_pdf.py uses) rather than checking in a binary
    file, so there's nothing to keep in sync if the demo copy changes."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    path = STATIC_DIR / DEMO_PDF_NAME
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "AI Media Literacy -- Course Handout")
    c.setFont("Helvetica", 11)
    lines = [
        "This one-page handout is seeded demo content for the 'document' lesson",
        "block type -- a real PDF served from backend/static/course-uploads/,",
        "the same place POST /api/courses/{id}/upload saves instructor uploads.",
        "",
        "Three things worth remembering when a document is the primary lesson",
        "content rather than a supplement: (1) always keep a download link",
        "visible, not just an inline viewer -- some browsers and most mobile",
        "apps handle embedded PDFs poorly; (2) a document lesson still needs a",
        "real estimated_minutes, learners skim PDFs slower than prose; (3) if",
        "the source document changes, upload a new one and update the lesson's",
        "content_blocks -- there's no versioning, the old file just becomes",
        "unreferenced.",
    ]
    y = 690
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.showPage()
    c.save()

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

INSTRUCTOR = {"email": "instructor@cortex.ai", "password": "instructorpass123", "full_name": "Priya Sharma"}

# Two demo courses, each with 3 chapters (Modules) of 2 lessons apiece, and
# a quiz on the first chapter -- enough real structure to exercise catalog
# browsing, chapter/lesson navigation, quiz-taking, enrollment progress, and
# certificate issuance end to end.
COURSES = [
    {
        "slug": "prompt-engineering-for-teams",
        "title": "Prompt Engineering for Teams",
        "category": "AI Skills",
        "description": "A practical course for teams standardizing how they write, share, and improve prompts together -- not a one-off tips list, a repeatable practice.",
        "chapters": [
            {
                "title": "Foundations of Prompting",
                "objective": "Understand what makes a prompt reliable, and why most failures are structural, not phrasing.",
                "lessons": [
                    {
                        "slug": "anatomy-of-a-good-prompt",
                        "title": "Anatomy of a Good Prompt",
                        "estimated_minutes": 9,
                        "content_markdown": (
                            "A prompt that works reliably usually has four parts, in this order: **role** "
                            "(who the model should act as), **context** (the specific facts it needs that "
                            "it can't infer), **task** (the exact action, stated as an instruction, not a "
                            "question), and **format** (what the output should look like).\n\n"
                            "Most prompts that fail are missing context, not phrased badly. \"Write a "
                            "summary of this\" fails less because of word choice and more because the "
                            "model doesn't know how long, for whom, or what to leave out. Naming the "
                            "missing constraint usually fixes more than rewording the sentence around it.\n\n"
                            "A useful habit: after writing a prompt, ask \"what would a new hire need to "
                            "know to do this task that isn't in here?\" Whatever's missing from that answer "
                            "is usually the fix."
                        ),
                    },
                    {
                        "slug": "common-failure-modes",
                        "title": "Common Failure Modes",
                        "estimated_minutes": 10,
                        "content_markdown": (
                            "Three failure modes account for most bad outputs on a team: **ambiguous "
                            "scope** (the prompt technically answers the question but not the one you "
                            "meant), **silent assumptions** (the model fills a gap with something "
                            "plausible-sounding instead of asking), and **format drift** (the output is "
                            "correct but not usable as-is, so someone has to reformat it by hand every "
                            "time).\n\n"
                            "Format drift is the most expensive one on a team, because it's invisible in "
                            "a single use and only shows up as wasted time at scale. Locking the output "
                            "format into the prompt itself (an example, a schema, explicit headers) is "
                            "cheap insurance against it.\n\n"
                            "When a prompt fails, resist the urge to just add more adjectives (\"be very "
                            "precise\"). Diagnose which of the three modes it is first -- the fix is "
                            "usually a missing constraint, not stronger wording."
                        ),
                    },
                ],
                "quiz": {
                    "title": "Foundations of Prompting Quiz",
                    "passing_score": 70,
                    "questions": [
                        {
                            "question": "A prompt that technically answers the question but not the one the author meant is an example of:",
                            "choices": ["Format drift", "Ambiguous scope", "A model capability limit", "A tokenizer issue"],
                            "correct_index": 1,
                        },
                        {
                            "question": "What's the most reliable fix for output that's correct but not usable as-is?",
                            "choices": [
                                "Add more adjectives like 'be precise'",
                                "Lower the temperature",
                                "Lock the output format into the prompt (example or schema)",
                                "Ask the model to try again",
                            ],
                            "correct_index": 2,
                        },
                        {
                            "question": "Which of these is NOT one of the four parts of a reliable prompt?",
                            "choices": ["Role", "Context", "Task", "Temperature"],
                            "correct_index": 3,
                        },
                    ],
                },
            },
            {
                "title": "Prompting Patterns for Teams",
                "objective": "Reusable patterns that hold up across different tasks, not just the one you tested them on.",
                "lessons": [
                    {
                        "slug": "role-and-context-framing",
                        "title": "Role and Context Framing",
                        "estimated_minutes": 8,
                        "content_markdown": (
                            "Assigning a role (\"You are a technical editor reviewing for clarity\") does "
                            "two things: it narrows the space of plausible outputs, and it gives you a "
                            "one-line way to redirect the model when it drifts (\"stay in the technical "
                            "editor role -- don't add new content, only tighten what's here\").\n\n"
                            "Context framing works best as a short, front-loaded block, not scattered "
                            "through the prompt. Put the facts the model needs first, the instruction "
                            "second -- it reads more like a briefing than a conversation, which is exactly "
                            "the point."
                        ),
                    },
                    {
                        "slug": "chaining-and-decomposition",
                        "title": "Chaining and Decomposition",
                        "estimated_minutes": 11,
                        "content_markdown": (
                            "A single prompt asking for research, analysis, and a recommendation in one "
                            "shot usually does all three worse than three separate prompts chained "
                            "together, each one's output feeding the next. Decomposition trades a bit of "
                            "extra setup for outputs you can actually inspect and correct at each step.\n\n"
                            "A good rule of thumb: if you'd hesitate to ship the output of step 2 without "
                            "reading it, it should be its own prompt -- not a paragraph buried inside a "
                            "longer one."
                        ),
                    },
                ],
            },
            {
                "title": "Rolling It Out",
                "objective": "Turn individual prompting skill into a team practice that survives someone going on vacation.",
                "lessons": [
                    {
                        "slug": "building-a-team-prompt-library",
                        "title": "Building a Team Prompt Library",
                        "estimated_minutes": 9,
                        "content_markdown": (
                            "A prompt library is only useful if it's a place people actually check before "
                            "writing a new prompt from scratch -- that means findable by task, not by "
                            "whoever wrote it, and each entry short enough to skim in ten seconds "
                            "(task, example input, example output).\n\n"
                            "Start with the five prompts your team reruns most often, not an exhaustive "
                            "catalog. A library with five entries everyone actually uses beats one with "
                            "fifty nobody opens."
                        ),
                    },
                    {
                        "slug": "measuring-whats-working",
                        "title": "Measuring What's Working",
                        "estimated_minutes": 8,
                        "content_markdown": (
                            "You don't need a formal eval pipeline to know if a prompt is working -- "
                            "tracking how often someone has to manually fix the output before using it is "
                            "a good enough proxy to start, and it's a number people already feel "
                            "intuitively.\n\n"
                            "Revisit prompts on a schedule, not just when they break. Model updates and "
                            "shifting team needs both quietly degrade a prompt that used to work fine."
                        ),
                    },
                ],
            },
        ],
    },
    {
        "slug": "building-ai-powered-products",
        "title": "Building AI-Powered Products",
        "category": "Product & Engineering",
        "description": "How to scope, design, and ship a product feature that uses an LLM -- for PMs and engineers deciding where AI actually belongs in the product, not just that it should be somewhere.",
        "chapters": [
            {
                "title": "Product Fundamentals",
                "objective": "Decide where AI genuinely helps vs. where it's a solution looking for a problem.",
                "lessons": [
                    {
                        "slug": "where-ai-fits-in-your-product",
                        "title": "Where AI Fits in Your Product",
                        "estimated_minutes": 10,
                        "content_markdown": (
                            "AI features tend to work best in one of three shapes: reducing a task from "
                            "many steps to one (drafting, summarizing), surfacing something a user would "
                            "otherwise miss (anomalies, relevant docs), or handling genuine ambiguity a "
                            "rules engine can't (open-ended text, mixed intent).\n\n"
                            "If a feature could be built as a deterministic rule or lookup table just as "
                            "well, building it with an LLM usually adds cost and unpredictability without "
                            "adding value. The test isn't \"can AI do this\" -- it's \"does this task "
                            "actually need judgment a rule can't express.\""
                        ),
                    },
                    {
                        "slug": "scoping-an-ai-feature",
                        "title": "Scoping an AI Feature",
                        "estimated_minutes": 11,
                        "content_markdown": (
                            "Scope an AI feature by its failure mode, not just its happy path: what does "
                            "the user see when the model is confidently wrong, and how do they recover "
                            "without losing trust in the whole product? That answer belongs in the spec, "
                            "not left to whoever implements it later.\n\n"
                            "A useful scoping question: \"what's the cost of this being wrong 10% of the "
                            "time?\" If that cost is high (financial, safety, irreversible), the feature "
                            "needs a human-in-the-loop step before it needs a better prompt."
                        ),
                    },
                ],
                "quiz": {
                    "title": "Product Fundamentals Quiz",
                    "passing_score": 70,
                    "questions": [
                        {
                            "question": "If a task could be solved just as well with a deterministic rule, what does that suggest about using an LLM for it?",
                            "choices": [
                                "LLMs are always a strict upgrade over rules",
                                "It probably adds cost/unpredictability without adding value",
                                "It's required for the feature to feel modern",
                                "Rules and LLMs can't be compared",
                            ],
                            "correct_index": 1,
                        },
                        {
                            "question": "What belongs in the spec for an AI feature, not left for later?",
                            "choices": [
                                "The exact model version forever",
                                "What the user sees when the model is confidently wrong",
                                "The marketing copy",
                                "The database schema",
                            ],
                            "correct_index": 1,
                        },
                        {
                            "question": "A high cost of being wrong 10% of the time suggests the feature needs:",
                            "choices": [
                                "A longer prompt",
                                "A human-in-the-loop step",
                                "A bigger model only",
                                "Nothing extra",
                            ],
                            "correct_index": 1,
                        },
                    ],
                },
            },
            {
                "title": "Design and UX for AI Features",
                "objective": "Design for a system that's sometimes wrong, without making every screen feel like a disclaimer.",
                "lessons": [
                    {
                        "slug": "designing-for-uncertainty",
                        "title": "Designing for Uncertainty",
                        "estimated_minutes": 9,
                        "content_markdown": (
                            "Showing a confidence score rarely helps users on its own -- most people "
                            "don't know what to do with \"73% confident.\" What helps is showing the "
                            "evidence behind the answer (the source passage, the fields it used) so the "
                            "user can judge it the way they'd judge a colleague's claim: by checking the "
                            "reasoning, not a number.\n\n"
                            "Design the edit path as carefully as the generate path. If accepting AI "
                            "output is one click but fixing it is ten, users will ship the wrong answer "
                            "just to avoid the friction."
                        ),
                    },
                    {
                        "slug": "trust-and-explainability",
                        "title": "Trust and Explainability",
                        "estimated_minutes": 9,
                        "content_markdown": (
                            "Trust is built by being right consistently on the cases a user can verify "
                            "themselves -- get those visibly wrong even once, and users generalize that "
                            "distrust to every case they can't verify, even if the feature is actually "
                            "fine there.\n\n"
                            "A short, honest explanation of what the feature can't do yet (\"doesn't see "
                            "attachments\") prevents more frustration than a longer one claiming it can "
                            "do everything."
                        ),
                    },
                ],
            },
            {
                "title": "Shipping and Iterating",
                "objective": "Get a feature into production responsibly, then actually learn from how it's used.",
                "lessons": [
                    {
                        "slug": "evals-before-launch",
                        "title": "Evals Before Launch",
                        "estimated_minutes": 10,
                        "content_markdown": (
                            "A small, hand-curated set of real (or realistic) inputs you check every "
                            "output against before shipping catches more regressions than an elaborate "
                            "automated pipeline nobody maintains. Start with 20-30 cases that represent "
                            "your actual traffic, including the annoying edge cases, not just the clean "
                            "demo inputs.\n\n"
                            "Re-run that same set after every prompt or model change. The value is in the "
                            "consistency of the comparison, not the sophistication of the scoring."
                        ),
                    },
                    {
                        "slug": "post-launch-monitoring",
                        "title": "Post-Launch Monitoring",
                        "estimated_minutes": 9,
                        "content_markdown": (
                            "The signal that matters most after launch is usually the simplest one to "
                            "track: how often users immediately undo, edit, or ignore the AI output. That "
                            "tells you more about real-world quality than an offline eval score ever will.\n\n"
                            "Keep a lightweight way to sample real outputs and read them yourself, "
                            "regularly. Dashboards catch drift in numbers; reading actual outputs catches "
                            "drift in quality that a metric hasn't been built to notice yet."
                        ),
                    },
                ],
            },
        ],
    },
    {
        # Exercises everything added on top of the original course system:
        # video/document/link lesson blocks, all four quiz question types,
        # and a certificate that expires -- see the module docstring above.
        "slug": "ai-media-literacy",
        "title": "AI Media Literacy: Video, Docs & Assessment",
        "category": "AI Skills",
        "description": "A short course that's also a live demo of this platform's richer lesson formats (video, PDF, external links) and quiz question types (multi-select, true/false, short answer) -- not just prose chapters.",
        "certificate_validity_days": 365,
        "chapters": [
            {
                "title": "Watch, Read, Explore",
                "objective": "See each new lesson format used for real, not just described.",
                "lessons": [
                    {
                        "slug": "how-neural-networks-actually-work",
                        "title": "How Neural Networks Actually Work",
                        "estimated_minutes": 20,
                        "content_markdown": "A video lesson -- see the embedded player below for the full explanation.",
                        "content_blocks": [
                            {"type": "text", "markdown": "This lesson is a **video block** -- a well-known, freely available explainer rather than platform-produced content, to show what embedding a real third-party video looks like."},
                            {
                                "type": "video",
                                "title": "But what is a neural network? (3Blue1Brown)",
                                "url": "https://www.youtube.com/watch?v=aircAruvnKk",
                                "transcript": "A visual, intuitive walkthrough of how a simple neural network recognizes handwritten digits -- neurons as numbers, weights and biases as knobs, and gradient descent as the process that tunes them.",
                            },
                        ],
                    },
                    {
                        "slug": "course-handout-pdf",
                        "title": "Course Handout (PDF)",
                        "estimated_minutes": 5,
                        "content_markdown": "A document lesson -- open the embedded PDF below or use the download link.",
                        "content_blocks": [
                            {"type": "text", "markdown": "This lesson is a **document block** -- an uploaded PDF, embedded with a download fallback for anything that can't render it inline."},
                            {"type": "document", "title": "AI Media Literacy -- Course Handout", "url": f"/static/course-uploads/{DEMO_PDF_NAME}", "filename": DEMO_PDF_NAME},
                        ],
                    },
                    {
                        "slug": "further-reading-ml-glossary",
                        "title": "Further Reading: the ML Glossary",
                        "estimated_minutes": 8,
                        "content_markdown": "A link lesson -- points outward rather than hosting the content itself.",
                        "content_blocks": [
                            {"type": "text", "markdown": "This lesson is a **link block** -- a clearly-labeled outbound card, not an auto-embed, since this app doesn't control or host the destination."},
                            {
                                "type": "link",
                                "title": "Google's Machine Learning Glossary",
                                "url": "https://developers.google.com/machine-learning/glossary",
                                "description": "A maintained, external reference for ML terminology -- worth bookmarking outside this course rather than duplicating here.",
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Applied Assessment",
                "objective": "See the newer quiz question types in a real, gradeable quiz.",
                "lessons": [],
                "quiz": {
                    "title": "Applied Assessment Quiz",
                    "passing_score": 70,
                    "randomize_questions": True,
                    "max_attempts": 3,
                    "questions": [
                        {
                            "type": "multiple_choice",
                            "question": "What's the most reliable signal that an AI feature is genuinely working well after launch?",
                            "choices": [
                                "The offline eval score stays flat",
                                "How often users immediately undo, edit, or ignore the output",
                                "The number of features shipped that quarter",
                                "Positive sentiment in the release announcement",
                            ],
                            "correct_index": 1,
                        },
                        {
                            "type": "true_false",
                            "question": "A confidence score on its own is usually enough for a user to judge whether an AI answer is trustworthy.",
                            "choices": ["True", "False"],
                            "correct_index": 1,
                        },
                        {
                            "type": "multi_select",
                            "question": "Which of these are true about the video/document/link lesson blocks added in this course? (select all that apply)",
                            "choices": [
                                "A learner can watch an embedded video without leaving the lesson",
                                "Every external link is automatically embedded and unlabeled",
                                "An uploaded PDF still has a download fallback if the inline viewer fails",
                                "A document lesson must also include a multiple-choice quiz",
                            ],
                            "correct_indices": [0, 2],
                        },
                        {
                            "type": "short_answer",
                            "question": "In 2-3 sentences, describe a real (or realistic) AI feature and one specific way its design accounts for the model sometimes being wrong.",
                            "sample_answer": "Example: a support-ticket triage assistant flags low-confidence classifications for human review instead of auto-routing them, so a wrong guess costs a second look, not a misrouted ticket.",
                        },
                    ],
                },
            },
        ],
    },
]


def main():
    Base.metadata.create_all(bind=engine)
    _write_demo_pdf()
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

        # Demo instructor account -- owns both seeded courses. Password is
        # a plain demo credential like the DEMO_EMAIL/DEMO_PASSWORD pair the
        # frontend auto-logs into; this one just isn't auto-logged-into,
        # it's there so the instructor-only routes/pages have a real
        # account to exercise against.
        instructor = db.query(User).filter(User.email == INSTRUCTOR["email"]).first()
        if not instructor:
            instructor = User(
                email=INSTRUCTOR["email"],
                hashed_password=hash_password(INSTRUCTOR["password"]),
                full_name=INSTRUCTOR["full_name"],
                role=UserRole.INSTRUCTOR,
            )
            db.add(instructor)
            db.flush()

        course_count = 0
        chapter_count = 0
        lesson_count = 0
        quiz_count = 0
        for course_data in COURSES:
            course = db.query(Course).filter(Course.slug == course_data["slug"]).first()
            if course:
                continue  # already seeded -- don't duplicate on a second run

            course = Course(
                slug=course_data["slug"],
                title=course_data["title"],
                description=course_data["description"],
                category=course_data["category"],
                instructor_id=instructor.id,
                is_published=True,
                certificate_validity_days=course_data.get("certificate_validity_days"),
            )
            db.add(course)
            db.flush()
            course_count += 1

            for chapter_index, chapter_data in enumerate(course_data["chapters"], start=1):
                module = Module(
                    course_id=course.id,
                    title=chapter_data["title"],
                    objective=chapter_data["objective"],
                    order_index=chapter_index,
                )
                db.add(module)
                db.flush()
                chapter_count += 1

                for lesson_index, lesson_data in enumerate(chapter_data["lessons"], start=1):
                    db.add(
                        Lesson(
                            module_id=module.id,
                            slug=lesson_data["slug"],
                            title=lesson_data["title"],
                            content_markdown=lesson_data["content_markdown"],
                            content_blocks=lesson_data.get("content_blocks", []),
                            order_index=lesson_index,
                            estimated_minutes=lesson_data["estimated_minutes"],
                        )
                    )
                    lesson_count += 1

                quiz_data = chapter_data.get("quiz")
                if quiz_data:
                    questions = [
                        {
                            "type": q.get("type", "multiple_choice"),
                            "question": q["question"],
                            "choices": q.get("choices", []),
                            "correct_index": q.get("correct_index"),
                            "correct_indices": q.get("correct_indices", []),
                            "sample_answer": q.get("sample_answer", ""),
                        }
                        for q in quiz_data["questions"]
                    ]
                    db.add(
                        Quiz(
                            module_id=module.id,
                            title=quiz_data["title"],
                            passing_score=quiz_data["passing_score"],
                            questions=questions,
                            randomize_questions=quiz_data.get("randomize_questions", False),
                            max_attempts=quiz_data.get("max_attempts"),
                        )
                    )
                    quiz_count += 1

        db.commit()

        # Demo learner account, enrolled in the media-literacy course with
        # its video/document/link lessons already marked read and one real
        # PENDING quiz attempt sitting in the instructor's grading queue --
        # "clickable end to end" for the grading-queue feature means there
        # has to be something waiting in it, not just an empty state.
        learner = db.query(User).filter(User.email == LEARNER["email"]).first()
        if not learner:
            learner = User(
                email=LEARNER["email"],
                hashed_password=hash_password(LEARNER["password"]),
                full_name=LEARNER["full_name"],
                role=UserRole.LEARNER,
            )
            db.add(learner)
            db.flush()

        media_course = db.query(Course).filter(Course.slug == "ai-media-literacy").first()
        pending_attempt_seeded = False
        if media_course and not db.query(Enrollment).filter(Enrollment.user_id == learner.id, Enrollment.course_id == media_course.id).first():
            db.add(Enrollment(user_id=learner.id, course_id=media_course.id))
            db.flush()

            watch_read_explore = next((m for m in media_course.modules if m.title == "Watch, Read, Explore"), None)
            if watch_read_explore:
                for lesson in watch_read_explore.lessons:
                    db.add(UserLessonProgress(user_id=learner.id, lesson_id=lesson.id))

            applied_assessment = next((m for m in media_course.modules if m.title == "Applied Assessment"), None)
            if applied_assessment and applied_assessment.quiz:
                quiz = applied_assessment.quiz
                # Answers keyed by ORIGINAL question index, matching how
                # submit_attempt stores them (see quizzes.py) -- correct on
                # every auto-gradable question, so the only thing blocking
                # this attempt from passing is the short_answer review.
                answers = []
                for q in quiz.questions:
                    qtype = q.get("type", "multiple_choice")
                    if qtype == "multi_select":
                        answers.append(q.get("correct_indices", []))
                    elif qtype == "short_answer":
                        answers.append(
                            "Our internal support-ticket triage assistant flags low-confidence classifications for a "
                            "human to double-check instead of auto-routing them, so a wrong guess costs a second look, "
                            "not a misrouted ticket."
                        )
                    else:
                        answers.append(q.get("correct_index"))
                db.add(
                    QuizAttempt(
                        user_id=learner.id,
                        quiz_id=quiz.id,
                        answers=answers,
                        score=100,  # provisional -- computed over the 3 auto-gradable questions, all correct
                        passed=False,  # forced False while pending, same as submit_attempt does
                        status="pending",
                        attempted_at=datetime.utcnow() - timedelta(hours=2),
                    )
                )
                pending_attempt_seeded = True

        db.commit()
        print(
            f"Seeded {len(TRACKS)} tracks, {len(COMMON_CORE_LESSONS)} common-core lessons, "
            f"{sum(len(v) for v in TRACK_LESSONS.values())} track lessons, "
            f"{course_count} courses ({chapter_count} chapters, {lesson_count} lessons, {quiz_count} quizzes), "
            f"demo learner {'with' if pending_attempt_seeded else 'without new'} a pending short-answer attempt queued for grading."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
