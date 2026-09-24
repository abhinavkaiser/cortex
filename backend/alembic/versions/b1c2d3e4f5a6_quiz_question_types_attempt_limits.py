"""quiz question types, attempt limits, grading status

Revision ID: b1c2d3e4f5a6
Revises: a7a7aa27141a
Create Date: 2026-09-24 20:57:37.978262

"""
from alembic import op
import sqlalchemy as sa


revision = 'b1c2d3e4f5a6'
down_revision = 'a7a7aa27141a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The two NOT NULL columns (quiz_attempts.status, quizzes
    # .randomize_questions) carry a server_default so this applies cleanly
    # against a database that already has rows in those tables -- SQLite
    # (even via batch/recreate mode) can't add a NOT NULL column with no
    # way to backfill existing rows. Every pre-existing QuizAttempt was
    # graded the old (auto-only) way, so 'graded' is the correct backfill
    # value, not just a placeholder -- same reasoning for
    # randomize_questions defaulting to off for every quiz that predates
    # this feature.
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='graded'))
        batch_op.add_column(sa.Column('graded_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('randomize_questions', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('max_attempts', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.drop_column('max_attempts')
        batch_op.drop_column('randomize_questions')

    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.drop_column('graded_at')
        batch_op.drop_column('status')
