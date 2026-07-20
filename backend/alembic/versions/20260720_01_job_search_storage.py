"""Add candidate profiles and PostgreSQL-backed vacancy search results.

Revision ID: 20260720_01
Revises: 2fd8a8e0b9b9
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260720_01"
down_revision: str | Sequence[str] | None = "2fd8a8e0b9b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("target_positions", postgresql.JSONB(), nullable=False),
        sa.Column("skills", postgresql.JSONB(), nullable=False),
        sa.Column("experience_years", sa.Float()),
        sa.Column("experience_level", sa.String(32)),
        sa.Column("salary_expectation", sa.Integer()),
        sa.Column("preferred_schedule", sa.String(32)),
        sa.Column("preferred_employment", sa.String(32)),
        sa.Column("location", sa.String(255)),
        sa.Column("industries", postgresql.JSONB(), nullable=False),
        sa.Column("languages", postgresql.JSONB(), nullable=False),
        sa.Column("education", postgresql.JSONB(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("source_filename", sa.String(512)),
        sa.Column("cv_text", sa.Text()),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "search_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid()),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("queries", postgresql.JSONB(), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("area", sa.Integer(), nullable=False),
        sa.Column("max_pages", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_found", sa.Integer(), nullable=False),
        sa.Column("relevant_count", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("filtered_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["candidate_profiles.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_runs_profile_id", "search_runs", ["profile_id"])
    op.create_index("ix_search_runs_status", "search_runs", ["status"])
    op.create_table(
        "vacancies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("company", sa.String(512)),
        sa.Column("salary_text", sa.String(255)),
        sa.Column("city", sa.String(255)),
        sa.Column("schedule", sa.String(255)),
        sa.Column("experience", sa.String(255)),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_url"),
    )
    op.create_index("ix_vacancies_source", "vacancies", ["source"])
    op.create_table(
        "search_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("search_run_id", sa.Uuid(), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(1024)),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_relevant", sa.Boolean()),
        sa.Column("filter_details", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["search_run_id"], ["search_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("search_run_id", "vacancy_id"),
    )
    op.create_index(
        "ix_search_results_search_run_id", "search_results", ["search_run_id"]
    )
    op.create_index("ix_search_results_vacancy_id", "search_results", ["vacancy_id"])
    op.create_index("ix_search_results_is_relevant", "search_results", ["is_relevant"])


def downgrade() -> None:
    op.drop_table("search_results")
    op.drop_table("vacancies")
    op.drop_table("search_runs")
    op.drop_table("candidate_profiles")
