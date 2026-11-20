"""add is_open_time to schedule

Revision ID: 8f1d8874d977
Revises: c7ca0d8dc6dd
Create Date: 2026-11-20 20:32:59.704071

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '8f1d8874d977'
down_revision = 'c7ca0d8dc6dd'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('schedule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_open_time', sa.Boolean(), nullable=True, server_default=sa.text('0')))


def downgrade():
    with op.batch_alter_table('schedule', schema=None) as batch_op:
        batch_op.drop_column('is_open_time')
