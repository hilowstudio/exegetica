"""Phase 2 (Government and Street Law): add law tables to db/social_sciences.db, in place.

Run after build_social_sciences_db.py (which recreates the file). This script drops and recreates
only its own tables, so it can be re-run on its own.

  cases, case_opinions        every Supreme Court opinion in U.S. Reports vols 1-572 (Harvard Caselaw
                              Access Project), joined to the Supreme Court Database's coding by its
                              SCDB id: issue area, vote, majority author, majority and dissent lists,
                              laws struck down, precedents overruled; plus CAP's citation-importance score
  case_passages(+_fts)        opinion text in chunks, keyword search
  case_vec                    one summary vector per case (name + head matter + opening), meaning search
  statutes(+_fts)             the U.S. Code (USLM XML) and Illinois Compiled Statutes, one row per section
  conan(+_fts, conan_vec)     Constitution Annotated (2022) essays, keyed to their clause
  legislators, legislator_terms, executives   every member of Congress since 1789, presidents and VPs
  glossary(+_fts)             Black's Law Dictionary (1910) and Webster's American Dictionary (1828)

    .venv/Scripts/python.exe scripts/socialsci/build_phase2.py [cases statutes conan legislators glossary]
"""
from __future__ import annotations

import csv
import glob
import html as _html
import io
import json
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / ".seed_cache" / "socialsci"
DB = ROOT / "db" / "social_sciences.db"
MODEL = "minishlab/potion-retrieval-32M"
CHUNK = 1500

ISSUE_AREA = {"1": "Criminal Procedure", "2": "Civil Rights", "3": "First Amendment", "4": "Due Process",
              "5": "Privacy", "6": "Attorneys", "7": "Unions", "8": "Economic Activity", "9": "Judicial Power",
              "10": "Federalism", "11": "Interstate Relations", "12": "Federal Taxation",
              "13": "Miscellaneous", "14": "Private Action"}
STRUCK = {"2": "a federal law", "3": "a state or territorial law", "4": "a municipal or local ordinance"}


def strip(h: str) -> str:
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</h[1-6]>|</div>|</tr>|</li>", "\n", h)
    t = _html.unescape(re.sub(r"(?s)<[^>]+>", " ", h)).replace("\xa0", " ").replace("\xad", "")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n\s*", "\n\n", t).strip()


def chunks(text: str):
    buf, n = [], 0
    for para in re.split(r"\n\s*\n|\n(?=[A-Z])", text):
        para = para.strip()
        if not para:
            continue
        while len(para) > CHUNK * 2:
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


def embedder():
    import numpy as np
    from model2vec import StaticModel
    model = StaticModel.from_pretrained(MODEL)

    def enc(texts):
        v = model.encode(texts).astype(np.float32)
        v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        return np.clip(np.round(v * 127.0), -127, 127).astype(np.int8)
    return enc


def load_vec(con):
    import sqlite_vec
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)


# ------------------------------------------------------------------ cases
def scdb_rows(pattern: str) -> dict[str, dict]:
    out = {}
    for zp in glob.glob(str(SEED / "scdb" / pattern)):
        z = zipfile.ZipFile(zp)
        for name in z.namelist():
            if name.endswith(".csv"):
                for row in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="latin-1")):
                    out.setdefault(row["caseId"], row)
    return out


def scdb_votes() -> tuple[dict[str, tuple[list, list]], dict[str, str]]:
    """caseId -> (majority justices, dissenting justices); justice number -> name."""
    votes: dict[str, tuple[list, list]] = {}
    names: dict[str, str] = {}
    for zp in [*glob.glob(str(SEED / "scdb" / "justice_modern.zip")), *glob.glob(str(SEED / "scdb" / "*Legacy*justiceCentered*"))]:
        z = zipfile.ZipFile(zp)
        for name in z.namelist():
            if not name.endswith(".csv"):
                continue
            seen = set()
            for row in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="latin-1")):
                names[row["justice"]] = row["justiceName"]
                key = (row["caseId"], row["justiceName"])
                if key in seen:  # one row per justice per case (cases with several issues repeat)
                    continue
                seen.add(key)
                maj, dis = votes.setdefault(row["caseId"], ([], []))
                (maj if row.get("majority") == "2" else dis if row.get("majority") == "1" else []).append(row["justiceName"])
    return votes, names


