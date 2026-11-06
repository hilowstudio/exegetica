"""Harvest the history people-and-events graph from Wikidata (CC0) into .seed_cache/socialsci/wikidata/.

Rules (docs/sources/history-graph-design.md, decided 2026-10-20):
  people  fame tiers: born in Illinois with 3+ Wikipedia articles, Americans 5+, everyone else 10+,
          20+ for anyone who died before 1400; plus anyone (with at least one article) who held an
          office in scope, signed a notable document, or took part in a conflict, a political event,
          an expedition, a reform movement, or a church council in the graph. Living people only if
          they hold an office in scope or have a historic public role (civil-rights leaders,
          astronauts, Nobel laureates, military commanders, church leaders).
  events  the categories in CATEGORIES, each with a fame bar for the world, the United States, and
          Illinois; inventions and discoveries by their inventor or date of invention.

Dates and office terms leave out deprecated statements (values Wikidata keeps on an item but marks wrong,
such as a misprinted death date copied from one encyclopedia), and carry each statement's rank, calendar,
and number of references. The export gives every day-precise Julian date in the Gregorian calendar
(Shakespeare's death, entered as 23 April 1616, comes out as 1616-05-03); the builder turns it back.

Queries go to the QLever Wikidata endpoint (qlever.dev), one at a time and paced. QLever returns
nothing when a sitelinks filter meets a join, so the count is cast: FILTER(xsd:integer(?s) >= n).
Every result is saved as a TSV, and _manifest.json in each folder records which ids each file
covers, so a widened scope fetches only the ids not yet fetched. A batch the endpoint can't finish
is split in half and retried.

    .venv/Scripts/python.exe scripts/socialsci/harvest_wikidata.py [select|people|events|places|labels ...]
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".seed_cache" / "socialsci" / "wikidata"
EP = "https://qlever.dev/api/wikidata"
WDQS = "https://query.wikidata.org/sparql"  # the official service: quick for lookups by exact label, which QLever must sort for
UA = "YorkvilleChristianSchool-HistoryResearch/1.0 (one-time archival harvest for classroom use)"
BATCH = 25000  # ids per VALUES query; QLever rate-limits by request count, so fewer, larger queries

PFX = """PREFIX wd: <http://www.wikidata.org/entity/> PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/> PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/> PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX pqv: <http://www.wikidata.org/prop/qualifier/value/>
PREFIX wikibase: <http://wikiba.se/ontology#> PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> PREFIX prov: <http://www.w3.org/ns/prov#>
"""
# a statement ?st that isn't deprecated, with its rank. QLever returns no rows at all for
# FILTER(?rank != wikibase:DeprecatedRank), so the ranks we keep are listed instead.
RANKED = "VALUES ?rank { wikibase:PreferredRank wikibase:NormalRank } ?st wikibase:rank ?rank ."

# ---- scope (every id checked against its English label, 2026-10-20) --------------------------------
LIVING_ROLES = {  # occupations that count as a historic public role for a living person
    "Q1021386": "civil rights advocate", "Q1476215": "human rights defender", "Q11631": "astronaut",
    "Q83460": "general", "Q132851": "admiral", "Q977459": "flag officer", "Q11545923": "military commander",
    "Q1402561": "military leader", "Q15995642": "religious leader", "Q152002": "pastor", "Q29182": "bishop",
    "Q45722": "cardinal", "Q1381391": "evangelist", "Q1423891": "Christian minister", "Q432386": "preacher",
}

# Event categories. world / us: the fewest Wikipedia language editions an item needs; anything located in
# Illinois needs only one. always: every item, whatever its fame. people: taking part in one of these
# events brings a person into the graph.
CATEGORIES: dict[str, dict] = {
    "conflict": {"people": True, "world": 5, "us": 2, "classes": {
        "Q198": "war", "Q178561": "battle", "Q188055": "siege", "Q831663": "military campaign",
        "Q645883": "military operation", "Q10931": "revolution", "Q124734": "rebellion", "Q45382": "coup d'état",
        "Q3199915": "massacre", "Q41397": "genocide", "Q3882219": "assassination", "Q2223653": "terrorist attack",
        "Q3002772": "political crisis", "Q107706": "armistice"}},
    "law and government": {"people": True, "world": 5, "us": 2, "classes": {
        "Q131569": "treaty", "Q49371": "legislation", "Q7755": "constitution", "Q727002": "charter",
        "Q1464916": "declaration of independence", "Q267995": "constitutional convention",
        "Q934744": "political scandal", "Q8016240": "trial", "Q18564543": "international conference",
        "Q7157512": "peace conference", "Q1072326": "summit", "Q2620826": "declaration"}},
    "U.S. law": {"people": True, "world": 1, "us": 1, "classes": {
        "Q476068": "Act of Congress", "Q102410240": "constitutional amendment", "Q1338798": "executive order",
        "Q7241458": "presidential proclamation", "Q85811481": "presidential impeachment"}},
    "elections": {"people": False, "world": 10, "us": 2, "classes": {"Q40231": "election", "Q43109": "referendum"}},
    "speeches and texts": {"people": False, "world": 5, "us": 2, "classes": {
        "Q861911": "speech", "Q28472638": "inaugural address", "Q60797": "sermon", "Q46337": "manifesto",
        "Q646754": "open letter", "Q1572600": "proclamation", "Q1284645": "edict", "Q2101619": "political slogan"}},
    "exploration": {"people": True, "world": 5, "us": 2, "classes": {
        "Q2401485": "expedition", "Q752783": "human spaceflight", "Q5916": "spaceflight", "Q26529": "space probe",
        "Q3533809": "circumnavigation", "Q1194369": "first ascent"}},
    "disasters": {"people": False, "world": 10, "us": 3, "classes": {
        "Q3839081": "disaster", "Q7944": "earthquake", "Q8092": "tropical cyclone", "Q8068": "flood",
        "Q7692360": "volcanic eruption", "Q168983": "conflagration", "Q168247": "famine", "Q12184": "pandemic",
        "Q3241045": "disease outbreak", "Q906512": "shipwreck", "Q744913": "aviation accident",
        "Q1078765": "railway accident", "Q1550225": "mining accident", "Q68800046": "industrial disaster",
        "Q15725976": "nuclear disaster", "Q3193890": "environmental disaster", "Q179057": "explosion"}},
    "society": {"people": True, "world": 5, "us": 2, "classes": {
        "Q49773": "social movement", "Q49776": "strike", "Q273120": "protest", "Q175331": "demonstration",
        "Q15631336": "protest march", "Q179366": "boycott", "Q124757": "riot", "Q177626": "migration",
        "Q837556": "forced displacement", "Q273182": "gold rush", "Q172754": "world's fair",
        "Q25929224": "transfer of sovereignty"}},
    "economy": {"people": False, "world": 5, "us": 2, "classes": {
        "Q114380": "financial crisis", "Q290178": "economic crisis", "Q176494": "recession"}},
    "eras": {"people": False, "world": 10, "us": 2, "classes": {
        "Q11514315": "historical period", "Q6428674": "era", "Q17522177": "age", "Q2198855": "cultural movement"}},
    "church": {"people": True, "world": 3, "us": 2, "classes": {
        "Q51645": "ecumenical council", "Q111161": "synod", "Q835439": "Great Awakening", "Q41521": "schism",
        "Q554482": "persecution of Christians", "Q7311395": "religious revival", "Q669970": "Imperial Diet"}},
    "olympics": {"people": False, "always": True, "classes": {
        "Q135976384": "Summer Olympics", "Q137592217": "Winter Olympics"}},
    "court": {"people": False, "always": True, "classes": {"Q19692072": "Supreme Court decision"}},
    "presidential elections": {"people": False, "always": True, "classes": {"Q47566": "U.S. presidential election"}},
}
INVENTIONS = {"people": False, "world": 10, "us": 5}  # selected by inventor (P61) or date of invention (P575)
EXCLUDE_FROM_INVENTIONS = {"Q6999": "astronomical object", "Q16521": "taxon", "Q7187": "gene", "Q8054": "protein",
                           "Q5": "human"}
EVENT_CLASSES = {q: label for c in CATEGORIES.values() for q, label in c["classes"].items()}

# ---- significance (2026-10-21): fame counts attention; these record editors' and historians' judgment -------
REFERENCE_IDS = {  # an entry in a curated reference work
    "P4823": "American National Biography", "P1415": "Oxford Dictionary of National Biography",
    "P1417": "Encyclopædia Britannica", "P11762": "Britannica Kids (kids)", "P11764": "Britannica Kids (students)",
    "P11765": "Britannica Kids (scholars)", "P2753": "Dictionary of Canadian Biography",
    "P1907": "Australian Dictionary of Biography", "P2745": "Dictionary of New Zealand Biography",
    "P6829": "Dictionary of Irish Biography", "P1648": "Dictionary of Welsh Biography",
    "P1986": "Dizionario Biografico degli Italiani", "P4459": "Diccionario Biográfico Español",
    "P3217": "Svenskt biografiskt lexikon", "P6234": "Biographie nationale de Belgique",
    "P6194": "Österreichisches Biographisches Lexikon", "P1563": "MacTutor History of Mathematics",
    "P9626": "Biographical Encyclopedia of Astronomers", "P10704": "Biographical Memoirs of Fellows of the Royal Society",
    "P2030": "NASA biographies", "P2736": "Biographical Directory of Federal Judges",
    "P9564": "Biographical Dictionary of Chinese Christianity", "P13345": "Biographical Dictionary of Republican China",
}
DESCRIBED_BY = {  # 'described by source' (P1343): national biographies and the encyclopedias of their day
    "Q15987216": "Dictionary of National Biography (1885-1900)", "Q590208": "Allgemeine Deutsche Biographie",
    "Q12912667": "Appletons' Cyclopædia of American Biography", "Q1485141": "Polish Biographical Dictionary",
    "Q1960551": "Russian Biographical Dictionary", "Q665807": "Biographisches Lexikon des Kaiserthums Oesterreich",
    "Q867541": "Encyclopædia Britannica, 11th edition", "Q602358": "Brockhaus and Efron Encyclopedic Dictionary",
    "Q3181656": "The Nuttall Encyclopædia", "Q1029706": "New International Encyclopedia",
    "Q19219752": "Meyers Konversations-Lexikon", "Q678259": "Nordisk familjebok", "Q1138524": "Pauly-Wissowa",
    "Q27680201": "Riemann's Music Dictionary", "Q16055052": "A Naval Biographical Dictionary",
    "Q19098835": "Library of the World's Best Literature", "Q105802405": "Dictionary of Women Worldwide",
}

PERSON_PROPS = {  # simple claims kept for each person
    "P27": "citizenship", "P106": "occupation", "P102": "party", "P140": "religion", "P241": "military branch",
    "P69": "educated at", "P22": "father", "P25": "mother", "P26": "spouse", "P40": "child", "P3373": "sibling",
    "P737": "influenced by", "P1066": "student of", "P802": "student", "P1344": "participant in",
    "P607": "conflict", "P166": "award", "P19": "birthplace", "P20": "deathplace", "P1157": "bioguide",
}
EVENT_PROPS = {
    "P31": "instance of", "P276": "location", "P17": "country", "P361": "part of", "P155": "follows",
    "P156": "followed by", "P828": "has cause", "P1542": "has effect", "P710": "participant",
    "P1891": "signatory", "P625": "coordinates", "P1031": "legal citation", "P61": "inventor or discoverer",
    "P823": "speaker", "P50": "author", "P170": "creator", "P991": "successful candidate", "P1346": "winner",
}
EVENT_DATES = ["P580", "P582", "P585", "P571", "P577", "P575", "P619", "P620", "P1619", "P576"]
PLACE_PROPS = {"P31": "instance of", "P17": "country", "P131": "located in", "P625": "coordinates"}

HUMAN_SL = "?p wdt:P31 wd:Q5 ; wikibase:sitelinks ?s ."


def sl(n: int) -> str:
    return f"FILTER(xsd:integer(?s) >= {n})"


def vq(ids) -> str:
    return " ".join("wd:" + q for q in ids)


OFFICE_POSITIONS = f"""
  {{ ?pos wdt:P1001 wd:Q30 }}                                  # U.S. federal offices
  UNION {{ ?pos wdt:P1001 wd:Q1204 }}                          # Illinois offices
  UNION {{ VALUES ?pos {{ wd:Q11144 wd:Q11147 wd:Q11696 wd:Q19546 }} }}   # justices, president, pope
  UNION {{ ?pos wdt:P279* wd:Q132050 ; wdt:P1001 ?st . ?st wdt:P31 wd:Q35657 }}   # state governors
  UNION {{ VALUES ?head {{ wd:Q48352 wd:Q2285706 }} ?pos wdt:P279* ?head ; wdt:P1001 ?c .
           VALUES ?ct {{ wd:Q6256 wd:Q3624078 wd:Q3024240 }} ?c wdt:P31 ?ct }}     # national heads
  UNION {{ ?pos wdt:P279* wd:Q116 }}                           # monarchs
