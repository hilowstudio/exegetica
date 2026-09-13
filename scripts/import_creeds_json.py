"""Import NET-NEW public-domain confessions/catechisms from NonlinearFruit/Creeds.json into the
MCP's `historical_documents` table (served by get_confession).

Only adds documents the MCP does NOT already have — dedup is by normalized title against the
existing rows, plus an explicit skip-list for known aliases (e.g. Keach's Catechism == the
"1695 Baptist Catechism") and for bare-Scripture "creeds" we already serve as Bible text.
Non-PD documents are excluded by their SourceAttribution (drops the 1978 Chicago Statement).

    .venv\\Scripts\\python.exe scripts\\import_creeds_json.py --dry-run   # preview net-new
    .venv\\Scripts\\python.exe scripts\\import_creeds_json.py             # write

This is a post-`build_database.py --rebuild` importer (re-run after any rebuild).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys

_DB = "db/study_bible.db"
_SRC = ".seed_cache/Creeds.json/creeds"

# Bare-Scripture "creeds" (we already serve the Bible) + known duplicates of existing docs.
_SKIP_FILES = {
    "christian_shema", "shema_yisrael", "christ_hymn_of_colossians",
    "christ_hymn_of_philippians", "confession_of_peter",   # Scripture text, already ours
    "1695_baptist_catechism",                              # == Keach's Catechism (already present)
}

# Tradition label per net-new doc (get_confession display). Default "Reformed".
_TRADITION = {
    "ignatius_creed": "Patristic", "irenaeus_rule_of_faith": "Patristic",
    "tertullians_rule_of_faith": "Patristic", "gregorys_declaration_of_faith": "Patristic",
    "council_of_orange": "Ecumenical", "ten_theses_of_berne": "Reformed",
    "abstract_of_principles": "Reformed (Baptist)", "puritan_catechism": "Reformed (Baptist)",
}


def norm_title(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    # drop connective words + 4-digit years, keep distinguishing words (first/second/…), so
    # "1689 London Baptist Confession" == the existing "London Baptist Confession of Faith".
    drop = {"the", "of", "faith", "a", "an", "and"}
    return " ".join(t for t in s.split() if t not in drop and not re.fullmatch(r"\d{4}", t))


def existing_titles(con) -> set[str]:
    out = set()
    for (t,) in con.execute("select distinct doc_title from historical_documents"):
        out.add(norm_title(t))
    return out


def sections(data) -> list[tuple]:
    """(section_num, section_label, content) for either Data shape (dict items or bare strings)."""
    if isinstance(data, str):
        data = [data]
    rows = []
    for i, item in enumerate(data or [], 1):
        if isinstance(item, str):  # short creed: a paragraph of text
            content, num, label = item.strip(), str(i), f"Paragraph {i}"
            if content:
                rows.append((num, label, content))
            continue
        if isinstance(item.get("Sections"), list):  # Chapter -> Sections (2nd Helvetic, WCF-style)
            chap = str(item.get("Chapter") or item.get("Number") or i)
            chap_title = item.get("Title") or f"Chapter {chap}"
            for sub in item["Sections"]:
                sub_n = str(sub.get("Section") or sub.get("Number") or "")
                content = (sub.get("Content") or "").strip()
                if content:
                    rows.append((f"{chap}.{sub_n}" if sub_n else chap, chap_title, content))
            continue
        if "Content" in item:  # Article/Title/Content confession
            num = str(item.get("Article") or item.get("Number") or i)
            label = item.get("Title") or f"Article {num}"
            content = item.get("Content") or ""
        else:  # Number/Question/Answer catechism
            num = str(item.get("Number") or i)
            label = f"Q{num}"
            q = (item.get("Question") or "").strip()
            a = (item.get("Answer") or "").strip()
            subs = item.get("SubQuestions") or []
            content = (f"Q. {q}\nA. {a}" if q or a else "").strip()
            for sq in subs:
                content += f"\n  Q. {(sq.get('Question') or '').strip()}\n  A. {(sq.get('Answer') or '').strip()}"
        content = content.strip()
        if content:
            rows.append((num, label, content))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(_DB)
    have = existing_titles(con)

    to_add, skipped = [], []
    for path in sorted(glob.glob(f"{_SRC}/*.json")):
        stem = os.path.splitext(os.path.basename(path))[0]
        d = json.load(open(path, encoding="utf-8"))
        meta, data = d.get("Metadata", {}), d.get("Data", [])
        title = meta.get("Title") or stem.replace("_", " ").title()
        src = meta.get("SourceAttribution") or ""
        alts = [norm_title(a) for a in (meta.get("AlternativeTitles") or [])]

        if stem in _SKIP_FILES:
            skipped.append((title, "already ours / Scripture")); continue
        if "public domain" not in src.lower():
            skipped.append((title, f"not PD ({src[:30]})")); continue
        if norm_title(title) in have or any(a in have for a in alts):
            skipped.append((title, "already in MCP")); continue

        secs = sections(data)
        if not secs:
            skipped.append((title, "no parseable sections")); continue
        doc_id = stem.replace("_", "-")
        is_cat = "catechism" in title.lower() or (
            isinstance(data, list) and any(isinstance(i, dict) and "Question" in i for i in data))
        doc_type = "catechism" if is_cat else ("creed" if "creed" in title.lower() else "confession")
        to_add.append({
            "doc_id": doc_id, "doc_title": title, "doc_type": doc_type,
            "doc_date": str(meta.get("Year") or ""), "tradition": _TRADITION.get(stem, "Reformed"),
            "sections": secs,
        })

    print(f"NET-NEW to add: {len(to_add)}    (skipped {len(skipped)})\n")
    for doc in to_add:
        print(f"  + {doc['doc_title']}  ({doc['doc_date']}, {doc['tradition']}, {len(doc['sections'])} sections)")
    print("\n  skipped:")
    for t, why in skipped:
        print(f"    - {t[:44]:44} {why}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        con.close()
        return

    n = 0
    for doc in to_add:
        for num, label, content in doc["sections"]:
            con.execute(
                "insert into historical_documents "
                "(doc_id, doc_title, doc_type, doc_date, tradition, section_num, section_label, content, topics) "
                "values (?,?,?,?,?,?,?,?,?)",
                (doc["doc_id"], doc["doc_title"], doc["doc_type"], doc["doc_date"],
                 doc["tradition"], num, label, content, None))
            n += 1
    con.commit()
    con.close()
    print(f"\nwrote {n} section rows across {len(to_add)} new documents into historical_documents")


if __name__ == "__main__":
    main()
