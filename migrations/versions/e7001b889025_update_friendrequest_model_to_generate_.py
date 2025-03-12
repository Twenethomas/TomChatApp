"""Update FriendRequest model to generate custom_id

Revision ID: e7001b889025
Revises: 6c4d75d3afb9
Create Date: 2025-03-11 21:34:35.980990

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7001b889025'
down_revision = '6c4d75d3afb9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('friend_request', schema=None) as batch_op:
        batch_op.alter_column('sender_id',
               existing_type=sa.VARCHAR(length=50, collation='Latin1_General_CI_AS'),
               nullable=False)
        batch_op.alter_column('receiver_id',
               existing_type=sa.VARCHAR(length=50, collation='Latin1_General_CI_AS'),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('friend_request', schema=None) as batch_op:
        batch_op.alter_column('receiver_id',
               existing_type=sa.VARCHAR(length=50, collation='Latin1_General_CI_AS'),
               nullable=True)
        batch_op.alter_column('sender_id',
               existing_type=sa.VARCHAR(length=50, collation='Latin1_General_CI_AS'),
               nullable=True)

    # ### end Alembic commands ###