"""

FLAGS = f"""
  OPTIONAL {{ ?e wdt:P17 wd:Q30 . BIND(1 AS ?us) }}
  OPTIONAL {{ ?e wdt:P276/wdt:P131* wd:Q1204 . BIND(1 AS ?il) }}
  OPTIONAL {{ VALUES ?dp {{ {' '.join('wdt:' + p for p in EVENT_DATES)} }} ?e ?dp ?dv . BIND(1 AS ?dated) }}"""


def category_query(cat: dict) -> str:
    floor = "" if cat.get("always") else "FILTER(xsd:integer(?s) >= 1)"
    return f"""SELECT DISTINCT ?e ?s ?us ?il ?dated WHERE {{
  VALUES ?c {{ {vq(cat['classes'])} }}
  ?e wdt:P31/wdt:P279* ?c ; wikibase:sitelinks ?s . {floor} {FLAGS}
}}"""


INVENTION_QUERY = f"""SELECT DISTINCT ?e ?s ?us ?il ?dated WHERE {{
  {{ ?e wdt:P61 ?who }} UNION {{ ?e wdt:P575 ?when }}
  ?e wikibase:sitelinks ?s . FILTER(xsd:integer(?s) >= 3)
  FILTER NOT EXISTS {{ ?e wdt:P31/wdt:P279* wd:Q6999 }}
  FILTER NOT EXISTS {{ VALUES ?no {{ wd:Q16521 wd:Q7187 wd:Q8054 wd:Q5 }} ?e wdt:P31 ?no }} {FLAGS}
}}"""

PARTICIPATION = sorted({q for c in CATEGORIES.values() if c["people"] for q in c["classes"]})

SELECT = {  # name -> query; people queries return ?p ?s, event queries ?e ?s and flags
    "fame_illinois": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(3)} ?p wdt:P19/wdt:P131* wd:Q1204 }}",
    "fame_us": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(5)} {{ ?p wdt:P27 wd:Q30 }} UNION {{ ?p wdt:P19/wdt:P17 wd:Q30 }} }}",
    "fame_world10": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(10)} FILTER NOT EXISTS {{ ?p wdt:P570 ?d . FILTER(YEAR(?d) < 1400) }} }}",
    "fame_world20": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(20)} }}",
    "role_office": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(1)} ?p wdt:P39 ?pos . {OFFICE_POSITIONS} }}",
    "role_signatory": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(1)} ?doc wdt:P1891 ?p ; wikibase:sitelinks ?ds . FILTER(xsd:integer(?ds) >= 3) }}",
    "role_living2": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(1)} VALUES ?o {{ {vq(LIVING_ROLES)} }} ?p wdt:P106 ?o }}",
    "role_nobel": f"SELECT DISTINCT ?p ?s WHERE {{ {HUMAN_SL} {sl(1)} ?p wdt:P166 ?aw . ?aw wdt:P279* wd:Q7191 }}",
    # taking part in an event, filtered to the selected events of the people-bearing categories locally
    "role_participant2": f"""SELECT DISTINCT ?p ?s ?e WHERE {{ {HUMAN_SL} {sl(1)}
        VALUES ?c {{ {vq(PARTICIPATION)} }} ?e wdt:P31/wdt:P279* ?c .
        {{ ?e wdt:P710 ?p }} UNION {{ ?p wdt:P1344 ?e }} UNION {{ ?p wdt:P607 ?e }} }}""",
    **{f"ev_{name.replace(' ', '_').replace('.', '')}": category_query(c) for name, c in CATEGORIES.items()},
    "ev_inventions": INVENTION_QUERY,
}
CATEGORY_FILES = {f"ev_{name.replace(' ', '_').replace('.', '')}": name for name in CATEGORIES} | {"ev_inventions": "inventions"}


# ---- transport ----------------------------------------------------------------------------------
class QueryFailed(Exception):
    pass


def run(query: str, dest: Path, endpoint: str = EP) -> int:
    """Run one query, save the TSV, return the row count. Skips work already on disk. A query the endpoint
    reports it can't finish (a timeout or out of memory) raises QueryFailed after two tries, so the caller
    can split it; a rate limit or a network error is waited out."""
    if dest.exists():
        return sum(1 for _ in dest.open(encoding="utf-8")) - 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.parse.urlencode({"query": PFX + query}).encode()
    heavy = 0
    for attempt in range(10):
        time.sleep(6)
        req = urllib.request.Request(endpoint, data=data, headers={
            "Accept": "text/tab-separated-values", "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                body = r.read().decode("utf-8")
            # QLever has been seen to repeat a small result after a stray copy of its own HTTP headers
            body = re.split(r"\r?\nHTTP/1\.[01] ", body)[0].rstrip("\r\n") + "\n"
            tmp = dest.with_suffix(".part")
            tmp.write_text(body, encoding="utf-8")
            tmp.replace(dest)
            return body.count("\n") - 1
        except urllib.error.HTTPError as e:
            try:
                msg = e.read().decode("utf-8", "replace")[:400]
            except Exception:  # noqa: BLE001
                msg = ""
            if "timed out" in msg or "allocate" in msg or "memory" in msg.lower():
                heavy += 1
                print(f"  {dest.name}: the endpoint couldn't finish ({msg[:80]!r})", flush=True)
                if heavy >= 2:
                    raise QueryFailed(dest.name)
                time.sleep(30)
                continue
            hint = e.headers.get("Retry-After") if e.headers else None
            wait = int(hint) + 2 if hint and hint.isdigit() else min(60 * (attempt + 1), 300)
            print(f"  HTTP {e.code} on {dest.name}; retry in {wait}s", flush=True)
            time.sleep(wait)
        except Exception as e:  # noqa: BLE001
            print(f"  {e!r} on {dest.name}; retry", flush=True)
            time.sleep(min(30 * (attempt + 1), 300))
    raise QueryFailed(dest.name)


def qid(cell: str) -> str:
    return cell.strip().strip("<>").rsplit("/", 1)[-1]


def lit(cell: str) -> str:
    c = cell.strip()
    return c[1:c.rfind('"')] if c.startswith('"') else c


def year(t: str) -> int | None:
    m = re.match(r'"?([+-]?)(\d+)-', t.strip())
    return (-1 if m.group(1) == "-" else 1) * int(m.group(2)) if m else None


def read(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    return rows[1:]


def values(ids: list[str], var: str = "?x") -> str:
    return f"VALUES {var} {{ {vq(ids)} }}"


# ---- batches with manifests ---------------------------------------------------------------------
def manifest(kind: str) -> dict[str, list[str]]:
    f = OUT / kind / "_manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def save_manifest(kind: str, man: dict) -> None:
    (OUT / kind).mkdir(parents=True, exist_ok=True)
    tmp = OUT / kind / "_manifest.json.part"
    tmp.write_text(json.dumps(man), encoding="utf-8")
    tmp.replace(OUT / kind / "_manifest.json")


def files(kind: str, prefix: str) -> list[Path]:
    """The cache files for one query kind, from the manifest (so 'positions' never picks up 'positions2')."""
    return sorted(OUT / kind / n for n in manifest(kind) if re.match(rf"{re.escape(prefix)}_\d+[a-z]*\.tsv$", n)
                  and (OUT / kind / n).exists())


def fetch(kind: str, prefix: str, ids, query_for) -> None:
    """Run query_for(chunk) for every id not yet covered by a <prefix> file in OUT/kind, BATCH ids at a time."""
    man = manifest(kind)
    pat = re.compile(rf"{re.escape(prefix)}_(\d+)[a-z]*\.tsv$")
    done: set[str] = set()
    nums = [0]
    for name, chunk in man.items():
        m = pat.match(name)
        if m:
            nums.append(int(m.group(1)) + 1)
            if (OUT / kind / name).exists():
                done.update(chunk)
    todo = sorted(set(ids) - done)
    n = max(nums)
    for i in range(0, len(todo), BATCH):
        _fetch_chunk(kind, man, f"{prefix}_{n:03d}.tsv", todo[i:i + BATCH], query_for)
        print(f"  {kind}/{prefix}: {min(i + BATCH, len(todo)):,} of {len(todo):,} new ids", flush=True)
        n += 1


def _fetch_chunk(kind: str, man: dict, name: str, chunk: list[str], query_for) -> None:
    man[name] = chunk
    save_manifest(kind, man)
    try:
        run(query_for(chunk), OUT / kind / name)
    except QueryFailed:
        if len(chunk) <= 500:
            raise
        del man[name]
        half = len(chunk) // 2
        for suffix, part in (("a", chunk[:half]), ("b", chunk[half:])):
            _fetch_chunk(kind, man, name.replace(".tsv", f"{suffix}.tsv"), part, query_for)


def detail(kind: str, ids: list[str], props: dict[str, str], claims_prefix: str = "claims") -> None:
    """Labels, descriptions, English Wikipedia titles, aliases, and simple claims for a list of items."""
    fetch(kind, "core", ids, lambda c: f"""SELECT ?x ?s ?label ?desc ?enwiki WHERE {{ {values(c)} ?x wikibase:sitelinks ?s .
        OPTIONAL {{ ?x rdfs:label ?label . FILTER(LANG(?label) = "en") }}
        OPTIONAL {{ ?x schema:description ?desc . FILTER(LANG(?desc) = "en") }}
        OPTIONAL {{ ?a schema:about ?x ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?enwiki }} }}""")
    fetch(kind, "aliases", ids, lambda c: f"""SELECT ?x ?alias WHERE {{ {values(c)} ?x skos:altLabel ?alias . FILTER(LANG(?alias) = "en") }}""")
    multilingual(kind, ids)
    pv = " ".join(f"wdt:{k}" for k in props)
    fetch(kind, claims_prefix, ids, lambda c: f"""SELECT ?x ?prop ?o WHERE {{ {values(c)} VALUES ?prop {{ {pv} }} ?x ?prop ?o }}""")


def multilingual(kind: str, ids: list[str]) -> None:
    """Names under Wikidata's 'mul' code. Since 2024 a name spelled the same in every language is kept once,
    as a multilingual label, and the English copy is often removed: Victor Hugo, Pablo Picasso, and
    Jacksonville, Florida have no English label at all, and the first build left out 30,400 people that way."""
    ids = [q for q in ids if q.startswith("Q")]
    fetch(kind, "mul", ids, lambda c: f"""SELECT ?x ?mul WHERE {{ {values(c)} ?x rdfs:label ?mul . FILTER(LANG(?mul) = "mul") }}""")
    if kind != "labels":
        fetch(kind, "mulaliases", ids, lambda c: f"""SELECT ?x ?alias WHERE {{ {values(c)} ?x skos:altLabel ?alias . FILTER(LANG(?alias) = "mul") }}""")


def dated(kind: str, prefix: str, ids: list[str], props: list[str]) -> None:
    """Dates with their precision (9 = year, 10 = month, 11 = day; 7 = century), rank, calendar, and number of
    references. Deprecated statements are left out: Jane Austen's item keeps a misprinted 24 July 1877 death
    date, marked deprecated, beside the preferred 18 July 1817."""
    pv = " ".join(f"p:{k}" for k in props)
    fetch(kind, prefix, ids, lambda c: f"""SELECT ?x ?prop ?t ?prec ?rank ?cal (COUNT(?ref) AS ?refs) WHERE {{
        {values(c)} VALUES ?prop {{ {pv} }} ?x ?prop ?st . {RANKED}
        ?st ?psv ?node . ?node wikibase:timeValue ?t ; wikibase:timePrecision ?prec ; wikibase:timeCalendarModel ?cal .
        FILTER(STRSTARTS(STR(?psv), "http://www.wikidata.org/prop/statement/value/"))
        OPTIONAL {{ ?st prov:wasDerivedFrom ?ref }} }} GROUP BY ?x ?prop ?t ?prec ?rank ?cal""")


# columns: ?x ?prop ?t ?prec ?rank ?cal ?refs (dates and dates2 took deprecated statements too; dates3 had
# no calendars or references)
DATES = "dates4"
SIGNALS = "signals2"  # the death signal of people with no dates, deprecated statements left out
# columns: ?x ?pos ?start ?sp ?sc ?end ?ep ?ec ?replaces ?replacedby, with the calendar of each term's dates
POSITIONS = "positions4"


PERSON_MIN_PREC = 6  # a person's date coarser than a millennium is noise (one item gave its living prime minister 10,000 BC)


def best_by_rank(rows) -> dict[tuple[str, str], str]:
    """(qid, property) -> the time of a person's best date statement: preferred over normal, then the most
    precise, then the best referenced, then the earliest, so a rebuild picks the same one. (The builder orders
    them the same way and turns Julian dates back.)"""
    best: dict[tuple[str, str], tuple] = {}
    for r in rows:
        if len(r) < 4 or int(lit(r[3]) or 0) < PERSON_MIN_PREC:
            continue
        q, prop, t = qid(r[0]), qid(r[1]), lit(r[2])
        refs = int(lit(r[6]) or 0) if len(r) > 6 and lit(r[6]).isdigit() else 0
        key = (-("PreferredRank" in r[4]) if len(r) > 4 else 0, -int(lit(r[3]) or 0), -refs, t)
        if (q, prop) not in best or key < best[(q, prop)][0]:
            best[(q, prop)] = (key, t)
    return {k: t for k, (_, t) in best.items()}


def earliest_year(t: str, prec: int) -> int | None:
    """The earliest year a date could mean: a birth 'in the 19th century', stored as the year 1900, could be
    as early as 1801, so it never makes someone count as living."""
    y = year(t)
    if y is None or prec >= 9:
        return y
    span = 10 if prec == 8 else 10 ** (9 - prec)
    a = abs(y)
    lo = a - a % span if prec == 8 else (a - 1) // span * span + 1
    return -(lo + span - 1) if y < 0 else lo


def ids_of(name: str, col: int = 0) -> dict[str, int]:
    return {qid(r[col]): int(lit(r[1]) or 0) for r in read(OUT / "select" / f"{name}.tsv") if r}


# ---- selection ------------------------------------------------------------------------------------
def select() -> None:
    for name, query in SELECT.items():
        dest = OUT / "select" / f"{name}.tsv"
        try:
            n = run(query, dest)
        except QueryFailed:
            n = _select_fallback(name, dest)
        print(f"select {name}: {n:,} rows", flush=True)


def _select_fallback(name: str, dest: Path) -> int:
    """A category the endpoint can't finish in one query: drop the Illinois check (the slowest part), then
    query class by class, and merge the parts into the category's file."""
    cat = CATEGORY_FILES.get(name)
    if not cat or cat == "inventions":
        raise QueryFailed(name)
    light = SELECT[name].replace("OPTIONAL { ?e wdt:P276/wdt:P131* wd:Q1204 . BIND(1 AS ?il) }", "")
    try:
        return run(light, dest)
    except QueryFailed:
        pass
    rows = ["?e\t?s\t?us\t?il\t?dated"]
    for q in CATEGORIES[cat]["classes"]:
        part = OUT / "select" / f"{name}__{q}.tsv"
        one = light.replace(f"VALUES ?c {{ {vq(CATEGORIES[cat]['classes'])} }}", f"VALUES ?c {{ wd:{q} }}")
        run(one, part)
        rows += ["\t".join(r) for r in read(part)]
    dest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows) - 1


