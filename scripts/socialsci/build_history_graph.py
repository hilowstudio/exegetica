"""Build the history people-and-events graph into db/social_sciences.db from the Wikidata harvest
(scripts/socialsci/harvest_wikidata.py). Design: docs/history-graph-design.md.

Tables:
  h_entities  every node: person, event, place, or item (an office, party, occupation, school, work)
  h_people    dates with precision, birth and death places, living flag, why the person is in scope
  h_events    category (conflict, U.S. law, inventions, eras ...), kind (the Wikidata class), start and
              end with precision, location, coordinates, legal citations, the matching case
  h_places    kind, country, located in, coordinates
  h_edges     typed, dated links (src, rel, dst, start, end, via)
  h_mentions  where people and events appear in our documents and court cases: stated links,
              confident name matches, hand tags
  h_names_fts full-text search over names and aliases

    .venv/Scripts/python.exe scripts/socialsci/build_history_graph.py [graph|stated|matches|hand ...]
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harvest_wikidata as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "db" / "social_sciences.db"
OUT = H.OUT

PERSON_REL = {"P27": "citizen_of", "P106": "occupation", "P102": "party", "P140": "religion", "P241": "served_in",
              "P69": "educated_at", "P22": "father", "P25": "mother", "P26": "spouse", "P40": "child",
              "P3373": "sibling", "P737": "influenced_by", "P1066": "student_of", "P802": "teacher_of",
              "P1344": "participated_in", "P607": "fought_in", "P166": "award", "P19": "born_in", "P20": "died_in"}
EVENT_REL = {"P31": "instance_of", "P276": "located_at", "P17": "country", "P361": "part_of", "P155": "follows",
             "P156": "followed_by", "P828": "caused_by", "P1542": "led_to"}
# links from a person (or group) to an event, stored person -> event
EVENT_AGENT = {"P1891": "signed", "P61": "invented", "P823": "gave", "P50": "authored", "P170": "created",
               "P991": "won", "P1346": "won"}
CATEGORY_ORDER = ["court", "presidential elections", "olympics", "U.S. law", "conflict", "law and government",
                  "elections", "exploration", "disasters", "society", "economy", "church", "speeches and texts",
                  "inventions", "eras"]


# ---- TSV cells and dates ----------------------------------------------------------------------------
def cell(v: str) -> str:
    """A TSV cell as plain text: an entity becomes its Q-id, a literal loses quotes and tags."""
    v = v.strip()
    if v.startswith("<"):
        return v.strip("<>").rsplit("/", 1)[-1]
    if v.startswith('"'):
        end = v.rfind('"')
        return v[1:end].replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
    return v


def rows(kind: str, prefix: str):
    for f in H.files(kind, prefix):
        for r in H.read(f):
            yield [cell(x) for x in r]


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def date(t: str, prec: int) -> tuple[str, int | None]:
    """An exported Wikidata time and its precision -> (text, year). AD dates keep a sortable four-digit
    year ('1809-02-12', '0450'); BC dates read '100 BC'. The export counts a year zero for dates precise
    to the year or better (-0099 is 100 BC); coarser dates are exported as entered."""
    m = re.match(r"([+-]?)(\d+)-(\d\d)-(\d\d)", t or "")
    if not m:
        return "", None
    year = int(m.group(2)) * (-1 if m.group(1) == "-" else 1)
    if year <= 0 and prec >= 9:
        year -= 1
    if year == 0:
        year = -1
    bc, y = year < 0, abs(year)
    era = " BC" if bc else ""
    if prec >= 11:
        return (f"{y} BC" if bc else f"{y:04d}-{m.group(3)}-{m.group(4)}"), year
    if prec == 10:
        return (f"{y} BC" if bc else f"{y:04d}-{m.group(3)}"), year
    if prec == 9:
        return (f"{y} BC" if bc else f"{y:04d}"), year
    if prec == 8:
        return f"{y // 10 * 10}s{era}", year
    if prec == 7:
        return f"{ordinal((y - 1) // 100 + 1)} century{era}", year
    if prec == 6:
        return f"{ordinal((y - 1) // 1000 + 1)} millennium{era}", year
    return (f"{y} BC" if bc else f"{y:04d}"), year


def point(wkt: str) -> tuple[float | None, float | None]:
    m = re.search(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", wkt or "", re.I)  # QLever writes POINT, the official service Point
    return (float(m.group(2)), float(m.group(1))) if m else (None, None)


def best_dates(kind: str, prefix: str) -> dict[tuple[str, str], tuple[str, int, int | None]]:
    """(qid, property) -> (date text, precision, year), keeping the most precise statement."""
    best: dict[tuple[str, str], tuple[str, int, int | None]] = {}
    for r in rows(kind, prefix):
        if len(r) < 4:
            continue
        q, prop, t, prec = r[0], r[1], r[2], int(r[3] or 0)
        txt, year = date(t, prec)
        if year is None:
            continue
        if (q, prop) not in best or prec > best[(q, prop)][1]:
            best[(q, prop)] = (txt, prec, year)
    return best


# ---- graph --------------------------------------------------------------------------------------
SCHEMA = """
drop table if exists h_entities; drop table if exists h_people; drop table if exists h_events;
drop table if exists h_places; drop table if exists h_edges; drop table if exists h_names_fts;
create table h_entities (qid text primary key, kind text, name text, description text, aliases text,
                         sitelinks integer, enwiki text);
