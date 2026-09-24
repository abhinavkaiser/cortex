#!/usr/bin/env python
"""One-time data migration: folds the 3 fixed curriculum Tracks (AI Leader /
AI Practitioner / AI Developer) and the shared Common Core into the
general-purpose Course system, so Tracks stop being a learner-facing
concept -- see README's "Formerly Tracks, now migrated into Courses"
section for the target state.

RUN ORDER (important): run this BEFORE the Alembic migration that drops
Module.track_id / Lesson.track_id / User.track_id / User.common_core_
completed_at (alembic/versions/d1e2f3a4b5c6_...py). This script reads those
soon-to-be-dropped columns to know what to migrate -- run the schema
migration first and there's nothing left here to read. Concretely:

    cd backend
    python scripts/migrate_tracks_to_courses.py   # this script -- data first
    alembic upgrade head                          # then drop the old columns

Because the app's SQLAlchemy models (app/models/module.py, lesson.py,
user.py) already match the END state -- track_id etc. removed -- this
script CANNOT read/write those columns through the ORM (the mapped classes
no longer declare them). It reads/writes them via raw SQL instead,
everywhere a legacy column is involved; the ORM is still used normally for
everything that touches only current columns (creating Course/Module rows,
Enrollment rows, and updating Module.course_id / Lesson.module_id, which
both models keep).

Idempotent and safe to re-run, same pattern scripts/seed.py already uses:
every "already migrated" condition is a plain SELECT that naturally
returns nothing once that piece of data has been moved (see each phase
below), so a second run is a no-op except printing zero counts.

Does NOT touch UserLessonProgress -- those rows key on lesson_id, which
doesn't change here (only the lesson's *module* changes), so a learner's
completion history carries over for free with no rewriting needed.

Does NOT drop or touch the `tracks` table -- Daily Pulse still depends on
it (DailyPulse.track_id). See models/track.py.
"""

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models.course import Course, Enrollment
from app.models.lesson import UserLessonProgress
from app.models.module import Module
from app.models.track import Track
from app.models.user import User, UserRole

# Course slug/title derived from each Track's own slug/name -- "leader" ->
# "ai-leader" / "AI Leader", matching the naming the rest of the app already
# uses for course slugs (kebab-case) vs. display titles.
def _course_slug_for_track(track_slug: str) -> str:
    return f"ai-{track_slug}"


COMMON_CORE_COURSE = {
    "slug": "ai-fundamentals",
    "title": "AI Fundamentals",
    "description": (
        "The shared foundations every learner starts with, before branching into a specialization -- "
        "what a language model actually does, prompting fundamentals, and where AI breaks down "
        "(hallucination, bias, limits). Formerly a mandatory Common Core gate every account passed "
        "through before unlocking a Track; now an ordinary course anyone can enroll in and complete "
        "at their own pace, same as any other."
    ),
    "category": "AI Skills",
}

COMMON_CORE_MODULE_TITLE = "Foundations"


def _find_instructor(db) -> User:
    """Owner for the 4 migrated courses. Prefers the seeded demo instructor
    (scripts/seed.py's instructor@cortex.ai) for continuity with a fresh
    dev DB; falls back to any instructor/admin account for a database that
    was seeded differently, since who specifically owns these migrated
    courses matters far less than them having a valid, real owner."""
    seeded = db.query(User).filter(User.email == "instructor@cortex.ai").first()
    if seeded:
        return seeded
    any_instructor = db.query(User).filter(User.role == UserRole.INSTRUCTOR).order_by(User.id).first()
    if any_instructor:
        return any_instructor
    any_admin = db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.id).first()
    if any_admin:
        return any_admin
    raise RuntimeError(
        "No instructor or admin account found to own the migrated courses -- run scripts/seed.py "
        "first (or create at least one instructor/admin user) before running this migration."
    )


def _get_or_create_course(db, *, slug: str, title: str, description: str, category: str, instructor_id: int) -> tuple[Course, bool]:
    existing = db.query(Course).filter(Course.slug == slug).first()
    if existing:
        return existing, False
    course = Course(
        slug=slug,
        title=title,
        description=description,
        category=category,
        instructor_id=instructor_id,
        is_published=True,
    )
    db.add(course)
    db.flush()
    return course, True