def event_rows() -> dict[str, dict]:
    """qid -> {sitelinks, us, il, dated, categories} over every category file."""
    out: dict[str, dict] = {}
    for fname, cat in CATEGORY_FILES.items():
        f = OUT / "select" / f"{fname}.tsv"
        if not f.exists():
            continue
        for r in read(f):
            if not r:
                continue
            r = r + [""] * (5 - len(r))
            q = qid(r[0])
            e = out.setdefault(q, {"s": 0, "us": False, "il": False, "dated": False, "cats": set()})
            e["s"] = max(e["s"], int(lit(r[1]) or 0))
            e["us"] |= bool(lit(r[2]))
            e["il"] |= bool(lit(r[3]))
            e["dated"] |= bool(lit(r[4]))
            e["cats"].add(cat)
    return out


def qualifies(e: dict, cat: str) -> bool:
    c = CATEGORIES.get(cat, INVENTIONS)
    if c.get("always"):
        return True
    return e["s"] >= c["world"] or (e["us"] and e["s"] >= c["us"]) or (e["il"] and e["s"] >= 1)


def events_selected() -> dict[str, set[str]]:
    """qid -> the categories it qualifies under."""
    keep = {}
    for q, e in event_rows().items():
        cats = {c for c in e["cats"] if qualifies(e, c)}
        if cats:
            keep[q] = cats
    return keep


