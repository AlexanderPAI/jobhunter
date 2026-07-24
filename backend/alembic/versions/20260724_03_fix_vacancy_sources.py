"""Repair vacancy sources from their canonical URLs.

Revision ID: 20260724_03
Revises: 20260724_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_03"
down_revision: str | Sequence[str] | None = "20260724_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE vacancies SET source = 'habr' "
            "WHERE external_url LIKE 'https://career.habr.com/%'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE vacancies SET source = 'hh' "
            "WHERE external_url ~ '^https?://([^.]+\\.)*hh\\.ru/'"
        )
    )


def downgrade() -> None:
    # The previous incorrect values cannot be reconstructed.
    pass
