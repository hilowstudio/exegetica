"""Social Sciences MCP server: history, government and civics tools over the owned social_sciences.db.

Self-hosted like the Study Bible server: every answer comes from data downloaded once and kept
(Avalon Project, Miller Center speeches, DocSouth, the Illinois Constitution, the U.S. Flag Code,
the Reading Room's history shelves). No tool calls an outside service at question time.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
from pathlib import Path
from typing import Any

import click
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent, Tool

from .database import SocialSciencesDB, get_db_path, roman_or_int

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("socialsci-mcp")

PROMPTS = Path(__file__).parent / "prompts"
SERVER_INSTRUCTIONS = (
    "This connector serves high-school U.S. History, Government and Street Law classes at a Christian "
    "school. It holds primary sources (founding documents, treaties, statutes, presidential speeches, "
    "slave narratives and first-person accounts), the U.S. and Illinois Constitutions and the U.S. Flag "
    "Code (for the Illinois Constitution Test), and public-domain history books. Ground every factual "
    "claim, date and quotation in these tools rather than memory, quote documents exactly, and cite "
    "the document, author, and date you draw on. When the sources don't settle a question, say so."
)
server = Server("social-sciences", version="0.1.0", instructions=SERVER_INSTRUCTIONS)
db: SocialSciencesDB | None = None
db_stamp: int | None = None  # the file's mtime when it was opened

SOURCE_ENUM = ["all", "documents", "speeches", "narratives", "books"]

TOOLS = [
    Tool(
        name="search_history",
        description=(
            "Search the history corpus by keyword and by meaning: founding documents, charters, treaties and "
            "statutes (Avalon Project), every major presidential speech (Miller Center), slave narratives and "
            "first-person Southern accounts (DocSouth), and public-domain history books from the Reading Room. "
            "Returns cited passages. Use it to find what a primary source actually says before answering."
        ),
        inputSchema={"type": "object", "properties": {
            "query": {"type": "string", "description": "What to look for, in plain words or exact phrases."},
            "source": {"type": "string", "enum": SOURCE_ENUM,
                       "description": "documents = founding/government documents; speeches = presidential speeches; "
                                      "narratives = slave narratives and first-person accounts; books = history books. Default all."},
            "year_from": {"type": "integer", "description": "Earliest year of the document."},
            "year_to": {"type": "integer", "description": "Latest year of the document."},
            "limit": {"type": "integer", "default": 8, "maximum": 20},
        }, "required": ["query"]},
    ),
    Tool(
        name="find_documents",
        description=(
            "Find documents by title, author or source (e.g. 'Declaration of Independence', 'Federalist 10', "
            "'Gettysburg', author 'Lincoln', source 'speeches'). Returns ids to open with get_document."
        ),
        inputSchema={"type": "object", "properties": {
            "title": {"type": "string"}, "author": {"type": "string"},
            "source": {"type": "string", "enum": SOURCE_ENUM},
            "year_from": {"type": "integer"}, "year_to": {"type": "integer"},
            "limit": {"type": "integer", "default": 15, "maximum": 50},
        }},
    ),
    Tool(
        name="get_document",
        description=(
            "Read a document's full text by id (from find_documents or search_history), in pages. "
            "Returns title, author, date, citation and the text."
        ),
        inputSchema={"type": "object", "properties": {
            "id": {"type": "integer"},
            "page": {"type": "integer", "default": 1, "description": "Page of about 6,000 characters."},
        }, "required": ["id"]},
    ),
    Tool(
        name="get_constitution",
        description=(
            "Exact text of the U.S. Constitution or the Illinois Constitution (1970), by part. U.S.: article "
            "and section, or amendment number (Roman or Arabic). Illinois: article and section. Omit the "
            "numbers to list the headings. Use it for the Constitution Test and any constitutional question."
        ),
        inputSchema={"type": "object", "properties": {
            "constitution": {"type": "string", "enum": ["us", "illinois"]},
            "article": {"type": "string", "description": "Article number, e.g. 'I' or '1'."},
            "section": {"type": "string", "description": "Section number within the article."},
            "amendment": {"type": "string", "description": "U.S. only: amendment number, e.g. 'XIV' or '14'."},
            "preamble": {"type": "boolean", "description": "Return the preamble."},
        }, "required": ["constitution"]},
    ),
    Tool(
        name="get_flag_code",
        description=(
            "The U.S. Flag Code (4 U.S.C. §§ 1-10): design, the Pledge, when and how to display the flag, "
            "respect for the flag, conduct during the anthem and pledge. Give a section number, or omit it "
            "for the list of sections. Part of the Illinois Constitution Test."
        ),
        inputSchema={"type": "object", "properties": {"section": {"type": "string"}}},
    ),
    Tool(
        name="constitution_test_guide",
        description=(
            "What the Illinois Constitution Test covers (the Declaration of Independence, the U.S. Constitution, "
            "the Illinois Constitution, and proper use of the flag) and where each part lives in these tools, "
            "with the headings of every article, amendment and flag-code section. Start here for test review."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="search_cases",
        description=(
            "Search every U.S. Supreme Court opinion from 1791 through about 2018 (U.S. Reports, Caselaw Access "
            "Project) by name, topic, or words in the opinions. Results show the citation, date, vote, who wrote "
            "for the majority, the issue area, and whether a law was struck down or a precedent overruled "
            "(Supreme Court Database coding). Landmark cases rank first. Open one with get_case."
        ),
        inputSchema={"type": "object", "properties": {
            "query": {"type": "string", "description": "A case name or a topic (e.g. 'Miranda', 'school prayer', 'search of a student's locker')."},
            "issue_area": {"type": "string", "description": "Optional: Criminal Procedure, Civil Rights, First Amendment, Due Process, Privacy, Federalism, Judicial Power, Economic Activity, and others."},
            "year_from": {"type": "integer"}, "year_to": {"type": "integer"},
            "limit": {"type": "integer", "default": 8, "maximum": 20},
        }, "required": ["query"]},
    ),
    Tool(
        name="get_case",
        description=(
            "Read a Supreme Court case by citation ('347 U.S. 483'), name ('Marbury v. Madison'), or id. Returns "
            "the coding (date, vote, majority and dissenting justices, issue area, law struck down) and the "
            "opinions: part='summary' (default: the header and the opening of the Court's opinion), "
            "'majority', 'concurrence', 'dissent', or 'all', in pages."
        ),
        inputSchema={"type": "object", "properties": {
            "case": {"type": "string"},
            "part": {"type": "string", "enum": ["summary", "majority", "concurrence", "dissent", "all"]},
            "page": {"type": "integer", "default": 1},
        }, "required": ["case"]},
    ),
    Tool(
        name="get_statute",
        description=(
            "The U.S. Code (current through Public Law 119-120) and the Illinois Compiled Statutes chapters on "
            "elections, vehicles, courts, criminal law and procedure, corrections, civil procedure and "
            "liability, families, estates, property and landlord-tenant, human rights, consumer fraud, and "
            "employment. Give a citation ('18 U.S.C. § 1001', '720 ILCS 5/12-3') for the exact section (long sections "
            "come in pages), or a query to search."
        ),
        inputSchema={"type": "object", "properties": {
            "citation": {"type": "string"},
            "query": {"type": "string"},
            "code": {"type": "string", "enum": ["usc", "ilcs"], "description": "Limit a search to one code."},
            "page": {"type": "integer", "default": 1, "description": "Page of a long section (about 7,000 characters each)."},
        }},
    ),
    Tool(
        name="get_constitution_annotation",
        description=(
            "The Constitution Annotated (Congressional Research Service, 2022): clause-by-clause essays on how "
            "each part of the Constitution has been understood and applied, with the leading cases. Give an "
            "article/section/clause or an amendment (with optional section) to list its essays, an essay_id to "
            "read one, or a query to search. Long essays come in pages."
        ),
        inputSchema={"type": "object", "properties": {
            "article": {"type": "string"}, "section": {"type": "string"}, "clause": {"type": "string"},
            "amendment": {"type": "string"}, "essay_id": {"type": "string"}, "query": {"type": "string"},
            "page": {"type": "integer", "default": 1, "description": "Page of a long essay (about 7,000 characters each)."},
        }},
    ),
    Tool(
        name="lookup_legislator",
        description=(
            "Every member of Congress since 1789 and every president and vice president: terms, chamber, state, "
            "district, and party, by name (optionally a state)."
        ),
        inputSchema={"type": "object", "properties": {
            "name": {"type": "string"}, "state": {"type": "string", "description": "Two-letter state code."},
        }, "required": ["name"]},
    ),
    Tool(
        name="define_term",
        description=(
            "Define a word as it was used in its time: Black's Law Dictionary (2nd ed., 1910) for legal terms, "
            "and Webster's American Dictionary of the English Language (1828) for founding-era English. Use it "
            "when an old document or opinion uses a word whose meaning has shifted."
        ),
        inputSchema={"type": "object", "properties": {
            "term": {"type": "string"},
            "source": {"type": "string", "enum": ["blacks", "webster", "both"]},
        }, "required": ["term"]},
    ),
    Tool(
        name="lookup_person",
        description=(
            "Who someone in history was: dates, a one-line description, offices held, speeches given, inventions "
            "and discoveries, writings, elections won, and the documents and Supreme Court cases where they appear. "
            "When a name fits several people it lists them with dates and ids; call again with the id (e.g. 'Q91') "
            "for the one meant. People and events come from Wikidata, kept on our server."
        ),
        inputSchema={"type": "object", "properties": {
            "name": {"type": "string", "description": "A name ('John Adams', 'Tecumseh'), an alias, or a Wikidata id"},
        }, "required": ["name"]},
    ),
    Tool(
        name="explore_family",
        description=(
            "A historical person's family tree: ancestors, descendants, spouses, siblings (the Adamses, the "
            "Roosevelts, royal houses). Draws a Mermaid diagram."
        ),
        inputSchema={"type": "object", "properties": {
            "person": {"type": "string", "description": "Name or Wikidata id"},
            "direction": {"type": "string", "enum": ["ancestors", "descendants", "both"], "default": "both"},
            "generations": {"type": "integer", "default": 3},
        }, "required": ["person"]},
    ),
    Tool(
        name="explore_life",
        description=(
            "A person's life in order: birth, schooling, offices held, wars, expeditions, and other events taken "
            "part in, speeches given, inventions, documents signed, works written, party and religion, death."
        ),
        inputSchema={"type": "object", "properties": {"person": {"type": "string"}}, "required": ["person"]},
    ),
    Tool(
        name="explore_event",
        description=(
            "Any event in the graph: wars and battles, treaties, laws and Supreme Court decisions, elections, "
            "speeches, expeditions and spaceflights, disasters and epidemics, inventions and discoveries, movements, "
            "strikes and protests, economic crises, church councils and revivals, the Olympic Games, and historical "
            "eras. Gives when and where, its category and kind, who took part (parties, signers, speakers, "
            "inventors, winners), what it was part of, what came before and after, its causes and effects, and "
            "where our documents and cases cover it. For the text of a creed or confession, use get_confession."
        ),
        inputSchema={"type": "object", "properties": {"event": {"type": "string"}}, "required": ["event"]},
    ),
    Tool(
        name="explore_historic_place",
        description=(
            "A place in history (a city, a battlefield, a state, a country): what kind of place, where, the events "
            "that happened there, and the notable people born or died there. (For places in the Bible, use "
            "explore_place.)"
        ),
        inputSchema={"type": "object", "properties": {"place": {"type": "string"}}, "required": ["place"]},
    ),
    Tool(
        name="find_historical_connection",
        description=(
            "How two historical people (or a person and an event) are connected: the shortest path through family, "
            "teachers and students, succession in office, shared events, signed documents, and co-written works, "
            "each link named. (For people in the Bible, use find_connection.)"
        ),
        inputSchema={"type": "object", "properties": {
            "from": {"type": "string"}, "to": {"type": "string"},
        }, "required": ["from", "to"]},
    ),
    Tool(
        name="timeline",
        description=(
            "What was happening in a span of years: the eras it falls in, the best-known events (optionally in one "
            "country, or of one kind), and the best-known people alive then. 'What else was going on in 1776?'"
        ),
        inputSchema={"type": "object", "properties": {
            "year_from": {"type": "integer", "description": "Negative for BC"}, "year_to": {"type": "integer"},
            "country": {"type": "string", "description": "e.g. 'United States', 'France'"},
            "kind": {"type": "string", "description": "e.g. 'battle', 'treaty', 'law', 'election', 'speech', 'expedition', "
                                                      "'disaster', 'invention', 'strike', 'council', 'Olympics'"},
        }, "required": ["year_from"]},
    ),
    Tool(
        name="succession",
        description=(
            "Who held an office in order ('President of the United States', 'Chief Justice of the United States', "
            "'Governor of Illinois', 'monarch of England'), or, given a person, each office they held with who came "
            "before and after."
        ),
        inputSchema={"type": "object", "properties": {
            "office": {"type": "string"}, "person": {"type": "string"},
        }},
    ),
    Tool(
        name="people_in_document",
        description=(
            "The people and events in one of our documents or Supreme Court cases: speakers, signers, the justices "
            "and how each voted, and people named in the text. Give a document id (from search_history or "
            "find_documents) or a case citation or name."
        ),
        inputSchema={"type": "object", "properties": {
            "document_id": {"type": "integer"}, "case": {"type": "string"},
        }},
    ),
]


def text(s: str) -> list[TextContent]:
    return [TextContent(type="text", text=s)]


def _cite(r: dict) -> str:
    who = f"{r['author']}, " if r.get("author") else ""
    when = r.get("date") or r.get("year")
    when = f" ({when})" if when and str(r.get("year") or "") not in (r.get("title") or "") else ""
    return f"{who}{r['title']}{when}"


async def h_search(a: dict) -> list[TextContent]:
    rows = await db.hybrid(a["query"], a.get("source"), a.get("year_from"), a.get("year_to"),
                           max(1, min(int(a.get("limit") or 8), 20)))
    if not rows:
        return text("No passages found. Try other words, a wider date range, or source=all.")
    out = []
    for i, r in enumerate(rows, 1):
        out.append(f"[{i}] {_cite(r)}  ·  {r['collection']}  ·  document id {r['doc_id']}\n"
                   f"Source: {r['citation']}\n{r['text'].strip()}")
    return text("\n\n---\n\n".join(out))


async def h_find(a: dict) -> list[TextContent]:
    rows = await db.find_documents(a.get("title"), a.get("source"), a.get("author"),
                                   a.get("year_from"), a.get("year_to"), max(1, min(int(a.get("limit") or 15), 50)))
    if not rows:
        return text("No matching documents. Try fewer title words, or search_history for the content.")
    return text("\n".join(f"id {r['id']}: {_cite(r)}  ·  {r['collection']}  ·  {r['words']:,} words" for r in rows))


async def h_get(a: dict) -> list[TextContent]:
    d = await db.document(int(a["id"]))
    if not d:
        return text(f"No document with id {a['id']}.")
    page = max(1, int(a.get("page") or 1))
    head = f"{_cite(d)}\nCollection: {d['collection']}\nSource: {d['citation']}\nRights: {d['rights']}\n"
    if d["text"] is None:  # a Reading Room book: serve its passages, and point to the reader
        ps = await db.document_passages(d["id"], (page - 1) * 4, 4)
        body = "\n\n".join(p["text"] for p in ps) or "(no more text)"
        return text(f"{head}Read the whole book in the Reading Room: {d['url']}\n\nPart {page}:\n\n{body}")
    size = 6000
    pages = max(1, -(-len(d["text"]) // size))
    chunk = d["text"][(page - 1) * size: page * size]
    more = f"\n\n[page {page} of {pages}; ask for page {page + 1} to continue]" if page < pages else f"\n\n[page {page} of {pages}]"
    return text(f"{head}\n{chunk}{more}")


async def h_constitution(a: dict) -> list[TextContent]:
    code = "us-constitution" if a["constitution"] == "us" else "il-constitution"
    name = "U.S. Constitution" if code == "us-constitution" else "Illinois Constitution (1970)"
    if a.get("preamble"):
        rows = await db.sections(code, "preamble")
    elif a.get("amendment"):
        if code != "us-constitution":
            return text("Amendments by number are for the U.S. Constitution. The Illinois Constitution's amendment process is Article 14.")
        rows = await db.sections(code, "amendment", a["amendment"])
    elif a.get("article"):
        rows = await db.sections(code, "article", a["article"], a.get("section"))
    else:
        rows = await db.sections(code)
        if not rows:
            return text(f"The {name} isn't loaded yet.")
        return text(f"{name}: headings\n" + "\n".join(f"- {r['heading']}" for r in rows))
    if not rows:
        return text(f"No such part of the {name}. Call get_constitution with only the constitution to list its parts.")
    return text(f"{name}\n\n" + "\n\n".join(f"{r['heading']}\n{r['text']}" for r in rows))


async def h_flag(a: dict) -> list[TextContent]:
    if a.get("section"):
        rows = await db.sections("flag-code", "section", roman_or_int(a["section"]))
    else:
        rows = await db.sections("flag-code")
        return text("U.S. Flag Code, 4 U.S.C. ch. 1\n" + "\n".join(f"- {r['heading']}" for r in rows))
    if not rows:
        return text("The Flag Code has sections 1 through 10.")
    return text("\n\n".join(f"{r['heading']}\n{r['text']}" for r in rows))


async def h_guide(a: dict) -> list[TextContent]:
    us = await db.sections("us-constitution")
    il = await db.sections("il-constitution")
    fc = await db.sections("flag-code")
    decl = await db.find_documents("Declaration of Independence", "documents", limit=3)
    parts = [
        "Illinois Constitution Test (required for U.S. History). Illinois law (105 ILCS 5/27-3) names "
        "the Declaration of Independence, the U.S. Constitution, the Illinois Constitution, and the proper "
        "use and display of the American flag. Check your teacher's study guide for what this year's test emphasizes.",
        "\n1. The Declaration of Independence: open it with get_document"
        + (f" (id {decl[0]['id']})." if decl else " (find it with find_documents)."),
        "\n2. The U.S. Constitution (get_constitution constitution=us):",
        *[f"   - {r['heading']}" for r in us if r["part"] != "amendment"],
        "   Amendments: " + ", ".join(r["number"] for r in us if r["part"] == "amendment") if us else "   (loading)",
        "\n3. The Illinois Constitution (get_constitution constitution=illinois):",
        *sorted({f"   - {r['heading'].split(', Section')[0]}" for r in il if r["part"] == "article"},
                key=lambda s: (int(''.join(ch for ch in s.split('Article ')[1].split(' ')[0] if ch.isdigit()) or 99)
                               if "Article " in s else 999)),  # the Transition Schedule comes last
        "\n4. The U.S. Flag (get_flag_code):",
        *[f"   - {r['heading']}" for r in fc],
    ]
    return text("\n".join(parts))


def _justice(name: str | None) -> str:
    """Supreme Court Database short names ('EWarren', 'HLBlack') as people write them ('E. Warren', 'H.L. Black')."""
    import re as _re
    n = name or ""
    suffix = " II" if n.endswith("2") else ""  # JHarlan2 is John Marshall Harlan II
    m = _re.match(r"^([A-Z]+?)([A-Z][a-z].*?)\d?$", n)
    return f"{'.'.join(m.group(1))}. {m.group(2)}{suffix}" if m else n


def _justices(names: str | None) -> str:
    return ", ".join(_justice(n.strip()) for n in (names or "").split(",") if n.strip())


def _case_card(c: dict) -> str:
    bits = [f"{c['short_name']}, {c['cite'] or 'U.S. Reports'} ({c['date'] or c['year']})"]
    meta = []
    if c.get("vote"):
        meta.append(f"vote {c['vote']}")
    if c.get("maj_writer"):
        meta.append(f"opinion by {_justice(c['maj_writer'])}")
    if c.get("issue_area"):
        meta.append(c["issue_area"])
    if c.get("struck_down"):
        meta.append(f"struck down {c['struck_down']}")
    if c.get("overruled_precedent"):
        meta.append("overruled precedent")
    if meta:
        bits.append("  ·  ".join(meta))
    bits.append(f"case id {c['id']}")
    return "\n".join(bits)


async def h_search_cases(a: dict) -> list[TextContent]:
    rows = await db.search_cases(a["query"], a.get("issue_area"), a.get("year_from"), a.get("year_to"),
                                 max(1, min(int(a.get("limit") or 8), 20)))
    if not rows:
        return text("No cases found. Try the case name, other words, or a wider date range.")
    return text("Source: U.S. Reports via the Caselaw Access Project (Harvard Law School); coding from the "
                "Supreme Court Database (Penn State).\n\n" + "\n\n".join(f"[{i}] " + _case_card(r) for i, r in enumerate(rows, 1)))


async def h_get_case(a: dict) -> list[TextContent]:
    c = await db.find_case(str(a["case"]))
    if not c:
        return text("No matching case. Try search_cases.")
    part = a.get("part") or "summary"
    page = max(1, int(a.get("page") or 1))
    ops = await db.case_opinions(c["id"])
    head = _case_card(c)
    if c.get("majority"):
        head += f"\nMajority: {_justices(c['majority'])}"
    if c.get("dissent"):
        head += f"\nDissent: {_justices(c['dissent'])}"
    head += "\nSource: U.S. Reports via the Caselaw Access Project; coding from the Supreme Court Database."
    if part == "summary":
        first = ops[0]["text"][:3500] if ops else ""
        others = ", ".join(f"{o['type']} ({o['author'] or 'unsigned'})" for o in ops)
        return text(f"{head}\nOpinions: {others}\n\n{(c.get('head') or '')[:1200]}\n\n[Opening of the Court's opinion]\n{first}"
                    "\n\n[Ask for part='majority', 'concurrence', 'dissent', or 'all' to read more.]")
    pick = ops if part == "all" else [o for o in ops if o["type"] == part]
    if not pick:
        return text(f"{head}\n\nThis case has no {part} opinion.")
    body = "\n\n".join(f"[{o['type'].title()} ({o['author'] or 'unsigned'})]\n{o['text']}" for o in pick)
    size = 7000
    pages = max(1, -(-len(body) // size))
    chunk = body[(page - 1) * size: page * size]
    return text(f"{head}\n\n{chunk}\n\n[page {page} of {pages}]")


PAGE = 7000


def _paged(head: str, body: str, page) -> list[TextContent]:
    """One page of a long record, with a footer that tells the model how to read on."""
    pages = max(1, -(-len(body) // PAGE))
    page = min(max(1, int(page or 1)), pages)
    chunk = body[(page - 1) * PAGE: page * PAGE]
    if pages == 1:
        return text(f"{head}\n\n{chunk}")
    more = f"; ask for page {page + 1} to continue" if page < pages else ""
    return text(f"{head}\n\n{chunk}\n\n[page {page} of {pages}{more}]")


async def h_statute(a: dict) -> list[TextContent]:
    if a.get("citation"):
        rows = await db.statute(a["citation"])
        if rows:
            # an Illinois section can have two texts (before and after a pending amendment): keep both
            body = "\n\n---\n\n".join(r["text"] for r in rows)
            return _paged(f"{rows[0]['citation']}. {rows[0]['heading']}", body, a.get("page"))
        if not a.get("query"):
            return text("No section with that citation. Check the form ('18 U.S.C. § 1001', '720 ILCS 5/12-3') or search with query.")
    rows = await db.search_statutes(a.get("query") or a.get("citation") or "", a.get("code"))
    if not rows:
        return text("No matching sections.")
    return text("\n\n---\n\n".join(f"{r['citation']}. {r['heading']}\n{r['text']}" for r in rows))


def _provision(a: dict) -> str | None:
    if a.get("amendment"):
        n = roman_or_int(a["amendment"])
        return f"Amdt{n}" + (f".S{roman_or_int(a['section'])}" if a.get("section") else "")
    if a.get("article"):
        roman = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI", "7": "VII"}.get(roman_or_int(a["article"]), str(a["article"]).upper())
        p = f"Art{roman}"
        if a.get("section"):
            p += f".S{roman_or_int(a['section'])}"
        if a.get("clause"):
            p += f".C{roman_or_int(a['clause'])}"
        return p
    return None


async def h_conan(a: dict) -> list[TextContent]:
    src = "Source: Constitution of the United States: Analysis and Interpretation (Congressional Research Service, 2022), govinfo.gov."
    if a.get("essay_id"):
        rows = await db.conan(essay_id=a["essay_id"])
        if not rows:
            return text("No essay with that id.")
        return _paged(f"{rows[0]['essay_id']} {rows[0]['title']}\n{src}", rows[0]["text"], a.get("page"))
    prov = _provision(a)
    if prov:
        rows = await db.conan(provision=prov)
        if rows:
            return text(f"Essays on {prov} ({len(rows)}). Open one with essay_id.\n{src}\n\n" +
                        "\n".join(f"- {r['essay_id']} {r['title']}" for r in rows[:80]) +
                        (f"\n(first 80 of {len(rows)}; name a narrower clause or search with query)" if len(rows) > 80 else ""))
        if not a.get("query"):
            return text(f"No essays found for {prov}. Try a query instead.")
    rows = await db.conan(query=a.get("query") or "")
    if not rows:
        return text("No matching essays.")
    return text(src + "\n\n" + "\n\n---\n\n".join(f"{r['essay_id']} {r['title']}\n{r['text']}" for r in rows))


async def h_legislator(a: dict) -> list[TextContent]:
    rows = await db.legislators(a["name"], a.get("state"))
    if not rows:
        return text("No one by that name in the congressional and executive records.")
    out = []
    for r in rows:
        if "executive" in r:
            out.append("Executive terms:\n" + "\n".join(f"- {e['name']}: {'President' if e['type'] == 'prez' else 'Vice President'}, "
                                                        f"{e['start']} to {e['end']} ({e['party'] or 'no party'}){', ' + e['how'] if e.get('how') else ''}"
                                                        for e in r["executive"]))
            continue
        terms = "\n".join(f"- {'Senator' if t['type'] == 'sen' else 'Representative'}, {t['state']}"
                          f"{'-' + t['district'] if t['type'] == 'rep' and t['district'] not in ('', 'None') else ''}, "
                          f"{t['party'] or 'no party'}, {t['start']} to {t['end']}" for t in r["terms"])
        out.append(f"{r['name']} (born {r['birthday'] or 'unknown'}){' (current member)' if r['current'] else ''}\n{terms}")
    return text("Source: @unitedstates/congress-legislators (public domain).\n\n" + "\n\n".join(out))


async def h_define(a: dict) -> list[TextContent]:
    src = None if (a.get("source") or "both") == "both" else a["source"]
    rows = await db.define(a["term"], src)
    if not rows:
        return text("No entry found. Try the singular form or a related word.")
    return text("\n\n".join(f"{r['term']} ({r['source']})\n{r['definition'][:2500]}" for r in rows))


# ---- people and events graph ------------------------------------------------------------------
WD = "Source: Wikidata (CC0), kept on our server; each id opens at wikidata.org/wiki/<id>."
PHRASE = {"father": "{a}'s father was {b}", "mother": "{a}'s mother was {b}", "child": "{a}'s child was {b}",
          "spouse": "{a} married {b}", "sibling": "{a} and {b} were siblings", "student_of": "{a} studied under {b}",
          "teacher_of": "{a} taught {b}", "influenced_by": "{a} was influenced by {b}", "succeeded": "{a} succeeded {b}",
          "participated_in": "{a} took part in {b}", "fought_in": "{a} fought in {b}", "signed": "{a} signed {b}",
          "gave": "{a} gave {b}", "won": "{a} won {b}", "invented": "{a} invented or discovered {b}",
          "authored": "{a} wrote {b}", "created": "{a} created {b}"}
SHORT = {"father": "father", "mother": "mother", "child": "child", "spouse": "married", "sibling": "sibling",
         "student_of": "studied under", "teacher_of": "taught", "influenced_by": "influenced by", "succeeded": "succeeded",
         "participated_in": "took part in", "fought_in": "fought in", "signed": "signed", "gave": "gave", "won": "won",
         "invented": "invented", "authored": "wrote", "created": "created"}
# councils and assemblies whose creed or confession is in the Study Bible's get_confession
CONFESSION_FOR = {"First Council of Nicaea": "The Nicene Creed", "First Council of Constantinople": "The Nicene Creed",
                  "Council of Chalcedon": "Chalcedonian Definition", "Second Council of Orange": "Council of Orange",
                  "Council of Trent": "Council of Trent", "Synod of Dort": "Canons of Dort",
                  "Westminster Assembly": "Westminster Confession of Faith", "Diet of Augsburg": "Augsburg Confession"}


def _d(t) -> str:
    """A stored date for display: '0450' -> '450'; '1861-03-04' and '100 BC' unchanged."""
    return re.sub(r"^0+(?=\d)", "", str(t or ""))


def _dt(t) -> str:
    """A stored date for display, trimmed to the day only when it is a calendar date ('19th century' stays whole)."""
    t = str(t or "")
    return _d(t[:10] if re.match(r"\d{4}-\d\d", t) else t)


def _sortkey(t: str) -> tuple:
    t = t or ""
    m = re.match(r"(\d+)(?:st|nd|rd|th) (century|millennium)( BC)?", t)
    if m:
        y = (int(m.group(1)) - 1) * (100 if m.group(2) == "century" else 1000) + 50
        return (-y if m.group(3) else y, t)
    m = re.match(r"(\d+)s?( BC)?", t)
    return ((-int(m.group(1)) if m.group(2) else int(m.group(1))), t) if m else (99999, t)


def _life(r: dict) -> str:
    b, d = r.get("birth_year"), r.get("death_year")
    fmt = lambda y: f"{-y} BC" if y < 0 else str(y)
    if b is None and d is None:
        return ""
    if d is None:
        return f" (born {fmt(b)}, living)" if r.get("living") else f" (born {fmt(b)})"
    return f" ({fmt(b) if b is not None else '?'}-{fmt(d)})"


def _year(v) -> str:
    return "" if v is None else (f"{-v} BC" if v < 0 else str(v))


def _span(s, e) -> str:
    s, e = _dt(s), _dt(e)
    return f" ({s} to {e})" if s and e and s != e else (f" ({s or e})" if s or e else "")


def _when(x: dict) -> str:
    return f" ({_dt(x.get('ev_start'))})" if x.get("ev_start") else ""


def _m(label: str) -> str:
    return (label or "").replace('"', "'")


def _offices(rows: list[dict]) -> list[dict]:
    """One entry per office: earliest start, latest end, number of terms."""
    groups: dict[str, dict] = {}
    for o in rows:
        g = groups.setdefault(o["qid"], {"name": o["name"], "start": o["start"], "end": o["end"], "terms": 0})
        g["terms"] += 1
        if o["start"] and (not g["start"] or o["start"] < g["start"]):
            g["start"] = o["start"]
        if o["end"] and (not g["end"] or o["end"] > g["end"]):
            g["end"] = o["end"]
    return list(groups.values())


async def _resolve(name: str, kind: str | None = None, kinds: tuple[str, ...] | None = None) -> tuple[dict | None, list[dict]]:
    rows = await db.find_entities(name, kind, kinds=kinds)
    return (rows[0] if rows else None), rows


async def _others(label: str, rows: list[dict]) -> str:
    """Others called by the same name (or alias), so the model can pick the right one by id."""
    want = label.strip().lower()
    same = [r for r in rows[1:] if r["name"].lower() == want
            or want in [x.strip().lower() for x in (r.get("aliases") or "").split(";")]]
    if not same:
        return ""
    lines = []
    for r in same[:6]:
        p = await db.person(r["qid"]) if r["kind"] == "person" else None
        lines.append(f"- {r['qid']} {r['name']}{_life(p) if p else ''}: {r.get('description') or r['kind']}")
    return (f"\n\nOther matches for '{label}' (this answer is about {rows[0]['qid']}). "
            "If the question meant another, call again with its id:\n" + "\n".join(lines))


async def _in_sources(qid: str, n: int = 10) -> str:
    ms = await db.mentions_of(qid, n)
    if not ms:
        return ""
    return "In our sources:\n" + "\n".join(
        f"- {'case ' + m['cite'] + ' ' if m['doc_type'] == 'case' and m.get('cite') else ''}{m['title']}"
        f"{' (' + str(m['year']) + ')' if m.get('year') and str(m['year']) not in (m['title'] or '') else ''}: "
        f"{m['role'] or m['how']} [{m['doc_type']} {m['doc_id']}]" for m in ms)


async def h_lookup_person(a: dict) -> list[TextContent]:
    top, rows = await _resolve(a["name"], "person")
    if not top:
        top, rows = await _resolve(a["name"])
        if not top:
            return text(f"No one named '{a['name']}' in the graph.")
    p = await db.person(top["qid"])
    if not p:
        return text(f"{top['name']} ({top['qid']}) is a {top['kind']}, not a person. {top.get('description') or ''}"
                    + ("\nUse explore_event." if top["kind"] == "event" else ""))
    q = p["qid"]
    out = [f"{p['name']}{_life(p)} [{q}]", p.get("description") or ""]
    if p.get("aliases"):
        out.append("Also called: " + p["aliases"][:300])
    for r in sorted(await db.links(q, ("born_in", "died_in")), key=lambda r: r["rel"] != "born_in"):
        out.append(f"{'Born' if r['rel'] == 'born_in' else 'Died'} in {r['name']}")
    offices = _offices(await db.links(q, ("held",), limit=80))
    if offices:
        out.append("Offices:\n" + "\n".join(f"- {o['name']}{_span(o['start'], o['end'])}"
                                            + (f", {o['terms']} terms" if o["terms"] > 1 else "") for o in offices[:20]))
    for rels, label in ((("gave",), "Speeches"), (("invented",), "Inventions and discoveries"), (("won",), "Won"),
                        (("signed",), "Signed"), (("authored",), "Writings")):
        xs = await db.links(q, rels, limit=12)
        if xs:
            out.append(f"{label}: " + "; ".join(f"{x['name']}{_when(x)}" for x in xs[:10]))
    for rel, label in (("party", "Party"), ("religion", "Religion"), ("occupation", "Occupation")):
        xs = await db.links(q, (rel,), limit=6)
        if xs:
            out.append(f"{label}: " + ", ".join(x["name"] for x in xs))
    out.append(await _in_sources(q))
    if p.get("enwiki"):
        out.append(f"English Wikipedia: {p['enwiki']}")
    return text("\n".join(x for x in out if x) + "\n\n" + WD + await _others(a["name"], rows))


async def h_explore_family(a: dict) -> list[TextContent]:
    top, rows = await _resolve(a["person"], "person")
    if not top:
        return text(f"No one named '{a['person']}' in the graph.")
    q, gens, way = top["qid"], int(a.get("generations") or 3), a.get("direction") or "both"
    p = await db.person(q)
    out = [f"Family of {top['name']}{_life(p) if p else ''} [{q}]"]
    names, edges = {q: top["name"]}, []
    up = await db.ancestors(q, gens) if way in ("ancestors", "both") else []
    if up:
        out.append("Ancestors:\n" + "\n".join(f"- {'  ' * (r['gen'] - 1)}{r['name']}{_life(r)} ({r['rel']}, generation {r['gen']}) [{r['qid']}]" for r in up))
        names.update({r["qid"]: r["name"] for r in up})
        edges += [(r["qid"], r["child"]) for r in up]
    for rel, label in (("spouse", "Spouses"), ("sibling", "Siblings")):
        seen: dict[str, dict] = {}
        for x in await db.links(q, (rel,)) + await db.links(q, (rel,), "in"):
            seen.setdefault(x["qid"], x)
        if seen:
            out.append(f"{label}: " + ", ".join(f"{x['name']}{_life(x)} [{x['qid']}]" for x in seen.values()))
    down = await db.descendants(q, gens) if way in ("descendants", "both") else []
    if down:
        out.append("Descendants:\n" + "\n".join(f"- {'  ' * (r['gen'] - 1)}{r['name']}{_life(r)} (generation {r['gen']}) [{r['qid']}]" for r in down[:150])
                   + (f"\n(+{len(down) - 150} more)" if len(down) > 150 else ""))
        names.update({r["qid"]: r["name"] for r in down})
        edges += [(r["parent"], r["qid"]) for r in down[:60]]
    if len(out) == 1:
        out.append("No family links recorded for this person.")
    lines = [f'  {x}["{_m(names[x])}"] --> {y}["{_m(names[y])}"]' for x, y in edges[:80] if x in names and y in names]
    if lines:
        out.append("\n".join(["```mermaid", "graph TD", *lines, "```"]))
    return text("\n\n".join(out) + "\n\n" + WD + await _others(a["person"], rows))


async def h_explore_life(a: dict) -> list[TextContent]:
    top, rows = await _resolve(a["person"], "person")
    if not top:
        return text(f"No one named '{a['person']}' in the graph.")
    q = top["qid"]
    p = await db.person(q)
    items = []
    if p and p.get("birth"):
        place = await db.links(q, ("born_in",))
        items.append((p["birth"], f"Born{' in ' + place[0]['name'] if place else ''}"))
    for r in await db.links(q, ("educated_at",)):
        items.append((r["start"] or "", f"Educated at {r['name']}"))
    for o in _offices(await db.links(q, ("held",), limit=80)):
        items.append((o["start"] or "", f"Held office: {o['name']}{_span(o['start'], o['end'])}"
                                         + (f", {o['terms']} terms" if o["terms"] > 1 else "")))
    verbs = {"participated_in": "Took part in", "fought_in": "Fought in", "signed": "Signed", "gave": "Gave",
             "invented": "Invented or discovered", "won": "Won"}
    for r in await db.links(q, tuple(verbs), limit=80):
        items.append((r["ev_start"] or "", f"{verbs[r['rel']]} {r['name']}{_when(r)} [{r['qid']}]"))
    for r in await db.links(q, ("authored",), limit=15):
        items.append((r["ev_start"] or "", f"Wrote {r['name']}"))
    if p and p.get("death"):
        place = await db.links(q, ("died_in",))
        items.append((p["death"], f"Died{' in ' + place[0]['name'] if place else ''}"))
    if not items:
        return text(f"No life events recorded for {top['name']} [{q}].")
    dated = sorted((x for x in items if x[0]), key=lambda x: _sortkey(x[0]))
    out = [f"Life of {top['name']}{_life(p) if p else ''} [{q}]"]
    out += [f"- {_dt(t)}: {what}" for t, what in dated] + [f"- {what}" for t, what in items if not t]
    for rel, label in (("party", "Party"), ("religion", "Religion"), ("award", "Awards")):
        xs = await db.links(q, (rel,), limit=8)
        if xs:
            out.append(f"{label}: " + ", ".join(x["name"] for x in xs))
    return text("\n".join(out) + "\n\n" + WD + await _others(a["person"], rows))


async def _item_card(top: dict, rows: list[dict], label: str) -> list[TextContent]:
    """A law, document, or other item that isn't stored as an event: what links to it and where it appears."""
    q = top["qid"]
    out = [f"{top['name']} [{q}]", top.get("description") or ""]
    for rel, lab in (("authored", "Written by"), ("signed", "Signed by"), ("gave", "Given by"), ("invented", "Invented by")):
        xs = await db.links(q, (rel,), "in", limit=30)
        if xs:
            out.append(f"{lab}: " + "; ".join(f"{x['name']}{_life(x)}" for x in xs))
    out.append(await _in_sources(q))
    return text("\n".join(x for x in out if x) + "\n\n" + WD + await _others(label, rows))