def candidates() -> dict[str, set[str]]:
    """Person id -> the reasons it qualifies (role_living only matters for the living; see final_people)."""
    people_events = {q for q, cats in events_selected().items()
                     if any(CATEGORIES.get(c, INVENTIONS).get("people") for c in cats)}
    why: dict[str, set[str]] = {}
    for name, reason in (("fame_illinois", "fame_illinois"), ("fame_us", "fame_us"), ("fame_world10", "fame_world10"),
                         ("fame_world20", "fame_world20"), ("role_office", "role_office"),
                         ("role_signatory", "role_signatory"), ("role_living2", "role_living"),
                         ("role_nobel", "role_nobel")):
        for q in ids_of(name):
            why.setdefault(q, set()).add(reason)
    for r in read(OUT / "select" / "role_participant2.tsv"):
        if len(r) >= 3 and qid(r[2]) in people_events:
            why.setdefault(qid(r[0]), set()).add("role_participant")
    return why


QUALIFY_DEAD = {"fame_illinois", "fame_us", "fame_world10", "fame_world20", "role_office", "role_signatory",
                "role_participant", "role_nobel"}
QUALIFY_LIVING = {"role_office", "role_living", "role_nobel", "role_signatory", "role_participant"}


def life_evidence() -> tuple[dict[str, int], set[str], dict[str, int]]:
    """Birth years, the people known to be dead (a death date, or a death statement of unknown date), and the
    latest year anyone was recorded active (floruit, work period), which counts for people with no birth date."""
    born: dict[str, int] = {}
    dead: set[str] = set()
    active: dict[str, int] = {}
    rows = [r for f in files("candidates", DATES) for r in read(f)]
    prec = {(qid(r[0]), qid(r[1]), lit(r[2])): int(lit(r[3]) or 0) for r in rows if len(r) >= 4}
    for (q, prop), t in best_by_rank(rows).items():
        if prop == "P570":
            dead.add(q)
        elif prop == "P569" and (y := earliest_year(t, prec.get((q, prop, t), 9))) is not None:
            born[q] = y
    for f in files("candidates", SIGNALS):
        for r in read(f):
            if len(r) < 2:
                continue
            q, kind = qid(r[0]), lit(r[1])
            if kind == "death":
                dead.add(q)
            elif len(r) >= 3 and (y := year(r[2])) is not None:
                active[q] = max(active.get(q, y), y)
    return born, dead, active