create table h_people (qid text primary key, birth text, birth_prec integer, birth_year integer, death text,
                       death_prec integer, death_year integer, birthplace text, deathplace text, living integer,
                       reasons text, bioguide text);
create table h_events (qid text primary key, category text, categories text, kind text, start text,
                       start_prec integer, start_year integer, end text, end_prec integer, end_year integer,
                       location text, country text, lat real, lon real, citation text, case_id integer);
create table h_places (qid text primary key, kind text, country text, located_in text, lat real, lon real);
create table h_edges (src text, rel text, dst text, start text, end text, via text);
"""


def load_core(con, kind: str, label: str, keep: set[str] | None = None) -> set[str]:
    aliases: dict[str, list[str]] = {}
    for r in rows(kind, "aliases"):
        if len(r) >= 2 and r[1] and (keep is None or r[0] in keep):
            aliases.setdefault(r[0], []).append(r[1])
    seen: set[str] = set()
    for r in rows(kind, "core"):
        if not r or r[0] in seen or (keep is not None and r[0] not in keep):
            continue
        r += [""] * (5 - len(r))
        q, s, name, desc, enwiki = r[:5]
        if not name:
            continue
        seen.add(q)
        con.execute("insert or ignore into h_entities values (?,?,?,?,?,?,?)",
                    (q, label, name, desc or None, "; ".join(dict.fromkeys(aliases.get(q, []))) or None,
                     int(s or 0) if (s or "").isdigit() else 0, enwiki or None))
    return seen


def claims_by_subject(kind: str, prefix: str, keep: set[str]) -> dict[str, dict[str, list[str]]]:
    out: dict[str, dict[str, list[str]]] = {}
    for r in rows(kind, prefix):
        if len(r) >= 3 and r[0] in keep:
            out.setdefault(r[0], {}).setdefault(r[1], []).append(r[2])
    return out


def graph(con) -> None:
    con.executescript(SCHEMA)
    why = H.final_people()
    selected = H.events_selected()

    # people
    people = load_core(con, "people", "person", set(why))
    born, dead, _ = H.life_evidence()
    d = best_dates("candidates", "dates")
    claims = claims_by_subject("people", "claims", people)
    for q in people:
        c = claims.get(q, {})
        b, dd = d.get((q, "P569")), d.get((q, "P570"))
        con.execute("insert into h_people values (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (q, b and b[0], b and b[1], b and b[2], dd and dd[0], dd and dd[1], dd and dd[2],
                     (c.get("P19") or [None])[0], (c.get("P20") or [None])[0], int("living" in why.get(q, ())),
                     ",".join(sorted(why.get(q, set()) - {"living"})), (c.get("P1157") or [None])[0]))
        for prop, rel in PERSON_REL.items():
            for o in dict.fromkeys(c.get(prop, [])):
                if o.startswith("Q"):
                    con.execute("insert into h_edges (src, rel, dst) values (?,?,?)", (q, rel, o))
    for r in rows("people", "positions2"):
        r += [""] * (8 - len(r))
        q, pos, start, sp, end, ep, rep, repby = r[:8]
        if q not in people or not pos.startswith("Q"):
            continue
        s = date(start, int(sp or 9))[0] if start else None
        e = date(end, int(ep or 9))[0] if end else None
        con.execute("insert into h_edges values (?,?,?,?,?,?)", (q, "held", pos, s, e, None))
        if rep.startswith("Q"):
            con.execute("insert into h_edges values (?,?,?,?,?,?)", (q, "succeeded", rep, s, None, pos))
        if repby.startswith("Q"):
            con.execute("insert into h_edges values (?,?,?,?,?,?)", (repby, "succeeded", q, e, None, pos))
    for r in rows("people", "works"):
        if len(r) >= 2 and r[0] in people:
            con.execute("insert into h_edges (src, rel, dst) values (?,?,?)", (r[0], "authored", r[1]))
    print(f"  people: {len(people):,}", flush=True)

    # events
    events = load_core(con, "events", "event", set(selected))
    d = best_dates("events", "dates2")
    ec = claims_by_subject("events", "claims2", events)
    dropped = 0
    for q in events:
        c = ec.get(q, {})
        cats = sorted(selected.get(q, ()), key=lambda x: CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else 99)
        if cats == ["inventions"] and c.get("P625"):
            # a discovered island or lake carries a discoverer and a date of discovery too; it is a place
            con.execute("delete from h_entities where qid = ?", (q,))
            dropped += 1
            continue
        kinds = [H.EVENT_CLASSES[k] for k in c.get("P31", []) if k in H.EVENT_CLASSES]
        s = next((d[(q, p)] for p in ("P580", "P585", "P575", "P619", "P1619", "P571", "P577") if (q, p) in d), None)
        e = next((d[(q, p)] for p in ("P582", "P620", "P576", "P585") if (q, p) in d), None)
        lat, lon = point((c.get("P625") or [""])[0])
        cites = "; ".join(dict.fromkeys(c.get("P1031", []))) or None
        con.execute("insert into h_events values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (q, cats[0] if cats else None, ", ".join(cats) or None, kinds[0] if kinds else None,
                     s and s[0], s and s[1], s and s[2], e and e[0], e and e[1], e and e[2],
                     (c.get("P276") or [None])[0], (c.get("P17") or [None])[0], lat, lon, cites, None))
        for prop, rel in EVENT_REL.items():
            for o in dict.fromkeys(c.get(prop, [])):
                if o.startswith("Q"):
                    con.execute("insert into h_edges (src, rel, dst) values (?,?,?)", (q, rel, o))
        for o in dict.fromkeys(c.get("P710", [])):  # participants: a person takes part, a country or army is a party
            if o in people:
                con.execute("insert into h_edges (src, rel, dst) values (?,?,?)", (o, "participated_in", q))
            elif o.startswith("Q"):
                con.execute("insert into h_edges (src, rel, dst) values (?,?,?)", (q, "party", o))
        for prop, rel in EVENT_AGENT.items():
            for o in dict.fromkeys(c.get(prop, [])):
                if o.startswith("Q"):
                    con.execute("insert into h_edges (src, rel, dst) values (?,?,?)", (o, rel, q))
    print(f"  events: {len(events) - dropped:,} ({dropped:,} discovered places left out)", flush=True)

    # places
    places = load_core(con, "places", "place")
    pc = claims_by_subject("places", "claims", places)
    for q in places:
        c = pc.get(q, {})
        lat, lon = point((c.get("P625") or [""])[0])
        con.execute("insert into h_places values (?,?,?,?,?,?)",
                    (q, (c.get("P31") or [None])[0], (c.get("P17") or [None])[0], (c.get("P131") or [None])[0], lat, lon))
    print(f"  places: {len(places):,}", flush=True)

    # everything else the edges point at
    n = 0
    for r in rows("labels", "core"):
        r += [""] * (3 - len(r))
        if r[1]:
            n += con.execute("insert or ignore into h_entities (qid, kind, name, description) values (?,?,?,?)",
                             (r[0], "item", r[1], r[2] or None)).rowcount
    print(f"  other items: {n:,}", flush=True)

    # index the links first: every step below looks them up by node (without these, naming the kinds
    # scanned millions of links once per event)
    con.executescript("""
        create index idx_h_edges_src on h_edges(src, rel);
        create index idx_h_edges_dst on h_edges(dst, rel);
    """)
    print("  links indexed", flush=True)
    # an event whose class isn't one of ours takes the name of its own class ("naval battle")
    con.execute("""update h_events set kind = (select n.name from h_edges x join h_entities n on n.qid = x.dst
                                               where x.src = h_events.qid and x.rel = 'instance_of' limit 1)
                   where kind is null""")
    # an edge that points at something with no English label is noise
    con.execute("delete from h_edges where dst not in (select qid from h_entities)")
    con.execute("delete from h_edges where src not in (select qid from h_entities)")
    con.executescript("""
        delete from h_edges where rowid not in (select min(rowid) from h_edges group by src, rel, dst, start, via);
        create index idx_h_entities_name on h_entities(name collate nocase);
        create index idx_h_people_birth on h_people(birth_year);
        create index idx_h_events_start on h_events(start_year);
        create index idx_h_events_category on h_events(category);
        create virtual table h_names_fts using fts5(name, aliases, content='h_entities', content_rowid='rowid',
                                                    tokenize='unicode61 remove_diacritics 2');
        insert into h_names_fts(h_names_fts) values ('rebuild');
    """)
    print(f"  edges: {con.execute('select count(*) from h_edges').fetchone()[0]:,}", flush=True)
    print("  events by category:", con.execute("select category, count(*) from h_events group by 1 order by 2 desc").fetchall(), flush=True)


# ---- stated mentions ----------------------------------------------------------------------------
def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def stated(con) -> None:
    """Links we know without reading: justices on every case, speakers of the presidential speeches,
    Wikidata's Supreme Court decisions matched to our cases by any of their U.S. Reports citations."""
    # each step clears only its own rows, so a rerun never wipes the hand tags
    con.executescript("""
        create table if not exists h_mentions (qid text, doc_type text, doc_id integer, how text, role text, passage_id integer);
        delete from h_mentions where how = 'stated';
    """)
    cases = {c: i for i, c in con.execute("select id, cite from cases where cite is not null")}
    n = 0
    for q, cites in con.execute("select qid, citation from h_events where citation is not null").fetchall():
        for m in re.finditer(r"(\d+)\s*U\.\s*S\.\s*(\d+)", cites):
            cid = cases.get(f"{m.group(1)} U.S. {m.group(2)}")
            if cid:
                con.execute("update h_events set case_id = ? where qid = ?", (cid, q))
                con.execute("insert into h_mentions values (?,?,?,?,?,?)", (q, "case", cid, "stated", "the case itself", None))
                n += 1
                break
    print(f"  decisions matched to cases: {n:,}", flush=True)

    # justices: SCDB codes ("EWarren", "JHarlan2", "SDOConnor", "WVanDevanter") -> people who held a seat
    seats = con.execute("""select e.src, p.name, e.start, e.end from h_edges e join h_entities p on p.qid = e.src
                           where e.rel = 'held' and e.dst in ('Q11144', 'Q11147')""").fetchall()
    by_last: dict[str, list[tuple]] = {}
    for q, name, s, e in seats:
        words = re.sub(r",? (Jr\.|Sr\.|II|III)$", "", name).split()
        start = int(s[:4]) if s and s[:4].isdigit() else 0
        end = int(e[:4]) if e and e[:4].isdigit() else 9999
        for key in {_letters(words[-1]), _letters("".join(words[-2:]))}:  # 'Van Devanter', 'O'Connor'
            by_last.setdefault(key, []).append((q, name, start, end))

    def justice(code: str, year: int) -> str | None:
        m = re.match(r"([A-Z]+)([A-Z][a-z].*?)(\d?)$", code or "")
        if not m:
            return None
        initials, last = m.group(1), _letters(m.group(2))
        found = {c[0] for c in by_last.get(last, []) if c[1][0] == initials[0] and c[2] - 1 <= year <= c[3] + 1}
        return found.pop() if len(found) == 1 else None

    n = total = 0
    for cid, year, maj, dis, writer in con.execute("select id, year, majority, dissent, maj_writer from cases"):
        for codes, role in ((maj, "in the majority"), (dis, "dissenting")):
            for code in (codes or "").split(", "):
                code = code.strip()
                if not code:
                    continue
                total += 1
                q = justice(code, year or 0)
                if q:
                    con.execute("insert into h_mentions values (?,?,?,?,?,?)",
                                (q, "case", cid, "stated", "wrote the opinion" if code == writer else role, None))
                    n += 1
    print(f"  justice votes linked: {n:,} of {total:,}", flush=True)

    # presidential speeches: Miller Center names the speaker; match first and last name against each
    # president's name and aliases ('Franklin D. Roosevelt' -> Franklin Delano Roosevelt)
    pairs: dict[tuple[str, str], set[str]] = {}
    exact: dict[str, set[str]] = {}
    labels: dict[str, set[str]] = {}  # a name beats an alias: John Quincy Adams also goes by "John Adams"
    for q, name, aliases in con.execute("""select distinct e.src, p.name, p.aliases from h_edges e join h_entities p on p.qid = e.src
                                           where e.rel = 'held' and e.dst in ('Q11696', 'Q11699')"""):
        labels.setdefault(_letters(name), set()).add(q)
        for nm in [name, *(a.strip() for a in (aliases or "").split(";"))]:
            exact.setdefault(_letters(nm), set()).add(q)
            w = re.findall(r"[A-Za-z']+", re.sub(r",? (Jr\.|Sr\.)$", "", nm))
            if len(w) >= 2:
                pairs.setdefault((w[0].lower(), w[-1].lower()), set()).add(q)
    n = 0
    for did, author in con.execute("select id, author from documents where source = 'miller-center'").fetchall():
        w = re.findall(r"[A-Za-z']+", author or "")
        qs = labels.get(_letters(author))
        if not qs or len(qs) != 1:
            qs = exact.get(_letters(author))  # "George W. Bush" and "George H. W. Bush" share a first and last name
        if not qs or len(qs) != 1:
            qs = pairs.get((w[0].lower(), w[-1].lower())) if len(w) >= 2 else None
        if qs and len(qs) == 1:
            con.execute("insert into h_mentions values (?,?,?,?,?,?)", (next(iter(qs)), "document", did, "stated", "speaker", None))
            n += 1
    speeches = con.execute("select count(*) from documents where source = 'miller-center'").fetchone()[0]
    print(f"  speeches linked to speakers: {n:,} of {speeches:,}", flush=True)
    con.execute("create index if not exists idx_h_mentions on h_mentions(qid)")
    con.execute("create index if not exists idx_h_mentions_doc on h_mentions(doc_type, doc_id)")


