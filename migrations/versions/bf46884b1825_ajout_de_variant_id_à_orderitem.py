"""Ajout de variant_id à OrderItem

Revision ID: bf46884b1825
Revises: 19045d33d0ac
Create Date: 2025-06-23 22:33:20.570714
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bf46884b1825'
down_revision = '19045d33d0ac'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('variant_id', sa.Integer(), nullable=True))
        # ✅ Ajout d’un nom explicite à la contrainte
        batch_op.create_foreign_key(
            'fk_orderitem_variant',   # ← nom requis par SQLite
            'product_variant',
            ['variant_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('order_item', schema=None) as batch_op:
        batch_op.drop_constraint('fk_orderitem_variant', type_='foreignkey')  # ← même nom ici
        batch_op.drop_column('variant_id')
