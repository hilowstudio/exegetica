"""
Parsers for public-domain Bible dictionaries into the `dictionaries` table.

Each source is a headword-keyed reference work. New PD dictionaries (ISBE,
Smith's, ...) are added by registering a source here with a small parser that
yields {"headword": str, "body": str} rows; the download/import scripts are
source-agnostic.
"""

import html
import re

# Registry of bundled dictionary sources. `parser` names a function in this
# module. Only cleanly public-domain, machine-readable sources are listed.
DICTIONARY_SOURCES = {
    "eastons": {
        "name": "Easton's Bible Dictionary",
        "url": "https://raw.githubusercontent.com/garydavenport73/eastons-bible-dictionary-json/HEAD/eastons.json",
        "filename": "eastons.json",
        "parser": "parse_eastons",
        "license": "Public Domain (M.G. Easton, 1897)",
    },
}

_BRACKET_XREF = re.compile(r"\[\d+\]")          # Easton's "[18]ADONIRAM" markers
_WS = re.compile(r"[ \t]+")


def _clean(text: str) -> str:
    """Unescape HTML entities and strip the numbered cross-reference markers."""
    t = html.unescape(text or "")
    t = _BRACKET_XREF.sub("", t)
    t = _WS.sub(" ", t)
    return t.strip()


def parse_eastons(data: dict):
    """Easton's JSON: {headword: [{"definition": "..."}], ...}."""
    for headword, entries in data.items():
        if not isinstance(entries, list):
            entries = [entries]
        parts = []
        for e in entries:
            d = e.get("definition") if isinstance(e, dict) else str(e)
            d = _clean(d)
            if d:
                parts.append(d)
        body = "\n\n".join(parts)
        hw = (headword or "").strip()
        if hw and body:
            yield {"headword": hw, "body": body}
