import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.connector import get_session
from backend.db.models import CandidateProfile, SearchResult, SearchRun, User
from backend.security import get_current_user

router = APIRouter(prefix="/v1/history", tags=["history"])


def _profile_data(profile: CandidateProfile) -> dict:
    fields = (
        "id",
        "name",
        "target_positions",
        "skills",
        "experience_years",
        "experience_level",
        "salary_expectation",
        "preferred_schedule",
        "preferred_employment",
        "location",
        "industries",
        "languages",
        "education",
        "summary",
        "search_prompt",
        "source_filename",
        "created_at",
        "updated_at",
    )
    return {field: getattr(profile, field) for field in fields}


def _search_data(search: SearchRun) -> dict:
    fields = (
        "id",
        "prompt",
        "queries",
        "filters",
        "area",
        "max_pages",
        "status",
        "total_found",
        "relevant_count",
        "created_at",
        "filtered_at",
    )
    return {field: getattr(search, field) for field in fields}


@router.get("/profiles")
async def profiles(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.scalars(
            select(CandidateProfile)
            .where(CandidateProfile.user_id == user.id)
            .options(selectinload(CandidateProfile.searches))
            .order_by(CandidateProfile.created_at.desc())
        )
    ).all()
    result = []
    for profile in rows:
        latest = (
            max(profile.searches, key=lambda item: item.created_at)
            if profile.searches
            else None
        )
        item = _profile_data(profile)
        item.update(
            latest_search_id=latest.id if latest else None,
            latest_queries=latest.queries if latest else None,
            last_search_at=latest.created_at if latest else None,
            relevant_count=latest.relevant_count if latest else None,
            total_found=latest.total_found if latest else None,
        )
        result.append(item)
    result.sort(
        key=lambda item: item["last_search_at"] or item["created_at"], reverse=True
    )
    return result


@router.get("/profiles/{profile_id}")
async def profile_detail(
    profile_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = await session.scalar(
        select(CandidateProfile)
        .where(CandidateProfile.id == profile_id, CandidateProfile.user_id == user.id)
        .options(selectinload(CandidateProfile.searches))
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    latest = (
        max(profile.searches, key=lambda item: item.created_at)
        if profile.searches
        else None
    )
    return {
        "profile": _profile_data(profile),
        "latest_search": _search_data(latest) if latest else None,
    }


@router.get("/searches/{search_id}/vacancies")
async def search_vacancies(
    search_id: uuid.UUID,
    relevant_only: bool = Query(False),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    search = await session.scalar(
        select(SearchRun)
        .where(SearchRun.id == search_id, SearchRun.user_id == user.id)
        .options(selectinload(SearchRun.results).selectinload(SearchResult.vacancy))
    )
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return [
        {
            "title": result.vacancy.title,
            "company": result.vacancy.company,
            "salary": result.vacancy.salary_text,
            "city": result.vacancy.city,
            "schedule": result.vacancy.schedule,
            "experience": result.vacancy.experience,
            "link": result.vacancy.external_url,
            "source": result.vacancy.source,
            "query": result.query,
        }
        for result in search.results
        if not relevant_only or result.is_relevant is True
    ]
