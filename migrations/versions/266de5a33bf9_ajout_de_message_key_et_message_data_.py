"""Ajout de message_key et message_data dans Notification

Revision ID: 266de5a33bf9
Revises: 6364abb47676
Create Date: 2025-07-23 21:47:13.848841
"""

from alembic import op
import sqlalchemy as sa


# Identifiants de migration
revision = '266de5a33bf9'
down_revision = '6364abb47676'
branch_labels = None
depends_on = None


def upgrade():
    # ⚠️ Important : ne PAS mettre nullable=False tout de suite
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('message_key', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('message_data', sa.JSON(), nullable=True))
        batch_op.drop_column('message')

    # ✅ Mise à jour des anciennes lignes avec une valeur par défaut
    op.execute("UPDATE notification SET message_key = 'default_key' WHERE message_key IS NULL")


def downgrade():
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('message', sa.String(length=500), nullable=False))
        batch_op.drop_column('message_data')
        batch_op.drop_column('message_key')
