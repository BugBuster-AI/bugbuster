"""'ind_run'

Revision ID: 131192693be9
Revises: 50475df202ff
Create Date: 2025-02-14 15:02:07.851824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '131192693be9'
down_revision: Union[str, None] = '50475df202ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_run_cases_group_case_created_at
        ON run_cases (group_run_id, case_id, created_at DESC)
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_run_cases_group_case_created_at
    """)
