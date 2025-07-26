"""Supprimer listing_id de Order

Revision ID: 9bad7431af8b
Revises: a5eb128ce497
Create Date: 2025-06-23 12:47:08.147115
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9bad7431af8b'
down_revision = 'a5eb128ce497'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.drop_column('listing_id')


def downgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('listing_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(None, 'listing', ['listing_id'], ['id'])