CURATION = ROOT / "scripts" / "socialsci" / "curation"


def excluded_people() -> set[str]:
    """People left out by review, each with its reason, in curation/exclude_people.csv (those known primarily
    for adult films, among others)."""
    f = CURATION / "exclude_people.csv"
    return {r["qid"] for r in csv.DictReader(f.open(encoding="utf-8"))} if f.exists() else set()


def final_people() -> dict[str, set[str]]:
    """Apply the living-people rule. Dead: any death statement, even 'unknown'. Otherwise a birth year
    before 1900, or (with no birth date) activity recorded only before 1900, means historical. Someone with
    no evidence at all counts as living, so the rule never admits a living person by accident. People on the
    reviewed exclusion list are left out."""
    why = candidates()
    born, dead, active = life_evidence()
    excluded = excluded_people()
    keep = {}
    for q, w in why.items():
        if q in excluded:
            continue
        if q in dead:
            living = False
        elif q in born:
            living = born[q] >= 1900
        elif q in active:
            living = active[q] >= 1900
        else:
            living = True
        if w & (QUALIFY_LIVING if living else QUALIFY_DEAD):
            keep[q] = w | ({"living"} if living else set())
    return keep


# ---- stages -------------------------------------------------------------------------------------
def people() -> None:
    cand = sorted(candidates())
    print(f"people: {len(cand):,} candidates", flush=True)
    dated("candidates", DATES, cand, ["P569", "P570"])
    # anyone without a death date may still have a death statement of unknown date (Ettore Majorana, who
    # vanished in 1938; Volodymyr Ivasyuk, whose recorded date is deprecated), which makes them historical
    have_death = {qid(r[0]) for f in files("candidates", DATES) for r in read(f) if len(r) > 1 and qid(r[1]) == "P570"}
    no_death = [q for q in cand if q not in have_death]
    print(f"people: {len(no_death):,} candidates with no death date", flush=True)
    fetch("candidates", SIGNALS, no_death, lambda c: f"""SELECT ?x ?kind ?t WHERE {{ {values(c)}
        {{ ?x p:P570 ?st . {RANKED} BIND("death" AS ?kind) }} UNION {{ ?x wdt:P1317 ?t . BIND("floruit" AS ?kind) }}
        UNION {{ ?x wdt:P2031 ?t . BIND("work" AS ?kind) }} UNION {{ ?x wdt:P2032 ?t . BIND("work" AS ?kind) }} }}""")
    why = final_people()
    ids = sorted(why)
    print(f"people: {len(ids):,} after the living-people rule ({sum('living' in w for w in why.values()):,} living)", flush=True)
    detail("people", ids, PERSON_PROPS)
    fetch("people", POSITIONS, ids, lambda c: f"""SELECT ?x ?pos ?start ?sp ?sc ?end ?ep ?ec ?replaces ?replacedby WHERE {{
        {values(c)} ?x p:P39 ?st . {RANKED} ?st ps:P39 ?pos .
        OPTIONAL {{ ?st pqv:P580 ?sv . ?sv wikibase:timeValue ?start ; wikibase:timePrecision ?sp ; wikibase:timeCalendarModel ?sc }}
        OPTIONAL {{ ?st pqv:P582 ?ev . ?ev wikibase:timeValue ?end ; wikibase:timePrecision ?ep ; wikibase:timeCalendarModel ?ec }}
        OPTIONAL {{ ?st pq:P1365 ?replaces }} OPTIONAL {{ ?st pq:P1366 ?replacedby }} }}""")
    fetch("people", "works", ids, lambda c: f"""SELECT ?x ?work WHERE {{ {values(c)} ?work wdt:P50 ?x ; wikibase:sitelinks ?s .
        FILTER(xsd:integer(?s) >= 3) }}""")
    place_refs(set(ids))


