"""Ajout du champ stock à Listing

Revision ID: 6abd71b77c0f
Revises: a9ce35fdb360
Create Date: 2025-06-26 18:01:45.862812

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6abd71b77c0f'
down_revision = 'a9ce35fdb360'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('listing', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stock', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('listing', schema=None) as batch_op:
        batch_op.drop_column('stock')

    # ### end Alembic commands ###
