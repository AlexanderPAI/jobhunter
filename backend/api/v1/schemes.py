from typing import Any, Dict

from pydantic import BaseModel, Field


class SearcherRequest(BaseModel):
    message: str = Field(..., description="Сообщение для AgentSearcher")


class VacancyCheckerRequest(BaseModel):
    csv_path: str = Field(..., description="Путь к csv-списку")
    user_profile: Dict[str, Any] = Field(..., description="Провиль пользователя")
