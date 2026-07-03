from datetime import datetime
from pathlib import Path
from typing import List

from langchain_core.tools import tool

from backend.utils.parser import HHParser, SearchFilters


@tool
async def parse_vacancies(
    search_queries: List[str],
    filters: dict,
    area: int = 1,
    max_pages: int = 1,
    csv_path: str = "",
) -> dict:
    """
    Запускает парсер hh.ru и сохраняет результат в CSV.

    Args:
        search_queries : список поисковых запросов
        filters        : параметры фильтрации (ЗП, график, опыт и т.д.)
        area           : регион (1 = Москва, 0 = вся Россия)
        max_pages      : страниц на каждый запрос
        csv_path       : имя CSV-файла (если пусто — генерируется по дате)

    Returns:
        dict {csv_path, total_count}
    """
    # Импорты — только внутри tool, агент о них не знает

    if not csv_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = Path(
            Path(__file__).parent.parent.parent
            / f"storage/results/vacancies_{timestamp}.csv"
        )
        # csv_path = f"storage/results/vacancies_{timestamp}.csv"

    search_filters = SearchFilters(
        **{key: value for key, value in filters.items() if value is not None}
    )

    parser = HHParser(
        search_queries=search_queries,
        area=area,
        max_pages=max_pages,
        filters=search_filters,
        save_to_json=False,
        save_to_csv=True,
        results_csv_path=csv_path,
    )

    vacancies = await parser.run_parser()

    return {
        "csv_path": csv_path,
        "total_count": len(vacancies),
    }
