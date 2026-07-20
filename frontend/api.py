import aiohttp

SEARCHER_URL = "http://backend:8080/v1/searcher/chat"
FILTER_URL = "http://backend:8080/v1/filter/check"


async def repeat_search(search_prompt: str, profile_id: str) -> list[dict]:
    timeout = aiohttp.ClientTimeout(total=1200)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            SEARCHER_URL,
            json={"message": search_prompt, "profile_id": profile_id},
        ) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Ошибка поиска {response.status}: {await response.text()}"
                )
            search_id = (await response.json())["search_id"]

        async with session.post(FILTER_URL, json={"search_id": search_id}) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Ошибка фильтрации {response.status}: {await response.text()}"
                )
            return (await response.json())["vacancies"]