async def h_explore_event(a: dict) -> list[TextContent]:
    top, rows = await _resolve(a["event"], "event")
    if not top:
        top, rows = await _resolve(a["event"], kinds=("item",))
        if not top:
            return text(f"No event named '{a['event']}' in the graph. Try search_history for documents about it.")
        return await _item_card(top, rows, a["event"])
    q = top["qid"]
    e = await db.event(q)
    if not e:
        return await _item_card(top, rows, a["event"])
    k = e.get("kind") or "event"
    head = k[:1].upper() + k[1:] + (f" ({e['category']})" if e.get("category") and e["category"] != k else "")
    out = [f"{e['name']} [{q}]", e.get("description") or "",
           head + _span(e.get("start"), e.get("end"))
           + (f"; at {e['location']}" if e.get("location") else "") + (f"; {e['country']}" if e.get("country") else "")]
    if e.get("case_id"):
        cite = next((c for c in (e.get("citation") or "").split("; ") if "U.S." in c or "U. S." in c), e.get("citation"))
        out.append(f"This is a Supreme Court decision in our case collection: get_case with '{cite}'.")
    if e["name"] in CONFESSION_FOR:
        out.append(f"The text it produced is in the Study Bible's confessions: get_confession with '{CONFESSION_FOR[e['name']]}'.")
    elif "church" in (e.get("categories") or ""):
        out.append("For writings from and about it, use the Study Bible's search_theology and get_church_fathers.")
    for rels, label, way in ((("part_of",), "Part of", "out"), (("part_of",), "Includes", "in"),
                             (("follows",), "After", "out"), (("followed_by",), "Before", "out"),
                             (("caused_by",), "Causes", "out"), (("led_to",), "Effects", "out"),
                             (("party",), "Parties", "out")):
        xs = await db.links(q, rels, way, limit=40)
        if xs:
            out.append(f"{label}: " + "; ".join(f"{x['name']}{_when(x)} [{x['qid']}]" for x in xs))
    for rel, label in (("won", "Won by"), ("gave", "Given by"), ("invented", "Invented or discovered by"),
                       ("authored", "Written by"), ("created", "Created by"), ("signed", "Signed by"),
                       ("participated_in", "People who took part"), ("fought_in", "Fought in it")):
        xs = await db.links(q, (rel,), "in", limit=400)
        if xs:
            xs.sort(key=lambda x: -(x["sitelinks"] or 0))
            out.append(f"{label} ({len(xs)}): " + "; ".join(f"{x['name']}{_life(x)}" for x in xs[:40])
                       + (f"; and {len(xs) - 40} more" if len(xs) > 40 else ""))
    ms = await db.mentions_of(q, 10)
    if ms:
        out.append("In our sources: " + "; ".join(f"{m['title']} [{m['doc_type']} {m['doc_id']}]" for m in ms))
    if e.get("enwiki"):
        out.append(f"English Wikipedia: {e['enwiki']}")
    return text("\n".join(x for x in out if x) + "\n\n" + WD + await _others(a["event"], rows))


