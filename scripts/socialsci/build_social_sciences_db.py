"""Build db/social_sciences.db: the owned corpus behind the Social Sciences Mode (socialsci_mcp).

Everything here was harvested once into .seed_cache/socialsci/ (see docs/social-sciences-sources.md);
this script turns it into one SQLite file, the way theology.db backs search_theology:

  documents   one row per document (source, collection, title, author, date, url, citation, rights, text)
  sections    the Constitution Test texts, addressable by part: U.S. Constitution (article / section /
              amendment), Illinois Constitution (article / section), U.S. Flag Code (4 U.S.C. §1-10)
  passages    ~1.5k-char chunks of every document and Reading Room history book, for citation
  passages_fts  FTS5 (title, text) over passages, BM25-ranked
  passages_vec  sqlite-vec int8 vectors (model2vec potion-retrieval-32M), for search by meaning

Sources (all cleared for self-hosting; rights notes in the plan doc):
  Avalon Project (Yale): public-domain and government documents only. Pages whose source note
    says "Used with the Permission of ..." or that cite a commercial press after 1930 are left out,
    because that permission was granted to Avalon, not to us.
  Miller Center presidential speeches: transcripts only (the editorial introductions are left out).
  DocSouth (UNC): North American Slave Narratives, First-Person Narratives of the American South,
    The Church in the Southern Black Community.
  Illinois Constitution (ilga.gov) and the U.S. Flag Code (govinfo, 4 U.S.C. ch. 1).
  The Reading Room (db/books.db): the History and "Society, Politics & Economics" shelves.

    .venv/Scripts/python.exe scripts/socialsci/build_social_sciences_db.py [--no-books] [--no-vectors]
"""
from __future__ import annotations

import argparse
import csv
import glob
import html as _html
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / ".seed_cache" / "socialsci"
DB = ROOT / "db" / "social_sciences.db"
BOOKS = ROOT / "db" / "books.db"
MODEL = "minishlab/potion-retrieval-32M"
CHUNK = 1500
BOOK_SECTIONS = ('"History"', '"Society, Politics & Economics"')
GOV = re.compile(r"government printing|g\.p\.o\.|u\.s\. govt|public papers of the presidents|federal register|"
                 r"congressional record|statutes at large|foreign relations of the united states|"
                 r"department of state|congress|"
                 r"senate|house of representatives|united nations|state department|"
                 r"office of|washington, d\.c\.: u\.s\.", re.I)

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman(s: str) -> int:
    s, total = s.upper(), 0
    for i, ch in enumerate(s):
        v = ROMAN.get(ch, 0)
        total += -v if i + 1 < len(s) and ROMAN.get(s[i + 1], 0) > v else v
    return total


def strip(h: str) -> str:
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</h[1-6]>|</div>|</tr>|</li>", "\n", h)
    t = _html.unescape(re.sub(r"(?s)<[^>]+>", " ", h)).replace("\xad", "").replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n\s*", "\n\n", t).strip()


def year_of(*vals: str) -> int | None:
    for v in vals:
        m = re.search(r"\b(1[0-9]{3}|20[0-2][0-9])\b", v or "")
        if m:
            return int(m.group(1))
    return None


