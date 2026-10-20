"""Social Sciences MCP server: history, government and civics tools over the owned social_sciences.db.

Self-hosted like the Study Bible server: every answer comes from data downloaded once and kept
(Avalon Project, Miller Center speeches, DocSouth, the Illinois Constitution, the U.S. Flag Code,
the Reading Room's history shelves). No tool calls an outside service at question time.
"""
from __future__ import annotations

import asyncio
import logging
import os
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
            "employment. Give a citation ('18 U.S.C. § 1001', '720 ILCS 5/12-3') for the exact section, or a "
            "query to search."
        ),
        inputSchema={"type": "object", "properties": {
            "citation": {"type": "string"},
            "query": {"type": "string"},
            "code": {"type": "string", "enum": ["usc", "ilcs"], "description": "Limit a search to one code."},
        }},
    ),
    Tool(
        name="get_constitution_annotation",
        description=(
            "The Constitution Annotated (Congressional Research Service, 2022): clause-by-clause essays on how "
            "each part of the Constitution has been understood and applied, with the leading cases. Give an "
            "article/section/clause or an amendment (with optional section) to list its essays, an essay_id to "
            "read one, or a query to search."
        ),
        inputSchema={"type": "object", "properties": {
            "article": {"type": "string"}, "section": {"type": "string"}, "clause": {"type": "string"},
            "amendment": {"type": "string"}, "essay_id": {"type": "string"}, "query": {"type": "string"},
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
                key=lambda s: int(''.join(ch for ch in s.split('Article ')[1].split(' ')[0] if ch.isdigit()) or 99)),
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


async def h_statute(a: dict) -> list[TextContent]:
    if a.get("citation"):
        rows = await db.statute(a["citation"])
        if rows:
            return text("\n\n".join(f"{r['citation']}. {r['heading']}\n{r['text']}" for r in rows))
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
        return text(f"{rows[0]['essay_id']} {rows[0]['title']}\n{src}\n\n{rows[0]['text']}" if rows else "No essay with that id.")
    prov = _provision(a)
    if prov:
        rows = await db.conan(provision=prov)
        if rows:
            return text(f"Essays on {prov} ({len(rows)}). Open one with essay_id.\n{src}\n\n" +
                        "\n".join(f"- {r['essay_id']} {r['title']}" for r in rows[:60]))
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


HANDLERS = {"search_history": h_search, "find_documents": h_find, "get_document": h_get,
            "get_constitution": h_constitution, "get_flag_code": h_flag, "constitution_test_guide": h_guide,
            "search_cases": h_search_cases, "get_case": h_get_case, "get_statute": h_statute,
            "get_constitution_annotation": h_conan, "lookup_legislator": h_legislator, "define_term": h_define}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    global db
    if db is None:
        path = get_db_path()
        if not path.exists():
            return text(f"Social sciences database not found at {path}. Run scripts/socialsci/build_social_sciences_db.py.")
        db = SocialSciencesDB(path)
        await db.connect()
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