def _next_order_index(db, course_id: int) -> int:
    existing_count = db.query(Module).filter(Module.course_id == course_id).count()
    return existing_count + 1


def main() -> None:
    db = SessionLocal()
    try:
        total_lessons_before = db.execute(text("SELECT count(*) FROM lessons")).scalar_one()

        instructor = _find_instructor(db)

        # ---- Phase 1: one Course per Track, plus the Common Core course ---
        courses_created = 0
        track_course_by_track_id: dict[int, Course] = {}
        for track in db.query(Track).order_by(Track.id).all():
            course, created = _get_or_create_course(
                db,
                slug=_course_slug_for_track(track.slug),
                title=track.name,
                description=track.description,
                category="AI Skills",
                instructor_id=instructor.id,
            )
            track_course_by_track_id[track.id] = course
            courses_created += int(created)

        common_core_course, created = _get_or_create_course(
            db,
            slug=COMMON_CORE_COURSE["slug"],
            title=COMMON_CORE_COURSE["title"],
            description=COMMON_CORE_COURSE["description"],
            category=COMMON_CORE_COURSE["category"],
            instructor_id=instructor.id,
        )
        courses_created += int(created)
        db.commit()

        # ---- Phase 2: repoint each track's real Modules at its new Course -
        # Also clears track_id on every lesson already inside one of these
        # modules (their course affiliation was always via module_id/
        # Lesson.course_id, never Lesson.track_id -- see models/lesson.py --
        # but leaving a stale track_id sitting around until the Alembic
        # column-drop runs is needless inconsistency for anyone inspecting
        # the DB in between the two steps).
        modules_repointed = 0
        module_lessons_detracked = 0
        for track_id, course in track_course_by_track_id.items():
            module_ids = [
                row[0]
                for row in db.execute(text("SELECT id FROM modules WHERE track_id = :tid"), {"tid": track_id}).all()
            ]
            for module_id in module_ids:
                db.execute(
                    text("UPDATE modules SET course_id = :cid, track_id = NULL WHERE id = :id"),
                    {"cid": course.id, "id": module_id},
                )
                modules_repointed += 1
                result = db.execute(
                    text("UPDATE lessons SET track_id = NULL WHERE module_id = :mid AND track_id IS NOT NULL"),
                    {"mid": module_id},
                )
                module_lessons_detracked += result.rowcount
        db.commit()

        # ---- Phase 3: any "flat" lesson directly under a track (no module)
        # gets a single new chapter Module created for it and moved in.
        flat_lessons_moved = 0
        catch_all_modules_created = 0
        for track in db.query(Track).order_by(Track.id).all():
            course = track_course_by_track_id[track.id]
            flat_lesson_ids = [
                row[0]
                for row in db.execute(
                    text("SELECT id FROM lessons WHERE track_id = :tid AND module_id IS NULL"), {"tid": track.id}
                ).all()
            ]
            if not flat_lesson_ids:
                continue

            catch_all = db.query(Module).filter(Module.course_id == course.id, Module.title == track.name).first()
            if not catch_all:
                catch_all = Module(
                    course_id=course.id,
                    title=track.name,
                    objective=f"Migrated from the original AI {track.name} track.",
                    order_index=_next_order_index(db, course.id),
                )
                db.add(catch_all)
                db.flush()
                catch_all_modules_created += 1

            for lesson_id in flat_lesson_ids:
                db.execute(
                    text("UPDATE lessons SET module_id = :mid, track_id = NULL WHERE id = :id"),
                    {"mid": catch_all.id, "id": lesson_id},
                )
                flat_lessons_moved += 1
        db.commit()

        # ---- Phase 4: the 3 genuine Common Core lessons (track_id NULL,
        # module_id NULL -- course lessons always have a module, so this
        # condition alone identifies them) get one shared chapter.
        common_core_lesson_ids = [
            row[0]
            for row in db.execute(text("SELECT id FROM lessons WHERE track_id IS NULL AND module_id IS NULL")).all()
        ]
        common_core_lessons_moved = 0
        if common_core_lesson_ids:
            common_core_module = (
                db.query(Module).filter(Module.course_id == common_core_course.id, Module.title == COMMON_CORE_MODULE_TITLE).first()
            )
            if not common_core_module:
                common_core_module = Module(
                    course_id=common_core_course.id,
                    title=COMMON_CORE_MODULE_TITLE,
                    objective="Everything every learner used to complete before a Track's curriculum unlocked.",
                    order_index=_next_order_index(db, common_core_course.id),
                )
                db.add(common_core_module)
                db.flush()

            for lesson_id in common_core_lesson_ids:
                db.execute(
                    text("UPDATE lessons SET module_id = :mid WHERE id = :id"),
                    {"mid": common_core_module.id, "id": lesson_id},
                )
                common_core_lessons_moved += 1
        db.commit()

        # Re-resolve the (possibly just-created) Common Core module's lesson
        # ids for phase 6's UserLessonProgress check below -- covers the
        # idempotent-rerun case where phase 4 found nothing to move (lessons
        # already moved on a prior run) but we still need to know which
        # lesson ids count as "Common Core" for existing progress rows.
        common_core_module_ids = [
            row[0] for row in db.execute(text("SELECT id FROM modules WHERE course_id = :cid"), {"cid": common_core_course.id}).all()
        ]
        all_common_core_lesson_ids = set(common_core_lesson_ids)
        if common_core_module_ids:
            placeholders = ",".join(str(mid) for mid in common_core_module_ids)
            all_common_core_lesson_ids |= {
                row[0] for row in db.execute(text(f"SELECT id FROM lessons WHERE module_id IN ({placeholders})")).all()
            }

        # ---- Phase 5: Enrollments for every user who had a track_id -------
        track_enrollments_created = 0
        common_core_enrollments_created = 0
        users_rows = db.execute(text("SELECT id, track_id, common_core_completed_at, created_at FROM users")).all()
        for user_id, track_id, common_core_completed_at, created_at in users_rows:
            # Raw SQL (see module docstring) returns SQLite's stored TEXT
            # representation for a DateTime column, not a Python datetime --
            # the ORM's type decoder never runs for a bare text() query, so
            # this has to parse it back by hand before handing it to
            # Enrollment.enrolled_at (a real DateTime-typed ORM column).
            if isinstance(created_at, str):
                enrolled_at = datetime.fromisoformat(created_at)
            else:
                enrolled_at = created_at or datetime.utcnow()

            if track_id is not None and track_id in track_course_by_track_id:
                course = track_course_by_track_id[track_id]
                exists = (
                    db.query(Enrollment).filter(Enrollment.user_id == user_id, Enrollment.course_id == course.id).first()
                )
                if not exists:
                    db.add(Enrollment(user_id=user_id, course_id=course.id, enrolled_at=enrolled_at))
                    track_enrollments_created += 1

            has_common_core_progress = bool(common_core_completed_at) or (
                all_common_core_lesson_ids
                and db.query(UserLessonProgress)
                .filter(UserLessonProgress.user_id == user_id, UserLessonProgress.lesson_id.in_(all_common_core_lesson_ids))
                .first()
                is not None
            )
            if has_common_core_progress:
                exists = (
                    db.query(Enrollment)
                    .filter(Enrollment.user_id == user_id, Enrollment.course_id == common_core_course.id)
                    .first()
                )
                if not exists:
                    db.add(Enrollment(user_id=user_id, course_id=common_core_course.id, enrolled_at=enrolled_at))
                    common_core_enrollments_created += 1

        db.commit()

        total_lessons_after = db.execute(text("SELECT count(*) FROM lessons")).scalar_one()

        print("Migration complete.")
        print(f"  Courses created:                 {courses_created} (of 4 possible -- 3 tracks + Common Core)")
        print(f"  Existing Modules repointed:       {modules_repointed}")
        print(f"  Lessons de-tracked (already in a migrated module): {module_lessons_detracked}")
        print(f"  Catch-all chapter Modules created: {catch_all_modules_created} (for flat, moduleless track lessons)")
        print(f"  Flat track lessons moved:          {flat_lessons_moved}")
        print(f"  Common Core lessons moved:         {common_core_lessons_moved}")
        print(f"  Track Enrollments created:         {track_enrollments_created}")
        print(f"  Common Core Enrollments created:   {common_core_enrollments_created}")
        print(f"  Total lesson count: {total_lessons_before} before -> {total_lessons_after} after (should be equal)")
        if total_lessons_before != total_lessons_after:
            print("  WARNING: lesson count changed -- this should never happen (lessons are only repointed, never inserted/deleted).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
