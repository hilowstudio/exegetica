"""Measure a tighter notability rule for the history graph and write the two review lists.

Fame (the number of Wikipedia language editions) measures attention. The significance signals record
judgment: a curated reference work's entry, Wikipedia's Vital Articles, a school textbook's mention, a major
honor. This script compares the two over the built graph and the harvested signals:

  drop list  people in the graph on fame alone (no office, signature, or event role) with no signal
  add list   people outside the graph with a signal

Each list shows every source separately, so the owner can decide which sources bring people in and which
only confirm someone already in.

    .venv/Scripts/python.exe scripts/socialsci/notability_review.py [measure|details|lists]
"""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harvest_wikidata as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "db" / "social_sciences.db"
SIG = H.OUT / "significance"
REVIEW = H.OUT.parent / "review"  # large; kept out of git (.seed_cache)
FAME = {"fame_illinois", "fame_us", "fame_world10", "fame_world20"}


def graph_people() -> dict[str, dict]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute("""SELECT p.qid, e.name, e.description, e.sitelinks, p.reasons, p.living, p.birth_year,
                                 p.death_year FROM h_people p JOIN h_entities e ON e.qid = p.qid""")
    out = {r[0]: {"name": r[1], "desc": r[2] or "", "s": r[3] or 0, "reasons": set((r[4] or "").split(",")) - {""},
                  "living": bool(r[5]), "born": r[6], "died": r[7]} for r in rows}
    con.close()
    return out


def references() -> dict[str, dict[str, int]]:
    """qid -> {source name: sitelinks} for the curated reference works and 'described by' sources."""
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for prop, name in H.REFERENCE_IDS.items():
        for r in H.read(H.OUT / "select" / f"ref_{prop}.tsv"):
            if r:
                out[H.qid(r[0])][name] = int(H.lit(r[1]) or 0)
    for src, name in H.DESCRIBED_BY.items():
        for r in H.read(H.OUT / "select" / f"described_{src}.tsv"):
            if r:
                out[H.qid(r[0])][name] = int(H.lit(r[1]) or 0)
    return out


def vital() -> dict[str, tuple[int, str]]:
    return {r["qid"]: (int(r["level"]), r["list"]) for r in csv.DictReader((SIG / "vital_people.tsv").open(encoding="utf-8"), delimiter="\t")}


def textbooks() -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for r in csv.DictReader((SIG / "textbook_mentions.tsv").open(encoding="utf-8"), delimiter="\t"):
        out[r["qid"]].add(r["book"])
    return out


def measure() -> None:
    g = graph_people()
    refs, vit, tb = references(), vital(), textbooks()
    fame_only = {q for q, p in g.items() if p["reasons"] and p["reasons"] <= FAME}
    print(f"graph: {len(g):,} people; fame only: {len(fame_only):,}")
    print(f"textbooks: {len(tb):,} people, {len(set(tb) & set(g)):,} in the graph")
    print(f"vital: {len(vit):,} people, {len(set(vit) & set(g)):,} in the graph, {len(set(vit) - set(g)):,} outside")
    print(f"reference works: {len(refs):,} people, {len(set(refs) & set(g)):,} in the graph, {len(set(refs) - set(g)):,} outside")
    by_src = Counter()
    by_src_out = Counter()
    for q, srcs in refs.items():
        for s in srcs:
            by_src[s] += 1
            if q not in g:
                by_src_out[s] += 1
    for s, n in by_src.most_common():
        print(f"  {s}: {n:,} ({by_src_out[s]:,} outside)")
    signal = set(refs) | set(vit) | set(tb)
    print(f"fame-only with no reference/vital/textbook signal: {len(fame_only - signal):,}")


