import csv
import logging

from langchain_core.tools import tool

logger = logging.getLogger("VACANCY_FILTER")


@tool
def save_filtered_csv(
    rows: list[dict], output_path: str, fieldnames: list[str] | None = None
) -> str:
    """
    Сохраняет отфильтрованные вакансии в CSV-файл.

    Args:
        rows       : список словарей -- строки CSV
        output_path: путь для сохранения файла
        fieldnames : заголовки CSV, нужны если rows пустой

    Returns:
        Путь к сохранённому файлу.
    """
    if not rows and not fieldnames:
        raise ValueError("Нет вакансий и заголовков для сохранения")

    fieldnames = fieldnames or list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    logger.info(f"Сохранено {len(rows)} вакансий -> {output_path}")
    return output_path
