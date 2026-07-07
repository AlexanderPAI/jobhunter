import asyncio
import pprint

import aiohttp

from backend.config import cfg


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

    async def chat(self, prompt: list[dict[str, str]]) -> str:
        """Send prompt to LLM"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.openrouter_url,
                headers={
                    "Authorization": f"Bearer {cfg.openrouter_key}",
                },
                json={
                    "model": self.model,
                    "messages": prompt,
                },
            ) as response:
                return await response.json()


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
