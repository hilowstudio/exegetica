"""
Parser for reformed-standards/compendium confession & catechism YAML.

Two outputs from each document:
  * proof-text rows for `confession_proof_texts` (the Scripture a section cites,
    resolved from OSIS to internal verse spans) — the verse<->confession graph;
  * section rows for `historical_documents` (used only for documents not already
    bundled from TheologAI), so get_confession gains the net-new standards.

Document shapes handled:
  - flat catechism:  {questions: [{number, question, answer, verses}]}
  - day-nested:      {days: [{questions: [...]}]}      (Heidelberg)
  - confession:      {chapters: [{number, articles: [{number, text, verses}]}]}
"""

import re
from typing import Iterator

from .refs import parse_osis

# Tradition label per compendium doc id (for get_confession display).
COMPENDIUM_TRADITION = {
    "apostles-creed": "Ecumenical", "nicene-creed": "Ecumenical",
    "athanasian-creed": "Ecumenical", "chalcedonian-definition": "Ecumenical",
    "39-articles": "Anglican",
    "savoy": "Reformed (Congregational)", "second-helvetic": "Reformed",
    "scots-confession": "Reformed", "95-theses": "Lutheran",
    "1689-confession": "Reformed (Baptist)", "keach": "Reformed (Baptist)",
    "1858-abstract-of-principles": "Reformed (Baptist)",
    "belgic-confession": "Reformed", "canons-of-dort": "Reformed",
    "heidelberg-catechism": "Reformed",
    "wcf": "Reformed", "wlc": "Reformed", "wsc": "Reformed", "wsc-pca": "Reformed",
    "sum-of-saving-knowledge": "Reformed", "catechism-young-children": "Reformed",
}

# compendium doc_id -> path under data/ in the repo (proof-texts imported for all).
COMPENDIUM_DOCS = {
    "wcf": "westminster/wcf", "wlc": "westminster/wlc", "wsc": "westminster/wsc",
    "wsc-pca": "westminster/wsc-pca",
    "sum-of-saving-knowledge": "westminster/sum-of-saving-knowledge",
    "heidelberg-catechism": "three-forms-of-unity/heidelberg-catechism",
    "belgic-confession": "three-forms-of-unity/belgic-confession",
    "canons-of-dort": "three-forms-of-unity/canons-of-dort",
    "1689-confession": "second-london/1689-confession",
    "keach": "second-london/keach",
    "1858-abstract-of-principles": "second-london/1858-abstract-of-principles",
    "second-helvetic": "swiss/second-helvetic",
    "scots-confession": "scottish/scots-confession",
    "savoy": "british/savoy",
    "39-articles": "anglican/39-articles",
    "95-theses": "reformation/95-theses",
    "apostles-creed": "ancient-church/apostles-creed",
    "nicene-creed": "ancient-church/nicene-creed",
    "athanasian-creed": "ancient-church/athanasian-creed",
    "chalcedonian-definition": "ancient-church/chalcedonian-definition",
    "catechism-young-children": "miscellany/catechism-young-children",
}

# Documents NOT already bundled from TheologAI -> also add to historical_documents.
COMPENDIUM_NEW_DOCS = {
    "wsc-pca", "sum-of-saving-knowledge", "1858-abstract-of-principles", "keach",
    "second-helvetic", "scots-confession", "savoy", "95-theses",
    "catechism-young-children",
}

_MARKER = re.compile(r"\[[a-z]{1,2}\]")


def _clean(text: str) -> str:
    """Drop inline footnote markers like [a],[bc] from display text."""
    return _MARKER.sub("", text or "").strip()


def _iter_sections(doc: dict) -> Iterator[tuple[str, str, dict]]:
    """Yield (section_label, section_text, verses_dict) for each article/question."""
    if "questions" in doc:
        for q in doc["questions"]:
            if isinstance(q, dict):
                yield _question_section(q)
    elif "days" in doc:
        for day in doc["days"]:
            if not isinstance(day, dict):
                continue
            for q in day.get("questions", []):
                if isinstance(q, dict):
                    yield _question_section(q)
    elif "chapters" in doc:
        for ch in doc["chapters"]:
            if not isinstance(ch, dict):
                continue
            cnum = ch.get("number")
            for art in ch.get("articles", []):
                if not isinstance(art, dict):
                    continue
                label = f"{cnum}.{art.get('number')}"
                yield label, _clean(art.get("text", "")), (art.get("verses") or {})


def _question_section(q: dict) -> tuple[str, str, dict]:
    label = f"Q{q.get('number')}"
    text = f"Q. {(q.get('question') or '').strip()}\n\nA. {_clean(q.get('answer', ''))}".strip()
    return label, text, (q.get("verses") or {})


def parse_compendium_proofs(doc: dict, doc_id: str) -> Iterator[dict]:
    """Yield one proof-text row per (section, marker, cited OSIS reference)."""
    title = doc.get("name", doc_id)
    for label, text, verses in _iter_sections(doc):
        # `verses` is usually {marker: [refs]}, but some docs give a bare list.
        if isinstance(verses, list):
            groups = {"": verses}
        elif isinstance(verses, dict):
            groups = verses
        else:
            groups = {}
        for marker, refs in groups.items():
            for ref in refs or []:
                if not isinstance(ref, str):
                    continue
                parsed = parse_osis(ref)
                if not parsed:
                    continue
                book, chap, v1, v2 = parsed
                yield {
                    "doc_id": doc_id, "doc_title": title, "section_label": label,
                    "section_text": text, "marker": marker, "osis_ref": ref,
                    "book": book, "chapter": chap, "verse_start": v1, "verse_end": v2,
                }


def parse_compendium_sections(doc: dict, doc_id: str) -> Iterator[dict]:
    """Yield historical_documents rows (for net-new documents)."""
    title = doc.get("name", doc_id)
    dtype = doc.get("type", "")
    date = str(doc.get("publication_year", ""))
    tradition = COMPENDIUM_TRADITION.get(doc_id, "Reformed")
    for i, (label, text, _verses) in enumerate(_iter_sections(doc)):
        if not text:
            continue
        yield {
            "doc_id": doc_id, "doc_title": title, "doc_type": dtype, "doc_date": date,
            "tradition": tradition, "section_num": i, "section_label": label,
            "content": text, "topics": "",
        }