# ---- confident name matches ---------------------------------------------------------------------
TITLES = set("""president king queen saint st pope general gen mr mrs miss sir lord lady emperor empress duke
duchess prince princess count earl baron captain capt colonel col major admiral judge justice senator
governor gov reverend rev dr doctor father brother sister the of and de la le van von der""".split())
REGNAL = re.compile(r"^[A-Z][a-z]+ [IVXL]+\.?$")


def _usable(name: str, is_label: bool = True) -> bool:
    """A name worth matching in running text: two or more words, at least two of them full name words
    (initials like 'J.' or 'A. A.' don't count), capitalized, and a regnal form ('Edward VI') only as the
    person's own name, never as someone else's alias."""
    words = re.findall(r"[A-Za-z][A-Za-z'.-]*", name)
    if len(words) < 2 or len(name) < 7 or len(name) > 60:
        return False
    if not is_label and REGNAL.match(name):
        return False
    full = [w for w in words if w.lower().strip(".") not in TITLES and len(w.strip(".")) >= 3]
    return len(full) >= 2 and all(w[0].isupper() or w.lower() in TITLES for w in words)


def matches(con) -> None:
    """Link people and events to documents and cases where their full name (or a distinctive alias)
    appears, keeping only confident matches: the name points to one person (or event) that existed by the
    document's date and is known well enough to be the one meant (5+ Wikipedias; 20+ in an undated book,
    taken as written by 1925), or to one far better known than any namesake (50+, ten times the next).
    Common two-word names ('John James') need 40+. Audited by hand: about 96% of a sample were right."""
    import ahocorasick

    con.execute("create table if not exists h_mentions (qid text, doc_type text, doc_id integer, how text, role text, passage_id integer)")
    con.execute("delete from h_mentions where how = 'match'")
    firsts, lasts = Counter(), Counter()
    for (nm,) in con.execute("select name from h_entities where kind = 'person'"):
        w = re.findall(r"[A-Za-z']+", nm)
        if len(w) >= 2:
            firsts[w[0]] += 1
            lasts[w[-1]] += 1
    common_first = {w for w, _ in firsts.most_common(400)}
    common_last = {w for w, _ in lasts.most_common(1500)}

    def surname(n: str) -> str:
        w = re.findall(r"[A-Za-z']+", re.sub(r",.*$|\s*\(.*?\)", "", n))
        return w[-1].lower() if w else ""

    cands: dict[str, list[tuple]] = {}
    event_qids = {q for (q,) in con.execute("select qid from h_entities where kind = 'event'")}
    for q, kind, name, aliases, sl, born, start in con.execute(
            """select e.qid, e.kind, e.name, e.aliases, e.sitelinks, p.birth_year, v.start_year from h_entities e
               left join h_people p on p.qid = e.qid left join h_events v on v.qid = e.qid
               where e.kind in ('person', 'event')"""):
        if kind == "event" and (sl or 0) < 5:
            continue
        for n, is_label in {(name, True), *[(a.strip(), False) for a in (aliases or "").split(";")]}:
            if not n or not _usable(n, is_label):
                continue
            if kind == "person" and not is_label and surname(n) != surname(name):
                continue  # an alias that isn't the person's own name ('Mary Jones' for Peter Sewally)
            if kind == "event" and not is_label and len(n.split()) < 3 and not re.search(
                    r"\d|\b(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|"
                    r"Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth|Nineteenth|Twentieth)\b", n):
                continue  # a short generic alias ('Criminal Code', 'World War'); 'Fifth Amendment' is kept
            w = [x for x in re.findall(r"[A-Za-z']+", n) if len(x) > 1]
            need = 40 if kind == "person" and len(w) == 2 and w[0] in common_first and w[1] in common_last else 0
            cands.setdefault(n, []).append((q, sl or 0, born if kind == "person" else start, need))
    event_names = {n for n, cs in cands.items() if any(c[0] in event_qids for c in cs)}
    auto = ahocorasick.Automaton()
    for n, cs in cands.items():
        auto.add_word(n, (n, cs))
    auto.make_automaton()
    print(f"  {len(cands):,} names to look for", flush=True)

    def pick(cs: list[tuple], year: int | None) -> str | None:
        floor, by = (5, year) if year else (20, 1925)
        fit = [c for c in cs if c[2] is None or c[2] <= by]
        if len(fit) == 1:
            return fit[0][0] if fit[0][1] >= max(floor, fit[0][3]) else None
        fit.sort(key=lambda c: -c[1])
        if len(fit) > 1 and fit[0][1] >= 50 and fit[0][1] >= 10 * max(fit[1][1], 1):
            return fit[0][0]
        return None

    def scan(sql: str, doc_type: str) -> int:
        found: dict[tuple[str, int], list] = {}
        for pid, doc_id, year, txt in con.execute(sql):
            for end, (n, cs) in auto.iter(txt or ""):
                start = end - len(n) + 1
                nxt = txt[end + 1] if end + 1 < len(txt) else ""
                possessive = nxt in "'’" and txt[end + 2:end + 3] == "s" and not txt[end + 3:end + 4].isalnum()
                if (start > 0 and (txt[start - 1].isalnum() or txt[start - 1] in "-'’")) or \
                        nxt.isalnum() or nxt == "-" or (nxt in "'’" and not possessive):
                    continue  # part of a longer word or name ("Maxwell-Fyfe"); "Lincoln's" is fine
                before = re.search(r"([A-Za-z]+)(\.?)\s+$", txt[max(0, start - 30):start])
                if before and before.group(1)[0].isupper() and before.group(1).lower() not in TITLES:
                    lead = txt[max(0, start - 30):start][:before.start()].rstrip()
                    abbrev = re.search(r"([A-Za-z]+)\.$", lead)  # "Rev." ends a title, not a sentence
                    if not lead or lead[-1] not in ".!?:;\"“(\n" or (abbrev and abbrev.group(1).lower() in TITLES):
                        continue  # the tail of a longer name ("John Henry Barrows", "Fort Sam Houston")
                after = txt[end + 1:end + 25]
                if re.match(r"\s+(?:[A-Z][a-z]+|&|Co\b|Inc\b|Company\b|Junior\b)", after):
                    continue  # the head of a longer name or a company ("Leland Stanford Junior", "Eli Lilly & Co.")
                if n in event_names and re.match(r"\s+of [A-Z]", after):
                    continue  # an event name inside a longer proper name ("Catholic Action of Hawaii")
                q = pick(cs, year)
                if q:
                    k = (q, doc_id)
                    if k in found:
                        found[k][1] += 1
                    else:
                        found[k] = [pid, 1]
        con.executemany("insert into h_mentions values (?,?,?,?,?,?)",
                        [(q, doc_type, d, "match", f"named {n} time{'s' if n != 1 else ''}", pid)
                         for (q, d), (pid, n) in found.items()])
        return len(found)

    n = scan("select p.id, p.doc_id, d.year, p.text from passages p join documents d on d.id = p.doc_id", "document")
    print(f"  document links: {n:,}", flush=True)
    n = scan("select p.id, p.case_id, c.year, p.text from case_passages p join cases c on c.id = p.case_id", "case")
    print(f"  case links: {n:,}", flush=True)


