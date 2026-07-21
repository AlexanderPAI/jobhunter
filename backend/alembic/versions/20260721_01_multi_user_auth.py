"""Add users and make profiles/searches user-owned.

Revision ID: 20260721_01
Revises: 20260720_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_01"
down_revision: str | Sequence[str] | None = "20260720_01"
branch_labels = None
depends_on = None

LEGACY_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    # Existing pre-authentication data remains isolated under a disabled account.
    op.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, is_active) "
            "VALUES (CAST(:id AS uuid), '__legacy__', 'unusable', false)"
        ).bindparams(id=LEGACY_USER_ID)
    )
    op.add_column("candidate_profiles", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("search_runs", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.execute(
        sa.text("UPDATE candidate_profiles SET user_id = CAST(:id AS uuid)").bindparams(
            id=LEGACY_USER_ID
        )
    )
    op.execute(
        sa.text("UPDATE search_runs SET user_id = CAST(:id AS uuid)").bindparams(
            id=LEGACY_USER_ID
        )
    )
    op.alter_column("candidate_profiles", "user_id", nullable=False)
    op.alter_column("search_runs", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_candidate_profiles_user",
        "candidate_profiles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_search_runs_user",
        "search_runs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_candidate_profiles_user_id", "candidate_profiles", ["user_id"])
    op.create_index("ix_search_runs_user_id", "search_runs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_search_runs_user_id", table_name="search_runs")
    op.drop_index("ix_candidate_profiles_user_id", table_name="candidate_profiles")
    op.drop_constraint("fk_search_runs_user", "search_runs", type_="foreignkey")
    op.drop_constraint(
        "fk_candidate_profiles_user", "candidate_profiles", type_="foreignkey"
    )
    op.drop_column("search_runs", "user_id")
    op.drop_column("candidate_profiles", "user_id")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