def place_refs(ids: set[str]) -> None:
    """How many references back each birthplace and deathplace of the people listed with two or more, so the
    builder can tell a sourced place from an unsourced one of the same name (Jane Austen's item gives both
    Steventon, Hampshire, with four references and Steventon, Oxfordshire, with none)."""
    count: dict[tuple[str, str], int] = {}
    for f in files("people", "claims"):
        for r in read(f):
            if len(r) >= 3 and qid(r[1]) in ("P19", "P20") and qid(r[0]) in ids:
                count[(qid(r[0]), qid(r[1]))] = count.get((qid(r[0]), qid(r[1])), 0) + 1
    several = sorted({q for (q, _), n in count.items() if n > 1})
    print(f"people: {len(several):,} with two or more birthplaces or deathplaces", flush=True)
    fetch("people", "placerefs", several, lambda c: f"""SELECT ?x ?prop ?o (COUNT(?ref) AS ?refs) WHERE {{ {values(c)}
        VALUES (?prop ?ps) {{ (p:P19 ps:P19) (p:P20 ps:P20) }} ?x ?prop ?st . {RANKED} ?st ?ps ?o .
        OPTIONAL {{ ?st prov:wasDerivedFrom ?ref }} }} GROUP BY ?x ?prop ?o""")


def events_stage() -> None:
    ids = sorted(events_selected())
    print(f"events: {len(ids):,}", flush=True)
    dated("events", DATES, ids, EVENT_DATES)
    detail("events", ids, EVENT_PROPS, claims_prefix="claims2")


