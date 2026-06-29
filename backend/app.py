import asyncio
import logging

from backend.utils.parser import HHParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_quires():
    queries = []
    while True:
        query = input(
            "Введи название вакансии (для перехода к следующему этапу, введи END: "
        )
        if query == "END":
            break
        queries.append(query)
    return queries


def get_pages_amount():
    max_pages = input("Введи количество страниц, которое нужно распарсить: ")
    return int(max_pages)


async def main():
    search_queries = get_quires()
    max_pages = get_pages_amount()

    parser = HHParser(
        search_queries=search_queries,
        area=1,
        max_pages=max_pages,
        save_to_csv=True,
    )
    await parser.run_parser()


if __name__ == "__main__":
    asyncio.run(main())