def cases(con) -> None:
    con.executescript("""
        drop table if exists cases; drop table if exists case_opinions; drop table if exists case_passages;
        drop table if exists case_passages_fts; drop table if exists case_vec;
        create table cases (id integer primary key, name text, short_name text, cite text, scdb_id text, date text,
            year integer, term text, chief text, issue_area text, vote text, maj_writer text, majority text,
            dissent text, struck_down text, overruled_precedent integer, importance real, head text, words integer);
        create table case_opinions (case_id integer, seq integer, type text, author text, text text);
        create table case_passages (id integer primary key, case_id integer, seq integer, text text);
    """)
    meta = scdb_rows("case_modern.zip") | scdb_rows("*Legacy*caseCentered*")
    votes, jnames = scdb_votes()
    print(f"  SCDB: {len(meta):,} cases coded", flush=True)
    n = 0
    for zp in sorted(glob.glob(str(SEED / "cap" / "us" / "*.zip")), key=lambda p: int(Path(p).stem)):
        z = zipfile.ZipFile(zp)
        for name in z.namelist():
            if not name.startswith("json/"):
                continue
            d = json.loads(z.read(name))
            ops = [o for o in d["casebody"].get("opinions") or [] if len((o.get("text") or "").strip()) > 300]
            if not ops:
                continue  # memorandum orders and denials carry no opinion
            cites = {c["type"]: c["cite"] for c in d.get("citations", [])}
            scdb_id = next((c["cite"].replace("SCDB ", "") for c in d.get("citations", []) if c["cite"].startswith("SCDB ")), None)
            m = meta.get(scdb_id or "", {})
            maj, dis = votes.get(scdb_id or "", ([], []))
            vote = f"{m.get('majVotes')}-{m.get('minVotes')}" if m.get("majVotes") else None
            date = d.get("decision_date") or ""
            head = (d["casebody"].get("head_matter") or "").strip()
            words = sum(len(o["text"].split()) for o in ops)
            cur = con.execute(
                "insert into cases (name, short_name, cite, scdb_id, date, year, term, chief, issue_area, vote, maj_writer, "
                "majority, dissent, struck_down, overruled_precedent, importance, head, words) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d.get("name"), d.get("name_abbreviation"), cites.get("official"), scdb_id, date, int(date[:4]) if date[:4].isdigit() else None,
                 m.get("term"), m.get("chief"), ISSUE_AREA.get(m.get("issueArea", "")), vote,
                 jnames.get(m.get("majOpinWriter", ""), None), ", ".join(maj) or None, ", ".join(dis) or None,
                 STRUCK.get(m.get("declarationUncon", "")), 1 if m.get("precedentAlteration") == "1" else 0,
                 ((d.get("analysis") or {}).get("pagerank") or {}).get("percentile"), head[:4000], words))
            cid = cur.lastrowid
            seq = 0
            for k, o in enumerate(ops):
                con.execute("insert into case_opinions values (?,?,?,?,?)", (cid, k, o.get("type"), (o.get("author") or "").strip(" .,:"), o["text"]))
                label = {"majority": "Opinion of the Court", "concurrence": "Concurrence", "dissent": "Dissent"}.get(o.get("type"), o.get("type"))
                for c in chunks(f"[{label}{', ' + o['author'].strip(' .,:') if o.get('author') else ''}]\n{o['text']}"):
                    con.execute("insert into case_passages (case_id, seq, text) values (?,?,?)", (cid, seq, c))
                    seq += 1
            n += 1
        if int(Path(zp).stem) % 50 == 0:
            print(f"  cases: vol {Path(zp).stem}, {n:,} opinions", flush=True)
            con.commit()
    con.commit()
    print(f"  cases: {n:,} with opinions; {con.execute('select count(*) from cases where scdb_id is not null and issue_area is not null').fetchone()[0]:,} joined to SCDB coding", flush=True)
    con.executescript("""
        create virtual table case_passages_fts using fts5(text, content='case_passages', content_rowid='id', tokenize='porter unicode61');
        insert into case_passages_fts(case_passages_fts) values ('rebuild');
        create index idx_case_pass on case_passages(case_id, seq);
        create index idx_case_op on case_opinions(case_id, seq);
        create index idx_cases_cite on cases(cite);
        create index idx_cases_name on cases(short_name);
    """)
    enc = embedder()
    rows = con.execute("select c.id, c.short_name || char(10) || coalesce(substr(c.head, 1, 600), '') || char(10) || "
                       "substr(o.text, 1, 1200) from cases c join case_opinions o on o.case_id = c.id and o.seq = 0").fetchall()
    q = enc([t for _, t in rows])
    con.execute(f"create virtual table case_vec using vec0(id integer primary key, emb int8[{q.shape[1]}])")
    con.executemany("insert into case_vec(id, emb) values (?, vec_int8(?))", [(i, q[k].tobytes()) for k, (i, _) in enumerate(rows)])
    con.commit()
    print(f"  cases: {len(rows):,} summary vectors", flush=True)