# A person's field is the first field, in this order, that any of their occupations falls under, so an
# actor who became a governor counts under politics. A key matches at the start of a word ('botan' finds
# 'botanist', 'count' leaves 'accountant' alone); a key starting with '~' matches anywhere ('~ologist').
FIELDS: list[tuple[str, tuple[str, ...]]] = [
    ("religion", ("priest", "bishop", "archbishop", "theolog", "missionar", "rabbi", "nun", "presbyter", "deacon", "cleric",
                  "monk", "ulema", "muhaddith", "mystic", "pastor", "preacher", "evangelist", "christian minister",
                  "religious", "pope", "cardinal", "abbot", "imam", "friar", "hymn")),
    ("politics and government", ("politician", "governor", "diplomat", "mayor", "ambassador", "statesperson", "civil servant",
                                 "official", "functionary", "minister", "president", "senator", "legislator", "member of parliament",
                                 "head of state", "prime minister", "secretary of state", "public servant")),
    ("royalty and nobility", ("monarch", "ruler", "sovereign", "consort", "aristocrat", "feudatory", "lady-in-waiting",
                              "noble", "samurai", "prince", "king", "queen", "emperor", "duke", "count", "courtier")),
    ("law", ("lawyer", "jurist", "judge", "prosecutor", "attorney", "barrister", "solicitor", "police")),
    ("military", ("military", "soldier", "officer", "general", "admiral", "resistance fighter", "partisan",
                  "freedom fighter", "spy", "guerrilla", "naval", "commander", "mercenary", "privateer")),
    ("activism and reform", ("activist", "suffrag", "feminist", "trade unionist", "revolutionary", "anarchist",
                             "rights", "environmentalist", "social worker", "esperantist", "abolition", "reformer")),
    ("science and medicine", ("physicist", "chemist", "mathematic", "botan", "zoolog", "biolog", "astronom", "physician",
                              "engineer", "inventor", "scientist", "geolog", "entomolog", "ornitholog", "psychiatr",
                              "surgeon", "nurse", "pharmac", "~ologist", "naturalist", "statistician",
                              "astrophysic", "neuroscien", "agronom", "horticultur", "genetic", "biochem", "physiolog",
                              "anatom", "dentist", "pediatric", "meteorolog", "medic", "doctor", "veterinar", "~pterist", "psychoanaly",
                              "psychotherap", "botanical collector", "scientific collector", "zoological collector")),
    ("scholarship and teaching", ("university teacher", "historian", "philosoph", "teacher", "pedagog", "linguist",
                                  "economist", "anthropolog", "sociolog", "archaeolog", "philolog", "literary scholar",
                                  "musicolog", "professor", "academic", "researcher", "scholar", "orientalist", "sinolog",
                                  "egyptolog", "medievalist", "librarian", "archivist", "folklorist", "ethnolog", "ethnograph",
                                  "geographer", "cartograph", "political scientist", "educator", "lecturer", "docent",
                                  "romanist", "lexicograph", "psycholog", "critic", "curator")),
    ("exploration and aviation", ("explorer", "pilot", "aviator", "astronaut", "cosmonaut", "traveler", "flight engineer",
                                  "navigator", "mountaineer")),
    ("business", ("businessperson", "entrepreneur", "banker", "manufacturer", "merchant", "industrialist", "financier",
                  "philanthropist", "restaurateur", "manager", "farmer", "executive", "investor", "trader", "publisher")),
    ("journalism and media", ("journalist", "columnist", "editor", "photojournalist", "correspondent", "commentator",
                              "editing staff", "reporter", "broadcaster")),
    ("literature", ("writer", "poet", "novelist", "playwright", "author", "essayist", "translator", "biographer",
                    "autobiographer", "memoirist", "diarist", "dramatist", "librettist")),
    ("visual arts and architecture", ("painter", "sculptor", "artist", "photographer", "illustrator", "architect", "printmaker",
                                      "draftsperson", "graphic", "designer", "engraver", "etcher", "lithographer",
                                      "watercolorist", "cartoonist", "caricaturist", "comics", "ceramicist", "calligraph",
                                      "muralist", "art", "typograph", "urban planner", "penciller", "patron of the arts")),
    ("music", ("musician", "singer", "composer", "pianist", "guitarist", "conductor", "songwriter", "violinist",
               "drummer", "rapper", "bandleader", "lyricist", "saxophonist", "organist", "trumpeter", "record producer",
               "recording artist", "opera", "music", "cellist", "bassist", "clarinetist", "flautist", "percussionist",
               "keyboardist", "banjoist", "jazz", "blues", "choir", "audio engineer", "disc jockey", "vocalist")),
    ("entertainment", ("actor", "actress", "director", "producer", "screenwriter", "comedian", "model", "presenter",
                       "television", "radio", "voice", "dub", "seiyū", "stunt", "dancer", "choreograph", "circus",
                       "magician", "cabaret", "ziegfeld", "socialite", "beauty pageant", "cinematograph", "film",
                       "animator", "entertainer", "youtuber", "influencer", "camera operator", "costume", "scenograph",
                       "theatre", "performer", "playmate", "showgirl", "pornographic", "dramaturg")),
    ("sports", ("player", "athlete", "coach", "competitor", "cyclist", "boxer", "swimmer", "rower", "gymnast", "wrestler",
                "skier", "skater", "jumper", "racing", "racer", "formula one", "fencer", "sailor", "runner", "sprinter",
                "golfer", "archer", "judoka", "canoeist", "kayaker", "weightlifter", "bobsledder", "referee", "rider",
                "equestrian", "cricketer", "chess", "jockey", "diver", "triathlete", "shooter", "biathlete", "luger",
                "thrower", "hurdler", "decathlete", "pentathlete", "climber", "surfer", "sportsperson", "martial artist",
                "fighter", "skipper", "coxswain", "driver", "darts", "snooker", "bowler", "umpire")),
    ("crime", ("serial killer", "criminal", "murderer", "gangster", "outlaw", "pirate", "bandit", "terrorist", "assassin")),
]


