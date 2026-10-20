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


HANDLERS = {"search_history": h_search, "find_documents": h_find, "get_document": h_get,
            "get_constitution": h_constitution, "get_flag_code": h_flag, "constitution_test_guide": h_guide}


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