async def h_explore_place(a: dict) -> list[TextContent]:
    top, rows = await _resolve(a["place"], "place")
    if not top:
        top, rows = await _resolve(a["place"], kinds=("item",))
        if not top:
            return text(f"No place named '{a['place']}' in the graph.")
    q = top["qid"]
    pl = await db.place(q)
    out = [f"{pl['name']} [{q}]", pl.get("description") or "",
           ", ".join(x for x in (pl.get("kind"), pl.get("located_in"), pl.get("country")) if x)]
    if pl.get("lat") is not None:
        out.append(f"Coordinates: {pl['lat']:.4f}, {pl['lon']:.4f}")
    evs = await db.links(q, ("located_at",), "in", limit=400)
    if evs:
        evs = sorted(sorted(evs, key=lambda x: -(x["sitelinks"] or 0))[:60], key=lambda x: _sortkey(x["ev_start"] or ""))
        out.append("Events here (the best known, in order):\n" + "\n".join(f"- {x['name']}{_when(x)} [{x['qid']}]" for x in evs))
    for rel, label in (("born_in", "Born here"), ("died_in", "Died here")):
        xs = await db.links(q, (rel,), "in", limit=400)
        if xs:
            xs.sort(key=lambda x: -(x["sitelinks"] or 0))
            out.append(f"{label} ({len(xs)}): " + "; ".join(f"{x['name']}{_life(x)}" for x in xs[:25]))
    return text("\n".join(x for x in out if x) + "\n\n" + WD + await _others(a["place"], rows))