# ---------------------------------------------------------------- sources
def avalon():
    """Yield (meta, text) for each cleared Avalon document; also count what was set aside."""
    root = SEED / "avalon"
    index = json.loads((root / "_index.json").read_text(encoding="utf-8")) if (root / "_index.json").exists() else {}
    set_aside = []
    for url, rel in sorted(index.items()):
        if not rel or rel.startswith("subject_menus/") or rel in ("default.asp", "index"):
            continue
        p = root / rel
        if not p.exists():
            continue
        s = p.read_text(encoding="latin-1")
        if 'class="document-title"' not in s:
            continue
        meta = dict(re.findall(r'<META NAME="(DC\.[A-Za-z.]+)" CONTENT="([^"]*)"', s, re.I))
        title = strip(re.search(r'(?is)class="document-title">(.*?)</div>', s).group(1)) or meta.get("DC.Title.Alternate", "")
        title = re.sub(r"\s+", " ", title).strip()
        body = s[s.find('class="document-title"'):]
        # page-menu tables (Contents / Notes links) can sit above the text as well as below it:
        # drop them, then cut at the source box or the site menu that closes the page
        body = re.sub(r'(?is)<table[^>]*class="page-menu".*?</table>', " ", body)
        cut = min([i for i in (body.find('class="sourcetable"'), body.find('class="site-menu"')) if i > 0] or [len(body)])
        cut = body.rfind("<", 0, cut) if cut < len(body) else cut  # cut before the tag, not inside it
        src_m = re.search(r'(?is)class="sourcecell">(.*?)</td>', body)
        source = strip(src_m.group(1)).replace("Source:", "").strip() if src_m else ""
        text = strip(body[:cut].split("</div>", 1)[-1] if "</div>" in body[:cut].lower() else body[:cut])
        text = re.sub(r"(?i)^\s*" + re.escape(title) + r"\s*", "", text).strip() if title else text
        text = re.sub(r"^(?:\s*(?:Art|Article|Section|Part|Chapter|Note)\.? ?\d+[ \t]*\n)+", "", text).strip()  # in-page link lists
        if len(text) < 200:
            continue
        pub = meta.get("DC.Publisher", "") + " " + source
        pub_year = year_of(meta.get("DC.Publisher", ""), source)
        licensed = bool(re.search(r"used with (the )?permission|copyright \d{4} (?!the avalon)|reprinted by permission", source, re.I))
        modern = pub_year is not None and pub_year > 1930 and not GOV.search(pub)
        if licensed or modern:
            set_aside.append((title, source[:120]))
            continue
        coll = rel.split("/", 1)[0].replace("_", " ").replace("century", "century").strip()
        coll = {"ancient": "Ancient documents", "medieval": "Medieval documents"}.get(coll, coll[:1].upper() + coll[1:])
        yield ({"source": "avalon", "collection": f"Avalon Project: {coll}", "title": title,
                "author": "; ".join(sorted(set(re.findall(r'DC\.Creator\.PersonalName" CONTENT="([^"]+)"', s)))) or None,
                # the title's year, else a date line at the very top of the document (a dateline,
                # not a year mentioned in passing, like a birth year in a memoir's first paragraph)
                "date": None, "year": year_of(title) or year_of(text[:80]), "url": url,
                "citation": f"The Avalon Project, Yale Law School. Source: {source}" if source else "The Avalon Project, Yale Law School",
                "rights": "public domain / government document"}, text)
    (SEED / "avalon_set_aside.json").write_text(json.dumps(set_aside, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  avalon: {len(set_aside)} licensed or modern-press documents set aside")


def miller():
    for f in sorted(glob.glob(str(SEED / "miller" / "x" / "speeches" / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        text = strip(d.get("transcript_html") or "") or (d.get("transcript") or "").strip()
        if len(text) < 200:
            continue
        yield ({"source": "miller-center", "collection": "presidential speeches",
                "title": d.get("title"), "author": d.get("president"),
                "date": (d.get("date") or "")[:10], "year": year_of(d.get("date") or ""), "url": d.get("url"),
                "citation": f"{d.get('president')}, \"{d.get('title')}\". Transcript: Miller Center, University of Virginia.",
                "rights": "public domain (speech text)"}, text)


def milestones():
    """The National Archives' Milestone Documents (96 on its current list): NARA's background essay plus the full
    transcript, both U.S. government works (public domain)."""
    for f in sorted((SEED / "nara" / "milestones").glob("*.html")):
        if f.stem in ("list", "constitution"):  # the Constitution comes in whole from the transcript pages
            continue
        s = f.read_text(encoding="utf-8")
        title = re.sub(r"\s*\|\s*National Archives\s*$", "", _html.unescape(re.search(r"(?s)<title>(.*?)</title>", s).group(1)).strip())
        s = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", s)
        lines = [ln.strip() for ln in _html.unescape(re.sub(r"(?s)<[^>]+>", "\n", s)).replace("\xa0", " ").split("\n") if ln.strip()]
        start = lines.index("View Transcript") + 1 if "View Transcript" in lines else None
        tr = lines.index("Transcript") if "Transcript" in lines else None
        catalog = next((k for k, ln in enumerate(lines) if re.fullmatch(r"View in (?:the )?National Archives Catalog", ln)), None)
        if start is None and tr is None and catalog is not None:
            # an image with no transcript (the Cuba photograph, the cotton gin patent): the essay sits
            # between the catalog link and "Teach with this document."
            start = catalog + 1
            tr = next((k for k in range(start, len(lines)) if lines[k].startswith("Teach with this document")), None)
        end = next((k for k in range(tr or 0, len(lines)) if lines[k].startswith("Contact us with questions")), len(lines))
        cite = next((ln for ln in lines if ln.startswith("Citation:")), "")
        background = " ".join(lines[start:tr]) if start and tr else ""
        transcript = "\n".join(lines[tr + 1:end]) if tr and lines[tr] == "Transcript" else ""
        if not transcript and len(background) < 200:
            continue
        text = (f"Background (National Archives): {background}\n\n" if background else "") + (f"Transcript:\n{transcript}" if transcript else "")
        yield ({"source": "nara", "collection": "National Archives Milestone Documents", "title": title,
                "author": None, "date": None, "year": year_of(title), "url": f"https://www.archives.gov/milestone-documents/{f.stem}",
                "citation": f"National Archives, Milestone Documents. {cite.replace('Citation:', '').strip()}".strip(),
                "rights": "U.S. government work (public domain)"}, text)


SUPPLEMENTS = [  # (Wikisource page file, title, author, date, collection)
    ("Cornerstone_Speech", "The Cornerstone Speech", "Alexander H. Stephens", "1861-03-21", "Speeches"),
    ("A_Model_of_Christian_Charity", "A Model of Christian Charity (\"A City upon a Hill\")", "John Winthrop", "1630", "Sermons"),
    ("The_American_Constitution_and_the_Slave", "The American Constitution and the Slave (Glasgow address)", "Frederick Douglass", "1860-03-26", "Speeches"),
    ("Petition_of_Right", "The Petition of Right", "Parliament of England", "1628", "Founding influences"),
]
GUTENBERG_SUPPLEMENTS = [  # (file, title, author, date, collection)
    ("locke-7370.txt", "Second Treatise of Government", "John Locke", "1690", "Founding influences"),
]


def supplements():
    """Public-domain texts the persona names that Avalon lacks: three from Wikisource (texts public
    domain; Wikisource's own contributions CC BY-SA 4.0, credited) and Worcester v. Georgia from the
    Harvard Caselaw Access Project (released without restriction)."""
    from lxml import html as LH
    base = SEED / "supplements"
    for stem, title, author, date, coll in SUPPLEMENTS:
        p = base / f"{stem}.json"
        if not p.exists():
            continue
        page = json.loads(p.read_text(encoding="utf-8"))["parse"]
        root = LH.fromstring(page["text"]["*"])
        for el in root.xpath('//*[contains(@class,"ws-noexport") or contains(@class,"wst-header") or contains(@class,"licenseContainer")'
                             ' or contains(@class,"wst-license") or contains(@class,"references") or contains(@class,"reference")'
                             ' or contains(@class,"mw-editsection") or self::style or self::script]'):
            el.getparent().remove(el)
        text = strip(LH.tostring(root, encoding="unicode"))
        text = re.split(r"This work was published before January 1, 1931", text)[0].strip()
        text = re.sub(r"\n+References\s*$", "", text).strip()
        yield ({"source": "wikisource", "collection": coll, "title": title, "author": author, "date": date,
                "year": year_of(date), "url": "https://en.wikisource.org/wiki/" + page["title"].replace(" ", "_"),
                "citation": f"{author}, {title} ({date}). Text: Wikisource (CC BY-SA 4.0).", "rights": "public domain text"}, text)
    for fname, title, author, date, coll in GUTENBERG_SUPPLEMENTS:
        p = base / fname
        if not p.exists():
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        start = re.search(r"\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\n", raw)
        end = re.search(r"\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", raw)
        body = raw[start.end() if start else 0: end.start() if end else len(raw)].strip()
        body = re.sub(r"\r\n?", "\n", body)
        ch1 = re.search(r"(?m)^CHAPTER\.? I\.", body)  # skip the digitizer's note and contents ahead of Chapter I
        body = body[ch1.start():] if ch1 else body
        body = re.sub(r"(?<!\n)\n(?!\n)", " ", body)  # unwrap hard-wrapped lines, keep paragraph breaks
        yield ({"source": "gutenberg", "collection": coll, "title": title, "author": author, "date": date,
                "year": year_of(date), "url": None, "citation": f"{author}, {title} ({date}).",
                "rights": "public domain"}, body)
    zp = base / "worcester.zip"
    if zp.exists():
        import zipfile
        d = json.loads(zipfile.ZipFile(zp).read("json/0515-01.json"))
        label = {"majority": "Opinion of the Court", "concurrence": "Concurring opinion", "dissent": "Dissenting opinion"}
        parts = [f"{label.get(o['type'], o['type'].title())} ({(o.get('author') or '').strip(' .')})\n{o['text'].strip()}"
                 for o in d["casebody"]["opinions"]]
        yield ({"source": "cap", "collection": "Supreme Court of the United States", "title": "Worcester v. Georgia",
                "author": "Supreme Court of the United States", "date": d.get("decision_date"), "year": 1832,
                "url": "https://static.case.law/us/31/", "citation": "Worcester v. Georgia, 31 U.S. (6 Pet.) 515 (1832). Text: Caselaw Access Project, Harvard Law School.",
                "rights": "public domain (court opinion)"}, "\n\n".join(parts))


DOCSOUTH = {"na-slave-narratives": "North American Slave Narratives",
            "first-person-narratives-american-south": "First-Person Narratives of the American South",
            "church-southern-black-community": "The Church in the Southern Black Community"}


def docsouth():
    for key, coll in DOCSOUTH.items():
        base = SEED / "docsouth" / key / key / "data"
        toc = {}
        with open(base / "toc.csv", encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                toc[Path(row["Filename"]).stem] = row
        for f in sorted((base / "texts").glob("*.txt")):
            row = toc.get(f.stem, {})
            text = f.read_text(encoding="utf-8", errors="replace").strip()
            if len(text) < 200:
                continue
            yield ({"source": "docsouth", "collection": coll, "title": (row.get("Title") or f.stem).strip(),
                    "author": re.sub(r"\s+", " ", row.get("Author") or "").strip() or None,
                    "date": (row.get("Date") or "").strip() or None, "year": year_of(row.get("Date") or ""),
                    "url": row.get("URL") or None,
                    "citation": f"Documenting the American South, University of North Carolina at Chapel Hill ({coll}).",
                    "rights": "DocSouth Data: available for use without restriction (credit UNC)"}, text)


# ------------------------------------------------- Constitution Test texts
def il_constitution():
    """-> (document text, [section rows]) for the Illinois Constitution."""
    parts, rows, sort = [], [], 0
    order = ["p"] + [str(i) for i in range(1, 15)] + ["trans"]  # contrans.htm is the Transition Schedule
    for k in order:
        p = SEED / "ilga" / f"con{k}.htm"
        if not p.exists():
            continue
        raw = p.read_text(encoding="latin-1")
        if "HTTP Error 404" in raw:  # ilga.gov served an error page for this part (cons.htm, the Transition Schedule)
            continue
        t = strip(raw)
        t = re.sub(r"^.*?Constitution of the State of Illinois\s*", "", t, flags=re.S).strip()
        # the site's navigation links ("to preceding Article", "to main Constitution page")
        t = re.sub(r"(?m)^\s*to (?:preceding|next|following) Article\s*$|^\s*to (?:Transition Schedule|main Constitution page)\s*$", "", t)
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        parts.append(t)
        if k == "p":
            sort += 1
            rows.append(("il-constitution", "preamble", "", "", "Preamble", t.replace("PREAMBLE", "").strip(), sort))
            continue
        art_m = re.match(r"(ARTICLE\s+([IVXL]+)|TRANSITION SCHEDULE)\s*\n?(.*?)\n", t)
        art_no = str(roman(art_m.group(2))) if art_m and art_m.group(2) else ("schedule" if k == "trans" else k)
        art_title = "" if k == "trans" else (art_m.group(3).strip().title() if art_m else "")
        for m in re.finditer(r"(?:SECTION|Paragraph)\s+(\d+[a-z]?)\.\s*([^\n]*)\n(.*?)(?=\n\s*(?:SECTION|Paragraph)\s+\d+[a-z]?\.|\Z)", t, re.S):
            sort += 1
            body = re.sub(r"\(Source: [^)]*\)\s*$", "", m.group(3).strip()).strip()
            body = re.sub(r"\s*\n\s*", " ", body)
            rows.append(("il-constitution", "article", art_no, m.group(1),
                         (f"Transition Schedule, Section {m.group(1)}: {m.group(2).strip().title()}" if k == "trans" else
                          f"Article {art_no}{' (' + art_title + ')' if art_title else ''}, Section {m.group(1)}: {m.group(2).strip().title()}"),
                         body, sort))
    return "\n\n".join(parts), rows


def amendment_documents(const_rows: list[tuple], titles: list[str]) -> list[tuple[dict, str]]:
    """One searchable document per amendment that has no Milestone page of its own (the Bill of Rights
    and the 13th-17th and 19th do), named like the Milestones and dated by ratification, so a search
    limited to 1900-1930 finds Prohibition and each amendment gets its own passage and title."""
    covered = set(range(1, 11)) | {int(m.group(1)) for t in titles
                                   if (m := re.match(r"(\d+)(?:st|nd|rd|th) Amendment to the U\.S\. Constitution", t))}
    out = []
    for r in const_rows:
        if r[1] != "amendment" or int(r[2]) in covered:
            continue
        n = int(r[2])
        topic = r[4].split(":", 1)[1].strip() if ":" in r[4] else ""
        rat = re.search(r"Ratified (\w+ \d{1,2}, (\d{4}))", r[5])
        year = int(rat.group(2)) if rat else None
        suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        title = f"{n}{suffix} Amendment to the U.S. Constitution" + (f": {topic}" if topic else "") + (f" ({year})" if year else "")
        out.append(({"source": "nara", "collection": "Founding documents", "title": title, "author": None,
                     "date": rat.group(1) if rat else None, "year": year,
                     "url": "https://www.archives.gov/founding-docs/amendments-11-27",
                     "citation": f"The Constitution: Amendments 11-27, Amendment {n}. National Archives.", "rights": "public domain"},
                    f"{r[4]}\n{r[5]}"))
    return out


def flag_code():
    s = (SEED / "uscode" / "t4ch1-2024.htm").read_text(encoding="utf-8", errors="replace")
    rows, parts = [], []
    heads = list(re.finditer(r'<h3 class="section-head">(.*?)</h3>', s, re.S))
    for i, h in enumerate(heads):
        seg = s[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(s)]
        seg = seg.split('class="source-credit"', 1)[0]
        body = "\n".join(strip(b) for b in re.findall(r'<p class="statutory-body[^"]*">(.*?)</p>', seg, re.S))
        head = strip(h.group(1))
        m = re.match(r"§\s*(\d+)\.\s*(.*)", head)
        num, title = (m.group(1), m.group(2)) if m else (str(i + 1), head)
        rows.append(("flag-code", "section", num, "", f"4 U.S.C. § {num}: {title}", body, i + 1))
        parts.append(f"§ {num}. {title}\n{body}")
    return "\n\n".join(parts), rows


def avalon_lines(rel: str) -> list[str]:
    """The text lines of one Avalon page's document body (title and navigation removed)."""
    p = SEED / "avalon" / rel
    if not p.exists():
        return []
    s = p.read_text(encoding="latin-1")
    body = s[s.find('class="document-title"'):]
    body = body[body.find(">") + 1:]
    body = re.sub(r'(?is)<table[^>]*class="page-menu".*?</table>', " ", body)
    cut = min([i for i in (body.find('class="site-menu"'), body.find('class="sourcetable"')) if i > 0] or [len(body)])
    cut = body.rfind("<", 0, cut) if cut < len(body) else cut
    t = _html.unescape(re.sub(r"(?s)<[^>]+>", "\n", body[:cut])).replace("\xa0", " ")
    return [ln.strip() for ln in t.split("\n") if ln.strip()]


def nara_lines(name: str) -> list[str]:
    """Visible text lines of a National Archives founding-documents transcript page."""
    p = SEED / "nara" / f"{name}.html"
    if not p.exists():
        return []
    s = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", p.read_text(encoding="utf-8"))
    t = _html.unescape(re.sub(r"(?s)<[^>]+>", "\n", s)).replace("\xa0", " ")
    return [ln.strip() for ln in t.split("\n") if ln.strip()]


ORDINAL = {"third": 1, "fourth": 2, "fifth": 3, "sixth": 4, "seventh": 5, "eighth": 6,
           "ninth": 7, "tenth": 8, "eleventh": 9, "twelfth": 10}


def amendment_topics() -> dict[int, str]:
    """Short topic labels for the amendments (Avalon's table of contents), e.g. 14 -> 'Citizen rights not to be abridged'."""
    out = {}
    for rel in ("18th_century/rights1.asp", "18th_century/amend1.asp"):
        for ln in avalon_lines(rel):
            m = re.fullmatch(r"([IVXL]+) - (.+)", ln)
            if m:
                out.setdefault(roman(m.group(1)), m.group(2).strip())
    return out


def us_constitution():
    """The U.S. Constitution and all 27 amendments from the National Archives transcripts (official,
    public domain): preamble, Articles I-VII by section, each amendment with its dates and NARA notes."""
    rows = []
    lines = nara_lines("constitution-transcript")
    if lines:
        i = lines.index("We the People")
        body = lines[i:]
        stop = next((k for k, ln in enumerate(body) if ln.startswith("done in Convention")), len(body))
        text = "\n".join(body[:stop + 1])
        pre, rest = text.split("Article. I.", 1)
        rows.append(("us-constitution", "preamble", "", "", "Preamble", re.sub(r"\s*\n\s*", " ", pre).strip(), 0))
        rest = "Article. I." + rest
        for am in re.finditer(r"(?s)Article\. ([IVX]+)\.\n(.*?)(?=\nArticle\. [IVX]+\.\n|\Z)", rest):
            n, abody = roman(am.group(1)), am.group(2)
            secs = list(re.finditer(r"(?s)Section\. (\d+)\.\n(.*?)(?=\nSection\. \d+\.\n|\Z)", abody))
            if secs:
                for sm in secs:
                    rows.append(("us-constitution", "article", str(n), sm.group(1), f"Article {n}, Section {sm.group(1)}",
                                 sm.group(2).strip(), n * 100 + int(sm.group(1))))
            else:
                rows.append(("us-constitution", "article", str(n), "", f"Article {n}", abody.strip(), n * 100))
    topics = amendment_topics()
    bor = nara_lines("bill-of-rights-transcript")
    text = "\n".join(bor)
    for m in re.finditer(r"(?s)Article the (\w+)\.\.\.\n(.*?)(?=\nArticle the \w+\.\.\.|\n(?:Attest|ATTEST|Frederick Augustus)|\Z)", text):
        num = ORDINAL.get(m.group(1).lower())
        if num:
            head = f"Amendment {num}" + (f": {topics[num]}" if num in topics else "")
            rows.append(("us-constitution", "amendment", str(num), "", head,
                         "Proposed by Congress September 25, 1789. Ratified December 15, 1791.\n" + m.group(2).strip(), 1000 + num))
    am = nara_lines("amendments-11-27")
    text = "\n".join(am)
    text = text[text.find("AMENDMENT XI\n"):text.find("Back to Constitution Main Page")]
    for m in re.finditer(r"(?s)AMENDMENT ([XVI]+)\n(.*?)(?=\nAMENDMENT [XVI]+\n|\Z)", text):
        num = roman(m.group(1))
        body = re.sub(r"Note:\n", "Note: ", m.group(2).strip())
        head = f"Amendment {num}" + (f": {topics[num]}" if num in topics else "")
        rows.append(("us-constitution", "amendment", str(num), "", head, body, 1000 + num))
    return rows


def nara_text(name: str, first: str, last_prefix: str) -> str:
    lines = nara_lines(name)
    try:
        i = next(k for k, ln in enumerate(lines) if ln.startswith(first))
    except StopIteration:
        return ""
    j = next((k for k, ln in enumerate(lines[i:], i) if ln.startswith(last_prefix)), len(lines) - 1)
    return "\n".join(lines[i:j + 1])


# ------------------------------------------------------- Reading Room books
def reading_room():
    con = sqlite3.connect(f"file:{BOOKS.as_posix()}?mode=ro", uri=True)
    where = " or ".join(f"section like '%{s}%'" for s in BOOK_SECTIONS)
    books = con.execute(f"select id, slug, title, author from books where ({where}) and coalesce(language,'en')='en'").fetchall()
    for bid, slug, title, author in books:
        chapters = con.execute("select html from book_chapters where book_id=? order by section_number", (bid,)).fetchall()
        text = "\n\n".join(strip(h or "") for (h,) in chapters)
        if len(text) < 500:
            continue
        yield ({"source": "reading-room", "collection": "Reading Room", "title": title, "author": author,
                "date": None, "year": None, "url": f"/read/{slug}",
                "citation": f"{author}, {title} (Exegetica Reading Room)", "rights": "public domain"}, text)
    con.close()


# ---------------------------------------------------------------- build
def chunks(text: str):
    buf, n = [], 0
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        while len(para) > CHUNK * 2:  # a run-on paragraph (OCR, transcripts): split on sentences
            cut = para.rfind(". ", 0, CHUNK) + 1 or CHUNK
            if buf:
                yield "\n".join(buf)
                buf, n = [], 0
            yield para[:cut].strip()
            para = para[cut:].strip()
        buf.append(para)
        n += len(para)
        if n >= CHUNK:
            yield "\n".join(buf)
            buf, n = [], 0
    if buf:
        yield "\n".join(buf)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-books", action="store_true")
    ap.add_argument("--no-vectors", action="store_true")
    a = ap.parse_args()
    tmp = DB.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript("""
        pragma journal_mode=off; pragma synchronous=off;
        create table documents (id integer primary key, source text, collection text, title text, author text,
                                date text, year integer, url text, citation text, rights text, text text, words integer);
        create table sections (id integer primary key, code text, part text, number text, sub text,
                               heading text, text text, sort integer);
        create table passages (id integer primary key, doc_id integer, seq integer, title text, text text);
        create table meta (key text primary key, value text);
    """)
    docs: list[tuple[dict, str]] = []
    for name, gen in (("avalon", avalon), ("milestones", milestones), ("supplements", supplements), ("miller", miller), ("docsouth", docsouth)):
        n0 = len(docs)
        docs.extend(gen())
        print(f"  {name}: {len(docs) - n0:,} documents", flush=True)
    il_text, il_rows = il_constitution()
    fc_text, fc_rows = flag_code()
    docs.append(({"source": "ilga", "collection": "Illinois Constitution", "title": "Constitution of the State of Illinois (1970)",
                  "author": None, "date": "1970-12-15", "year": 1970, "url": "https://www.ilga.gov/commission/lrb/conmain.htm",
                  "citation": "Constitution of the State of Illinois (1970), Illinois General Assembly.", "rights": "public domain"}, il_text))
    docs.append(({"source": "govinfo", "collection": "U.S. Code", "title": "The United States Flag Code (4 U.S.C. §§ 1-10)",
                  "author": None, "date": "2024", "year": 2024, "url": "https://www.govinfo.gov/content/pkg/USCODE-2024-title4/html/USCODE-2024-title4-chap1.htm",
                  "citation": "4 U.S.C. ch. 1, U.S. Code (2024 ed.), govinfo.gov.", "rights": "U.S. government work"}, fc_text))
    const_text = nara_text("constitution-transcript", "We the People", "done in Convention")
    if const_text:
        docs.append(({"source": "nara", "collection": "Founding documents", "title": "The Constitution of the United States",
                      "author": None, "date": "1787-09-17", "year": 1787, "url": "https://www.archives.gov/founding-docs/constitution-transcript",
                      "citation": "The Constitution of the United States: A Transcription, National Archives.", "rights": "public domain"}, const_text))
    const_rows = us_constitution()
    docs.extend(amendment_documents(const_rows, [m["title"] for m, _ in docs]))
    decl_text = nara_text("declaration-transcript", "In Congress, July 4, 1776", "Matthew Thornton")
    if decl_text:
        docs.append(({"source": "nara", "collection": "Founding documents", "title": "The Declaration of Independence",
                      "author": "Thomas Jefferson et al.", "date": "1776-07-04", "year": 1776, "url": "https://www.archives.gov/founding-docs/declaration-transcript",
                      "citation": "Declaration of Independence: A Transcription, National Archives.", "rights": "public domain"}, decl_text))
    rows = const_rows + il_rows + fc_rows
    con.executemany("insert into sections (code, part, number, sub, heading, text, sort) values (?,?,?,?,?,?,?)", rows)
    print(f"  sections: {sum(r[0]=='us-constitution' for r in rows)} U.S. Constitution, "
          f"{sum(r[0]=='il-constitution' for r in rows)} Illinois, {sum(r[0]=='flag-code' for r in rows)} Flag Code", flush=True)

    def add(meta: dict, text: str, keep_text: bool) -> None:
        cur = con.execute("insert into documents (source, collection, title, author, date, year, url, citation, rights, text, words) "
                          "values (?,?,?,?,?,?,?,?,?,?,?)",
                          (meta["source"], meta["collection"], meta["title"], meta["author"], meta["date"], meta["year"],
                           meta["url"], meta["citation"], meta["rights"], text if keep_text else None, len(text.split())))
        con.executemany("insert into passages (doc_id, seq, title, text) values (?,?,?,?)",
                        [(cur.lastrowid, i, meta["title"], c) for i, c in enumerate(chunks(text))])

    for meta, text in docs:
        add(meta, text, True)
    if not a.no_books and BOOKS.exists():
        n = 0
        for meta, text in reading_room():
            add(meta, text, False)  # the book itself lives in books.db; keep only its passages here
            n += 1
            if n % 100 == 0:
                print(f"  reading room: {n} books", flush=True)
        print(f"  reading room: {n:,} books", flush=True)
    con.commit()
    print("indexing full text…", flush=True)
    con.executescript("""
        create virtual table passages_fts using fts5(title, text, content='passages', content_rowid='id',
                                                     tokenize='porter unicode61');
        insert into passages_fts(passages_fts) values ('rebuild');
        create index idx_passages_doc on passages(doc_id, seq);
        create index idx_sections on sections(code, part, number, sub);
        create index idx_documents_title on documents(title);
    """)
    if not a.no_vectors:
        import numpy as np
        import sqlite_vec
        from model2vec import StaticModel
        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
        model = StaticModel.from_pretrained(MODEL)
        total = con.execute("select count(*) from passages").fetchone()[0]
        print(f"embedding {total:,} passages…", flush=True)
        dim, last_id, start = None, 0, 0
        while True:  # stream in batches: holding every passage in memory at once ran the build out of RAM
            batch = con.execute("select id, title || char(10) || text from passages where id > ? order by id limit 20000",
                                (last_id,)).fetchall()
            if not batch:
                break
            last_id = batch[-1][0]
            v = model.encode([t for _, t in batch]).astype(np.float32)
            v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
            q = np.clip(np.round(v * 127.0), -127, 127).astype(np.int8)
            if dim is None:
                dim = q.shape[1]
                con.execute(f"create virtual table passages_vec using vec0(id integer primary key, emb int8[{dim}])")
            con.executemany("insert into passages_vec(id, emb) values (?, vec_int8(?))",
                            [(i, q[k].tobytes()) for k, (i, _) in enumerate(batch)])
            start += len(batch)
            if start % 100000 < len(batch):
                print(f"  {start:,} embedded", flush=True)
        con.execute("insert into meta values ('vec_model', ?), ('vec_dim', ?)", (MODEL, str(dim)))
    stats = dict(con.execute("select source, count(*) from documents group by source").fetchall())
    con.execute("insert into meta values ('stats', ?)", (json.dumps(stats),))
    con.commit()
    con.execute("vacuum")
    con.close()
    DB.unlink(missing_ok=True)
    tmp.rename(DB)
    print(f"built {DB} ({DB.stat().st_size / 1e6:,.0f} MB): {stats}")


if __name__ == "__main__":
    main()
