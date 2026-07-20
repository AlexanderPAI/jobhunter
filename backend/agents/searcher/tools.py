from typing import List

from langchain_core.tools import tool

from backend.utils.parser import CareerHabrParser, HHParser, SearchFilters


@tool
async def parse_vacancies(
    search_queries: List[str],
    filters: dict,
    area: int = 1,
    max_pages: int = 1,
) -> dict:
    """
    Запускает парсер hh.ru и возвращает найденные вакансии.

    Args:
        search_queries : список поисковых запросов
        filters        : параметры фильтрации (ЗП, график, опыт и т.д.)
        area           : регион (1 = Москва, 0 = вся Россия)
        max_pages      : страниц на каждый запрос
    Returns: dict {vacancies, total_count}
    """
    # Импорты — только внутри tool, агент о них не знает

    search_filters = SearchFilters(
        **{key: value for key, value in filters.items() if value is not None}
    )

    parser = HHParser(
        search_queries=search_queries,
        area=area,
        max_pages=max_pages,
        filters=search_filters,
        save_to_json=False,
        save_to_csv=False,
    )

    vacancies = await parser.run_parser()

    return {
        "vacancies": vacancies,
        "total_count": len(vacancies),
    }


@tool
async def parse_habr_vacancies(
    search_queries: List[str],
    filters: dict,
    area: int = 1,
    max_pages: int = 1,
) -> dict:
    """
    Запускает парсер career.habr.com и возвращает найденные вакансии.

    Args:
        search_queries : список поисковых запросов
        filters        : параметры фильтрации (часть применяется после сбора)
        area           : регион (1 = Москва, 0 = вся Россия)
        max_pages      : страниц на каждый запрос
    Returns: dict {vacancies, total_count}
    """
    search_filters = SearchFilters(
        **{key: value for key, value in filters.items() if value is not None}
    )

    parser = CareerHabrParser(
        search_queries=search_queries,
        area=area,
        max_pages=max_pages,
        filters=search_filters,
        save_to_json=False,
        save_to_csv=False,
    )

    vacancies = await parser.run_parser()

    return {
        "vacancies": vacancies,
        "total_count": len(vacancies),
    }
