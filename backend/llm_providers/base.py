from typing import Any, Protocol


class LLMProviderError(RuntimeError):
    """Понятная для API ошибка обращения к LLM-провайдеру."""


class LLMAdapter(Protocol):
    """Контракт LLM-адаптера, который используют агенты."""

    async def chat(self, prompt: list[dict[str, str]]) -> dict[str, Any]: ...