async def h_connection(a: dict) -> list[TextContent]:
    async def pick(name):
        top, rows = await _resolve(name, kinds=("person", "event"))
        return (top, rows) if top else await _resolve(name)
    (x, xr), (y, yr) = await pick(a["from"]), await pick(a["to"])
    if not x or not y:
        return text(f"Couldn't find {'either name' if not x and not y else repr(a['from'] if not x else a['to'])} in the graph.")
    path = await db.connection_path(x["qid"], y["qid"])
    others = await _others(a["from"], xr) + await _others(a["to"], yr)
    if path is None:
        return text(f"No connection within six links between {x['name']} [{x['qid']}] and {y['name']} [{y['qid']}] "
                    "through family, teachers, succession, shared events, signed documents, or co-written works." + others)
    lines = [f"{x['name']} to {y['name']}, {len(path)} link{'s' if len(path) != 1 else ''}:"]
    mer = ["```mermaid", "graph LR"]
    for s in path:
        via = f" as {s['via_name']}" if s["rel"] == "succeeded" and s.get("via_name") else ""
        lines.append("- " + PHRASE.get(s["rel"], "{a} " + s["rel"] + " {b}").format(
            a=f"{s['src_name']} [{s['src']}]", b=f"{s['dst_name']} [{s['dst']}]") + via)
        mer.append(f'  {s["src"]}["{_m(s["src_name"])}"] -- {SHORT.get(s["rel"], s["rel"])} --> {s["dst"]}["{_m(s["dst_name"])}"]')
    mer.append("```")
    return text("\n".join(lines) + "\n\n" + "\n".join(mer) + "\n\n" + WD + others)