def _key(k: str) -> re.Pattern:
    return re.compile(re.escape(k[1:]) if k.startswith("~") else r"\b" + re.escape(k))


_FIELD_RES = [(f, [_key(k) for k in keys]) for f, keys in FIELDS]


def field_of(occs: list[str]) -> str:
    low = [o.lower() for o in occs]
    for field, pats in _FIELD_RES:
        if any(p.search(o) for o in low for p in pats):
            return field
    return "other" if occs else "no occupation recorded"


def occupations(qids: set[str]) -> dict[str, list[str]]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    out: dict[str, list[str]] = defaultdict(list)
    for src, name in con.execute("""SELECT x.src, e.name FROM h_edges x JOIN h_entities e ON e.qid = x.dst
                                    WHERE x.rel = 'occupation'"""):
        if src in qids:
            out[src].append(name)
    con.close()
    return out


def top_occupations() -> None:
    g = graph_people()
    refs, vit, tb = references(), vital(), textbooks()
    fame_only = {q for q, p in g.items() if p["reasons"] and p["reasons"] <= FAME} - set(refs) - set(vit) - set(tb)
    occ = occupations(fame_only)
    c = Counter(o for q in fame_only for o in set(occ.get(q, [])))
    print("no occupation:", sum(1 for q in fame_only if q not in occ))
    for o, n in c.most_common(400):
        print(f"{n}\t{o}")


OUTSIDE = "outsiders"  # harvest folder for people outside the graph who hold a signal
OUTSIDE_PROPS = {"P27": "citizenship", "P106": "occupation", "P39": "position held", "P19": "birthplace"}


def honor_holders() -> dict[str, set[str]]:
    """qid -> the honors held, from the honors harvest (select/honors2_<award>.tsv)."""
    out: dict[str, set[str]] = defaultdict(set)
    for f in sorted((H.OUT / "select").glob("honors2_*.tsv")):
        award = f.stem.split("_", 1)[1]
        for r in H.read(f):
            if r:
                out[H.qid(r[0])].add(award)
    return out


def outsiders() -> list[str]:
    g = graph_people()
    ids = set(references()) | set(vital()) | set(honor_holders())
    return sorted(ids - set(g))


