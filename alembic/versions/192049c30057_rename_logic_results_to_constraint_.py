"""rename logic_results to constraint_results

Revision ID: 192049c30057
Revises: 116ac14ba6d6
Create Date: 2026-02-04 22:49:30.635984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '192049c30057'
down_revision: Union[str, Sequence[str], None] = '116ac14ba6d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename logic_results column to constraint_results."""
    op.alter_column('run_results', 'logic_results',
                    new_column_name='constraint_results')


def downgrade() -> None:
    """Revert constraint_results column to logic_results."""
    op.alter_column('run_results', 'constraint_results',
                    new_column_name='logic_results')