async def h_timeline(a: dict) -> list[TextContent]:
    y0 = int(a["year_from"])
    y1 = int(a.get("year_to") or y0)
    if y1 < y0:
        y0, y1 = y1, y0
    country = None
    if a.get("country"):
        c = await db.find_entities(a["country"], kinds=("place", "item"), limit=3)
        country = c[0]["qid"] if c else None
    evs = await db.timeline(y0, y1, country, a.get("kind"), 40)
    eras = await db.eras_during(y0, y1, country if a.get("country") else None) if not a.get("kind") else []
    lives = await db.notable_lives(y0, y1, country, 12)
    span = _year(y0) if y0 == y1 else f"{_year(y0)} to {_year(y1)}"
    out = [f"{span}{' in ' + a['country'] if a.get('country') else ''}{', ' + a['kind'] if a.get('kind') else ''}"]
    if eras:
        out.append("Eras: " + "; ".join(f"{r['name']}{_span(r['start'], r['end'])}" for r in eras))
    if evs:
        out.append("Events (the 40 best known, in order):\n" + "\n".join(
            f"- {_dt(r['start'] or _year(r['start_year']))}: {r['name']}"
            f"{' (' + r['kind'] + ')' if r.get('kind') else ''}{', ' + r['country'] if r.get('country') else ''} [{r['qid']}]" for r in evs))
    if lives:
        out.append("Alive then, among the best known: " + "; ".join(f"{r['name']}{_life(r)}" for r in lives))
    if len(out) == 1:
        out.append("Nothing recorded for that span.")
    return text("\n\n".join(out) + "\n\n" + WD)


