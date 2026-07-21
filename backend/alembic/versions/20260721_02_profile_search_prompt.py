"""Store the generated search prompt on candidate profiles.

Revision ID: 20260721_02
Revises: 20260721_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_02"
down_revision: str | Sequence[str] | None = "20260721_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("search_prompt", sa.Text()))


def downgrade() -> None:
    op.drop_column("candidate_profiles", "search_prompt")
