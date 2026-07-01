from pathlib import Path

from langchain_core.tools import tool

from backend.utils.readers import FileReader


@tool
def extract_cv_text(cv_path: str) -> str:
    """
    Читает файл резюме и возвращает его текстовое содержимое.

    Args:
        cv_path: путь к файлу резюме (.txt, .pdf, .docx, .doc)

    Returns:
        Текст резюме в виде строки.
    """
    file_path = Path(cv_path)
    file_reader = FileReader()
    return file_reader.read_file(file_path)
