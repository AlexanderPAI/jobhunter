"""Create the initial test table.

Revision ID: 2fd8a8e0b9b9
Revises:

This revision was already applied to the development database, but its file was
not committed. Keeping it restores the Alembic history and also supports a
clean database installation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2fd8a8e0b9b9"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "test",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(4096)),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("test")
