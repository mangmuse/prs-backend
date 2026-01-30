"""remove row_constraints from dataset_rows

Revision ID: 9049b6c4b524
Revises: bde21e3845f6
Create Date: 2026-01-31 00:58:48.263633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9049b6c4b524'
down_revision: Union[str, Sequence[str], None] = 'bde21e3845f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('dataset_rows', 'row_constraints')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('dataset_rows', sa.Column('row_constraints', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
