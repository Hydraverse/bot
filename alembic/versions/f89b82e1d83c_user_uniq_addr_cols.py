"""user_uniq addr cols

Revision ID: f89b82e1d83c
Revises: 2a55f3af34c1
Create Date: 2022-01-17 04:24:22.568043+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f89b82e1d83c'
down_revision = '2a55f3af34c1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_uniq', schema=None) as batch_op:
        batch_op.add_column(sa.Column('addr_shr_hy', sa.String(length=34), nullable=True))
        batch_op.add_column(sa.Column('addr_shr_pk', sa.String(length=52), nullable=True))
        batch_op.add_column(sa.Column('addr_loc_hy', sa.String(length=34), nullable=True))
        batch_op.add_column(sa.Column('addr_loc_pk', sa.String(length=52), nullable=True))
        batch_op.create_unique_constraint(None, ['addr_loc_hy'])
        batch_op.create_unique_constraint(None, ['addr_shr_hy'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_uniq', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('addr_loc_pk')
        batch_op.drop_column('addr_loc_hy')
        batch_op.drop_column('addr_shr_pk')
        batch_op.drop_column('addr_shr_hy')

    # ### end Alembic commands ###