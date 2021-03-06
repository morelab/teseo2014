"""Added name stuff

Revision ID: 1ee1e1f6aaf3
Revises: 2a8495339e14
Create Date: 2014-02-28 12:14:50.343113

"""

# revision identifiers, used by Alembic.
revision = '1ee1e1f6aaf3'
down_revision = '2a8495339e14'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('person', sa.Column('first_name', sa.UnicodeText(), nullable=False))
    op.add_column('person', sa.Column('first_surname', sa.UnicodeText(), nullable=False))
    op.add_column('person', sa.Column('second_surname', sa.UnicodeText(), nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('person', 'second_surname')
    op.drop_column('person', 'first_surname')
    op.drop_column('person', 'first_name')
    ### end Alembic commands ###
