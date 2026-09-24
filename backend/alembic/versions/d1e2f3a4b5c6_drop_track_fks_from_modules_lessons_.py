"""drop track FKs from modules/lessons/users, Common Core gate from users

Revision ID: d1e2f3a4b5c6
Revises: c2d3e4f5a6b7
Create Date: 2026-09-25 09:00:00.000000

Tracks (AI Leader/Practitioner/Developer) and the Common Core gate are no
longer a learner-facing concept -- see README's "Formerly Tracks, now
migrated into Courses"
section and scripts/migrate_tracks_to_courses.py, which merges the fixed
3-Track curriculum (and Common Core) into ordinary Courses.

IMPORTANT -- run order: this migration assumes
scripts/migrate_tracks_to_courses.py has ALREADY been run against this
same database. That script reads Module.track_id/Lesson.track_id/
User.track_id/User.common_core_completed_at (via raw SQL, since the ORM
models no longer declare these columns as of this change) to repoint
every Module/Lesson at a Course and backfill Enrollment rows -- if this
migration runs first, that data is gone and the migrate script has
nothing left to read. Correct order:

    python scripts/migrate_tracks_to_courses.py
    alembic upgrade head

Deliberately does NOT touch the `tracks` table or `daily_pulses.track_id`
-- Daily Pulse still generates/serves one pulse per Track, per day,
independent of any learner's course enrollments (see models/track.py).
"""
from alembic import op
import sqlalchemy as sa


revision = 'd1e2f3a4b5c6'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.drop_column('track_id')

    with op.batch_alter_table('lessons', schema=None) as batch_op:
        batch_op.drop_column('track_id')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('track_id')
        batch_op.drop_column('common_core_completed_at')


def downgrade() -> None:
    # Columns come back empty (NULL) -- this does not restore the
    # track/Common-Core assignments that migrate_tracks_to_courses.py
    # already folded into Enrollment rows. A real rollback of the data
    # itself would mean reversing that script, not just this schema change.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('common_core_completed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('track_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('lessons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('track_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('track_id', sa.Integer(), nullable=True))
