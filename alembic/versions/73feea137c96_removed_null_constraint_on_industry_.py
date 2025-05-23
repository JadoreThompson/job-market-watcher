"""Removed null constraint on industry field and added created_at field on cleaned_data

Revision ID: 73feea137c96
Revises: f77d52eed3a5
Create Date: 2025-04-26 15:04:21.696955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73feea137c96'
down_revision: Union[str, None] = 'f77d52eed3a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cleaned_data', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.alter_column('cleaned_data', 'industry',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('scraped_data', 'industry',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('scraped_data', 'industry',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('cleaned_data', 'industry',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('cleaned_data', 'created_at')
    # ### end Alembic commands ###
