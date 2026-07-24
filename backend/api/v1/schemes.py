import uuid

from pydantic import BaseModel, Field


class SearcherRequest(BaseModel):
    message: str = Field(..., description="Сообщение для AgentSearcher")
    profile_id: uuid.UUID | None = Field(None, description="Идентификатор профиля")


class VacancyCheckerRequest(BaseModel):
    search_id: uuid.UUID = Field(..., description="Идентификатор поиска")


class ResumeRecommendationsRequest(BaseModel):
    profile_id: uuid.UUID = Field(..., description="Идентификатор профиля")


class VacancyMatchRequest(BaseModel):
    profile_id: uuid.UUID = Field(..., description="Идентификатор профиля")
    vacancy_id: uuid.UUID = Field(..., description="Идентификатор вакансии")