def claim_rows(kind: str, prefix: str, subjects: set[str] | None = None):
    for f in files(kind, prefix):
        for r in read(f):
            if len(r) >= 3 and (subjects is None or qid(r[0]) in subjects):
                yield qid(r[0]), qid(r[1]), r[2]


def referenced(kind: str, prefix: str, props: set[str], subjects: set[str]) -> set[str]:
    return {qid(o) for s, p, o in claim_rows(kind, prefix, subjects)
            if p in props and o.startswith("<http://www.wikidata.org/entity/Q")}


def places() -> None:
    people_ids, event_ids = set(final_people()), set(events_selected())
    ids = sorted(referenced("people", "claims", {"P19", "P20"}, people_ids) |
                 referenced("events", "claims2", {"P276", "P17"}, event_ids))
    print(f"places: {len(ids):,}", flush=True)
    detail("places", ids, PLACE_PROPS)


def labels() -> None:
    """Labels for everything else the claims point at (offices, parties, occupations, schools, works)."""
    people_ids, event_ids = set(final_people()), set(events_selected())
    place_ids = {qid(r[0]) for f in files("places", "core") for r in read(f) if r}
    have = people_ids | event_ids | place_ids
    other: set[str] = set()
    for kind, prefix, subjects in (("people", "claims", people_ids), ("events", "claims2", event_ids), ("places", "claims", place_ids)):
        other |= {qid(o) for s, p, o in claim_rows(kind, prefix, subjects) if o.startswith("<http://www.wikidata.org/entity/Q")}
    for f in files("people", POSITIONS):
        for r in read(f):
            if r and qid(r[0]) in people_ids and len(r) >= 2 and r[1]:
                other.add(qid(r[1]))
    for f in files("people", "works"):
        other |= {qid(r[1]) for r in read(f) if len(r) >= 2 and r[1] and qid(r[0]) in people_ids}
    ids = sorted(other - have)
    print(f"labels: {len(ids):,} other items", flush=True)
    fetch("labels", "core", ids, lambda c: f"""SELECT ?x ?label ?desc WHERE {{ {values(c)}
        OPTIONAL {{ ?x rdfs:label ?label . FILTER(LANG(?label) = "en") }}
        OPTIONAL {{ ?x schema:description ?desc . FILTER(LANG(?desc) = "en") }} }}""")
    multilingual("labels", ids)


