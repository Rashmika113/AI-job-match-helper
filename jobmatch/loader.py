"""Turn an uploaded CV (PDF or plain text) into a string."""

from __future__ import annotations

import io
import re
from pathlib import Path

from pypdf import PdfReader


def read_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return clean_text("\n".join(pages))


def read_upload(filename: str, data: bytes) -> str:
    """Read an uploaded file by its extension: .pdf, .txt or .md."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        text = read_pdf(data)
        if not text:
            raise ValueError(
                "No text found in this PDF. Is it a scanned image? Try pasting the text instead."
            )
        return text
    if suffix in {".txt", ".md"}:
        return clean_text(data.decode("utf-8", errors="replace"))
    raise ValueError(f"Unsupported file type {suffix!r}. Upload a PDF or .txt file.")


def clean_text(text: str) -> str:
    """Normalise whitespace but keep line breaks, which separate CV sections."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()
