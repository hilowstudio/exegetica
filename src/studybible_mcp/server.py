#!/usr/bin/env python3
"""
Study Bible MCP Server.

Provides Bible-study tools (readable text, Greek/Hebrew lexicons, morphology,
cross-references, proper names, a Theographic people/place graph, and open study
notes) over the Model Context Protocol. Supports stdio and Streamable HTTP.

Adapted from djayatillake/studybible-mcp (MIT); trimmed to a self-hosted,
data-owning core.
"""

import asyncio
import contextlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import click
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
)

from .database import (
    StudyBibleDB, BOOK_ABBREV_MAP, SINGLE_CHAPTER_BOOKS,
    DEUTERO_BOOKS, resolve_folded_ref, _NAME_TO_OSIS, _OSIS_TO_NAME,
)
from .tools import (
    TOOLS,
    format_lexicon_entry, format_verse, format_name_entry,
    format_genealogy, format_person_events, format_place_history,
    format_passage_entities, format_connection_path, format_enriched_verse,
    mermaid_genealogy, mermaid_connection_path, mermaid_person_timeline,
    mermaid_place_network,
    format_study_notes, format_dictionary_article, format_key_terms,
)
from .hermeneutics import get_genre_from_reference, format_genre_guidance
from .parsers.commentaries import COMMENTARIES
from .clients import OPTIONAL_TRANSLATIONS, ATTRIBUTION, fetch_optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("study-bible-mcp")

# ---------------------------------------------------------------------------
# The Theologian persona (MCP prompt + always-on server orientation)
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_persona() -> str:
    """Load the full Theologian persona text (falls back to a stub if missing)."""
    try:
        return (_PROMPTS_DIR / "theologian.md").read_text(encoding="utf-8").strip()
    except OSError:
        logger.warning("theologian.md not found in %s", _PROMPTS_DIR)
        return (
            "# The Theologian\n\nRespond as a Reformed, exegesis-first pastoral "
            "theologian. Ground every claim in the Study Bible tools and cite what "
            "you draw on."
        )


# Concise, always-on orientation delivered to the client at connect time. The
# full persona stays behind the invokable "theologian" prompt so ordinary tool
# use is not forced into character.
SERVER_INSTRUCTIONS = (
    "This connector serves pastors, theologians, and seminary students with "
    "readable translations, Hebrew/Greek lexicons and morphology, a concordance, "
    "cross-references and UBS parallels, a people/place graph, public-domain "
    "commentaries, a patristic catena, and the creeds, confessions, and "
    "catechisms. Work exegesis-first: establish the text in its grammatical, "
    "historical, and literary context before drawing theology, read Scripture "
    "christotelically, and ground answers in these tools rather than memory, "
    "citing what you draw on. For the full pastoral-theological voice and its "
    "doctrinal commitments (Reformed, Progressive Covenantalist, Marshall on "
    "sanctification), invoke the 'theologian' prompt."
)

server = Server("study-bible", version="0.1.0", instructions=SERVER_INSTRUCTIONS)