async def h_succession(a: dict) -> list[TextContent]:
    if a.get("office"):
        top, rows = await _resolve(a["office"], "item")
        holders = await db.office_holders(top["qid"]) if top else []
        if not holders:
            for r in rows[1:]:
                holders = await db.office_holders(r["qid"])
                if holders:
                    top = r
                    break
        if not holders:
            return text(f"No holders recorded for '{a['office']}'. Try the full title ('Governor of Illinois').")
        return text(f"{top['name']} [{top['qid']}], {len(holders)} terms recorded:\n" + "\n".join(
            f"- {h['name']}{_life(h)}{_span(h['start'], h['end'])}" for h in holders) + "\n\n" + WD)
    if a.get("person"):
        top, rows = await _resolve(a["person"], "person")
        if not top:
            return text(f"No one named '{a['person']}' in the graph.")
        q = top["qid"]
        before = {r["via"]: r for r in await db.links(q, ("succeeded",)) if r.get("via")}
        after = {r["via"]: r for r in await db.links(q, ("succeeded",), "in") if r.get("via")}
        lines = []
        for o in await db.links(q, ("held",), limit=80):
            b, f = before.get(o["qid"]), after.get(o["qid"])
            lines.append(f"- {o['name']}{_span(o['start'], o['end'])}"
                         + (f"; before: {b['name']}" if b else "") + (f"; after: {f['name']}" if f else ""))
        return text(f"Offices of {top['name']} [{q}]:\n" + ("\n".join(dict.fromkeys(lines)) or "none recorded") + "\n\n" + WD
                    + await _others(a["person"], rows))
    return text("Give an office or a person.")


