from pathlib import Path

import docx
import pdfplumber


class FileReader:
    def __init__(self):
        self.file_readers = {
            ".txt": self._read_txt,
            ".pdf": self._read_pdf,
            ".docx": self._read_docx,
            ".doc": self._read_docx,
        }

    @staticmethod
    def _read_txt(file_path) -> str:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _read_pdf(file_path) -> str:
        with pdfplumber.open(file_path) as pdf_file:
            return "\n".join(page.extract_text() or "" for page in pdf_file.pages)

    @staticmethod
    def _read_docx(file_path) -> str:
        document = docx.Document(file_path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    def read_file(self, file_path):
        suffix = Path(file_path).suffix.lower()
        reader = self.file_readers.get(suffix, None)
        if reader is None:
            raise ValueError(f"Unsupported {suffix}")
        return reader(file_path)
