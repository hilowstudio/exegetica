"""Seed teacher_courses (decision 0026) from the school's book list, so each teacher's Living Library opens
on the books for their own classes.

    python scripts/seed_teacher_courses.py "Curriculum Count_Classroom Supplies 2026_27.xlsx"           # what it would do
    python scripts/seed_teacher_courses.py "Curriculum Count_Classroom Supplies 2026_27.xlsx" --write   # write to Neon

The list has one tab per teacher, named for them. A tab is matched to an account when exactly one address in
TEACHER_EMAILS contains a surname from the tab's name; its courses are the courses of the works it lists
(webapp/data/yorkville.json), found by ISBN or title. Only the address and course keys are written, as
'school' rows, and a course a teacher removed is never put back. Names are read here and nowhere stored or
printed (pass --show-names to see which tabs went unmatched on your own screen). Reads .env for
TEACHER_EMAILS and DATABASE_URL. Needs only the standard library to read the sheet."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def sheets(path: Path) -> list[tuple[str, list[str]]]:
    """(tab name, every non-empty cell's text) for each tab of an .xlsx, read with the standard library."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        out = []
        for s in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
            target = rels[s.get(f"{{{NS['r']}}}id")].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            cells = []
            for c in ET.fromstring(z.read(target)).iter(f"{{{NS['m']}}}c"):
                v = c.find("m:v", NS)
                if c.get("t") == "s" and v is not None:
                    cells.append(shared[int(v.text)])
                elif c.get("t") == "inlineStr":
                    cells.append("".join(t.text or "" for t in c.iter(f"{{{NS['m']}}}t")))
                elif v is not None and v.text:
                    cells.append(v.text)
            out.append((s.get("name"), [x.strip() for x in cells if x and x.strip()]))
        return out


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower().replace("&", "and")).strip()


def courses_for(cells: list[str], works: list[dict]) -> set[str]:
    text = " " + _norm(" ".join(cells)) + " "
    cores = set()                                  # the nine digits an ISBN-10 and its ISBN-13 share
    for cell in cells:                             # one cell at a time, so neighbouring ISBNs never run together
        flat = re.sub(r"[\s\-]", "", cell)
        cores |= {m[3:12] for m in re.findall(r"97[89]\d{10}", flat)}
        cores |= {m[:9] for m in re.findall(r"(?<!\d)\d{9}[\dXx](?!\d)", flat)}
    found = set()
    for w in works:
        isbn = any((i[3:12] if len(i) == 13 else i[:9]) in cores for i in w.get("isbns") or [])
        names = []
        for n in [w.get("title") or "", *(w.get("aka") or [])]:
            names.append(_norm(n))
            head = _norm(n.split(":")[0])
            if len(head.split()) >= 2:            # "Tim Tebow: Through My Eyes", never a bare "History"
                names.append(head)
        named = any(len(t) >= 5 and f" {t} " in text for t in names)
        if isbn or named:
            found.update(w["courses"])
    return found


def account_for(tab: str, emails: list[str]) -> str | None:
    tokens = [t for t in re.findall(r"[a-z]+", tab.lower()) if len(t) >= 3 and t not in ("music", "the")]
    for t in tokens:
        hits = [e for e in emails if t in re.sub(r"[^a-z]", "", e.split("@")[0])]
        if len(hits) == 1:
            return hits[0]
    return None


async def write(rows: list[tuple[str, str]]) -> int:
    from webapp import db
    await db.init_pool()
    if not db.ready():
        sys.exit("DATABASE_URL is not set or Neon is unreachable.")
    try:
        n = 0
        for email, key in rows:
            status = await db.execute("insert into teacher_courses (email, course_key, source) values ($1, $2, 'school') "
                                      "on conflict (email, course_key) do nothing", email, key)
            n += status.endswith(" 1")
        return n
    finally:
        await db.close_pool()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("xlsx", type=Path)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show-names", action="store_true")
    a = ap.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
    import os
    emails = sorted({e.strip().lower() for e in (os.environ.get("TEACHER_EMAILS") or "").split(",") if e.strip()})
    works = json.loads((ROOT / "webapp" / "data" / "yorkville.json").read_text(encoding="utf-8"))["works"]
    rows, unmatched, empty = [], [], []
    tabs = sheets(a.xlsx)
    for i, (tab, cells) in enumerate(tabs, 1):
        keys = courses_for(cells, works)
        who = account_for(tab, emails)
        label = tab if a.show_names else f"tab {i}"
        if not keys:
            empty.append(label)
        elif not who:
            unmatched.append(label)
        else:
            rows += [(who, k) for k in sorted(keys)]
    teachers = len({e for e, _ in rows})
    print(f"{len(tabs)} tabs: {teachers} matched to an account with {len(rows)} course rows; "
          f"{len(unmatched)} with books but no single matching account ({', '.join(unmatched) or 'none'}); "
          f"{len(empty)} listing none of the school's texts ({', '.join(empty) or 'none'}).")
    if a.write:
        print(f"wrote {asyncio.run(write(rows))} new rows (rows already there, or removed by a teacher, are left as they are)")
    else:
        print("nothing written; pass --write to write these rows")


if __name__ == "__main__":
    main()
