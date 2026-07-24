"""Store profile-to-vacancy analyses.

Revision ID: 20260724_02
Revises: 20260724_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260724_02"
down_revision: str | Sequence[str] | None = "20260724_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vacancy_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), nullable=False),
        sa.Column("skill", sa.String(64), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("vacancy_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vacancy_analyses_profile_id", "vacancy_analyses", ["profile_id"]
    )
    op.create_index("ix_vacancy_analyses_user_id", "vacancy_analyses", ["user_id"])
    op.create_index(
        "ix_vacancy_analyses_vacancy_id", "vacancy_analyses", ["vacancy_id"]
    )
    op.create_index(
        "ix_vacancy_analyses_user_created_at",
        "vacancy_analyses",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_vacancy_analyses_user_created_at", table_name="vacancy_analyses")
    op.drop_index("ix_vacancy_analyses_vacancy_id", table_name="vacancy_analyses")
    op.drop_index("ix_vacancy_analyses_user_id", table_name="vacancy_analyses")
    op.drop_index("ix_vacancy_analyses_profile_id", table_name="vacancy_analyses")
    op.drop_table("vacancy_analyses")