# ---- hand tags (scripts/socialsci/tags/core-document-tags.jsonl) --------------------------------
TAGS = Path(__file__).parent / "tags" / "core-document-tags.jsonl"
STRIP_TITLES = re.compile(r"^(?:Mr|Mrs|Miss|Dr|Gen|General|Col|Colonel|Capt|Captain|Sir|Hon|President|Senator|Justice|Judge|King|Queen)\.?\s+", re.I)
KINDS = {"person": ("person",), "place": ("place", "item"), "event": ("event", "item")}  # laws and documents can be items
COLS = ("qid", "name", "aliases", "sl", "born", "died", "start", "desc")
SEL = """select e.qid, e.name, e.aliases, e.sitelinks, p.birth_year, p.death_year, v.start_year, e.description
         from {src} left join h_people p on p.qid = e.qid left join h_events v on v.qid = e.qid"""
STOP = set("the of a an and in on at to for by with from as is was who what which his her their its".split())


def _years(hint: str) -> list[int]:
    return [int(y) for y in re.findall(r"\b(1[0-9]{3}|20[0-2][0-9])\b", hint or "")]


def _words(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if w not in STOP]


def forms(name: str) -> list[str]:
    base = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    return [n for n in dict.fromkeys((name, STRIP_TITLES.sub("", name), base, STRIP_TITLES.sub("", base))) if n]


