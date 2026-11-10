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

SUPPORTED = ("epub", "pdf", "txt", "md", "docx")


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


def _from_docx(data: bytes) -> str:
    """A Word document's paragraphs, read straight from its XML (no extra dependency)."""
    import html as _html
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        logger.exception("docx parse failed")
        return ""
    paras = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        p = p.replace("<w:tab/>", "<w:t>\t</w:t>").replace("<w:br/>", "<w:t>\n</w:t>")
        runs = re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", p, re.S)
        paras.append(_html.unescape("".join(runs)))
    return "\n\n".join(x for x in paras if x.strip())


def extract_text(data: bytes, source_format: str) -> str:
    """Plain text from the file bytes; collapses runs of blank lines. "" on failure."""
    fmt = (source_format or "").lower().lstrip(".")
    if fmt in ("txt", "md", "text"):
        text = _from_txt(data)
    elif fmt == "epub":
        text = _from_epub(data)
    elif fmt == "pdf":
        text = _from_pdf(data)
    elif fmt == "docx":
        text = _from_docx(data)
    else:
        text = ""
    return re.sub(r"\n{3,}", "\n\n", (text or "").strip())


def _epub_toc(data: bytes) -> list[str]:
    try:
        from ebooklib import epub

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

        titles: list[str] = []

        def walk(items):
            for it in items:
                if isinstance(it, (list, tuple)):
                    walk(it)
                else:
                    t = getattr(it, "title", None)
                    if t:
                        titles.append(str(t).strip())

        walk(book.toc or [])
        return titles
    except Exception:  # noqa: BLE001
        logger.exception("epub toc failed")
        return []


def _pdf_toc(data: bytes) -> list[str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        titles: list[str] = []

        def walk(items):
            for it in items:
                if isinstance(it, list):
                    walk(it)
                else:
                    t = getattr(it, "title", None)
                    if t:
                        titles.append(str(t).strip())

        walk(getattr(reader, "outline", []) or [])
        return titles
    except Exception:  # noqa: BLE001
        logger.exception("pdf outline failed")
        return []


# Generic front-matter / back-matter TOC entries that aren't real content sections.
_TOC_SKIP = re.compile(
    r"^\s*(cover|title\s*page|copyright|contents|table of contents|dedication|"
    r"acknowledge?ments?|about the author|colophon|index|notes?|bibliography|"
    r"foreword|frontmatter|nav|toc)\s*$", re.I)


def extract_toc(data: bytes, source_format: str) -> list[str]:
    """A published table of contents (ordered entry titles) from an EPUB's nav or a PDF's
    outline, with obvious front/back-matter entries filtered out. [] when unavailable."""
    fmt = (source_format or "").lower().lstrip(".")
    raw = _epub_toc(data) if fmt == "epub" else (_pdf_toc(data) if fmt == "pdf" else [])
    return [t for t in raw if t and not _TOC_SKIP.match(t)]


def looks_full(text: str, min_chars: int = 500) -> bool:
    """The 'verified-full' heuristic: substantial text, not an empty/scanned/DRM'd shell.
    A scanned image-only PDF yields ~nothing → not full → we reject rather than store an
    empty copy and delete the original."""
    return bool(text) and len(text) >= min_chars
