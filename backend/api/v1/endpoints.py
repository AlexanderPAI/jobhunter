import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.cv_analyzer.agent import CVAnalyzerAgent
from backend.agents.resume_advisor.agent import ResumeAdvisorAgent
from backend.agents.searcher.agent import Agent as SearchAgent
from backend.agents.vacancy_filter.agent import VacancyFilterAgent
from backend.api.v1.schemes import (
    ResumeRecommendationsRequest,
    SearcherRequest,
    VacancyCheckerRequest,
)
from backend.db.connector import get_session
from backend.db.models import CandidateProfile, User
from backend.db.repositories import create_profile
from backend.llm_providers.base import LLMProviderError
from backend.security import get_current_user

router = APIRouter(prefix="/v1", dependencies=[Depends(get_current_user)])

# вынести в конфиги
UPLOAD_DIR = Path("backend/storage/cv")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
}

cv_analyzer_agent = CVAnalyzerAgent()
resume_advisor_agent = ResumeAdvisorAgent()
search_agent = SearchAgent()
vacancy_filter_agent = VacancyFilterAgent()


@router.post("/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported {file.content_type}. Upload only *.pdf, *.docx, *.doc, *.txt files",
        )
    extension = ALLOWED_TYPES[file.content_type]
    save_filename = f"{uuid.uuid4()}{extension}"
    file_path = UPLOAD_DIR / save_filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "original_filename": file.filename,
        "stored_filename": save_filename,
        "content_type": file.content_type,
        "path": str(file_path),
    }


@router.post("/cv_analyzer/send_cv")
async def cv_analyzer(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported {file.content_type}. Upload only *.pdf, *.docx, *.doc, *.txt files",
        )
    extension = ALLOWED_TYPES[file.content_type]
    save_filename = f"{uuid.uuid4()}{extension}"
    file_path = UPLOAD_DIR / save_filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        search_prompt, user_profile, state = await cv_analyzer_agent.run(str(file_path))
    except LLMProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    profile = await create_profile(
        session,
        user_profile,
        user_id=user.id,
        search_prompt=search_prompt,
        source_filename=file.filename,
        cv_text=state.get("cv_text"),
    )

    return {
        "search_prompt": search_prompt,
        "user_profile": user_profile,
        "profile_id": str(profile.id),
    }


@router.post("/resume_advisor/recommendations")
async def resume_recommendations(
    request: ResumeRecommendationsRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    profile = await session.scalar(
        select(CandidateProfile).where(
            CandidateProfile.id == request.profile_id,
            CandidateProfile.user_id == user.id,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    recommendations, _ = await resume_advisor_agent.run(
        profile.raw_data,
        profile.cv_text,
        skill="base",
    )
    return {
        "profile_id": str(profile.id),
        "recommendations": recommendations,
    }


@router.post("/searcher/chat")
async def searcher_chat(
    searcher_request: SearcherRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if searcher_request.profile_id is not None:
        profile = await session.scalar(
            select(CandidateProfile).where(
                CandidateProfile.id == searcher_request.profile_id,
                CandidateProfile.user_id == user.id,
            )
        )
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
    search_id = await search_agent.run(
        searcher_request.message,
        str(searcher_request.profile_id) if searcher_request.profile_id else None,
        str(user.id),
    )
    return {"search_id": search_id}


@router.post("/filter/check")
async def filter_check(
    request: VacancyCheckerRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    profile = await session.scalar(
        select(CandidateProfile)
        .join(CandidateProfile.searches)
        .where(
            CandidateProfile.user_id == user.id,
            CandidateProfile.searches.any(id=request.search_id, user_id=user.id),
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile for search not found")
    rows, _ = await vacancy_filter_agent.run(str(request.search_id), profile.raw_data)
    return {
        "search_id": str(request.search_id),
        "total_count": len(rows),
        "vacancies": rows,
    }
