"""
Parsers for two datasets vendored by TJ-Frederick/TheologAI:

- Historical documents (creeds / confessions / catechisms) — public-domain texts
  in a small JSON schema {title, type, date, sections[], topics[]}. Catechism
  sections are {question, q, a}; other sections are {title, content, topics}.
- The UBS Parallel Passage Database (CC BY-SA 4.0) — a Paratext XML of <Passage>
  groups, each a set of <Verse> references that are editorially parallel.
"""

import re
import xml.etree.ElementTree as ET
from typing import Iterator

from .lxx import usfm_to_internal

# The 17 documents and their tradition (for display / filtering).
DOC_TRADITION = {
    "apostles-creed": "Ecumenical", "nicene-creed": "Ecumenical",
    "athanasian-creed": "Ecumenical", "chalcedonian-definition": "Ecumenical",
    "westminster-confession": "Reformed", "westminster-larger-catechism": "Reformed",
    "westminster-shorter-catechism": "Reformed", "belgic-confession": "Reformed",
    "canons-of-dort": "Reformed", "heidelberg-catechism": "Reformed",
    "london-baptist-1689": "Reformed (Baptist)",
    "augsburg-confession": "Lutheran", "39-articles": "Anglican",
    "council-of-trent": "Catholic", "baltimore-catechism": "Catholic",
    "confession-of-dositheus": "Orthodox", "philaret-catechism": "Orthodox",
}


def parse_historical_document(data: dict, doc_id: str) -> Iterator[dict]:
    """Yield one row per section of a creed/confession/catechism."""
    title = data.get("title", doc_id)
    dtype = data.get("type", "")
    date = data.get("date", "")
    tradition = DOC_TRADITION.get(doc_id, "")
    for i, sec in enumerate(data.get("sections", []) or []):
        if not isinstance(sec, dict):
            continue
        if "q" in sec or "a" in sec:
            # Heidelberg-style catechism: {question: <number>, q, a}
            label = f"Q{sec.get('question', i + 1)}"
            content = f"Q. {(sec.get('q') or '').strip()}\n\nA. {(sec.get('a') or '').strip()}".strip()
        elif "answer" in sec or "question_number" in sec:
            # Baltimore/Philaret-style catechism: {question_number, question, answer}
            label = f"Q{sec.get('question_number', i + 1)}"
            content = f"Q. {(sec.get('question') or '').strip()}\n\nA. {(sec.get('answer') or '').strip()}".strip()
        else:
            label = sec.get("title", "") or f"Section {i + 1}"
            content = (sec.get("content") or "").strip()
        if not content:
            continue
        topics = sec.get("topics") or []
        yield {
            "doc_id": doc_id, "doc_title": title, "doc_type": dtype, "doc_date": date,
            "tradition": tradition, "section_num": i, "section_label": label,
            "content": content, "topics": ", ".join(topics) if isinstance(topics, list) else str(topics or ""),
        }


def _parse_ubs_ref(ref: str) -> tuple[str, int, int, int] | None:
    """'GEN 2:24' -> ('Gen',2,24,24); 'MRK 10:7-8' -> ('Mrk',10,7,8)."""
    parts = ref.strip().split(None, 1)
    if len(parts) != 2 or ":" not in parts[1]:
        return None
    book = usfm_to_internal(parts[0])
    chap_s, verses = parts[1].split(":", 1)
    if not chap_s.strip().isdigit():
        return None
    chapter = int(chap_s)
    m1 = re.match(r"\d+", verses.strip())
    if not m1:
        return None
    v1 = int(m1.group())
    v2 = v1
    if "-" in verses:
        tail = verses.split("-", 1)[1]
        tail = tail.split(":", 1)[1] if ":" in tail else tail  # cross-chapter -> take end verse
        m2 = re.match(r"\d+", tail.strip())
        if m2:
            v2 = int(m2.group())
    if v2 < v1:
        v2 = v1
    return book, chapter, v1, v2


def parse_ubs_parallels(xml_text: str) -> Iterator[dict]:
    """Yield {group_id, book, chapter, verse_start, verse_end, ref_display} rows."""
    root = ET.fromstring(xml_text)
    group_id = 0
    for passage in root.findall("Passage"):
        group_id += 1
        for verse_el in passage.findall("Verse"):
            ref = (verse_el.text or "").strip()
            parsed = _parse_ubs_ref(ref)
            if not parsed:
                continue
            book, chapter, v1, v2 = parsed
            disp = f"{book} {chapter}:{v1}" + (f"-{v2}" if v2 != v1 else "")
            yield {
                "group_id": group_id, "book": book, "chapter": chapter,
                "verse_start": v1, "verse_end": v2, "ref_display": disp,
            }
