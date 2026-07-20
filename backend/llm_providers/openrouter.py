import asyncio
import pprint
from typing import Any

import aiohttp

from backend.config import cfg


class LLMProviderError(RuntimeError):
    """Понятная для API ошибка обращения к LLM-провайдеру."""


class OpenRouterAdapter:
    def __init__(
        self,
        openrouter_url: str,
        openrouter_key: str,
        model: str,
    ):
        self.openrouter_url = openrouter_url
        self.openrouter_key = openrouter_key
        self.model = model

    async def chat(self, prompt: list[dict[str, str]]) -> dict[str, Any]:
        """Send prompt to LLM"""
        timeout = aiohttp.ClientTimeout(total=300, connect=30, sock_read=240)
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        url=self.openrouter_url,
                        headers={"Authorization": f"Bearer {self.openrouter_key}"},
                        json={"model": self.model, "messages": prompt},
                    ) as response:
                        payload = await response.json(content_type=None)
                        if response.status >= 400:
                            message = payload.get("error", {}).get("message", payload)
                            raise LLMProviderError(
                                f"OpenRouter вернул HTTP {response.status}: {message}"
                            )
                        choices = payload.get("choices") or []
                        choice = choices[0] if choices else {}
                        content = (choice.get("message") or {}).get("content")
                        if not isinstance(content, str) or not content.strip():
                            finish_reason = choice.get("finish_reason") or "не указан"
                            raise LLMProviderError(
                                "OpenRouter вернул пустой ответ "
                                f"(finish_reason={finish_reason})"
                            )
                        return payload
            except (
                TimeoutError,
                aiohttp.ClientConnectionError,
                LLMProviderError,
            ) as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(1)

        detail = str(last_error) if last_error else "неизвестная ошибка"
        raise LLMProviderError(
            f"OpenRouter не дал корректный ответ после двух попыток: {detail}"
        ) from last_error


llm = OpenRouterAdapter(
    openrouter_url="https://openrouter.ai/api/v1/chat/completions",
    openrouter_key=cfg.openrouter_key,
    model="z-ai/glm-5.2",
)


async def main() -> None:
    prompt = [{"role": "user", "content": "Расскажи, что ты умеешь?"}]
    response = await llm.chat(prompt=prompt)
    pprint.pprint(response)


if __name__ == "__main__":
    asyncio.run(main())