def candidates(con, name: str, kind: str) -> list[dict]:
    """Exact names and aliases first, then every node whose name or aliases hold the first and last
    name words (or, for a short name, all its words), so 'Franklin D. Roosevelt' finds 'Franklin Delano
    Roosevelt' and 'George III' finds 'George III of Great Britain'; the scoring then decides."""
    out: dict[str, dict] = {}
    ks = KINDS[kind]
    kq = ",".join("?" * len(ks))
    for n in forms(name):
        for r in con.execute(SEL.format(src="h_entities e") + f" where e.kind in ({kq}) and e.name = ? collate nocase", (*ks, n)):
            out[r[0]] = dict(zip(COLS, r), exact=True)
        words = [w for w in re.findall(r"[A-Za-z0-9']+", n) if len(w) > 1 or w.isdigit()]
        if not words:
            continue
        need = words if len(words) <= 3 else [words[0], words[-1]]
        expr = " ".join('"' + w + '"' for w in need)
        try:
            hits = con.execute(SEL.format(src="h_names_fts f join h_entities e on e.rowid = f.rowid") +
                               f" where h_names_fts match ? and e.kind in ({kq}) order by e.sitelinks desc limit 60",
                               (expr, *ks)).fetchall()
        except sqlite3.OperationalError:
            hits = []
        for r in hits:
            exact = n.lower() == (r[1] or "").lower() or n.lower() in [a.strip().lower() for a in (r[2] or "").split(";")]
            if r[0] not in out:
                out[r[0]] = dict(zip(COLS, r), exact=exact)
    return list(out.values())