# --------------------------------------------------------------- statutes
def uslm_text(el) -> str:
    """Text of a USLM section: its subsections, paragraphs and clauses, one per line, with the editorial
    notes, source credits, and the section's own number and heading left out."""
    import copy
    from lxml import etree
    s = copy.deepcopy(el)
    for bad in s.xpath('.//*[local-name()="notes" or local-name()="note" or local-name()="sourceCredit"]'
                       ' | ./*[local-name()="num" or local-name()="heading"]'):
        bad.getparent().remove(bad)
    for blk in s.xpath('.//*[local-name()="subsection" or local-name()="paragraph" or local-name()="subparagraph"'
                       ' or local-name()="clause" or local-name()="subclause" or local-name()="item"'
                       ' or local-name()="chapeau" or local-name()="continuation" or local-name()="p"]'):
        blk.tail = "\n" + (blk.tail or "")
        if len(blk) == 0 or blk.text:
            blk.text = "\n" + (blk.text or "") if blk.text else blk.text
    t = etree.tostring(s, method="text", encoding="unicode")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\s*\n\s*", "\n", t).strip()


def statutes(con) -> None:
    from lxml import etree
    con.executescript("""
        drop table if exists statutes; drop table if exists statutes_fts;
        create table statutes (id integer primary key, code text, title text, section text, heading text,
                               citation text, text text);
    """)
    zp = next(iter(glob.glob(str(SEED / "uscode" / "xml_uscAll@*.zip"))), None)
    n = 0
    if zp:
        z = zipfile.ZipFile(zp)
        for name in sorted(z.namelist()):
            if not name.endswith(".xml"):
                continue
            root = etree.fromstring(z.read(name))
            title_no = re.sub(r"^usc0*", "", Path(name).stem)
            for sec in root.iter("{*}section"):
                ident = sec.get("identifier") or ""
                if not ident.startswith("/us/usc/") or sec.get("status") in ("repealed", "transferred", "omitted"):
                    continue
                num_el, head_el = sec.find("{*}num"), sec.find("{*}heading")
                num = (num_el.get("value") if num_el is not None else None) or ident.rsplit("/s", 1)[-1]
                heading = "".join(head_el.itertext()).strip() if head_el is not None else ""
                body = uslm_text(sec)
                if len(body) < 20:
                    continue
                con.execute("insert into statutes (code, title, section, heading, citation, text) values (?,?,?,?,?,?)",
                            ("usc", title_no, num, heading, f"{title_no} U.S.C. § {num}", body))
                n += 1
        print(f"  U.S. Code: {n:,} sections", flush=True)
    m = 0
    for f in sorted((SEED / "ilcs").rglob("*K*.html")):
        s = f.read_text(encoding="latin-1", errors="replace")
        t = strip(s)
        cm = re.match(r"\s*\(?\s*(\d+)\s+ILCS\s+([\d.]+)/([^\s)]+)\)?", t)
        if not cm:
            continue
        ch, act, sec = cm.group(1), cm.group(2), cm.group(3)
        body = t[cm.end():].strip()
        # the section number can carry its own dots (11-501.2), so match it exactly; older acts have no heading
        hm = re.match(r"\(?[^)\n]*\)?\s*\n?\s*Sec\.\s*" + re.escape(sec) + r"\.\s*(?!\()([^.\n]{0,160}\.)", body)
        heading = hm.group(1).strip() if hm else ""
        body = re.sub(r"\(Source: P\.A\.[^)]*\)\s*$", "", body).strip()
        con.execute("insert into statutes (code, title, section, heading, citation, text) values (?,?,?,?,?,?)",
                    ("ilcs", ch, f"{act}/{sec}", heading, f"{ch} ILCS {act}/{sec}", body))
        m += 1
    print(f"  Illinois statutes: {m:,} sections", flush=True)
    con.executescript("""
        create virtual table statutes_fts using fts5(citation, heading, text, content='statutes', content_rowid='id', tokenize='porter unicode61');
        insert into statutes_fts(statutes_fts) values ('rebuild');
        create index idx_statutes_cite on statutes(code, title, section);
    """)
    con.commit()


