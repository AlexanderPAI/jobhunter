from datetime import datetime
from typing import List

from langchain_core.tools import tool

from backend.utils.parser import HHParser


@tool
async def parse_vacancies(
    search_queries: List[str],
    area: int = 1,
    max_pages: int = 3,
) -> dict:
    """
    Запускает парсер hh.ru по переданному списку поисковых запросов.

    Args:
        search_queries: список наименований вакансий для поиска
        area: регион (1 = Москва, 0 = вся Россия)
        max_pages: максимальное количество страниц на запрос

    Returns:
        dict с ключами csv_path и total_count
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"vacancies_{timestamp}.csv"

    parser = HHParser(
        search_queries=search_queries,
        area=area,
        max_pages=max_pages,
        save_to_json=False,
        save_to_csv=True,
        results_csv_path=csv_filename,
        csv_override=csv_filename,
    )

    await parser.run_parser()

    return {
        "csv_path": csv_filename,
        "total_count": len(parser.results),
    }