def fetch_tolerant(kind: str, prefix: str, ids, query_for, chunk: int = 2000, qlever: bool = True) -> None:
    """H.fetch, and when QLever can't finish a batch (it times out on its own internal sort when busy, even
    on a few hundred ids), the ids still uncovered go to Wikidata's own query service in small batches."""
    if qlever:
        try:
            H.fetch(kind, prefix, ids, query_for)
            return
        except H.QueryFailed as e:
            print(f"  QLever gave up on {e}; the rest go to WDQS", flush=True)
    man = H.manifest(kind)
    done = {q for name, c in man.items() if re.match(rf"{re.escape(prefix)}_\d+[a-z]*\.tsv$", name)
            and (H.OUT / kind / name).exists() for q in c}
    todo = sorted(set(ids) - done)
    for i in range(0, len(todo), chunk):
        name = f"{prefix}_{900 + i // chunk:03d}.tsv"
        man[name] = todo[i:i + chunk]
        H.save_manifest(kind, man)
        H.run(query_for(todo[i:i + chunk]), H.OUT / kind / name, endpoint=H.WDQS)
        print(f"  {kind}/{prefix} via WDQS: {min(i + chunk, len(todo)):,} of {len(todo):,}", flush=True)


def details() -> None:
    """Names, dates, citizenship, and occupations of the signal holders outside the graph."""
    ids = outsiders()
    print(f"outsiders: {len(ids):,}", flush=True)
    H.fetch(OUTSIDE, "core", ids, lambda c: f"""SELECT ?x ?s ?label ?desc ?enwiki WHERE {{ {H.values(c)} ?x wikibase:sitelinks ?s .
        OPTIONAL {{ ?x rdfs:label ?label . FILTER(LANG(?label) = "en") }}
        OPTIONAL {{ ?x schema:description ?desc . FILTER(LANG(?desc) = "en") }}
        OPTIONAL {{ ?a schema:about ?x ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?enwiki }} }}""")
    H.fetch(OUTSIDE, "mul", ids, lambda c: f"""SELECT ?x ?mul WHERE {{ {H.values(c)} ?x rdfs:label ?mul . FILTER(LANG(?mul) = "mul") }}""")
    H.dated(OUTSIDE, H.DATES, ids, ["P569", "P570"])
    # the death signal and the active years, as two plain queries: WDQS evaluates a UNION before the id list
    # and times out, and QLever times out on its own sort when busy (both seen 2026-10-26)
    covered = {q for name, c in H.manifest(OUTSIDE).items() if name.startswith(H.SIGNALS + "_")
               and (H.OUT / OUTSIDE / name).exists() for q in c}
    need = [q for q in ids if q not in covered]
    print(f"outsiders: {len(need):,} still without the death signal", flush=True)
    fetch_tolerant(OUTSIDE, "signals3d", need, qlever=True, chunk=500, query_for=lambda c: f"""SELECT ?x ?kind WHERE {{
        {H.values(c)} ?x p:P570 ?st . {H.RANKED} BIND("death" AS ?kind) }}""")
    fetch_tolerant(OUTSIDE, "signals3w", need, qlever=True, chunk=500, query_for=lambda c: f"""SELECT ?x ?kind ?t WHERE {{
        {H.values(c)} VALUES (?prop ?kind) {{ (wdt:P1317 "floruit") (wdt:P2031 "work") (wdt:P2032 "work") }} ?x ?prop ?t }}""")
    pv = " ".join(f"wdt:{k}" for k in OUTSIDE_PROPS)
    fetch_tolerant(OUTSIDE, "claims", ids, lambda c: f"""SELECT ?x ?prop ?o WHERE {{ {H.values(c)} VALUES ?prop {{ {pv} }} ?x ?prop ?o }}""")
    # names of the occupations and countries those claims point at that no earlier harvest named
    have = {H.qid(r[0]) for f in H.files("labels", "core") for r in H.read(f) if r}
    have |= {H.qid(r[0]) for f in H.files("places", "core") for r in H.read(f) if r}
    want = sorted({H.qid(o) for s, p, o in H.claim_rows(OUTSIDE, "claims") if p in ("P106", "P27")
                   and o.startswith("<http://www.wikidata.org/entity/Q")} - have)
    print(f"outsiders: {len(want):,} occupation and country labels to fetch", flush=True)
    H.fetch(OUTSIDE, "labels", want, lambda c: f"""SELECT ?x ?label ?mul WHERE {{ {H.values(c)}
        OPTIONAL {{ ?x rdfs:label ?label . FILTER(LANG(?label) = "en") }}
        OPTIONAL {{ ?x rdfs:label ?mul . FILTER(LANG(?mul) = "mul") }} }}""")