# ------------------------------------------------------------------ conan
def conan(con) -> None:
    import pypdf
    con.executescript("""
        drop table if exists conan; drop table if exists conan_fts; drop table if exists conan_vec;
        create table conan (id integer primary key, essay_id text, provision text, title text, text text);
    """)
    r = pypdf.PdfReader(str(SEED / "conan" / "GPO-CONAN-2022.pdf"))
    pages = [(p.extract_text() or "") for p in r.pages]
    full = "\n".join(pages)
    heads = [m for m in re.finditer(r"(?m)^((?:Art|Amdt)[IVX0-9]+\.[A-Za-z0-9.]+)[ \t]+([^\n]{3,140})$", full)
             if "...." not in m.group(2) and not re.search(r"\d{2,4}\s*$", m.group(2))]
    found: dict[str, tuple] = {}
    for k, m in enumerate(heads):
        eid = m.group(1).rstrip(".")
        end = heads[k + 1].start() if k + 1 < len(heads) else len(full)
        body = full[m.end():end].strip()
        body = re.sub(r"\n(?:[^\n]{0,80}—Literal Print|Constitution of the United States of America)\n?\d*\n", "\n", body)
        lines = [ln for ln in body.split("\n") if ln.strip()]
        if len(body) < 200 or (lines and sum("...." in ln for ln in lines) / len(lines) > 0.2):
            continue  # a table-of-contents block, not the essay
        provision = re.sub(r"\.\d+(\.\d+)*$", "", eid)  # ArtI.S8.C3.1.2 -> ArtI.S8.C3
        body = "\n".join(ln for ln in body.split("\n") if "......" not in ln).strip()  # trailing contents lines
        if eid not in found or len(body) > len(found[eid][3]):  # the essay is the longest block under its id;
            found[eid] = (eid, provision, m.group(2).strip(), body)  # shorter ones are footnote cross-references
    rows = list(found.values())
    con.executemany("insert into conan (essay_id, provision, title, text) values (?,?,?,?)", rows)
    con.executescript("""
        create virtual table conan_fts using fts5(title, text, content='conan', content_rowid='id', tokenize='porter unicode61');
        insert into conan_fts(conan_fts) values ('rebuild');
        create index idx_conan on conan(provision, essay_id);
    """)
    enc = embedder()
    ids = con.execute("select id, title || char(10) || substr(text, 1, 1500) from conan").fetchall()
    q = enc([t for _, t in ids])
    con.execute(f"create virtual table conan_vec using vec0(id integer primary key, emb int8[{q.shape[1]}])")
    con.executemany("insert into conan_vec(id, emb) values (?, vec_int8(?))", [(i, q[k].tobytes()) for k, (i, _) in enumerate(ids)])
    con.commit()
    print(f"  Constitution Annotated: {len(rows):,} essays", flush=True)