def significance() -> None:
    """Signals of historical significance beyond fame, for measuring a tighter rule: entries in curated
    reference works and the awards of every candidate, plus everyone Wikidata places in those reference works
    (people of real significance whom fame alone never brought in)."""
    for prop, name in REFERENCE_IDS.items():
        dest = OUT / "select" / f"ref_{prop}.tsv"
        n = run(f"SELECT DISTINCT ?p ?s WHERE {{ ?p wdt:P31 wd:Q5 ; wdt:{prop} ?id ; wikibase:sitelinks ?s }}", dest)
        print(f"select ref {name}: {n:,}", flush=True)
    for src, name in DESCRIBED_BY.items():
        dest = OUT / "select" / f"described_{src}.tsv"
        n = run(f"SELECT DISTINCT ?p ?s WHERE {{ ?p wdt:P31 wd:Q5 ; wdt:P1343 wd:{src} ; wikibase:sitelinks ?s }}", dest)
        print(f"select described by {name}: {n:,}", flush=True)
    cand = sorted(candidates())
    fetch("candidates", "awards", cand, lambda c: f"SELECT ?x ?award WHERE {{ {values(c)} ?x wdt:P166 ?award }}")
    honors()


def award_family(root: str, depth: int = 3, cap: int = 3000) -> list[str]:
    """The award and every item under it, level by level: people hold the sub-award (the Nobel Prize in
    Physics, the Academy Award for Best Actor), which points to the parent as a subclass, an instance, or a
    part. (The first harvest matched the parent alone and found no Nobel laureates; a '*' path over the three
    properties times out.)"""
    fam, level = {root}, [root]
    for d in range(depth):
        dest = OUT / "families" / f"{root}_{d}.tsv"
        run(f"""SELECT DISTINCT ?x WHERE {{ {values(level, '?y')}
                {{ ?x wdt:P279 ?y }} UNION {{ ?x wdt:P31 ?y }} UNION {{ ?x wdt:P361 ?y }} }}""", dest)
        new = [qid(r[0]) for r in read(dest) if r and qid(r[0]) not in fam]
        if not new or len(fam) + len(new) > cap:
            break
        fam.update(new)
        level = new
    return sorted(fam)


def honors() -> None:
    """Everyone holding an honor on the candidate list (curation/honors_candidates.csv, from the 2026-10-23
    research: the reviewed list with corrected families plus new candidates; rows marked 'out' are skipped).
    An honor is found by P166 over its family (the 'family_qids' column, else award_family), or, when
    recipients are recorded another way (Olympic champions as a qualifier on 'participant in', saints by
    canonization status, Statuary Hall by the statue that depicts them), by the row's own 'query', which
    returns ?p ?s. Saved as select/honors2_<qid>.tsv."""
    for r in csv.DictReader((CURATION / "honors_candidates.csv").open(encoding="utf-8")):
        if r["recommend"] == "out":
            continue
        dest = OUT / "select" / f"honors2_{r['qid']}.tsv"
        if (r.get("query") or "").strip():
            n = run(r["query"], dest)
        else:
            fam = (r.get("family_qids") or "").split() or award_family(r["qid"])
            n = run(f"""SELECT DISTINCT ?p ?s WHERE {{ {values(fam, '?a')} ?p wdt:P166 ?a ; wdt:P31 wd:Q5 ;
                        wikibase:sitelinks ?s }}""", dest)
        print(f"select honor {r['award']}: {n:,}", flush=True)


def multilingual_stage() -> None:
    """Multilingual names for the items already harvested without an English label (the stage run once, after
    the 'mul' change; new items get both from detail())."""
    for kind in ("people", "events", "places", "labels"):
        col = 1 if kind == "labels" else 2
        ids = sorted({qid(r[0]) for f in files(kind, "core") for r in read(f) if r and (len(r) <= col or not r[col].strip())})
        print(f"{kind}: multilingual names for {len(ids):,} items with no English label", flush=True)
        multilingual(kind, ids)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    stages = {"select": select, "people": people, "events": events_stage, "places": places, "labels": labels,
              "multilingual": multilingual_stage, "significance": significance, "honors": honors}
    for s in sys.argv[1:] or list(stages):
        stages[s]()