def choose(cs: list[dict], hint: str, year: int | None, role: str, name: str = "", explain: bool = False):
    """Score each candidate and take a clear winner (2 points ahead), or on a tie the far better-known one
    (2.5 times the Wikipedia articles); otherwise leave the tag unmatched.
      name     exact name +4; exact alias +2; the same words with at most one extra +2
      years    the hint's years match a birth, death, or start year +6; plainly someone else's -4
      words    hint words found in the description, up to +3
      date     born after the document, or dead before a document they signed or wrote, -20"""
    if not cs:
        return None
    ys = set(_years(hint))
    hint = re.sub(r"\bU\.\s?S\.(?:\s?A\.)?", "United States", hint or "")  # descriptions spell it out
    hw = {w for w in _words(hint) if len(w) > 2}
    nw = set(_words(STRIP_TITLES.sub("", re.sub(r"\s*\(.*?\)\s*", " ", name))))
    bare = STRIP_TITLES.sub("", re.sub(r"\s*\(.*?\)\s*", " ", name)).strip().lower()

    def score(c):
        sc = 0
        cn = (c.get("name") or "").lower()
        if cn in (name.lower(), bare):
            sc += 4
        elif c.get("exact"):
            sc += 2
        elif nw and nw <= set(_words(cn)) and len(set(_words(cn)) - nw) <= 1:
            sc += 2
        dates = {c.get("born"), c.get("died"), c.get("start")} - {None}
        if ys and dates & ys:
            sc += 6
        elif ys and c.get("born") and all(abs(d - y) > 3 for d in dates for y in ys):
            sc -= 4  # the hint's years point at someone else
        sc += min(3, len(hw & set(_words(c.get("desc")))))
        if year and c.get("born") and c["born"] > year:
            sc -= 20
        if year and role in ("author", "signer", "addressed_to") and c.get("died") and c["died"] < year:
            sc -= 20
        return sc

    ranked = sorted(cs, key=lambda c: (-score(c), -(c.get("sl") or 0)))
    if explain:
        return [(score(c), c.get("sl"), c["qid"], c["name"], (c.get("desc") or "")[:50]) for c in ranked[:6]]
    top = score(ranked[0])
    if top < 2:
        return None  # nothing about the best candidate actually fits
    if len(ranked) == 1 or top >= score(ranked[1]) + 2:
        return ranked[0]["qid"]
    a, b = ranked[0].get("sl") or 0, ranked[1].get("sl") or 0
    return ranked[0]["qid"] if a >= 20 and a >= 2.5 * max(b, 1) else None


