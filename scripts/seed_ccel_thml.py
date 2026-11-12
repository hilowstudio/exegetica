"""Build a Reading Room book straight from CCEL ThML, for works the ccel-paragraphs dataset never carried.

seed_theology_reader.py builds the CCEL shelf from the HuggingFace dataset; a few works CCEL hosts are missing from
it (Calvin's commentaries among them). CCEL serves each work's full ThML at https://ccel.org/ccel/<path>.xml, so this
fetches the volumes, keeps the author's own front matter (never a translator's or editor's: house rule, no
translator or editor credit), and writes one book whose chapters follow the work's own divisions:

- a `div1` chapter becomes a chapter; each `div2` passage (e.g. "John 1:1-5") a `<h3>` within it;
- the passage's printed translation (a one-cell table in ThML) becomes a displayed quotation;
- `<note>` footnotes become "[n]" markers with "[n] text" paragraphs, which webapp/typeset.py gathers as notes;
- scripture-reference and index markup is reduced to its text.

    python scripts/seed_ccel_thml.py calvin-john [--dry-run] [--db db/books.db]

Re-running replaces the book (same slug). Fetched ThML is cached in .seed_cache/ccel_thml/.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".seed_cache" / "ccel_thml"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

WORKS = {
    "calvin-john": {
        "slug": "ccel-calvin-john",
        "title": "Commentary on the Gospel According to John",
        "author": "John Calvin",
        "author_sort": "Calvin, John",
        "volumes": ["c/calvin/calcom34", "c/calvin/calcom35"],
        # the author's own front matter, retitled; everything else outside the chapters is dropped
        "front": {"Calvin's Epistle Dedicatory": "The Epistle Dedicatory", "The Argument": "The Argument"},
        "salutation": {"Calvin's Epistle Dedicatory"},     # front matter that opens with a printed address
        "chapter": lambda t: re.sub(r"^Chapter (\d+)$", r"John \1", t),
    },
}

HEADING_CLASS = re.compile(r"^(BOOK-CHAP|3rdLevel|HDG-|QUOTE16|TableCaption)")
KEEP = {"i", "b", "em", "strong", "sup", "sub", "br"}
ED_SIGN = re.compile(r"\s*[—–-]+\s*(<i>)?\s*Ed(itor)?\s*\.?\s*(</i>)?\s*\.?\s*(\))?\s*$")


def fetch(path: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (path.replace("/", "_") + ".xml")
    if not f.exists():
        import httpx
        r = httpx.get(f"https://ccel.org/ccel/{path}.xml", follow_redirects=True, timeout=120,
                      headers={"User-Agent": "Exegetica reading-room seeder"})
        r.raise_for_status()
        f.write_text(r.text, encoding="utf-8")
    return f.read_text(encoding="utf-8")


def parse(xml: str):
    from lxml import etree
    xml = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)(\w+);", lambda m: html.unescape(m.group(0)), xml)
    return etree.fromstring(xml.encode("utf-8"), etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False))


def esc(s: str | None) -> str:
    return html.escape(re.sub(r"\s+", " ", s or ""), quote=False)


class Chapter:
    def __init__(self, title: str):
        self.title, self.body, self.notes = title, [], []

    def inline(self, el) -> str:
        """An element's content as inline HTML; notes leave a marker and are kept for the chapter's end."""
        out = esc(el.text)
        for ch in el:
            tag = ch.tag if isinstance(ch.tag, str) else ""
            if tag == "note":
                n = ch.get("n") or str(len(self.notes) + 1)
                note = " ".join(self.inline(p) for p in ch.iter("p")).strip()
                note = ED_SIGN.sub("", note).strip()       # an editor's sign-off: no editor credit in the book
                self.notes.append((n, note))
                out = out.rstrip()
                # typeset links a marker only when a letter precedes it in the same text: after "<i>…</i>" it
                # goes inside the closing tag
                m = re.search(r"(</(?:i|b|em|strong)>)+$", out)
                out = (out[:m.start()] + f"[{n}]" + m.group(0)) if m else out + f"[{n}]"
            elif tag in ("scripCom", "insertIndex", "image") or not tag:
                pass
            elif tag in KEEP:
                inner = self.inline(ch)
                out += "<br>" if tag == "br" else f"<{tag}>{inner}</{tag}>" if inner.strip() else inner
            else:                                   # span, a, scripRef, ...: their words only
                out += self.inline(ch)
            out += esc(ch.tail)
        return out

    def block(self, el, skip_headings: bool = True) -> None:
        tag = el.tag if isinstance(el.tag, str) else ""
        cls = el.get("class") or ""
        if tag == "p":
            if skip_headings and HEADING_CLASS.match(cls):
                return
            text = self.inline(el).strip()
            if not text or text == " ":
                return
            if cls in ("Center", "QUOTE12", "SCRIPTURE"):
                self.body.append(f"<blockquote><p>{text}</p></blockquote>")
            else:
                self.body.append(f"<p>{text}</p>")
        elif tag == "table":                        # the passage as the translation prints it
            ps = [self.inline(p).strip() for p in el.iter("p") if not HEADING_CLASS.match(p.get("class") or "")]
            ps = [p for p in ps if p]
            if ps:
                self.body.append("<blockquote>" + "".join(f"<p>{p}</p>" for p in ps) + "</blockquote>")
        elif tag in ("div2", "div3"):
            t = (el.get("title") or "").strip()
            if t:
                self.body.append(f"<h3>{esc(re.sub(r'(?<=\d)-(?=\d)', '–', t))}</h3>")
            for ch in el:
                self.block(ch)
        elif tag in ("div", "ul", "ol"):
            if tag == "div":
                for ch in el:
                    self.block(ch)
            else:
                items = [self.inline(li).strip() for li in el.iter("li")]
                self.body.append(f"<{tag}>" + "".join(f"<li>{x}</li>" for x in items if x) + f"</{tag}>")
        # scripCom, note at block level, comments: nothing to show

    def html(self) -> str:
        notes = [f"<p>[{n}] {t}</p>" for n, t in self.notes if t]
        return "\n".join([f"<h2>{esc(self.title)}</h2>", *self.body, *notes])


def salutation(div) -> str:
    """An epistle's printed address (several display lines in capitals) as one line of italic text."""
    lines = [re.sub(r"\s+", " ", "".join(p.itertext())).strip() for p in div.iter("p")
             if HEADING_CLASS.match(p.get("class") or "")][1:]
    words = " ".join(x for x in lines if x)
    return words[:1].upper() + words[1:].lower() if words else ""


