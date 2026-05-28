from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import fitz  # PyMuPDF


@dataclass
class PdfTextResult:
    text: str
    page_count: int = 0
    error: str = ""


def extract_pdf_text(pdf_path: str) -> PdfTextResult:
    """Extract text from a PDF using PyMuPDF."""

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        return PdfTextResult(text="", page_count=0, error=f"Failed to open PDF: {exc}")

    pages: list[str] = []
    try:
        page_count = len(doc)
        for page in doc:
            try:
                pages.append(page.get_text("text"))
            except Exception:
                pages.append("")
    except Exception as exc:
        return PdfTextResult(text="", page_count=0, error=f"Failed to read PDF text: {exc}")
    finally:
        doc.close()

    text = "\n".join(pages).strip()
    return PdfTextResult(text=text, page_count=page_count, error="")
