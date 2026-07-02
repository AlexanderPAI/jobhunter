from pydantic import BaseModel, Field


class SearcherRequest(BaseModel):
    message: str = Field(..., description="Сообщение для AgentSearcher")
