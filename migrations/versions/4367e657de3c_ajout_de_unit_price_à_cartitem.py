"""Ajout de unit_price à CartItem

Revision ID: 4367e657de3c
Revises: bf46884b1825
Create Date: 2025-06-23 22:49:24.044194

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4367e657de3c'
down_revision = 'bf46884b1825'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cart_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_price', sa.Float(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cart_item', schema=None) as batch_op:
        batch_op.drop_column('unit_price')

    # ### end Alembic commands ###