def build(spec: dict) -> list[Chapter]:
    chapters: list[Chapter] = []
    for path in spec["volumes"]:
        root = parse(fetch(path))
        body = root.find("ThML.body")
        for div in body.iter("div1"):
            title = (div.get("title") or "").strip()
            if div.get("type") == "Chapter":
                ch = Chapter(spec["chapter"](title))
            elif title in spec["front"]:
                ch = Chapter(spec["front"][title])
                sal = salutation(div) if title in spec.get("salutation", ()) else ""
                if sal:
                    sal = re.sub(r"\bgeneva\b", "Geneva", re.sub(r"\bjohn calvin\b", "John Calvin", sal))
                    sal = re.sub(r"\bthe syndics and council\b", "the Syndics and Council", sal)
                    sal = re.sub(r"\bthe lord the spirit\b", "the Lord the spirit", sal)
                    ch.body.append(f"<p><em>{esc(sal.rstrip('.'))}.</em></p>")
            else:
                continue
            for el in div:
                ch.block(el)
            chapters.append(ch)
    return chapters


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work", choices=sorted(WORKS))
    ap.add_argument("--db", default=str(ROOT / "db" / "books.db"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    spec = WORKS[a.work]
    chapters = build(spec)
    rows = []
    for n, ch in enumerate(chapters, 1):
        h = ch.html()
        rows.append((n, ch.title, h, len(re.sub(r"<[^>]+>", " ", h).split())))
    wc = sum(r[3] for r in rows)
    for n, t, h, w in rows:
        print(f"  {n:>3}  {t:<28} {w:>7,} words  {h.count('<h3>'):>3} passages  {len(re.findall(r'<p>\[\d+\] ', h)):>3} notes")
    print(f"{spec['slug']}: {len(rows)} chapters, {wc:,} words")
    if a.dry_run:
        return
    shelf = json.dumps(["Christianity"])
    con = sqlite3.connect(a.db)
    try:
        cur = con.cursor()
        old = cur.execute("select id from books where slug=?", (spec["slug"],)).fetchone()
        if old:
            cur.execute("delete from book_chapters where book_id=?", old)
            cur.execute("delete from books where id=?", old)
        cur.execute(
            """insert into books(slug,title,author,author_sort,source,license,us_clear,language,subjects,genres,section,
                                 genres_backup,title_backup,cover_url,chapter_count,word_count,access,front_html,added_at)
               values(?,?,?,?,'ccel','Public Domain (CCEL)',1,'en','[]',?,?,?,?,null,?,?,null,null,datetime('now'))""",
            (spec["slug"], spec["title"], spec["author"], spec["author_sort"], shelf, shelf, shelf, spec["title"],
             len(rows), wc))
        bid = cur.lastrowid
        cur.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                        [(bid, *r) for r in rows])
        con.commit()
    finally:
        con.close()
    print(f"loaded into {a.db}")


if __name__ == "__main__":
    main()
