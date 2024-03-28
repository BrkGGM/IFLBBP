"""update

Revision ID: 447283328bab
Revises: cf4735fe91aa
Create Date: 2024-03-24 15:31:31.835375

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '447283328bab'
down_revision = 'cf4735fe91aa'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('son_paylasma_tarihi', sa.DateTime(), nullable=True))
        batch_op.drop_column('name')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.VARCHAR(length=20), nullable=True))
        batch_op.drop_column('son_paylasma_tarihi')

    # ### end Alembic commands ###