# ---- the two review lists ------------------------------------------------------------------------
# Reference works fall in two groups: the modern national biographies and Britannica, edited to a standard
# of lasting significance, and the encyclopedias and national biographies of the 19th and early 20th
# centuries, which record the notables of their own day.
HISTORIC_REFS = set(H.DESCRIBED_BY.values())
MODERN_REFS = set(H.REFERENCE_IDS.values())


def _names(*pairs) -> dict[str, str]:
    """qid -> name from (kind, prefix, label column, mul prefix) harvest files: English, else multilingual."""
    out: dict[str, str] = {}
    for kind, prefix, col in pairs:
        for f in H.files(kind, prefix):
            for r in H.read(f):
                if len(r) > col and H.lit(r[col]).strip() and H.qid(r[0]) not in out:
                    out[H.qid(r[0])] = H.lit(r[col])
    return out


def outsider_rows() -> dict[str, dict]:
    """Outsiders with name, description, sitelinks, dates, living status, citizenship, and occupations."""
    core = {}
    for f in H.files(OUTSIDE, "core"):
        for r in H.read(f):
            if r:
                r = r + [""] * (5 - len(r))
                core[H.qid(r[0])] = {"s": int(H.lit(r[1]) or 0), "label": H.lit(r[2]), "desc": H.lit(r[3]), "enwiki": H.lit(r[4])}
    mul = _names((OUTSIDE, "mul", 1))
    rows = [r for f in H.files(OUTSIDE, H.DATES) for r in H.read(f)]
    prec = {(H.qid(r[0]), H.qid(r[1]), H.lit(r[2])): int(H.lit(r[3]) or 0) for r in rows if len(r) >= 4}
    born, died, dead, active = {}, {}, set(), {}
    for (q, prop), t in H.best_by_rank(rows).items():
        y = H.earliest_year(t, prec.get((q, prop, t), 9))
        if prop == "P570":
            dead.add(q)
            died[q] = H.year(t)
        elif prop == "P569" and y is not None:
            born[q] = y
    for f in H.files(OUTSIDE, H.SIGNALS) + H.files(OUTSIDE, "signals3d") + H.files(OUTSIDE, "signals3w"):
        for r in H.read(f):
            if len(r) >= 2 and H.lit(r[1]) == "death":
                dead.add(H.qid(r[0]))
            elif len(r) >= 3 and (y := H.year(r[2])) is not None:
                active[H.qid(r[0])] = max(active.get(H.qid(r[0]), y), y)
    labels = _names(("labels", "core", 1), ("labels", "mul", 1), (OUTSIDE, "labels", 1), (OUTSIDE, "labels", 2),
                    ("places", "core", 2), ("places", "mul", 1))
    occ, us, offices = defaultdict(list), set(), defaultdict(list)
    for s, p, o in H.claim_rows(OUTSIDE, "claims"):
        if p == "P106":
            occ[s].append(labels.get(H.qid(o), ""))
        elif p == "P27" and H.qid(o) == "Q30":
            us.add(s)
        elif p == "P39":
            offices[s].append(H.qid(o))
    out = {}
    for q, c in core.items():
        if q in dead:
            living = False
        elif q in born:
            living = born[q] >= 1900
        elif q in active:
            living = active[q] >= 1900
        else:
            living = True
        out[q] = {"name": c["label"] or mul.get(q) or c["enwiki"] or q, "desc": c["desc"], "s": c["s"],
                  "born": born.get(q), "died": died.get(q), "living": living, "us": q in us,
                  "occs": [o for o in occ.get(q, []) if o], "offices": len(offices.get(q, []))}
    return out


def graph_extra(qids: set[str]) -> tuple[dict[str, list[str]], set[str]]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    us = {s for (s,) in con.execute("SELECT src FROM h_edges WHERE rel = 'citizen_of' AND dst = 'Q30'") if s in qids}
    con.close()
    return occupations(qids), us


