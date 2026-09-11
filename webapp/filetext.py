"""Extract plain text from an uploaded book file (EPUB / PDF / TXT / MD).

Turns a teacher's legally-accessed copy into grounding text for the private tier-1
vault (the Living Library upload path). Never raises; returns "" on failure so a bad
file degrades to "no text" rather than crashing the extraction.
"""
from __future__ import annotations

import io
import logging
import os
import re
import tempfile

logger = logging.getLogger("study-bible-web.filetext")

SUPPORTED = ("epub", "pdf", "txt", "md")


def _from_txt(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:  # noqa: BLE001
            continue
    return data.decode("utf-8", "replace")


def _from_epub(data: bytes) -> str:
    try:
        import ebooklib
        from bs4 import BeautifulSoup
        from ebooklib import epub

        # ebooklib reads by path — park the bytes in a temp file, parse, delete.
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            book = epub.read_epub(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        parts: list[str] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            for t in soup(["script", "style"]):
                t.extract()
            txt = soup.get_text("\n").strip()
            if txt:
                parts.append(txt)
        return "\n\n".join(parts)
    except Exception:  # noqa: BLE001
        logger.exception("epub parse failed")
        return ""


_re_pagenum = re.compile(r"^\s*\d{1,4}\s*$")


def _strip_page_numbers(page_text: str) -> str:
    """Drop lines that are nothing but a page number. pypdf lands each page's number
    on its own line, and a bare integer is indistinguishable from an arabic chapter
    heading downstream — so hundreds of page numbers would over-segment the book."""
    return "\n".join(ln for ln in page_text.split("\n") if not _re_pagenum.match(ln))


def _from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(_strip_page_numbers(page.extract_text() or "") for page in reader.pages)
    except Exception:  # noqa: BLE001
        logger.exception("pdf parse failed")
        return ""


def extract_text(data: bytes, source_format: str) -> str:
    """Plain text from the file bytes; collapses runs of blank lines. "" on failure."""
    fmt = (source_format or "").lower().lstrip(".")
    if fmt in ("txt", "md", "text"):
        text = _from_txt(data)
    elif fmt == "epub":
        text = _from_epub(data)
    elif fmt == "pdf":
        text = _from_pdf(data)
    else:
        text = ""
    return re.sub(r"\n{3,}", "\n\n", (text or "").strip())


def looks_full(text: str, min_chars: int = 500) -> bool:
    """The 'verified-full' heuristic: substantial text, not an empty/scanned/DRM'd shell.
    A scanned image-only PDF yields ~nothing → not full → we reject rather than store an
    empty copy and delete the original."""
    return bool(text) and len(text) >= min_chars
