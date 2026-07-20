import uuid

from pydantic import BaseModel, Field


class SearcherRequest(BaseModel):
    message: str = Field(..., description="Сообщение для AgentSearcher")
    profile_id: uuid.UUID | None = Field(None, description="Идентификатор профиля")


class VacancyCheckerRequest(BaseModel):
    search_id: uuid.UUID = Field(..., description="Идентификатор поиска")
