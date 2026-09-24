"""certificate expiry

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-09-24 21:05:12.331084

"""
from alembic import op
import sqlalchemy as sa


revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('certificates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('certificate_validity_days', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('certificate_validity_days')

    with op.batch_alter_table('certificates', schema=None) as batch_op:
        batch_op.drop_column('expires_at')
