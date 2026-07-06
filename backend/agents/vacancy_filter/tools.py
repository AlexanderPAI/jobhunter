import csv
import logging

from langchain_core.tools import tool

logger = logging.getLogger("VACANCY_FILTER")


@tool
def save_filtered_csv(rows: list[dict], output_path: str) -> str:
    """
    Сохраняет отфильтрованные вакансии в CSV-файл.

    Args:
        rows       : список словарей -- строки CSV
        output_path: путь для сохранения файла

    Returns:
        Путь к сохранённому файлу.
    """
    if not rows:
        raise ValueError("Нет вакансий для сохранения")

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Сохранено {len(rows)} вакансий -> {output_path}")
    return output_path