def honor_catalog() -> dict[str, tuple[str, str]]:
    """award qid -> (name, standing) from the candidate list: 'current' (the reviewed list, 59 honors, the nine
    'decide' ones approved 2026-10-23), 'recommended' (new candidates the 2026-10-26 research recommends in,
    not yet approved), or 'decide'."""
    out = {}
    for r in csv.DictReader((H.CURATION / "honors_candidates.csv").open(encoding="utf-8")):
        standing = "current" if "existing" in r["notes"] else "recommended" if r["recommend"] == "in" else r["recommend"]
        out[r["qid"]] = (r["award"], standing)
    return out


HONOR_COLS = {"current": "honors", "recommended": "honors_recommended", "decide": "honors_to_decide"}


def _signals(q, refs, vit, tb, hon) -> dict[str, str]:
    r = refs.get(q, {})
    cat = honor_catalog.cache if hasattr(honor_catalog, "cache") else honor_catalog()
    honor_catalog.cache = cat
    held = [cat.get(a, (a, "current")) for a in hon.get(q, ())]
    return {"refs_modern": "; ".join(sorted(s for s in r if s in MODERN_REFS)),
            "refs_historic": "; ".join(sorted(s for s in r if s in HISTORIC_REFS)),
            "vital": str(vit[q][0]) if q in vit else "", "textbook": "; ".join(sorted(tb.get(q, ()))),
            **{col: "; ".join(sorted(n for n, st in held if st == standing)) for standing, col in HONOR_COLS.items()}}


def _year(y) -> str:
    return "" if y is None else (f"{-y} BC" if y < 0 else str(y))


