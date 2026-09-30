from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from ..config import ALLOWED_EXTENSIONS


class ExtractionError(ValueError):
    """Raised when an uploaded file cannot be turned into usable text."""


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ExtractionError("Unsupported file type. Please upload a PDF or DOCX file.")

    if ext == ".pdf":
        try:
            reader = PdfReader(BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ExtractionError(
                "Could not read this PDF. It may be corrupted or password protected."
            ) from exc
    else:
        try:
            doc = Document(BytesIO(data))
            parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text for cell in row.cells))
            text = "\n".join(parts)
        except Exception as exc:
            raise ExtractionError("Could not read this DOCX file.") from exc

    text = text.strip()
    if len(text) < 50:
        raise ExtractionError(
            "No readable text found in this file. Scanned/image-only files are not supported."
        )
    return text