async def h_people_in_document(a: dict) -> list[TextContent]:
    if a.get("case"):
        c = await db.find_case(a["case"])
        if not c:
            return text("No case found by that citation or name.")
        doc_type, doc_id, title = "case", c["id"], f"{c['name']}, {c['cite']} ({c['year']})"
    elif a.get("document_id"):
        d = await db.document(int(a["document_id"]))
        if not d:
            return text("No document with that id.")
        doc_type, doc_id, title = "document", d["id"], _cite(d)
    else:
        return text("Give a document_id or a case.")
    ms = await db.mentions_in(doc_type, doc_id)
    if not ms:
        return text(f"{title}: no people or events linked yet.")
    how = {"stated": "stated in the record", "hand": "tagged by reading", "match": "name found in the text"}
    groups: dict[str, list[str]] = {}
    for m in ms:
        groups.setdefault(how.get(m["how"], m["how"]), []).append(
            f"- {m['name']}{_life(m)}{', ' + m['role'] if m.get('role') else ''} [{m['qid']}]")
    return text(title + "\n\n" + "\n\n".join(f"{k}:\n" + "\n".join(v) for k, v in groups.items()) + "\n\n" + WD)


HANDLERS = {"search_history": h_search, "find_documents": h_find, "get_document": h_get,
            "get_constitution": h_constitution, "get_flag_code": h_flag, "constitution_test_guide": h_guide,
            "search_cases": h_search_cases, "get_case": h_get_case, "get_statute": h_statute,
            "get_constitution_annotation": h_conan, "lookup_legislator": h_legislator, "define_term": h_define,
            "lookup_person": h_lookup_person, "explore_family": h_explore_family, "explore_life": h_explore_life,
            "explore_event": h_explore_event, "explore_historic_place": h_explore_place,
            "find_historical_connection": h_connection, "timeline": h_timeline, "succession": h_succession,
            "people_in_document": h_people_in_document}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    global db, db_stamp
    path = get_db_path()
    # the web app swaps in a newer copy of the file while this server runs; reopen when it changes
    stamp = path.stat().st_mtime_ns if path.exists() else None
    if db is not None and stamp != db_stamp:
        with contextlib.suppress(Exception):
            await db.conn.close()
        db = None
    if db is None:
        if not path.exists():
            return text(f"Social sciences database not found at {path}. Run scripts/socialsci/build_social_sciences_db.py.")
        db = SocialSciencesDB(path)
        await db.connect()
        db_stamp = stamp
    handler = HANDLERS.get(name)
    if not handler:
        return text(f"Unknown tool: {name}")
    try:
        return await handler(arguments or {})
    except Exception as e:  # noqa: BLE001
        logger.exception("tool %s failed", name)
        return text(f"Error in {name}: {e}")


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [Prompt(name="historian", description="The Historian persona for the Social Sciences Mode.",
                   arguments=[PromptArgument(name="question", description="Optional question", required=False)])]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    persona = (PROMPTS / "historian.md").read_text(encoding="utf-8")
    q = (arguments or {}).get("question")
    msg = persona + (f"\n\n---\n\nQuestion: {q}" if q else "")
    return GetPromptResult(messages=[PromptMessage(role="user", content=TextContent(type="text", text=msg))])


async def run_stdio_server() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


@click.command()
@click.option("--transport", type=click.Choice(["stdio"]), default="stdio")
@click.option("--db-path", type=click.Path(), envvar="SOCIAL_SCIENCES_DB")
def main(transport: str, db_path: str | None) -> None:
    if db_path:
        os.environ["SOCIAL_SCIENCES_DB"] = db_path
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
