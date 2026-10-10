"""Document parsing and text extraction for PDF and DOCX files."""

import io
import logging
from pathlib import Path

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DocumentParser:
    """Extracts text from PDF and DOCX documents for legal analysis."""

    @classmethod
    def extract_text_from_pdf(cls, file_bytes_or_path: bytes | str | Path) -> str:
        """Extract text from a PDF file."""
        try:
            if isinstance(file_bytes_or_path, bytes):
                stream = io.BytesIO(file_bytes_or_path)
                reader = PdfReader(stream)
            else:
                reader = PdfReader(str(file_bytes_or_path))

            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(f"--- Sahifa {i + 1} ---\n{text}")

            full_text = "\n\n".join(pages_text).strip()
            logger.info("Extracted %d chars from PDF", len(full_text))
            return full_text
        except Exception as e:
            logger.error("Error extracting text from PDF: %s", e)
            raise ValueError(f"PDF matnini ajratib bo'lmadi: {e}") from e

    @classmethod
    def extract_text_from_docx(cls, file_bytes_or_path: bytes | str | Path) -> str:
        """Extract text from a DOCX Word file."""
        try:
            if isinstance(file_bytes_or_path, bytes):
                stream = io.BytesIO(file_bytes_or_path)
                doc = Document(stream)
            else:
                doc = Document(str(file_bytes_or_path))

            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        paragraphs.append(row_text)

            full_text = "\n\n".join(paragraphs).strip()
            logger.info("Extracted %d chars from DOCX", len(full_text))
            return full_text
        except Exception as e:
            logger.error("Error extracting text from DOCX: %s", e)
            raise ValueError(f"DOCX matnini ajratib bo'lmadi: {e}") from e

    @classmethod
    def extract_text(cls, filename: str, file_bytes: bytes) -> str:
        """Auto-detect file extension and extract text."""
        ext = filename.lower().rsplit(".", 1)[-1]
        if ext == "pdf":
            return cls.extract_text_from_pdf(file_bytes)
        elif ext in ("docx", "doc"):
            return cls.extract_text_from_docx(file_bytes)
        elif ext in ("txt", "md"):
            return file_bytes.decode("utf-8", errors="replace")
        else:
            raise ValueError(
                f"Qo'llab-quvvatlanmaydigan fayl formati: .{ext}. Iltimos, PDF yoki Word (.docx) yuklang."
            )
