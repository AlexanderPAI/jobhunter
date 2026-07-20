import uuid
from typing import Any

from sqlalchemy import text

from frontend.db.connector import async_session


async def get_profiles() -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            p.id, p.name, p.summary, p.target_positions, p.experience_level,
            p.location, p.created_at,
            latest.id AS latest_search_id, latest.queries AS latest_queries,
            latest.created_at AS last_search_at,
            latest.relevant_count,
            latest.total_found
        FROM candidate_profiles AS p
        LEFT JOIN LATERAL (
            SELECT id, queries, created_at, relevant_count, total_found
            FROM search_runs
            WHERE profile_id = p.id
            ORDER BY created_at DESC
            LIMIT 1
        ) AS latest ON TRUE
        ORDER BY COALESCE(latest.created_at, p.created_at) DESC
        """
    )
    async with async_session() as session:
        result = await session.execute(query)
        return [dict(row) for row in result.mappings().all()]


async def get_profile(
    profile_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    profile_query = text(
        """
        SELECT id, name, target_positions, skills, experience_years,
               experience_level, salary_expectation, preferred_schedule,
               preferred_employment, location, industries, languages,
               education, summary, source_filename, created_at, updated_at
        FROM candidate_profiles
        WHERE id = :profile_id
        """
    )
    search_query = text(
        """
        SELECT id, prompt, queries, filters, area, max_pages, status,
               total_found, relevant_count, created_at, filtered_at
        FROM search_runs
        WHERE profile_id = :profile_id
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    params = {"profile_id": uuid.UUID(profile_id)}
    async with async_session() as session:
        profile_result = await session.execute(profile_query, params)
        profile = profile_result.mappings().one_or_none()
        search_result = await session.execute(search_query, params)
        search = search_result.mappings().one_or_none()
        return (
            dict(profile) if profile else None,
            dict(search) if search else None,
        )


async def get_search_vacancies(
    search_id: str, *, relevant_only: bool
) -> list[dict[str, Any]]:
    relevance_clause = "AND result.is_relevant IS TRUE" if relevant_only else ""
    query = text(
        f"""
        SELECT vacancy.title,
               vacancy.company,
               vacancy.salary_text AS salary,
               vacancy.city,
               vacancy.schedule,
               vacancy.experience,
               vacancy.external_url AS link,
               vacancy.source,
               result.query
        FROM search_results AS result
        JOIN vacancies AS vacancy ON vacancy.id = result.vacancy_id
        WHERE result.search_run_id = :search_id
          {relevance_clause}
        ORDER BY result.position
        """
    )
    async with async_session() as session:
        result = await session.execute(query, {"search_id": uuid.UUID(search_id)})
        return [dict(row) for row in result.mappings().all()]