def lists() -> None:
    REVIEW.mkdir(parents=True, exist_ok=True)
    g = graph_people()
    refs, vit, tb, hon = references(), vital(), textbooks(), honor_holders()

    fame_only = {q for q, p in g.items() if p["reasons"] and p["reasons"] <= FAME}
    occ, us = graph_extra(fame_only)
    cols = ["qid", "name", "description", "sitelinks", "field", "occupations", "us", "living", "born", "died", "fame",
            "refs_modern", "refs_historic", "vital", "textbook", "honors", "honors_recommended", "honors_to_decide"]
    with (REVIEW / "fame_only.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        for q in sorted(fame_only, key=lambda q: -g[q]["s"]):
            p = g[q]
            w.writerow({"qid": q, "name": p["name"], "description": p["desc"], "sitelinks": p["s"],
                        "field": field_of(occ.get(q, [])), "occupations": "; ".join(occ.get(q, [])[:4]),
                        "us": "yes" if q in us else "", "living": "yes" if p["living"] else "",
                        "born": _year(p["born"]), "died": _year(p["died"]),
                        "fame": "; ".join(sorted(p["reasons"])), **_signals(q, refs, vit, tb, hon)})
    print(f"wrote fame_only.csv: {len(fame_only):,} people")

    excluded = H.excluded_people()   # the reviewed exclusion list holds outside the graph too
    out = {q: p for q, p in outsider_rows().items() if q not in excluded}
    cols = ["qid", "name", "description", "sitelinks", "field", "occupations", "us", "living", "born", "died",
            "offices_held", "refs_modern", "refs_historic", "vital", "honors", "honors_recommended", "honors_to_decide"]
    with (REVIEW / "outside_with_signal.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        for q in sorted(out, key=lambda q: -out[q]["s"]):
            p = out[q]
            sig = _signals(q, refs, vit, tb, hon)
            sig.pop("textbook")
            w.writerow({"qid": q, "name": p["name"], "description": p["desc"], "sitelinks": p["s"],
                        "field": field_of(p["occs"]), "occupations": "; ".join(p["occs"][:4]),
                        "us": "yes" if p["us"] else "", "living": "yes" if p["living"] else "",
                        "born": _year(p["born"]), "died": _year(p["died"]), "offices_held": p["offices"] or "", **sig})
    print(f"wrote outside_with_signal.csv: {len(out):,} people")


def _split(v: str) -> list[str]:
    return [x.strip() for x in v.split(";") if x.strip()]


def _died(r) -> int | None:
    d = r["died"]
    return None if not d else (-int(d[:-3]) if d.endswith(" BC") else int(d))


def stats() -> None:
    """Counts for the review document, from the two CSVs."""
    fo = list(csv.DictReader((REVIEW / "fame_only.csv").open(encoding="utf-8")))
    ow = list(csv.DictReader((REVIEW / "outside_with_signal.csv").open(encoding="utf-8")))
    # strong: a modern reference, Vital Articles, a textbook, or an honor on the current list or recommended by the research
    base = lambda r: bool(r["refs_modern"] or r["vital"] or r["textbook"] or r["honors"])
    strong = lambda r: base(r) or bool(r["honors_recommended"])
    anysig = lambda r: strong(r) or bool(r["refs_historic"])
    proposed = lambda r: bool(r["honors_to_decide"])

    # ---- drop side
    print(f"FAME ONLY {len(fo):,}; strong signal with the current honors only {sum(base(r) for r in fo):,}, with the recommended honors too {sum(strong(r) for r in fo):,}")
    print(f"  strong signal {sum(strong(r) for r in fo):,}; only a 19th-century reference "
          f"{sum(anysig(r) and not strong(r) for r in fo):,}; no signal {sum(not anysig(r) for r in fo):,}; "
          f"no signal but a to-decide honor {sum(not anysig(r) and proposed(r) for r in fo):,}")
    for name, key in (("modern reference", "refs_modern"), ("19th-century reference", "refs_historic"),
                      ("Vital Articles", "vital"), ("textbook", "textbook"), ("current honor", "honors"),
                      ("recommended honor", "honors_recommended")):
        keys = ("refs_modern", "refs_historic", "vital", "textbook", "honors", "honors_recommended")
        only = sum(1 for r in fo if r[key] and sum(bool(r[k]) for k in keys) == 1)
        print(f"  {name}: {sum(bool(r[key]) for r in fo):,} (the only signal for {only:,})")
    by = defaultdict(lambda: [0, 0, 0, 0])
    for r in fo:
        b = by[r["field"]]
        b[0] += 1
        b[1] += not strong(r)
        b[2] += not anysig(r)
        b[3] += not anysig(r) and proposed(r)
    print("  field | fame-only | no strong signal | no signal at all | of those, a to-decide honor")
    for f, (a, b, c, d) in sorted(by.items(), key=lambda x: -x[1][1]):
        print(f"  {f} | {a:,} | {b:,} ({100 * b // max(a, 1)}%) | {c:,} | {d:,}")
    tier = Counter()
    for r in fo:
        if not strong(r):
            reasons = set(_split(r["fame"]))
            tier["Illinois-born" if "fame_illinois" in reasons else "American" if "fame_us" in reasons else
                 "world 20+" if "fame_world20" in reasons else "world 10+"] += 1
    print("  no strong signal by fame tier:", dict(tier))
    bands = Counter()
    for r in fo:
        if not strong(r):
            s = int(r["sitelinks"])
            bands["40+" if s >= 40 else "20-39" if s >= 20 else "10-19" if s >= 10 else "5-9" if s >= 5 else "3-4"] += 1
    print("  no strong signal by Wikipedia editions:", dict(bands))
    print("  most famous with no strong signal, by field:")
    for f in sorted(by, key=lambda x: -by[x][1]):
        top = [r for r in fo if r["field"] == f and not strong(r)][:10]
        print(f"    {f}: " + "; ".join(f"{r['name']} ({r['sitelinks']})" for r in top))
    print("  honors that confirm fame-only people (current | recommended | to decide):")
    hc = Counter(h for r in fo for h in _split(r["honors"]))
    hr = Counter(h for r in fo for h in _split(r["honors_recommended"]))
    hd = Counter(h for r in fo for h in _split(r["honors_to_decide"]))
    sole = Counter(_split(r["honors_to_decide"])[0] for r in fo if not anysig(r) and len(_split(r["honors_to_decide"])) == 1)
    print("    current: " + "; ".join(f"{h} {n:,}" for h, n in hc.most_common(25)))
    print("    recommended: " + "; ".join(f"{h} {n:,}" for h, n in hr.most_common(25)))
    print("    to decide: " + "; ".join(f"{h} {n:,} (sole {sole.get(h, 0):,})" for h, n in hd.most_common(30)))

    # ---- add side (living people stay out under the living-people rule, so they're counted apart)
    hist = [r for r in ow if not r["living"]]
    print(f"\nOUTSIDE WITH SIGNAL {len(ow):,}: historical {len(hist):,}; living {len(ow) - len(hist):,}")
    nsrc = lambda r: (len(_split(r["refs_modern"])) + len(_split(r["refs_historic"])) + bool(r["vital"])
                      + len(_split(r["honors"])) + len(_split(r["honors_recommended"])))
    era = lambda r: "pre-1400" if (_died(r) is not None and _died(r) < 1400) else "1400+"
    c = Counter((era(r), min(nsrc(r), 3)) for r in hist)
    print("  by era and number of sources (3 = 3+):", {f"{k[0]} {k[1]}": f"{v:,}" for k, v in sorted(c.items())})
    print(f"  no Wikipedia article in any language: {sum(int(r['sitelinks']) == 0 for r in hist):,}")
    src = defaultdict(list)
    for r in hist:
        for key in ("refs_modern", "refs_historic"):
            for s in _split(r[key]):
                src[s].append(r)
        if r["vital"]:
            src["Vital Articles"].append(r)
        for h in _split(r["honors"]):
            src[f"honor (current): {h}"].append(r)
        for h in _split(r["honors_recommended"]):
            src[f"honor (recommended): {h}"].append(r)
        for h in _split(r["honors_to_decide"]):
            src[f"honor (to decide): {h}"].append(r)
    print("  source | historical outside | 1400+ | U.S. | with a Wikipedia article | only this source | top fields")
    for s, rs in sorted(src.items(), key=lambda x: -len(x[1])):
        late = [r for r in rs if era(r) == "1400+"]
        fields = Counter(r["field"] for r in rs).most_common(3)
        print(f"  {s} | {len(rs):,} | {len(late):,} | {sum(bool(r['us']) for r in rs):,} | "
              f"{sum(int(r['sitelinks']) > 0 for r in rs):,} | {sum(nsrc(r) == 1 for r in rs):,} | "
              + ", ".join(f"{k} {v:,}" for k, v in fields))
        top = rs[:5] + [r for r in rs if 1 <= int(r["sitelinks"]) <= 3][:3]
        print("     e.g. " + "; ".join(f"{r['name']} ({r['born'] or '?'}-{r['died'] or '?'}; {r['sitelinks']}; {r['description'][:40]})" for r in top))

    # ---- scenarios for the add side
    def count(rule):
        return sum(1 for r in hist if rule(r))
    us_refs = {"American National Biography", "Biographical Directory of Federal Judges",
               "Appletons' Cyclopædia of American Biography"}
    print("\n  SCENARIOS (historical people added)")
    print(f"    American National Biography + Federal Judges + Vital + current and recommended honors: "
          f"{count(lambda r: bool(set(_split(r['refs_modern'])) & us_refs or r['vital'] or r['honors'] or r['honors_recommended'])):,}")
    print(f"    ... plus Appletons' (1887-89): "
          f"{count(lambda r: bool((set(_split(r['refs_modern'])) | set(_split(r['refs_historic']))) & us_refs or r['vital'] or r['honors'] or r['honors_recommended'])):,}")
    print(f"    any modern reference with a Wikipedia article, died 1400+: "
          f"{count(lambda r: bool(r['refs_modern']) and int(r['sitelinks']) > 0 and era(r) == '1400+'):,}")
    print(f"    two or more sources, died 1400+: {count(lambda r: nsrc(r) >= 2 and era(r) == '1400+'):,}")
    print(f"    three or more sources, any era: {count(lambda r: nsrc(r) >= 3):,}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"measure": measure, "occ": top_occupations, "details": details, "lists": lists,
     "stats": stats}[sys.argv[1] if len(sys.argv) > 1 else "measure"]()