def hand(con) -> None:
    """Match each hand tag to a graph node: name and alias candidates, ranked by the hint's dates and the
    document's date, then by fame. Tags with no candidate in the graph get one label lookup on Wikidata."""
    con.execute("create table if not exists h_mentions (qid text, doc_type text, doc_id integer, how text, role text, passage_id integer)")
    con.execute("delete from h_mentions where how = 'hand'")
    tags = [json.loads(ln) for ln in TAGS.read_text(encoding="utf-8").splitlines() if ln.strip()]
    years = {d: y for d, y in con.execute("select id, year from documents")}

    out, missing = [], []
    for d in tags:
        year = years.get(d["doc_id"])
        for e in d["entities"]:
            q = choose(candidates(con, e["name"], e["kind"]), e.get("hint", ""), year, e.get("role", ""), e["name"])
            if q:
                out.append((q, "document", d["doc_id"], "hand", e.get("role"), None))
            else:
                missing.append((d["doc_id"], e))
    print(f"  matched in the graph: {len(out):,}; to look up: {len(missing):,}", flush=True)

    # one Wikidata label lookup for the rest; a cache file is named for the names it covers
    names = sorted({STRIP_TITLES.sub("", re.sub(r"\s*\(.*?\)\s*", " ", e["name"]).strip()) for _, e in missing})
    found: dict[tuple[str, str], list[dict]] = {}
    for n0 in range(0, len(names), 300):
        chunk = names[n0:n0 + 300]
        vals = " ".join('"' + n.replace("\\", "").replace('"', "") + '"@en' for n in chunk)
        dest = H.OUT / "hand" / f"labels_{hashlib.sha1(vals.encode()).hexdigest()[:12]}.tsv"
        H.run(f"""SELECT ?l ?x ?s ?human ?coord ?born ?died ?desc WHERE {{ VALUES ?l {{ {vals} }}
                  {{ ?x rdfs:label ?l }} UNION {{ ?x skos:altLabel ?l }}
                  ?x wikibase:sitelinks ?s .
                  OPTIONAL {{ ?x wdt:P31 wd:Q5 . BIND(1 AS ?human) }}
                  OPTIONAL {{ ?x wdt:P625 ?coord }}
                  OPTIONAL {{ ?x wdt:P569 ?born }} OPTIONAL {{ ?x wdt:P570 ?died }}
                  OPTIONAL {{ ?x schema:description ?desc . FILTER(LANG(?desc) = "en") }} }}""", dest, H.WDQS)
        for r in H.read(dest):
            r = [cell(x) for x in r] + [""] * 8
            label, q, s, human, coord, born, died, desc = r[:8]
            # people are people; anything else may answer a place tag or an event tag (battles have coordinates)
            found.setdefault((label, "person" if human else "other"), []).append(
                {"qid": q, "sl": int(s or 0) if s.isdigit() else 0, "desc": desc, "coord": coord,
                 "born": H.year(born) if born else None, "died": H.year(died) if died else None})
    added = 0
    still = []
    for doc_id, e in missing:
        n = STRIP_TITLES.sub("", re.sub(r"\s*\(.*?\)\s*", " ", e["name"]).strip())
        cs = list({c["qid"]: c for c in found.get((n, "person" if e["kind"] == "person" else "other"), [])}.values())
        q = choose([dict(c, start=None, exact=True, name=n) for c in cs], e.get("hint", ""), years.get(doc_id), e.get("role", ""), e["name"])
        if not q:
            still.append((doc_id, e["name"], e["kind"]))
            continue
        c = next(c for c in cs if c["qid"] == q)
        if con.execute("insert or ignore into h_entities (qid, kind, name, description, sitelinks) values (?,?,?,?,?)",
                       (q, e["kind"], n, c["desc"] or None, c["sl"])).rowcount:
            added += 1
            if e["kind"] == "person":
                con.execute("insert or ignore into h_people (qid, birth_year, death_year, living, reasons) values (?,?,?,0,'hand')",
                            (q, c["born"], c["died"]))
            elif e["kind"] == "place":
                lat, lon = point(c["coord"])
                con.execute("insert or ignore into h_places (qid, lat, lon) values (?,?,?)", (q, lat, lon))
            else:
                con.execute("insert or ignore into h_events (qid, category) values (?, 'documents and acts')", (q,))
        out.append((q, "document", doc_id, "hand", e.get("role"), None))
    con.executemany("insert into h_mentions values (?,?,?,?,?,?)", out)
    con.execute("insert into h_names_fts(h_names_fts) values ('rebuild')")
    print(f"  hand tags linked: {len(out):,} ({added:,} new nodes from Wikidata); unmatched: {len(still):,}", flush=True)
    (H.OUT / "hand" / "unmatched.tsv").write_text("\n".join(f"{d}\t{k}\t{n}" for d, n, k in still), encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    jobs = sys.argv[1:] or ["graph", "stated", "matches", "hand"]
    con = sqlite3.connect(DB)
    for j in jobs:
        print(f"{j}…", flush=True)
        globals()[j](con)
        con.commit()
    con.close()


if __name__ == "__main__":
    main()