# Database connection (initialized lazily on first tool call)
db: StudyBibleDB | None = None


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """Expose The Theologian as an invokable prompt."""
    return [
        Prompt(
            name="theologian",
            description=(
                "Answer as The Theologian: a Reformed, exegesis-first pastoral "
                "voice (Progressive Covenantalism; Walter Marshall on "
                "sanctification) that grounds counsel and exposition in the "
                "Study Bible tools. Optionally pass a question to answer in "
                "character."
            ),
            arguments=[
                PromptArgument(
                    name="question",
                    description="The theological or pastoral question to answer in character (optional).",
                    required=False,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Return the persona text, optionally seeded with the user's question."""
    if name != "theologian":
        raise ValueError(f"Unknown prompt: {name}")

    persona = _load_persona()
    question = (arguments or {}).get("question", "").strip()
    body = persona if not question else f"{persona}\n\n---\n\nNow answer as this mind:\n\n{question}"
    return GetPromptResult(
        description="The Theologian — Reformed, exegesis-first pastoral voice.",
        messages=[
            PromptMessage(role="user", content=TextContent(type="text", text=body)),
        ],
    )


def text(msg: str) -> list[TextContent]:
    """Wrap a string in a single-element TextContent list."""
    return [TextContent(type="text", text=msg)]


def _book_abbr(book_str: str) -> str:
    """Resolve a book name/abbreviation to its internal code."""
    return BOOK_ABBREV_MAP.get(book_str.lower().strip(), book_str[:3].title())


def _is_single_chapter(book_str: str) -> bool:
    """True for the 5 single-chapter books, where a bare 'Book N' means verse N."""
    return _book_abbr(book_str) in SINGLE_CHAPTER_BOOKS


def _parse_passage(reference: str) -> tuple[str, int, int, int] | None:
    """Parse a passage reference to (book_abbr, chapter, verse_start, verse_end).

    'Romans 3:21-26' -> ('Rom', 3, 21, 26); 'Psalm 23' -> ('Psa', 23, 1, 999)
    whole chapter; 'John 3:16' -> ('Jhn', 3, 16, 16); 'Jude 3' -> ('Jud', 1, 3, 3).
    Folded deuterocanon units resolve too ('Susanna 5' -> ('Dan', 13, 5, 5)).
    """
    folded = resolve_folded_ref(reference)
    if folded:
        return folded
    m = re.match(r'^(.+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$', reference.strip())
    if not m:
        return None
    book_str, n, v1, v2 = m.groups()
    book_abbr = _book_abbr(book_str)
    if v1 is None:
        if _is_single_chapter(book_str):
            return (book_abbr, 1, int(n), int(n))   # 'Jude 3' -> verse 3
        return (book_abbr, int(n), 1, 999)          # 'Psalm 23' -> whole chapter
    return (book_abbr, int(n), int(v1), int(v2) if v2 else int(v1))


def _passage_words(verse_rows: list[dict]) -> list[dict]:
    """Flatten the per-word tag dicts across a set of verse rows."""
    out: list[dict] = []
    for row in verse_rows:
        raw = row.get("word_data")
        if not raw:
            continue
        try:
            words = json.loads(raw)
        except (ValueError, TypeError):
            continue
        out.extend(w for w in words if isinstance(w, dict))
    return out


async def _vocabulary_rows(words: list[dict], threshold: int) -> list[tuple[int, dict]]:
    """Rare words (corpus frequency <= threshold), deduped by Strong's, rarest first."""
    strongs = [(w.get("strongs") or "").strip().upper() for w in words]
    freqs = await db.get_frequencies([s for s in strongs if s])
    best: dict[str, tuple[int, dict]] = {}
    for w in words:
        s = (w.get("strongs") or "").strip().upper()
        if not s or s not in freqs:
            continue
        f = freqs[s]
        if f > threshold:
            continue
        if s not in best or f < best[s][0]:
            best[s] = (f, w)
    return sorted(best.values(), key=lambda t: (t[0], t[1].get("word", "")))


def _format_vocabulary(rows: list[tuple[int, dict]], threshold: int, heading: str) -> str:
    if not rows:
        return f"*No words at or below {threshold} occurrences in {heading}.*"
    lines = [f"### Vocabulary — {heading} (≤ {threshold}× in the corpus)", "",
             "| Freq | Word | Gloss | Strong's |", "| ---: | --- | --- | --- |"]
    for f, w in rows:
        word = (w.get("word") or "").replace("|", "/")
        gloss = (w.get("gloss") or "").replace("|", "/").strip()
        strongs = w.get("strongs", "")
        lines.append(f"| {f} | {word} | {gloss} | {strongs} |")
    return "\n".join(lines)


def _route_deutero(reference: str, book: str, requested: str) -> str:
    """Deuterocanon text is bundled only in WEB, so route those references there.

    Keys off intent: a pure deuterocanon book code, or a folded citation
    (Susanna, Bel, Letter of Jeremiah, Psalm 151). Canonical chapters and
    explicit BYO-key translations are left untouched.
    """
    if requested in OPTIONAL_TRANSLATIONS:
        return requested
    if book in DEUTERO_BOOKS or resolve_folded_ref(reference):
        return "WEB"
    return requested


def _resolve_commentary_ids(sources: list[str]) -> list[str]:
    """Map user-supplied commentary names/ids to known commentary ids."""
    ids = []
    for s in sources:
        key = str(s).strip().lower()
        if key in COMMENTARIES:
            ids.append(key)
            continue
        match = next((cid for cid, name in COMMENTARIES.items()
                      if key in cid or key in name.lower()), None)
        if match:
            ids.append(match)
    return ids


def get_db_path() -> Path:
    """Locate the SQLite database, checking env var then common locations."""
    if env_path := os.environ.get("STUDY_BIBLE_DB"):
        return Path(env_path)

    pkg_dir = Path(__file__).parent
    local_db = pkg_dir.parent.parent / "db" / "study_bible.db"
    if local_db.exists():
        return local_db

    cwd_db = Path.cwd() / "db" / "study_bible.db"
    if cwd_db.exists():
        return cwd_db

    for candidate in (Path("/app/db/study_bible.db"), Path("/data/study_bible.db")):
        if candidate.exists():
            return candidate

    return local_db


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Bible study tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch a tool call to its handler, initializing the DB on first use."""
    global db

    if db is None:
        db_path = get_db_path()
        if not db_path.exists():
            return text(
                f"Database not found at {db_path}. "
                "Run 'python scripts/build_database.py' first."
            )
        db = StudyBibleDB(db_path)
        await db.connect()

    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return text(f"Unknown tool: {name}")

    try:
        return await handler(arguments)
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return text(f"Error: {str(e)}")


# =========================================================================
# Text / lexicon / morphology handlers
# =========================================================================

async def handle_word_study(args: dict[str, Any]) -> list[TextContent]:
    """Deep dive into a Greek or Hebrew word."""
    strongs = args.get("strongs")
    word = args.get("word")
    language = args.get("language", "greek")

    if strongs:
        entry = await db.get_lexicon_entry(strongs)
    elif word:
        entries = await db.search_lexicon(word, language=language, limit=1)
        entry = entries[0] if entries else None
    else:
        return text("Please provide either 'strongs' number or 'word' to study.")

    if not entry:
        return text("No entry found for the given word/Strong's number.")

    verses = await db.get_verses_with_strongs(entry["strongs"], limit=5)
    result = format_lexicon_entry(entry)

    if verses:
        result += "\n\n## Example Passages\n"
        for v in verses:
            result += f"\n**{v['reference']}**: {v['text_english']}\n"

    return text(result)


async def handle_lookup_verse(args: dict[str, Any]) -> list[TextContent]:
    """Get a verse in a readable translation, with optional original + interlinear."""
    reference = args.get("reference", "")
    translation = (args.get("translation") or "BSB").upper()
    include_original = args.get("include_original", True)
    include_morphology = args.get("include_morphology", False)

    if not reference:
        return text("Please provide a verse reference (e.g., 'John 3:16').")

    normalized = db._normalize_reference(reference)
    verse = await db.get_verse(reference)
    translation = _route_deutero(reference, normalized.split(".")[0], translation)

    readable_text = None
    readable_note = None
    if translation in OPTIONAL_TRANSLATIONS:
        readable_text, readable_note = await fetch_optional(translation, reference)
    elif await db.has_translations():
        row = await db.get_translation_verse(translation, normalized)
        readable_text = row["text"] if row else None

    if not verse and not readable_text:
        return text(readable_note or f"Verse not found: {reference}")

    if verse:
        result = format_verse(
            verse, include_original, include_morphology,
            readable_text=readable_text,
            translation_label=translation if readable_text else None,
        )
        if not readable_text:
            if translation in OPTIONAL_TRANSLATIONS and readable_note:
                result += f"\n*{readable_note}*\n"
            else:
                result += f"\n*No {translation} text for this verse — showing the STEPBible word-gloss.*\n"
    else:
        # Translation-only verse (e.g. a deuterocanon verse absent from the tagged text).
        result = f"## {_format_xref_target(normalized)}\n\n**{translation}:** {readable_text}\n"

    if readable_text and translation in ATTRIBUTION:
        result += f"\n{ATTRIBUTION[translation]}\n"

    genre = get_genre_from_reference(reference)
    if genre:
        result += f"\n\n---\n{format_genre_guidance(genre)}"

    if args.get("reader_mode") and verse and await db.has_word_frequency():
        threshold = int(args.get("vocab_threshold") or 30)
        vocab = await _vocabulary_rows(_passage_words([verse]), threshold)
        result += "\n\n---\n" + _format_vocabulary(vocab, threshold, reference)

    result += (
        f"\n\n---\n*Cross-references available via `get_cross_references` "
        f"(reference='{reference}').*"
    )
    return text(result)


async def handle_get_passage(args: dict[str, Any]) -> list[TextContent]:
    """Return a readable passage (verse range or whole chapter) in a translation."""
    reference = args.get("reference", "")
    translation = (args.get("translation") or "BSB").upper()
    if not reference:
        return text("Please provide a passage reference (e.g., 'Romans 3:21-26' or 'Psalm 23').")

    if translation in OPTIONAL_TRANSLATIONS:
        live, err = await fetch_optional(translation, reference)
        if not live:
            return text(err or f"No {translation} text for {reference}.")
        out = f"## {reference} ({translation})\n\n{live}\n"
        if translation in ATTRIBUTION:
            out += f"\n{ATTRIBUTION[translation]}\n"
        return text(out)

    if not await db.has_translations():
        return text("Translations not available. Run the translation download/import scripts.")

    parsed = _parse_passage(reference)
    if not parsed:
        return text(f"Could not parse passage: {reference}. Try 'Romans 3:21-26' or 'Psalm 23'.")
    book, chapter, v1, v2 = parsed
    translation = _route_deutero(reference, book, translation)
    verses = await db.get_translation_passage(translation, book, chapter, v1, v2)
    if not verses:
        avail = ", ".join(await db.available_translations())
        return text(f"No {translation} text found for {reference}. Available: {avail}.")

    lines = [f"## {reference} ({translation})", ""]
    for v in verses:
        lines.append(f"**{v['verse']}** {v['text']}")

    if args.get("reader_mode") and await db.has_word_frequency():
        threshold = int(args.get("vocab_threshold") or 30)
        trows = await db.get_verses_in_range(book, chapter, v1, v2)
        if trows:
            vocab = await _vocabulary_rows(_passage_words(trows), threshold)
            lines.append("\n---\n" + _format_vocabulary(vocab, threshold, reference))
    return text("\n".join(lines))


async def handle_compare_translations(args: dict[str, Any]) -> list[TextContent]:
    """Show one verse across several translations side by side."""
    reference = args.get("reference", "")
    requested = args.get("translations")
    if not reference:
        return text("Please provide a verse reference (e.g., 'John 3:16').")
    if not await db.has_translations():
        return text("Translations not available. Run the translation download/import scripts.")

    normalized = db._normalize_reference(reference)
    tr_list = [t.upper() for t in requested] if requested else await db.available_translations()
    # Deuterocanon is bundled only in WEB; make sure it is in the comparison set.
    if (normalized.split(".")[0] in DEUTERO_BOOKS or resolve_folded_ref(reference)) and "WEB" not in tr_list:
        tr_list = ["WEB"] + tr_list

    lines = [f"## {reference} — Translation Comparison", ""]
    found = False
    attributions: set[str] = set()
    for tr in tr_list:
        if tr in OPTIONAL_TRANSLATIONS:
            live, err = await fetch_optional(tr, reference)
            if live:
                lines.append(f"**{tr}:** {live}\n")
                found = True
                if tr in ATTRIBUTION:
                    attributions.add(ATTRIBUTION[tr])
            else:
                lines.append(f"**{tr}:** _{err}_\n")
        else:
            row = await db.get_translation_verse(tr, normalized)
            if row:
                lines.append(f"**{tr}:** {row['text']}\n")
                found = True
    if not found:
        return text(f"No translation text found for {reference}.")
    lines.extend(sorted(attributions))
    return text("\n".join(lines))


async def handle_vocabulary_list(args: dict[str, Any]) -> list[TextContent]:
    """Reader-mode vocabulary: the rarest original-language words in a passage."""
    reference = args.get("reference", "")
    threshold = int(args.get("threshold") or 30)
    if not reference:
        return text("Please provide a passage reference (e.g., 'Romans 3:21-26').")
    if not await db.has_word_frequency():
        return text("Word-frequency data not available. Run scripts/build_word_frequency.py.")

    parsed = _parse_passage(reference)
    if not parsed:
        return text(f"Could not parse passage: {reference}. Try 'Romans 3:21-26' or 'Psalm 23'.")
    book, chapter, v1, v2 = parsed
    rows = await db.get_verses_in_range(book, chapter, v1, v2)
    if not rows:
        return text(
            f"No tagged original-language text for {reference}. "
            "Frequency vocabulary covers the Hebrew OT and Greek NT."
        )
    vocab = await _vocabulary_rows(_passage_words(rows), threshold)
    body = _format_vocabulary(vocab, threshold, reference)
    return text(f"## Reader Vocabulary\n\n{body}\n\n"
                f"*Rarest first; frequency is occurrences across the tagged corpus. "
                f"Raise `threshold` to include more common words.*")


async def handle_search_lexicon(args: dict[str, Any]) -> list[TextContent]:
    """Search across lexicon entries by English meaning."""
    query = args.get("query", "")
    language = args.get("language")  # None means both
    limit = args.get("limit", 10)

    if not query:
        return text("Please provide a search query.")

    entries = await db.search_lexicon(query, language=language, limit=limit)
    if not entries:
        return text(f"No entries found for '{query}'.")

    result = f"## Lexicon Search: '{query}'\n\nFound {len(entries)} entries:\n\n"
    for entry in entries:
        result += f"### {entry['strongs']} - {entry['word']} ({entry['transliteration']})\n"
        result += f"{entry['short_definition']}\n\n"
    return text(result)


async def handle_parse_morphology(args: dict[str, Any]) -> list[TextContent]:
    """Explain a grammatical parsing code."""
    code = args.get("code", "")
    language = args.get("language", "greek")

    if not code:
        return text("Please provide a morphology code to parse.")

    parsing = await db.get_morphology(code, language)
    if not parsing:
        return text(f"Unknown morphology code: {code}")

    result = f"## Morphology: {code}\n\n"
    result += f"**Language**: {parsing['language'].title()}\n"
    result += f"**Part of Speech**: {parsing['part_of_speech']}\n"
    for field, label in (
        ("person", "Person"), ("number", "Number"), ("tense", "Tense"),
        ("voice", "Voice"), ("mood", "Mood"), ("case_value", "Case"),
        ("gender", "Gender"),
    ):
        if parsing.get(field):
            result += f"**{label}**: {parsing[field]}\n"
    result += f"\n**Full Parsing**: {parsing['parsing']}\n"
    return text(result)


async def handle_search_by_strongs(args: dict[str, Any]) -> list[TextContent]:
    """Find all verses containing a Strong's number."""
    strongs = args.get("strongs", "")
    limit = args.get("limit", 20)

    if not strongs:
        return text("Please provide a Strong's number (e.g., 'G26' or 'H3068').")

    entry = await db.get_lexicon_entry(strongs)
    if not entry:
        return text(f"Unknown Strong's number: {strongs}")

    verses = await db.get_verses_with_strongs(strongs, limit=limit)
    result = f"## Verses with {strongs} ({entry['word']} - {entry['transliteration']})\n\n"
    result += f"*{entry['short_definition']}*\n\n"
    if verses:
        for v in verses:
            result += f"**{v['reference']}**: {v['text_english']}\n\n"
    else:
        result += "No verses found with this Strong's number in the database.\n"
    return text(result)


# =========================================================================
# Cross-reference handlers
# =========================================================================

def _format_xref_target(raw: str) -> str:
    """Pretty-print an internal ref: 'Jhn.3.16' -> 'Jhn 3:16', and a range
    'Jhn.1.1-Jhn.1.3' -> 'Jhn 1:1-3'."""
    def fmt_one(r: str) -> str:
        p = r.split(".")
        return f"{p[0]} {p[1]}:{p[2]}" if len(p) == 3 else r

    if "-" in raw:
        start, end = raw.split("-", 1)
        sp, ep = start.split("."), end.split(".")
        if len(sp) == 3 and len(ep) == 3:
            if sp[0] == ep[0] and sp[1] == ep[1]:
                return f"{sp[0]} {sp[1]}:{sp[2]}-{ep[2]}"
            if sp[0] == ep[0]:
                return f"{sp[0]} {sp[1]}:{sp[2]}-{ep[1]}:{ep[2]}"
            return f"{fmt_one(start)}–{fmt_one(end)}"
        return raw
    return fmt_one(raw)


async def handle_get_cross_references(args: dict[str, Any]) -> list[TextContent]:
    """Find related passages by reference or theme."""
    reference = args.get("reference")
    theme = args.get("theme")
    source_filter = args.get("source")
    limit_raw = args.get("limit")
    limit = int(limit_raw) if limit_raw is not None else 8
    min_strength_raw = args.get("min_strength")
    min_strength = int(min_strength_raw) if min_strength_raw is not None else None

    if theme:
        refs = await db.get_thematic_references(theme)
        if not refs:
            return text(f"No cross-references found for theme '{theme}'.")
        result = f"## Cross-References: {theme}\n\n"
        for ref in refs:
            result += f"- **{ref['reference']}**: {ref['note']}\n"
        return text(result)

    if reference:
        refs = await db.get_cross_references(
            reference, source_filter=source_filter, limit=limit, min_strength=min_strength,
        )
        if not refs:
            return text(
                f"No cross-references found for {reference}."
                + (f" (source filter: {source_filter})" if source_filter else "")
            )

        result = f"## Cross-References for {reference}\n\n"
        for ref in refs:
            target = _format_xref_target(ref.get("target", ""))
            note = ref.get("note")
            votes = ref.get("relevance")
            tag = f"  *(votes: {votes})*" if votes else ""
            result += f"- {target}{tag}"
            if note:
                result += f" — {note}"
            result += "\n"
        result += "\n*Source: [OpenBible.info](https://www.openbible.info) cross-references (CC BY 4.0).*\n"
        return text(result)

    return text("Please provide either 'reference' or 'theme'.")


# =========================================================================
# Proper-name handler
# =========================================================================

async def handle_lookup_name(args: dict[str, Any]) -> list[TextContent]:
    """Look up a biblical person/place/thing, enriched with ACAI data when present."""
    name = args.get("name", "")
    name_type = args.get("type")

    if not name:
        return text("Please provide a name to look up.")

    entries = await db.lookup_name(name, name_type=name_type)
    if not entries:
        return text(f"No entries found for '{name}'.")

    acai_data = None
    try:
        if await db.has_acai_data():
            acai_data = await db.get_acai_entity(name)
    except Exception:
        pass

    result = f"## Biblical Names: {name}\n\n"
    for entry in entries:
        result += format_name_entry(entry, acai_data=acai_data)
        result += "\n---\n\n"
    return text(result)


# =========================================================================
# Graph handlers (Theographic Bible Metadata)
# =========================================================================

async def _check_graph_data() -> list[TextContent] | None:
    if not await db.graph_has_data():
        return text(
            "Graph data not available. Run 'python scripts/import_theographic.py' "
            "to import Theographic Bible Metadata."
        )
    return None


async def handle_explore_genealogy(args: dict[str, Any]) -> list[TextContent]:
    """Trace a person's family tree."""
    if err := await _check_graph_data():
        return err

    person_name = args.get("person", "")
    direction = args.get("direction", "both")
    generations = args.get("generations", 5)
    if not person_name:
        return text("Please provide a person's name.")

    matches = await db.graph_find_person(person_name)
    if not matches:
        return text(f"No person found matching '{person_name}'.")

    person = matches[0]
    ancestors = descendants = []
    if direction in ("ancestors", "both"):
        ancestors = await db.graph_get_ancestors(person["id"], generations)
    if direction in ("descendants", "both"):
        descendants = await db.graph_get_descendants(person["id"], generations)

    result = format_genealogy(person["name"], ancestors, descendants)

    family = await db.graph_get_family(person["id"])
    family_lines = []
    if family["partners"]:
        family_lines.append("**Spouse(s)**: " + ", ".join(p["name"] for p in family["partners"]))
    if family["siblings"]:
        family_lines.append("**Siblings**: " + ", ".join(p["name"] for p in family["siblings"]))
    if family_lines:
        result += "\n### Immediate Family\n" + "\n".join(family_lines) + "\n"
    if person.get("description"):
        result += f"\n### About\n{person['description']}\n"

    diagram = mermaid_genealogy(person["name"], ancestors, descendants, family)
    if diagram:
        result += f"\n### Family Tree Diagram\n{diagram}\n"
    return text(result)


async def handle_people_in_passage(args: dict[str, Any]) -> list[TextContent]:
    """Find entities mentioned in a verse or chapter."""
    if err := await _check_graph_data():
        return err

    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a Bible reference (e.g., 'Romans 8' or 'Genesis 22:1').")

    ref_stripped = reference.strip()
    m = re.match(r'^(\d?\s*[a-zA-Z]+)\s+(\d+)$', ref_stripped)
    if ":" in ref_stripped or (m and _is_single_chapter(m.group(1))):
        # Verse-level (includes "Jude 3" = Jude 1:3).
        entities = await db.graph_get_verse_entities(db._normalize_reference(ref_stripped))
    elif m:
        # Chapter-level for multi-chapter books.
        entities = await db.graph_get_chapter_entities(_book_abbr(m.group(1)), int(m.group(2)))
    else:
        return text(f"Could not parse reference: {reference}. Use 'Romans 8' or 'Genesis 22:1'.")

    return text(format_passage_entities(reference, entities))


async def handle_explore_person_events(args: dict[str, Any]) -> list[TextContent]:
    """Timeline of a person's life events."""
    if err := await _check_graph_data():
        return err

    person_name = args.get("person", "")
    if not person_name:
        return text("Please provide a person's name.")

    matches = await db.graph_find_person(person_name)
    if not matches:
        return text(f"No person found matching '{person_name}'.")

    person = matches[0]
    events = await db.graph_get_person_events(person["id"])
    event_places = {}
    for evt in events:
        places = await db.graph_get_event_places(evt["id"])
        if places:
            event_places[evt["id"]] = places

    result = format_person_events(person["name"], events, event_places)
    diagram = mermaid_person_timeline(person["name"], events, event_places)
    if diagram:
        result += f"\n### Timeline Diagram\n{diagram}\n"
    return text(result)


async def handle_explore_place(args: dict[str, Any]) -> list[TextContent]:
    """Biblical history of a location."""
    if err := await _check_graph_data():
        return err

    place_name = args.get("place", "")
    if not place_name:
        return text("Please provide a place name.")

    matches = await db.graph_find_place(place_name)
    if not matches:
        return text(f"No place found matching '{place_name}'.")

    place = matches[0]
    events = await db.graph_get_place_events(place["id"])
    people = await db.graph_get_place_people(place["id"])

    result = format_place_history(place, events, people)
    diagram = mermaid_place_network(place, events, people)
    if diagram:
        result += f"\n### Place Network Diagram\n{diagram}\n"
    return text(result)


async def handle_find_connection(args: dict[str, Any]) -> list[TextContent]:
    """Find a relationship path between two people."""
    if err := await _check_graph_data():
        return err

    name1 = args.get("person1", "")
    name2 = args.get("person2", "")
    if not name1 or not name2:
        return text("Please provide both person1 and person2 names.")

    matches1 = await db.graph_find_person(name1)
    matches2 = await db.graph_find_person(name2)
    if not matches1:
        return text(f"No person found matching '{name1}'.")
    if not matches2:
        return text(f"No person found matching '{name2}'.")

    person1, person2 = matches1[0], matches2[0]
    path = await db.graph_find_path(person1["id"], person2["id"])
    result = format_connection_path(person1["name"], person2["name"], path)
    diagram = mermaid_connection_path(person1["name"], person2["name"], path)
    if diagram:
        result += f"\n### Relationship Diagram\n{diagram}\n"
    return text(result)


async def handle_graph_enriched_search(args: dict[str, Any]) -> list[TextContent]:
    """Verse text plus graph context (people/places and their families)."""
    if err := await _check_graph_data():
        return err

    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a verse reference (e.g., 'Genesis 22:1').")

    verse = await db.get_verse(reference)
    normalized = db._normalize_reference(reference)
    entities = await db.graph_get_verse_entities(normalized)

    family_data = {}
    for p in entities.get("people", []):
        name = p.get("entity_name", p.get("entity_id"))
        person_matches = await db.graph_find_person(name)
        if person_matches:
            family_data[name] = await db.graph_get_family(person_matches[0]["id"])

    return text(format_enriched_verse(reference, verse, entities, family_data))


# =========================================================================
# Open study-notes handlers (Aquifer: unfoldingWord / Tyndale / SIL / FIA)
# =========================================================================

async def _check_aquifer_data() -> list[TextContent] | None:
    if not await db.has_aquifer_data():
        return text(
            "Study-notes data not available. Run "
            "'python scripts/download_stepbible.py --aquifer' and rebuild the database."
        )
    return None


async def handle_get_study_notes(args: dict[str, Any]) -> list[TextContent]:
    """Get study notes for a verse or chapter."""
    reference = args.get("reference", "")
    chapter_only = args.get("chapter_only", False)
    if not reference:
        return text("Please provide a Bible reference (e.g., 'John 3:16' or 'Genesis 1').")

    if err := await _check_aquifer_data():
        return err

    ref_stripped = reference.strip()
    m = re.match(r'^(\d?\s*[a-zA-Z]+)\s+(\d+)$', ref_stripped)
    # A bare "Book N" is a chapter for multi-chapter books, but a verse for
    # single-chapter books ("Jude 3" = Jude 1:3).
    is_chapter = chapter_only or (
        ':' not in ref_stripped and m is not None and not _is_single_chapter(m.group(1))
    )
    if is_chapter and m:
        notes = await db.get_chapter_study_notes(_book_abbr(m.group(1)), int(m.group(2)))
    else:
        notes = await db.get_study_notes(reference)

    if not notes:
        return text(f"No study notes found for {reference}.")

    return text(f"## Study Notes: {reference}\n\n" + format_study_notes(notes))


async def handle_get_bible_dictionary(args: dict[str, Any]) -> list[TextContent]:
    """Search dictionary articles across Aquifer and bundled PD dictionaries."""
    topic = args.get("topic", "")
    if not topic:
        return text("Please provide a topic to look up.")

    parts: list[str] = []
    if await db.has_aquifer_data():
        articles = await db.get_bible_dictionary(topic)
        if articles:
            parts.append(format_dictionary_article(articles))
    if await db.has_dictionaries():
        for e in await db.search_dictionaries(topic):
            parts.append(f"## {e['headword']}\n*{e['source_name']}*\n\n{e['body']}")

    if not parts:
        return text(f"No dictionary article found for '{topic}'.")
    return text("\n\n---\n\n".join(parts))


async def handle_get_key_terms(args: dict[str, Any]) -> list[TextContent]:
    """Look up biblical/theological key terms."""
    term = args.get("term", "")
    if not term:
        return text("Please provide a term to look up.")
    if err := await _check_aquifer_data():
        return err
    terms = await db.get_key_terms(term)
    if not terms:
        return text(f"No key term found for '{term}'.")
    return text(format_key_terms(terms))


async def handle_get_septuagint(args: dict[str, Any]) -> list[TextContent]:
    """Look up the Greek Septuagint text of a verse, mapping LXX<->standard numbering."""
    reference = args.get("reference", "")
    numbering = args.get("numbering", "english")
    if not reference:
        return text("Please provide a Bible reference (e.g., 'Psalm 51:1').")
    if not await db.has_lxx_data():
        return text(
            "Septuagint data not available. Run 'python scripts/download_lxx.py' "
            "then 'python scripts/import_lxx.py'."
        )

    normalized = db._normalize_reference(reference)
    if numbering == "lxx":
        lxx_ref = normalized
        standard_ref = await db.lxx_to_standard(lxx_ref) or lxx_ref
    else:
        standard_ref = normalized
        lxx_ref = await db.standard_to_lxx(standard_ref) or standard_ref

    verse = await db.get_lxx_verse(lxx_ref)
    if not verse:
        return text(
            f"No Septuagint text found for {reference} "
            f"(resolved to LXX {_format_xref_target(lxx_ref)}). It may be outside the "
            "Greek Old Testament, or the numbering may not line up."
        )

    lxx_disp = _format_xref_target(lxx_ref)
    std_disp = _format_xref_target(standard_ref)
    result = f"## Septuagint (LXX): {lxx_disp}\n\n"
    if verse.get("text_greek"):
        result += f"**Greek (Swete):** {verse['text_greek']}\n\n"
    if verse.get("text_english"):
        result += f"**English (Brenton):** {verse['text_english']}\n\n"
    if lxx_ref != standard_ref:
        result += (
            f"*Versification: this is **LXX {lxx_disp}**, which corresponds to "
            f"**{std_disp}** in the Hebrew/English numbering.*\n"
        )
    else:
        result += "*LXX and Hebrew/English numbering agree for this verse.*\n"
    result += (
        "\n*Greek: Swete LXX (Public Domain). English: Brenton 1851 (Public Domain). "
        "Mapping: Copenhagen Alliance (CC BY).*\n"
    )
    return text(result)


async def handle_get_commentary(args: dict[str, Any]) -> list[TextContent]:
    """Return public-domain commentary on a verse, optionally from named sources."""
    reference = args.get("reference", "")
    sources = args.get("sources")
    if not reference:
        return text("Please provide a verse reference (e.g., 'Romans 3:23').")
    if not await db.has_commentaries():
        return text(
            "Commentaries not available. Run 'python scripts/download_commentaries.py' "
            "then 'python scripts/import_commentaries.py'."
        )

    normalized = db._normalize_reference(reference)
    parts = normalized.split(".")
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return text(f"Please provide a specific verse, e.g. 'Romans 3:23' (got '{reference}').")
    book, chapter, verse = parts[0], int(parts[1]), int(parts[2])

    src_filter = _resolve_commentary_ids(sources) if sources else None
    if sources and not src_filter:
        avail = ", ".join(name for _, name in COMMENTARIES.items())
        return text(f"No commentary matched {sources}. Available: {avail}.")

    rows = await db.get_commentary(book, chapter, verse, src_filter)
    if not rows:
        return text(
            f"No commentary found for {reference}"
            + (f" from the requested source(s)." if sources else ".")
        )

    lines = [f"## Commentary on {reference}", ""]
    for r in rows:
        rng = (str(r['verse_start']) if r['verse_start'] == r['verse_end']
               else f"{r['verse_start']}-{r['verse_end']}")
        header = f"### {r['source_name']}"
        if not (r['verse_start'] == r['verse_end'] == verse):
            header += f"  *(on {parts[0]} {chapter}:{rng})*"
        lines.append(header)
        body = r['text']
        if len(body) > 2500:
            body = body[:2500].rstrip() + " …\n\n*[Commentary truncated — long entry.]*"
        lines.append(body)
        lines.append("")

    lines.append("*Public-domain commentaries via the HelloAO Free Use Bible API.*")
    return text("\n".join(lines))


async def handle_get_church_fathers(args: dict[str, Any]) -> list[TextContent]:
    """Return public-domain church-father comments (a catena) on a verse."""
    reference = args.get("reference", "")
    father = args.get("father")
    limit = int(args.get("limit") or 8)
    if not reference:
        return text("Please provide a verse reference (e.g., 'John 1:1').")
    if not await db.has_catena():
        return text(
            "Patristic catena not available. Run 'python scripts/download_catena.py' "
            "then 'python scripts/import_catena.py'."
        )

    normalized = db._normalize_reference(reference)
    parts = normalized.split(".")
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return text(f"Please provide a specific verse, e.g. 'John 1:1' (got '{reference}').")
    book, chapter, verse = parts[0], int(parts[1]), int(parts[2])

    total = await db.count_catena(book, chapter, verse)
    rows = await db.get_catena(book, chapter, verse, limit, father)
    if not rows:
        return text(
            f"No church-father comments found for {reference}"
            + (f" from '{father}'." if father else ".")
        )

    lines = [f"## Church Fathers on {reference}", ""]
    shown = f"showing {len(rows)}" + (" earliest" if not father and total > len(rows) else "")
    lines.append(f"*{total} patristic comment(s) on file; {shown}.*\n")
    for r in rows:
        yr = r.get("year")
        year_disp = (f"c. {yr} AD" if yr and yr > 0 else f"c. {abs(yr)} BC" if yr else "")
        cat = f" — {r['father_category']}" if r.get("father_category") else ""
        lines.append(f"### {r['father_name']}" + (f" ({year_disp})" if year_disp else "") + cat)
        quote = r["quote"] or ""
        if len(quote) > 1800:
            quote = quote[:1800].rstrip() + " …"
        lines.append(quote)
        src = r.get("source_title") or ""
        if r.get("source_url"):
            src = f"[{src or 'source'}]({r['source_url']})"
        if src:
            lines.append(f"*— {src}*")
        lines.append("")

    sources = {r.get("source") for r in rows}
    credits = []
    if "historical-christian-faith" in sources or None in sources:
        credits.append("HistoricalChristianFaith")
    if "sermonindex" in sources:
        credits.append("SermonIndex (CC BY 4.0)")
    lines.append(f"*Public-domain patristic excerpts via {' and '.join(credits)}.*")
    return text("\n".join(lines))


# A Scripture reference embedded in a free-text query, e.g. "what does Hebrews 1:3 mean",
# "faith in Hebrews 11", "the book of Romans". Book names longest-first so "1 john" beats "john".
_REF_IN_QUERY = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in sorted(_NAME_TO_OSIS, key=len, reverse=True))
    + r")\b\.?(?:\s+(\d+)(?:\s*:\s*(\d+))?)?",
    re.I,
)


def _detect_scripture_ref(query: str):
    """(osis_book, chapter|None, verse|None) if the query names a Bible book, else None."""
    m = _REF_IN_QUERY.search(query or "")
    if not m:
        return None
    osis = _NAME_TO_OSIS.get(m.group(1).lower())
    if not osis:
        return None
    ch = int(m.group(2)) if m.group(2) else None
    v = int(m.group(3)) if m.group(3) else None
    return osis, ch, v


async def handle_search_theology(args: dict[str, Any]) -> list[TextContent]:
    """Ground a query in the church's public-domain theological treasury (full-text/BM25)."""
    query = (args.get("query") or "").strip()
    author = args.get("author")
    limit = int(args.get("limit") or 8)
    if not query:
        return text("Please provide a query (a theological term, phrase, or question).")
    if not getattr(db, "has_theology", False):
        return text(
            "The theology grounding corpus (theology.db) is not attached. Build it with "
            "'python scripts/build_theology_grounding.py' (and set THEOLOGY_DB if it lives elsewhere)."
        )
    fts = await db.search_theology(query, author=author, limit=limit)
    sem = await db.semantic_theology(query, limit=limit)
    if author:  # the vec KNN doesn't filter by author, so post-filter
        a = author.strip().lower()
        sem = [s for s in sem if a in (s.get("author") or "").lower()]
    fts_works = {r.get("work_id") for r in fts}
    sem = [s for s in sem if s.get("work_id") not in fts_works][:limit]  # drop overlap with keyword hits

    # Reference-aware grounding: if the query names a Bible book/verse, surface the works devoted
    # to it (whose paragraphs are `refs`-tagged) — this is how e.g. a Hebrews question grounds on
    # Owen's Exposition, which keyword/semantic ranking alone would not reliably surface.
    ref = _detect_scripture_ref(query)
    ref_rows, ref_label = [], ""
    if ref:
        osis, ch, v = ref
        seen = {(r.get("work_id"), (r.get("text") or "")[:60]) for r in fts + sem}
        for r in await db.theology_by_ref(osis, ch, v, limit=6):
            if (r.get("work_id"), (r.get("text") or "")[:60]) not in seen:
                ref_rows.append(r)
        ref_label = _OSIS_TO_NAME.get(osis, osis).title() + (f" {ch}" if ch else "") + (f":{v}" if v else "")

    if not fts and not sem and not ref_rows:
        return text(f"No passages found for '{query}'" + (f" in {author}'s works." if author else "."))

    def _blocks(rows, refs_ok):
        out = []
        for r in rows:
            passage = (r.get("text") or "").strip()
            if len(passage) > 1400:
                passage = passage[:1400].rstrip() + " …"
            out.append(f"### {r.get('author', '?')} — *{r.get('title', '')}*")
            out.append(passage)
            refs = r.get("refs") if refs_ok else None
            if refs and refs not in ("[]", "null"):
                try:
                    rl = json.loads(refs)
                    if rl:
                        out.append(f"*Scripture cited: {', '.join(str(x) for x in rl[:8])}*")
                except Exception:
                    pass
            out.append("")
        return out

    lines = [f"## Theology Library — grounding for “{query}”", ""]
    if ref_rows:
        lines.append(f"### Works on {ref_label}")
        lines += _blocks(ref_rows, True)
    if fts:
        lines.append("### Keyword matches")
        lines += _blocks(fts, True)
    if sem:
        lines.append("### Related by meaning")
        lines += _blocks(sem, False)
    lines.append("*Full public-domain texts, housed locally (CCEL and other PD editions). Cite the author and work.*")
    return text("\n".join(lines))


async def handle_get_confession(args: dict[str, Any]) -> list[TextContent]:
    """List / retrieve / search creeds, confessions, and catechisms."""
    document = args.get("document")
    topic = args.get("topic")
    section = args.get("section")
    if not await db.has_historical_documents():
        return text(
            "Historical documents not available. Run 'python scripts/download_theologai.py' "
            "then 'python scripts/import_theologai.py'."
        )

    if topic and not document:
        rows = await db.search_historical_documents(topic)
        if not rows:
            return text(f"No creed/confession/catechism sections found for '{topic}'.")
        lines = [f"## Creeds & Confessions on '{topic}'", ""]
        for r in rows:
            lines.append(f"### {r['doc_title']} — {r['section_label']}  *({r['tradition']})*")
            body = r["content"]
            lines.append(body[:1200].rstrip() + " …" if len(body) > 1200 else body)
            lines.append("")
        return text("\n".join(lines))

    if document:
        doc_id = await db.find_historical_doc_id(document)
        if not doc_id:
            avail = ", ".join(d["doc_title"] for d in await db.list_historical_documents())
            return text(f"No document matched '{document}'. Available: {avail}.")
        secs = await db.get_historical_document(doc_id)
        meta = secs[0]
        header = f"## {meta['doc_title']}\n*{(meta['doc_type'] or '').title()} · {meta['tradition']} · {meta['doc_date']}*\n"
        if section:
            s = str(section).strip().lower()
            qm = re.match(r"^q?(\d+)$", s)
            if qm:  # a catechism question number: exact match so 'Q1' != 'Q10'
                target = f"q{qm.group(1)}"
                secs = [x for x in secs if (x["section_label"] or "").strip().lower() == target]
            else:
                secs = [x for x in secs if s in (x["section_label"] or "").lower()]
            if not secs:
                return text(f"No section '{section}' found in {meta['doc_title']}.")
        if section or len(secs) <= 12:
            lines = [header]
            for x in secs:
                if x["section_label"]:
                    lines.append(f"### {x['section_label']}")
                body = x["content"]
                lines.append(body[:1600].rstrip() + " …" if len(body) > 1600 else body)
                lines.append("")
            return text("\n".join(lines))
        # Long document: return an index so a section can be requested.
        lines = [header, f"*{len(secs)} sections — request one with `section`, or search with `topic`.*", ""]
        for x in secs[:100]:
            preview = (x["content"] or "").replace("\n", " ")[:80]
            lines.append(f"- **{x['section_label']}**: {preview}…")
        return text("\n".join(lines))

    docs = await db.list_historical_documents()
    lines = ["## Historical Documents (creeds, confessions, catechisms)", ""]
    for d in docs:
        lines.append(f"- **{d['doc_title']}** — {d['doc_type']} · {d['tradition']} · {d['doc_date']} "
                     f"({d['sections']} sections)")
    lines.append("\n*Retrieve one with `document`, a section with `section`, or search all with `topic`.*")
    return text("\n".join(lines))


async def handle_find_confessions_by_verse(args: dict[str, Any]) -> list[TextContent]:
    """Confession/catechism articles that cite a given verse as a proof text."""
    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a verse reference (e.g., 'Romans 1:20').")
    if not await db.has_confession_proofs():
        return text("Confession proof-texts not available. Run scripts/download_confessions.py "
                    "then scripts/import_confessions.py.")
    normalized = db._normalize_reference(reference)
    try:
        book, chapter, verse = normalized.split(".")[0], int(normalized.split(".")[1]), int(normalized.split(".")[2])
    except (IndexError, ValueError):
        return text(f"Could not parse a single verse from '{reference}'. Try 'Romans 1:20'.")

    rows = await db.find_confessions_by_verse(book, chapter, verse)
    if not rows:
        return text(f"No confession or catechism article cites {reference} as a proof text.")

    lines = [f"## Confessions citing {reference}", "",
             f"*{len(rows)} citation(s) across "
             f"{len({r['doc_id'] for r in rows})} standard(s).*", ""]
    current = None
    for r in rows:
        if r["doc_title"] != current:
            current = r["doc_title"]
            lines.append(f"\n### {current}")
        body = (r["section_text"] or "").replace("\n\n", " ").strip()
        if len(body) > 360:
            body = body[:360].rstrip() + " …"
        lines.append(f"- **{r['section_label']}** — {body}")
    lines.append(f"\n*Proof texts for any article: `get_confession_proofs`.*")
    return text("\n".join(lines))


async def handle_get_confession_proofs(args: dict[str, Any]) -> list[TextContent]:
    """Show the Scripture proof texts behind a confession article, with the verses."""
    document = args.get("document", "")
    section = args.get("section")
    if not document:
        return text("Please name a document (e.g., 'Westminster Confession' or 'wsc').")
    if not await db.has_confession_proofs():
        return text("Confession proof-texts not available. Run scripts/download_confessions.py "
                    "then scripts/import_confessions.py.")

    docs = await db.confession_proof_docs()
    key = document.strip().lower()
    match = next((d for d in docs if d["doc_id"] == key), None) \
        or next((d for d in docs if key in d["doc_id"].lower() or key in d["doc_title"].lower()), None)
    if not match:
        avail = ", ".join(f"{d['doc_title']} ({d['doc_id']})" for d in docs)
        return text(f"No proof-text document matched '{document}'. Available: {avail}.")

    rows = await db.get_confession_proofs(match["doc_id"], str(section) if section else None)
    if not rows:
        return text(f"No proof texts for {match['doc_title']}"
                    + (f", section {section}" if section else "") + ".")

    lines = [f"## {match['doc_title']} — Proof Texts"
             + (f" ({section})" if section else ""), ""]
    current_label = None
    for r in rows:
        if r["section_label"] != current_label:
            current_label = r["section_label"]
            lines.append(f"\n### {current_label}")
            body = (r["section_text"] or "").strip()
            lines.append(body[:900].rstrip() + (" …" if len(body) > 900 else ""))
            lines.append("\n**Proof texts:**")
        # Resolve the cited verse's readable text.
        ref_norm = f"{r['book']}.{r['chapter']}.{r['verse_start']}"
        tr = "WEB" if r["book"] in DEUTERO_BOOKS else "BSB"
        vrow = await db.get_translation_verse(tr, ref_norm)
        disp = _format_xref_target(ref_norm)
        if r["verse_end"] != r["verse_start"]:
            disp += f"-{r['verse_end']}"
        vtext = f" — {vrow['text']}" if vrow else ""
        lines.append(f"- [{r['marker']}] **{disp}**{vtext}")
    return text("\n".join(lines))


_MONTH_NAMES = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}
_MONTH_ABBR = {m[:3]: i for m, i in _MONTH_NAMES.items()}


def _parse_calendar_date(s: str) -> tuple[int, int] | None:
    """Parse 'January 1', 'Jan 1', '1/1', '1-1' -> (month, day)."""
    s = (s or "").strip().lower()
    m = re.match(r"^([a-z]+)\.?\s+(\d{1,2})$", s)
    if m:
        name = m.group(1)
        month = _MONTH_NAMES.get(name) or _MONTH_ABBR.get(name[:3])
        if month:
            return month, int(m.group(2))
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


async def handle_get_devotional(args: dict[str, Any]) -> list[TextContent]:
    """Verse-keyed or date-keyed public-domain devotional readings."""
    reference = args.get("reference")
    date = args.get("date")
    if not await db.has_devotionals():
        return text("Devotionals not available. Run scripts/download_devotionals.py "
                    "then scripts/import_devotionals.py.")

    if reference:
        normalized = db._normalize_reference(reference)
        try:
            p = normalized.split(".")
            rows = await db.get_devotionals_by_verse(p[0], int(p[1]), int(p[2]))
        except (IndexError, ValueError):
            return text(f"Could not parse a verse from '{reference}'.")
        if not rows:
            return text(f"No devotional reading is keyed to {reference}.")
        header = f"## Devotionals on {reference}"
    elif date:
        md = _parse_calendar_date(date)
        if not md:
            return text("Could not parse the date. Try 'January 1' or '1/1'.")
        rows = await db.get_devotionals_by_date(*md)
        if not rows:
            return text(f"No devotional reading for {date}.")
        header = f"## Devotional Reading — {date}"
    else:
        return text("Provide a verse `reference` (e.g., 'Isaiah 40:31') or a `date` (e.g., 'January 1').")

    lines = [header, ""]
    for r in rows:
        lines.append(f"### {r['title']} · *{r['source_name']}*")
        if r["key_ref"]:
            lines.append(f"**Key verse:** {r['key_ref']}\n")
        lines.append(r["body"])
        lines.append("")
    lines.append("*Devotional / homiletical reflection — read alongside, not in place of, exegesis.*")
    return text("\n".join(lines))


async def handle_get_parallel_passages(args: dict[str, Any]) -> list[TextContent]:
    """Find the UBS parallel-passage group(s) a verse belongs to."""
    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a verse reference (e.g., 'Matthew 19:5').")
    if not await db.has_parallel_passages():
        return text(
            "Parallel passages not available. Run 'python scripts/download_theologai.py' "
            "then 'python scripts/import_theologai.py'."
        )
    normalized = db._normalize_reference(reference)
    parts = normalized.split(".")
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return text(f"Please provide a specific verse, e.g. 'Matthew 19:5' (got '{reference}').")
    book, chapter, verse = parts[0], int(parts[1]), int(parts[2])

    rows = await db.get_parallel_passages(book, chapter, verse)
    if not rows:
        return text(f"No UBS parallel passages found for {reference}.")

    groups: dict[int, list[str]] = {}
    for r in rows:
        groups.setdefault(r["group_id"], []).append(r["ref_display"])

    lines = [f"## Parallel Passages for {reference}", ""]
    for refs in groups.values():
        lines.append("- " + "  =  ".join(refs))
    lines.append("\n*UBS Parallel Passage Database — © United Bible Societies, CC BY-SA 4.0.*")
    return text("\n".join(lines))


_TOOL_HANDLERS = {
    "word_study": handle_word_study,
    "lookup_verse": handle_lookup_verse,
    "get_passage": handle_get_passage,
    "compare_translations": handle_compare_translations,
    "vocabulary_list": handle_vocabulary_list,
    "search_lexicon": handle_search_lexicon,
    "get_cross_references": handle_get_cross_references,
    "lookup_name": handle_lookup_name,
    "parse_morphology": handle_parse_morphology,
    "search_by_strongs": handle_search_by_strongs,
    "explore_genealogy": handle_explore_genealogy,
    "people_in_passage": handle_people_in_passage,
    "explore_person_events": handle_explore_person_events,
    "explore_place": handle_explore_place,
    "find_connection": handle_find_connection,
    "graph_enriched_search": handle_graph_enriched_search,
    "get_study_notes": handle_get_study_notes,
    "get_bible_dictionary": handle_get_bible_dictionary,
    "get_key_terms": handle_get_key_terms,
    "get_commentary": handle_get_commentary,
    "get_church_fathers": handle_get_church_fathers,
    "search_theology": handle_search_theology,
    "get_confession": handle_get_confession,
    "find_confessions_by_verse": handle_find_confessions_by_verse,
    "get_confession_proofs": handle_get_confession_proofs,
    "get_devotional": handle_get_devotional,
    "get_parallel_passages": handle_get_parallel_passages,
    "get_septuagint": handle_get_septuagint,
}


# =========================================================================
# Transports
# =========================================================================

async def run_stdio_server():
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_http_server(host: str, port: int):
    """Run the MCP server over Streamable HTTP (with a /health endpoint)."""
    try:
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from starlette.responses import JSONResponse
        from collections.abc import AsyncIterator
        import uvicorn
    except ImportError:
        logger.error("HTTP transport requires extras: pip install '.[http]'")
        sys.exit(1)

    session_manager = StreamableHTTPSessionManager(app=server)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> "AsyncIterator[None]":
        async with session_manager.run():
            yield

    async def health(request):
        db_path = get_db_path()
        return JSONResponse({
            "status": "healthy" if db_path.exists() else "degraded",
            "database": str(db_path),
            "database_exists": db_path.exists(),
            "version": "0.1.0",
        })

    app = Starlette(
        lifespan=lifespan,
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Mount("/mcp", app=session_manager.handle_request),
        ],
    )
    logger.info(f"Starting Streamable HTTP server on http://{host}:{port}/mcp")
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()


@click.command()
@click.option("--transport", type=click.Choice(["stdio", "http"]), default="stdio",
              envvar="TRANSPORT", help="Transport protocol.")
@click.option("--host", default="127.0.0.1", help="Host for HTTP transport.")
@click.option("--port", default=8080, type=int, envvar="PORT", help="Port for HTTP transport.")
@click.option("--db-path", type=click.Path(), envvar="STUDY_BIBLE_DB", help="Path to SQLite database.")
def main(transport: str, host: str, port: int, db_path: str | None):
    """Run the Study Bible MCP server."""
    if db_path:
        os.environ["STUDY_BIBLE_DB"] = db_path
    logger.info(f"Starting Study Bible MCP server (transport: {transport})")
    if transport == "stdio":
        asyncio.run(run_stdio_server())
    else:
        asyncio.run(run_http_server(host, port))


if __name__ == "__main__":
    main()