# ------------------------------------------------------------ legislators
def legislators(con) -> None:
    con.executescript("""
        drop table if exists legislators; drop table if exists legislator_terms; drop table if exists executives;
        create table legislators (id integer primary key, bioguide text, name text, first text, last text,
                                  birthday text, gender text, current integer);
        create table legislator_terms (legislator_id integer, type text, state text, district text, party text,
                                       start text, end text);
        create table executives (id integer primary key, name text, birthday text, type text, party text,
                                 start text, end text, how text);
    """)
    base = SEED / "legislators"
    for fname, current in (("legislators-historical.json", 0), ("legislators-current.json", 1)):
        for p in json.loads((base / fname).read_text(encoding="utf-8")):
            nm = p.get("name", {})
            full = nm.get("official_full") or " ".join(x for x in (nm.get("first"), nm.get("middle"), nm.get("last"), nm.get("suffix")) if x)
            cur = con.execute("insert into legislators (bioguide, name, first, last, birthday, gender, current) values (?,?,?,?,?,?,?)",
                              (p.get("id", {}).get("bioguide"), full, nm.get("first"), nm.get("last"),
                               p.get("bio", {}).get("birthday"), p.get("bio", {}).get("gender"), current))
            con.executemany("insert into legislator_terms values (?,?,?,?,?,?,?)",
                            [(cur.lastrowid, t.get("type"), t.get("state"), str(t.get("district", "")), t.get("party"),
                              t.get("start"), t.get("end")) for t in p.get("terms", [])])
    for p in json.loads((base / "executive.json").read_text(encoding="utf-8")):
        nm = p.get("name", {})
        full = " ".join(x for x in (nm.get("first"), nm.get("middle"), nm.get("last"), nm.get("suffix")) if x)
        for t in p.get("terms", []):
            con.execute("insert into executives (name, birthday, type, party, start, end, how) values (?,?,?,?,?,?,?)",
                        (full, p.get("bio", {}).get("birthday"), t.get("type"), t.get("party"), t.get("start"), t.get("end"), t.get("how")))
    con.executescript("create index idx_leg_last on legislators(last); create index idx_terms on legislator_terms(legislator_id);")
    con.commit()
    print(f"  legislators: {con.execute('select count(*) from legislators').fetchone()[0]:,}; "
          f"executive terms: {con.execute('select count(*) from executives').fetchone()[0]:,}", flush=True)


# --------------------------------------------------------------- glossary
def glossary(con) -> None:
    con.executescript("""
        drop table if exists glossary; drop table if exists glossary_fts;
        create table glossary (id integer primary key, source text, term text, definition text);
    """)
    rows = []
    t = (SEED / "blacks" / "blacks-1910.txt").read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"-\s*\n\s*", "", t)  # rejoin words hyphenated across OCR lines
    for m in re.finditer(r"(?m)^([A-Z][A-Z' ,&-]{1,60}[A-Z])\.\s+(.+?)(?=\n\s*\n[A-Z][A-Z' ,&-]{1,60}[A-Z]\.\s|\Z)", t, re.S):
        term, body = m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()
        if 15 < len(body) < 20000 and not term.startswith(("THE ", "OF ")):
            rows.append(("Black's Law Dictionary (2nd ed., 1910)", term.title(), body))
    nb = len(rows)
    with open(SEED / "webster" / "webster1828.csv", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) >= 2 and row[0].strip():
                rows.append(("Webster's American Dictionary of the English Language (1828)", row[0].strip(), strip(row[1])))
    con.executemany("insert into glossary (source, term, definition) values (?,?,?)", rows)
    con.executescript("""
        create virtual table glossary_fts using fts5(term, definition, content='glossary', content_rowid='id', tokenize='unicode61');
        insert into glossary_fts(glossary_fts) values ('rebuild');
        create index idx_glossary_term on glossary(term collate nocase);
    """)
    con.commit()
    print(f"  glossary: {nb:,} Black's entries, {len(rows) - nb:,} Webster 1828 entries", flush=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    jobs = sys.argv[1:] or ["cases", "statutes", "conan", "legislators", "glossary"]
    con = sqlite3.connect(DB)
    con.execute("pragma journal_mode=wal")
    load_vec(con)
    for j in jobs:
        print(f"{j}…", flush=True)
        globals()[j](con)
    con.execute("insert or replace into meta values ('phase2', ?)", (json.dumps(jobs),))
    con.commit()
    con.execute("pragma journal_mode=delete")
    con.execute("vacuum")
    con.close()
    print(f"done: {DB} ({DB.stat().st_size / 1e6:,.0f} MB)")


if __name__ == "__main__":
    main()
