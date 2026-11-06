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
import importlib
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
    CallToolResult,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
)

from .database import (
    StudyBibleDB, BOOK_ABBREV_MAP, SINGLE_CHAPTER_BOOKS,
    DEUTERO_BOOKS, resolve_folded_ref, _NAME_TO_OSIS, _OSIS_TO_NAME, base_strongs,
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
from .parsers.lxx import swete_ref
from .clients import OPTIONAL_TRANSLATIONS, ATTRIBUTION, Unavailable, esv_configured, fetch_optional

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
    """Load the full Theologian persona: theologian.md (the voice) followed by doctrine.md (the
    tradition's doctrine, shared with the student chat). Falls back to a stub if missing."""
    try:
        persona = (_PROMPTS_DIR / "theologian.md").read_text(encoding="utf-8").strip()
        doctrine = (_PROMPTS_DIR / "doctrine.md").read_text(encoding="utf-8").strip()
        return f"{persona}\n\n---\n\n{doctrine}"
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

# Database connection (initialized lazily on first tool call, under _db_lock so two
# concurrent first calls can't both open it)
db: StudyBibleDB | None = None
_db_lock = asyncio.Lock()

# Every tool call ends within this many seconds. The web app stops waiting at 30, so the
# server gives up first and can still answer with a clean error.
TOOL_DEADLINE = 25.0


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


def failed(msg: str) -> CallToolResult:
    """A failed tool call: isError true, so the client sees the failure as one."""
    return CallToolResult(content=[TextContent(type="text", text=msg)], isError=True)


class NotInstalled(Exception):
    """A dataset this server was built without: a failure, not an empty answer. The build
    hint goes to the log for the operator; the model gets only the plain sentence."""

    def __init__(self, what: str, fix: str):
        super().__init__(f"{what} not installed ({fix})")
        self.what = what


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


# When ESV or NET can't be reached, the bundled BSB is served with a note naming the substitution
# (docs/harness-maturity-proposal.md, Layer 2, step 5). That is a served answer, so it stays an
# ordinary result. Only when no text can be served at all is the call a failure.
FALLBACK_TRANSLATION = "BSB"


def _stand_in_note(e: Unavailable, translation: str) -> str:
    return f"*{e} This is the {translation} in its place. Name the {translation} when quoting it.*"


def _default_translation(reference: str, book: str) -> str:
    """With no translation asked for: the ESV where this server has a Crossway key, so students read
    the wording their class uses, and the BSB otherwise. The deuterocanon comes from the WEB, the
    only translation here that holds it. A failed ESV fetch falls back to the BSB with a note."""
    if book in DEUTERO_BOOKS or resolve_folded_ref(reference):
        return "WEB"
    return "ESV" if esv_configured() else "BSB"


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


async def _open_db() -> None:
    """Open the database once. The lock makes a second first call wait for the first, and
    `db` is set only after connect() finishes, so no call sees a half-open connection."""
    global db
    async with _db_lock:
        if db is None:
            db_path = get_db_path()
            if not db_path.exists():
                raise NotInstalled("Bible database", f"no file at {db_path}; run scripts/build_database.py")
            fresh = StudyBibleDB(db_path)
            await fresh.connect()
            db = fresh


async def _stop_queries() -> None:
    """Stop the query a timed-out call left running. Every call shares one connection whose
    queries run in turn on aiosqlite's worker thread, so a runaway query would hold up all later
    calls. interrupt() stops whichever statement is running (rarely another call's, which then
    fails cleanly). The cursor() that follows has the worker drop any cursor the timed-out call
    left open; while one stays open, SQLite keeps the interrupt in force for every later query."""
    if db is None or db.conn is None:
        return
    with contextlib.suppress(Exception):
        await db.conn.interrupt()
        async with asyncio.timeout(1):  # the cursor() runs even if this wait gives up
            await db.conn.cursor()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Dispatch a tool call to its handler, initializing the DB on first use.

    Every failure comes back with isError true and a plain sentence; the details (stack trace,
    SQL, paths) go to the log only. "No results" answers stay ordinary results.
    """
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return failed(f"Unknown tool: {name}")

    try:
        async with asyncio.timeout(TOOL_DEADLINE):
            if db is None:
                await _open_db()
            return await handler(arguments)
    except TimeoutError:
        logger.warning("tool %s stopped at its %g s deadline", name, TOOL_DEADLINE)
        await _stop_queries()
        return failed(f"The {name} tool took too long (over {TOOL_DEADLINE:g} seconds) and was "
                      "stopped. Try a narrower request.")
    except NotInstalled as e:
        logger.error("tool %s: %s", name, e)
        return failed(f"The {e.what} is not installed on this server.")
    except Exception:
        logger.exception("tool %s failed", name)
        return failed(f"The {name} tool failed on this request. Try different arguments or another tool.")


# =========================================================================
# Text / lexicon / morphology handlers
# =========================================================================

async def handle_word_study(args: dict[str, Any]) -> list[TextContent]:
    """Deep dive into a Greek or Hebrew word."""
    strongs = args.get("strongs")
    word = args.get("word")
    language = args.get("language")  # None: Greek first, then Hebrew

    if strongs:
        entry = await db.get_lexicon_entry(strongs)
    elif word:
        entry = await db.find_word(word, language=language)
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


async def handle_lookup_verse(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Get a verse in a readable translation, with optional original + interlinear."""
    reference = args.get("reference", "")
    requested = (args.get("translation") or "").upper()
    include_original = args.get("include_original", True)
    include_morphology = args.get("include_morphology", False)

    if not reference:
        return text("Please provide a verse reference (e.g., 'John 3:16').")

    normalized = db._normalize_reference(reference)
    verse = await db.get_verse(reference)
    book = normalized.split(".")[0]
    translation = _route_deutero(reference, book, requested) if requested else _default_translation(reference, book)

    readable_text = None
    readable_note = None
    stand_in = None
    if translation in OPTIONAL_TRANSLATIONS:
        try:
            readable_text, readable_note = await fetch_optional(translation, reference)
        except Unavailable as e:
            stand_in = e
            translation = _route_deutero(reference, normalized.split(".")[0], FALLBACK_TRANSLATION)
    if translation not in OPTIONAL_TRANSLATIONS and await db.has_translations():
        row = await db.get_translation_verse(translation, normalized)
        readable_text = row["text"] if row else None

    if not verse and not readable_text:
        if stand_in:
            return failed(f"{stand_in} The {translation} has no text for {reference} either.")
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
                if stand_in:
                    result += f"\n*{stand_in}*"
                result += f"\n*No {translation} text for this verse — showing the STEPBible word-gloss.*\n"
    else:
        # Translation-only verse (e.g. a deuterocanon verse absent from the tagged text).
        result = f"## {_format_xref_target(normalized)}\n\n**{translation}:** {readable_text}\n"

    if stand_in and readable_text:
        result += f"\n{_stand_in_note(stand_in, translation)}\n"

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


async def handle_get_passage(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Return a readable passage (verse range or whole chapter) in a translation."""
    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a passage reference (e.g., 'Romans 3:21-26' or 'Psalm 23').")
    requested = (args.get("translation") or "").upper()
    translation = requested or _default_translation(reference, (_parse_passage(reference) or ("",))[0])

    stand_in = None
    if translation in OPTIONAL_TRANSLATIONS:
        try:
            live, err = await fetch_optional(translation, reference)
        except Unavailable as e:
            live, err, stand_in = None, None, e
        if live:
            out = f"## {reference} ({translation})\n\n{live}\n"
            if translation in ATTRIBUTION:
                out += f"\n{ATTRIBUTION[translation]}\n"
            return text(out)
        if not stand_in:
            return text(err or f"No {translation} text for {reference}.")
        translation = FALLBACK_TRANSLATION

    if not await db.has_translations():
        raise NotInstalled("translation library", "run the translation download/import scripts")

    parsed = _parse_passage(reference)
    if not parsed:
        return text(f"Could not parse passage: {reference}. Try 'Romans 3:21-26' or 'Psalm 23'.")
    book, chapter, v1, v2 = parsed
    translation = _route_deutero(reference, book, translation)
    verses = await db.get_translation_passage(translation, book, chapter, v1, v2)
    if not verses:
        if stand_in:
            return failed(f"{stand_in} The {translation} has no text for {reference} either.")
        avail = ", ".join(await db.available_translations())
        return text(f"No {translation} text found for {reference}. Available: {avail}.")

    lines = [f"## {reference} ({translation})", ""]
    if stand_in:
        lines += [_stand_in_note(stand_in, translation), ""]
    for v in verses:
        lines.append(f"**{v['verse']}** {v['text']}")

    if args.get("reader_mode") and await db.has_word_frequency():
        threshold = int(args.get("vocab_threshold") or 30)
        trows = await db.get_verses_in_range(book, chapter, v1, v2)
        if trows:
            vocab = await _vocabulary_rows(_passage_words(trows), threshold)
            lines.append("\n---\n" + _format_vocabulary(vocab, threshold, reference))
    return text("\n".join(lines))


async def handle_compare_translations(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Show one verse across several translations side by side."""
    reference = args.get("reference", "")
    requested = args.get("translations")
    if not reference:
        return text("Please provide a verse reference (e.g., 'John 3:16').")
    if not await db.has_translations():
        raise NotInstalled("translation library", "run the translation download/import scripts")

    normalized = db._normalize_reference(reference)
    tr_list = [t.upper() for t in requested] if requested else await db.available_translations()
    # Deuterocanon is bundled only in WEB; make sure it is in the comparison set.
    if (normalized.split(".")[0] in DEUTERO_BOOKS or resolve_folded_ref(reference)) and "WEB" not in tr_list:
        tr_list = ["WEB"] + tr_list

    lines = [f"## {reference} — Translation Comparison", ""]
    found = False
    attributions: set[str] = set()
    unreached: list[Unavailable] = []
    for tr in tr_list:
        if tr in OPTIONAL_TRANSLATIONS:
            try:
                live, err = await fetch_optional(tr, reference)
            except Unavailable as e:
                live, err = None, str(e)
                unreached.append(e)
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
    if unreached and FALLBACK_TRANSLATION not in tr_list:
        row = await db.get_translation_verse(FALLBACK_TRANSLATION, normalized)
        if row:
            missing = " and ".join(f"the {e.translation}" for e in unreached)
            lines.append(f"**{FALLBACK_TRANSLATION}:** {row['text']}\n")
            lines.append(f"*The {FALLBACK_TRANSLATION} is shown in place of {missing}.*\n")
            found = True
    if not found:
        if unreached:
            return failed(f"{unreached[0]} The {FALLBACK_TRANSLATION} has no text for {reference} either.")
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
        raise NotInstalled("word-frequency data", "run scripts/build_word_frequency.py")

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


_STRONGS_SCAN = 1500   # verses read for the counts and the tally of the word that follows


def _strongs_uses(words: list, target: str) -> list[int]:
    """Positions of the words tagged with `target`. A plain number also matches its lettered forms
    (H3068 finds H3068G), as in get_verses_with_strongs; a lettered one matches only itself."""
    plain = base_strongs(target) == target
    return [i for i, w in enumerate(words)
            if isinstance(w, dict) and (base_strongs(w.get("strongs", "")) if plain else w.get("strongs")) == target]


def _bare(word: str) -> str:
    """A word without its punctuation, for the tally: 'κρίνεται·' -> 'κρίνεται', 'אֶת\\־' -> 'אֶת'."""
    return word.strip(".,;:·’'\"!?()[]\\־׃")


async def handle_search_by_strongs(args: dict[str, Any]) -> list[TextContent]:
    """Find the verses containing a Strong's number, in one book or the whole Bible, each with the
    original words around the term. A tally of the word that follows shows the constructions, so
    "how does John use believe" is answered from the text in one call."""
    strongs = args.get("strongs", "")
    limit = args.get("limit", 20)
    book_name = (args.get("book") or "").strip()

    if not strongs:
        return text("Please provide a Strong's number (e.g., 'G26' or 'H3068').")

    entry = await db.get_lexicon_entry(strongs)
    if not entry:
        return text(f"Unknown Strong's number: {strongs}")
    book = _book_abbr(book_name) if book_name else None
    if book and book not in set(BOOK_ABBREV_MAP.values()):
        return text(f"Unknown book: {book_name}. Name a book of the Bible, such as John or 1 John.")

    target = db._normalize_strongs(strongs)
    rows = await db.get_verses_with_strongs(strongs, limit=_STRONGS_SCAN, book=book)
    result = f"## Verses with {strongs} ({entry['word']} - {entry['transliteration']})\n\n"
    result += f"*{entry['short_definition']}*\n\n"
    if not rows:
        where = f" in {book_name}" if book else ""
        return text(result + f"No verses found with this Strong's number{where} in the database.\n")

    verses, uses, after, forms = [], 0, {}, {}
    for v in rows:
        words = json.loads(v["word_data"]) if v.get("word_data") else []
        at = _strongs_uses(words, target)
        uses += len(at)
        for i in at:
            if i + 1 < len(words):
                nxt = words[i + 1]
                key = base_strongs(nxt.get("strongs", ""))
                after[key] = after.get(key, 0) + 1
                forms.setdefault(key, {})
                form = _bare(nxt.get("word", ""))
                forms[key][form] = forms[key].get(form, 0) + 1
        verses.append((v, words, at))

    scope = f"In {book_name}" if book else "In the whole Bible"
    capped = len(rows) >= _STRONGS_SCAN
    result += (f"{scope}: {uses} uses in {len(rows)}{'+' if capped else ''} verses"
               f"{' (the counts cover the first ' + str(_STRONGS_SCAN) + '; name a book to narrow it)' if capped else ''}. "
               f"The first {min(limit, len(rows))} follow, in Bible order.\n\n")
    if after:
        top = sorted(after.items(), key=lambda kv: -kv[1])[:8]
        tally = " · ".join(f"{max(forms[k], key=forms[k].get)} ({k}) {n}" for k, n in top)
        result += f"The word right after it: {tally}\n\n"
    label = "Greek" if target.startswith("G") else "Hebrew"
    for v, words, at in verses[:limit]:
        result += f"**{v['reference']}**: {v['text_english']}\n"
        spans = []
        for i in at:
            span = []
            for j in range(max(0, i - 2), min(len(words), i + 4)):
                w = words[j].get("word", "")
                span.append(f"**{w}** [{words[j].get('morph', '')}]" if j == i else w)
            spans.append(" ".join(span))
        if spans:
            result += f"{label}: {' … '.join(spans)}\n"
        result += "\n"
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
    limit_raw = args.get("limit")
    limit = int(limit_raw) if limit_raw is not None else 8
    # Rows readers voted below zero are links they judged wrong, so the floor starts at 0.
    min_strength_raw = args.get("min_strength")
    min_strength = int(min_strength_raw) if min_strength_raw is not None else 0

    if theme:
        refs = await db.get_thematic_references(theme)
        if not refs:
            return text(f"No cross-references found for theme '{theme}'.")
        result = f"## Cross-References: {theme}\n\n"
        for ref in refs:
            result += f"- **{ref['reference']}**: {ref['note']}\n"
        return text(result)

    if reference:
        refs = await db.get_cross_references(reference, limit=limit, min_strength=min_strength)
        if not refs:
            return text(f"No cross-references found for {reference}.")

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

    # Each entry gets the ACAI record for that same person or place, or none (see acai_for_names).
    try:
        acai = await db.acai_for_names(entries)
    except Exception:  # noqa: BLE001  (ACAI only enriches; the entries stand without it)
        logger.exception("ACAI enrichment failed")
        acai = {}

    result = f"## Biblical Names: {name}\n\n"
    for entry in entries:
        result += format_name_entry(entry, acai_data=acai.get(entry.get("id")))
        result += "\n---\n\n"
    return text(result)


# =========================================================================
# Graph handlers (Theographic Bible Metadata)
# =========================================================================

async def _require_graph_data() -> None:
    if not await db.graph_has_data():
        raise NotInstalled("people-and-places graph", "run scripts/import_theographic.py")


def _others_note(label: str, matches: list[dict]) -> str:
    """When a name fits several people, say who else it could mean, with ids the model can pass back."""
    if len(matches) < 2:
        return ""
    lines = []
    for m in matches[1:]:
        about = (m.get("description") or "").strip().replace("\n", " ")
        about = (about[:90] + "...") if len(about) > 90 else about
        if m.get("also_called"):
            about = f"called {m['also_called']}" + (f"; {about}" if about else "")
        where = f"; mentioned in {m.get('mentions') or 0} verse(s), e.g. {m['sample_ref']}" if m.get("sample_ref") else ""
        lines.append(f"- `{m['id']}` {m['name']}" + (f": {about}" if about else "") + where)
    return (f"\n\n### Other people named '{label}'\nThis answer is about `{matches[0]['id']}` "
            f"({matches[0]['name']}). If the question meant someone else, call again with their id:\n" + "\n".join(lines))


async def handle_explore_genealogy(args: dict[str, Any]) -> list[TextContent]:
    """Trace a person's family tree."""
    await _require_graph_data()

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
    return text(result + _others_note(person_name, matches))


async def handle_people_in_passage(args: dict[str, Any]) -> list[TextContent]:
    """Find entities mentioned in a verse or chapter."""
    await _require_graph_data()

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
    await _require_graph_data()

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
    return text(result + _others_note(person_name, matches))


async def handle_explore_place(args: dict[str, Any]) -> list[TextContent]:
    """Biblical history of a location."""
    await _require_graph_data()

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
    await _require_graph_data()

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
    return text(result + _others_note(name1, matches1) + _others_note(name2, matches2))


async def handle_graph_enriched_search(args: dict[str, Any]) -> list[TextContent]:
    """Verse text plus graph context (people/places and their families)."""
    await _require_graph_data()

    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a verse reference (e.g., 'Genesis 22:1').")

    verse = await db.get_verse(reference)
    normalized = db._normalize_reference(reference)
    entities = await db.graph_get_verse_entities(normalized)

    # the verse mention already names the exact person (mary_1943, not "a Mary"), so use its id
    family_data = {}
    for p in entities.get("people", []):
        if p.get("entity_id"):
            family_data[p["entity_id"]] = await db.graph_get_family(p["entity_id"])

    return text(format_enriched_verse(reference, verse, entities, family_data))


# =========================================================================
# Open study-notes handlers (Aquifer: unfoldingWord / Tyndale / SIL / FIA)
# =========================================================================

async def _require_aquifer_data() -> None:
    if not await db.has_aquifer_data():
        raise NotInstalled("study-notes library",
                           "run scripts/download_stepbible.py --aquifer and rebuild the database")


async def handle_get_study_notes(args: dict[str, Any]) -> list[TextContent]:
    """Get study notes for a verse or chapter."""
    reference = args.get("reference", "")
    chapter_only = args.get("chapter_only", False)
    if not reference:
        return text("Please provide a Bible reference (e.g., 'John 3:16' or 'Genesis 1').")

    await _require_aquifer_data()

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
    await _require_aquifer_data()
    terms = await db.get_key_terms(term)
    if not terms:
        return text(f"No key term found for '{term}'.")
    return text(format_key_terms(terms))


THEODOTION = {"Dan": "Dat", "Sus": "Sut", "Bel": "Bet"}  # Swete's Old Greek book -> its Theodotion text


async def handle_get_septuagint(args: dict[str, Any]) -> list[TextContent]:
    """Look up the Greek Septuagint text of a verse, mapping LXX<->standard numbering."""
    reference = args.get("reference", "")
    numbering = args.get("numbering", "english")
    if not reference:
        return text("Please provide a Bible reference (e.g., 'Psalm 51:1').")
    if not await db.has_lxx_data():
        raise NotInstalled("Septuagint", "run scripts/download_lxx.py then scripts/import_lxx.py")

    normalized = db._normalize_reference(reference)
    if numbering == "lxx":
        lxx_ref = swete_ref(normalized)  # 2 Esdras 11:1 is Swete's Nehemiah 1:1
        standard_ref = await db.lxx_to_standard(lxx_ref) or normalized
    else:
        standard_ref = normalized
        routed = await db.standard_to_lxx(standard_ref)
        if routed == "":
            return text(f"The Septuagint has no verse for {reference}: the Greek text lacks it.")
        lxx_ref = swete_ref(routed or standard_ref)  # Susanna 5 is Sus 1:5
    if standard_ref.startswith("Ps2.1."):  # the WEB files Psalm 151 as its own book; it is Psalm 151 to a reader
        standard_ref = f"Psa.151.{standard_ref.rsplit('.', 1)[1]}"

    verse = await db.get_lxx_verse(lxx_ref)
    # Swete prints two Greek texts of Daniel, Susanna, and Bel; Brenton translated Theodotion's
    book, _, rest = lxx_ref.partition(".")
    theodotion = await db.get_lxx_verse(f"{THEODOTION[book]}.{rest}") if book in THEODOTION else None
    if not verse and not theodotion:
        return text(
            f"No Septuagint text found for {reference} "
            f"(resolved to LXX {_format_xref_target(lxx_ref)}). It may be outside the "
            "Greek Old Testament, or the numbering may not line up."
        )

    lxx_disp = _format_xref_target(lxx_ref)
    std_disp = _format_xref_target(standard_ref)
    heading = standard_ref.endswith(".0")  # verse 0: a psalm heading, unnumbered in English Bibles
    differs = lxx_ref != standard_ref
    result = f"## Septuagint (LXX): {lxx_disp}"
    result += f" (English {std_disp})\n\n" if differs and not heading else "\n\n"
    for row, greek_label, english_label in (
        (verse, "Greek (Swete, Old Greek)" if theodotion else "Greek (Swete)", "English (Brenton)"),
        (theodotion, "Greek (Swete, Theodotion)", "English (Brenton, from Theodotion)"),
    ):
        if not row:
            continue
        if row.get("text_greek"):
            result += f"**{greek_label}:** {row['text_greek']}\n\n"
        elif row.get("text_english"):
            result += ("*Swete's Greek text, used here, has no Greek for this verse. Brenton's English "
                       "translates a Greek text that has it.*\n\n")
        if row.get("text_english"):
            result += f"**{english_label}:** {row['text_english']}\n\n"
    if heading:
        result += (
            f"*Versification: **LXX {lxx_disp}** is part of the heading of {std_disp.rsplit(':', 1)[0]}, "
            "which English Bibles print without a verse number.*\n"
        )
    elif differs:
        result += f"*Versification: this is **LXX {lxx_disp}**, which is **{std_disp}** in English Bibles.*\n"
    else:
        result += "*LXX and English numbering agree for this verse.*\n"
    result += (
        "\n*Greek: Swete LXX (Public Domain). English: Brenton 1851 (Public Domain). "
        "Mapping: Copenhagen Alliance (CC BY-SA 4.0).*\n"
    )
    return text(result)


async def handle_get_commentary(args: dict[str, Any]) -> list[TextContent]:
    """Return public-domain commentary on a verse, optionally from named sources."""
    reference = args.get("reference", "")
    sources = args.get("sources")
    if not reference:
        return text("Please provide a verse reference (e.g., 'Romans 3:23').")
    if not await db.has_commentaries():
        raise NotInstalled("commentary library",
                           "run scripts/download_commentaries.py then scripts/import_commentaries.py")

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
        raise NotInstalled("church-fathers catena", "run scripts/download_catena.py then scripts/import_catena.py")

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
        raise NotInstalled("theology library", "theology.db is not attached; build it with "
                           "scripts/build_theology_grounding.py, and set THEOLOGY_DB if it lives elsewhere")
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
            # The locator: the paragraph's place in the work, so a citation can point to it. Passages
            # found by meaning come from a chunked copy that keeps no paragraph number.
            seq, total = r.get("seq"), r.get("n_paragraphs")
            where = f" (paragraph {seq + 1:,} of {total:,})" if seq is not None and total else ""
            out.append(f"### {r.get('author', '?')} — *{r.get('title', '')}*{where}")
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
    lines.append("*Full public-domain texts, housed locally (CCEL and other PD editions). Cite the author and "
                 "work, with the paragraph where one is given.*")
    return text("\n".join(lines))


# The confession texts carry chapter titles and no chapter numbers. The 1689's paragraphs end in
# the source's footnote counters, and its proof rows lost the numeral of books like 1 Corinthians.
# The proof-text index carries the standard numbering ("29.2"), so a confession that has one is
# numbered from it: a chapter takes its number from a paragraph whose text matches an indexed
# article, a chapter with no match takes the number between its neighbours, and paragraphs count
# in order within their chapter. Its proof texts come from the index too.
_PROOF_EDITION = {"london-baptist-1689": "1689-confession", "westminster-confession": "wcf"}
_DOC_ALIASES = {
    "1689": "london-baptist-1689", "lbcf": "london-baptist-1689", "second london": "london-baptist-1689",
    "wcf": "westminster-confession", "wsc": "westminster-shorter-catechism",
    "wlc": "westminster-larger-catechism", "shorter catechism": "westminster-shorter-catechism",
    "larger catechism": "westminster-larger-catechism", "heidelberg": "heidelberg-catechism",
    "belgic": "belgic-confession", "dort": "canons-of-dort", "thirty nine articles": "39-articles",
    "trent": "council-of-trent", "augsburg": "augsburg-confession", "nicene": "nicene-creed",
    "apostles": "apostles-creed", "athanasian": "athanasian-creed", "chalcedon": "chalcedonian-definition",
}
_SECTION_WORDS = re.compile(r"\b(?:chapter|chap|ch|article|art|paragraph|para|par|section|sec)\b\.?|§", re.I)
_PROSE = re.compile(r"\b[a-z]{3,}\b")               # a row of proof references holds at most an "etc."
_FOOTNOTE = re.compile(r"\s+\d{1,3}\s*$")           # the 1689's trailing footnote counters
_INLINE_PARA = re.compile(r"(?:^|(?<=[\s.;:]))(\d{1,2})\.\s*(?=[A-Z(])")   # Westminster's "1. ... 2. ..."
_outlines: dict[str, list[dict]] = {}


def _plain(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())[:50]


async def _find_document(name: str) -> str | None:
    """The doc_id a document name means: an exact title or id, the shortest title that contains it,
    a common short name ('1689', 'WCF', 'Shorter Catechism'), or the title holding all its words
    ('1689 London Baptist Confession')."""
    want = _plain(name)
    if not want:
        return None
    docs = await db.list_historical_documents()
    for d in docs:
        if want in (_plain(d["doc_title"]), _plain(d["doc_id"])):
            return d["doc_id"]
    holding = [d for d in docs if want in _plain(d["doc_title"])]
    if not holding:
        alias = next((doc_id for key, doc_id in _DOC_ALIASES.items() if re.search(rf"\b{key}\b", want)), None)
        if alias:
            return alias
        words = [w for w in want.split() if len(w) >= 3 and not w.isdigit() and w not in ("the", "and", "faith")]
        holding = [d for d in docs if words and all(w in _plain(d["doc_title"]).split() for w in words)]
    return min(holding, key=lambda d: len(d["doc_title"]))["doc_id"] if holding else None


def _section_numbers(section: str) -> tuple[int, int | None] | None:
    """(chapter, paragraph or None) for a numbered section: '29', '29.2', '29:2', 'chapter 29',
    'ch. 29 para 2'. None for a title or a catechism question."""
    m = re.fullmatch(r"\s*(\d{1,3})\s*(?:[.:,]\s*|\s+)?(\d{1,3})?\s*\.?\s*", _SECTION_WORDS.sub(" ", section or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)) if m.group(2) else None


def _paragraphs(content: str) -> list[str]:
    """A row's paragraphs: the row itself, or a chapter's numbered paragraphs in order. Numbering that
    starts over at 1 is another chapter's text run on, and is left out."""
    t = re.sub(r"\[[\d.\s/]+\]\s*", "", content or "").strip()   # Book of Confessions codes, '[6.051 / 6.183]'
    if not _INLINE_PARA.match(t):
        return [_FOOTNOTE.sub("", t).strip()]
    bits = _INLINE_PARA.split(t)
    out: list[str] = []
    for i in range(1, len(bits) - 1, 2):
        if bits[i] == "1" and out:
            break
        out.append(bits[i + 1].strip())
    return out


async def _confession_outline(doc_id: str) -> list[dict] | None:
    """[{num, title, paras: [{num, text, row, indexed}]}] for a confession numbered from its proof-text
    index, else None. `indexed` is the index's own label for a paragraph. It differs from the number
    shown where the editions part: Westminster 31 has four paragraphs here and five in the index."""
    edition = _PROOF_EDITION.get(doc_id)
    if not edition or not await db.has_confession_proofs():
        return None
    if doc_id not in _outlines:
        index = {_letters(o["section_text"]): o["section_label"] for o in await db.confession_proof_outline(edition)}
        chapters: list[dict] = []
        for x in await db.get_historical_document(doc_id):
            if not chapters or chapters[-1]["title"] != (x["section_label"] or ""):
                chapters.append({"num": None, "title": x["section_label"] or "", "paras": []})
            ch = chapters[-1]
            if len(_PROSE.findall(x["content"] or "")) < 4:
                continue
            for p in _paragraphs(x["content"]):
                label = index.get(_letters(p))
                ch["paras"].append({"num": len(ch["paras"]) + 1, "text": p, "row": x["section_num"], "indexed": label})
                if label and ch["num"] is None:
                    ch["num"] = int(label.split(".")[0])
        for i, ch in enumerate(chapters):
            if ch["num"] is None:
                before = next((c["num"] for c in reversed(chapters[:i]) if c["num"]), 0)
                after = next((c["num"] for c in chapters[i + 1:] if c["num"]), None)
                if after is not None and after - before == 2:
                    ch["num"] = before + 1
        _outlines[doc_id] = chapters
    return _outlines[doc_id]


def _para_label(ch: dict, p: dict) -> str:
    return f"{ch['num']}.{p['num']}" if ch["num"] else f"¶{p['num']}"


async def _proof_refs(edition: str, labels: list[str]) -> dict[str, str]:
    """{article label: its proof references, with book numerals intact} from the proof-text index."""
    out: dict[str, list[str]] = {}
    for r in await db.get_confession_proofs(edition, labels) if labels else []:
        ref = _format_xref_target(f"{r['book']}.{r['chapter']}.{r['verse_start']}")
        if r["verse_end"] and r["verse_end"] != r["verse_start"]:
            ref += f"-{r['verse_end']}"
        refs = out.setdefault(r["section_label"], [])
        if ref not in refs:
            refs.append(ref)
    return {label: "; ".join(refs) for label, refs in out.items()}


async def _numbered_confession(meta: dict, doc_id: str, outline: list[dict], section) -> str:
    """A numbered confession: its chapter list, or the chapters and paragraphs a section names."""
    header = f"## {meta['doc_title']}\n*{(meta['doc_type'] or '').title()} · {meta['tradition']} · {meta['doc_date']}*\n"
    if not section:
        if len(outline) > 12:
            lines = [header, f"*{len(outline)} chapters. Request one with `section` ('29'), a paragraph "
                             "('29.2'), or words from its title, or search with `topic`.*", ""]
            lines += [f"- **{ch['num'] or 'unnumbered'}** {ch['title']} ({len(ch['paras'])} "
                      f"paragraph{'' if len(ch['paras']) == 1 else 's'})" for ch in outline]
            return "\n".join(lines)
        chosen = [(ch, ch["paras"]) for ch in outline]
    else:
        nums = _section_numbers(str(section))
        if nums:
            chosen = [(ch, [p for p in ch["paras"] if nums[1] is None or p["num"] == nums[1]])
                      for ch in outline if ch["num"] == nums[0]]
            chosen = [(ch, ps) for ch, ps in chosen if ps]
        else:
            want = _plain(str(section))
            named = [ch for ch in outline if _plain(ch["title"]) == want] or \
                    [ch for ch in outline if want and want in _plain(ch["title"])]
            chosen = [(ch, ch["paras"]) for ch in named]
        if not chosen:
            return (f"No section '{section}' found in {meta['doc_title']}. Name a chapter ('29'), a paragraph "
                    "('29.2'), or words from a chapter title.")
    proofs = await _proof_refs(_PROOF_EDITION[doc_id], [p["indexed"] for _, ps in chosen for p in ps if p["indexed"]])
    lines = [header]
    for ch, paras in chosen:
        lines.append(f"### Chapter {ch['num']}: {ch['title']}" if ch["num"] else f"### {ch['title']} (unnumbered)")
        for p in paras:
            label = _para_label(ch, p)
            note = f" (numbered {p['indexed']} in the proof-text edition)" if p["indexed"] and p["indexed"] != label else ""
            body = p["text"]
            lines.append(f"**{label}**{note} {body[:1600].rstrip()}{' …' if len(body) > 1600 else ''}")
            if p["indexed"] in proofs:
                lines.append(f"Proof texts: {proofs[p['indexed']]}")
            lines.append("")
    lines.append("*Cite a paragraph by the number shown here, chapter.paragraph.*")
    return "\n".join(lines)


def _matching_sections(secs: list[dict], section: str) -> list[dict]:
    """The sections of an unnumbered document that a request names: an exact label ('Q1', 'Article
    XII', '1.2'), a catechism question by number ('1', 'question 1'), a chapter of a document labelled
    '1.1', '1.2' ('1' or 'chapter 1'), or words from a title."""
    s = section.strip().lower()

    def label(x):
        return (x["section_label"] or "").strip().lower()

    exact = [x for x in secs if label(x) == s]
    if exact:
        return exact
    question = re.fullmatch(r"(?:q|question)\s*\.?\s*(\d+)", s)
    nums = _section_numbers(s)
    if question or (nums and nums[1] is None):
        number = int(question.group(1)) if question else nums[0]
        asked = [x for x in secs if label(x) == f"q{number}"]
        return asked if asked or question else [x for x in secs if label(x).startswith(f"{number}.")]
    if nums:
        return [x for x in secs if label(x) == f"{nums[0]}.{nums[1]}"]
    return [x for x in secs if s in label(x)]


async def handle_get_confession(args: dict[str, Any]) -> list[TextContent]:
    """List / retrieve / search creeds, confessions, and catechisms."""
    document = args.get("document")
    topic = args.get("topic")
    section = args.get("section")
    if not await db.has_historical_documents():
        raise NotInstalled("creeds and confessions library",
                           "run scripts/download_theologai.py then scripts/import_theologai.py")

    if topic and not document:
        rows = await db.search_historical_documents(topic)
        lines = [f"## Creeds & Confessions on '{topic}'", ""]
        for r in rows:
            outline = await _confession_outline(r["doc_id"]) if r["doc_id"] in _PROOF_EDITION else None
            if outline is not None:   # numbered paragraphs; a row of proof references is passed over
                hits = [(ch, p) for ch in outline for p in ch["paras"] if p["row"] == r["section_num"]]
                inside = [(ch, p) for ch, p in hits if topic.lower() in p["text"].lower()]
                for ch, p in inside or hits[:1]:
                    lines.append(f"### {r['doc_title']} {_para_label(ch, p)} ({ch['title']})  *({r['tradition']})*")
                    lines.append(p["text"][:1200].rstrip() + " …" if len(p["text"]) > 1200 else p["text"])
                    lines.append("")
                continue
            lines.append(f"### {r['doc_title']} — {r['section_label']}  *({r['tradition']})*")
            body = r["content"]
            lines.append(body[:1200].rstrip() + " …" if len(body) > 1200 else body)
            lines.append("")
        if len(lines) == 2:
            return text(f"No creed/confession/catechism sections found for '{topic}'.")
        return text("\n".join(lines))

    if document:
        doc_id = await _find_document(document)
        if not doc_id:
            avail = ", ".join(d["doc_title"] for d in await db.list_historical_documents())
            return text(f"No document matched '{document}'. Available: {avail}.")
        secs = await db.get_historical_document(doc_id)
        meta = secs[0]
        outline = await _confession_outline(doc_id)
        if outline is not None:
            return text(await _numbered_confession(meta, doc_id, outline, section))
        header = f"## {meta['doc_title']}\n*{(meta['doc_type'] or '').title()} · {meta['tradition']} · {meta['doc_date']}*\n"
        if section:
            secs = _matching_sections(secs, str(section))
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
        raise NotInstalled("confession proof-text index",
                           "run scripts/download_confessions.py then scripts/import_confessions.py")
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
        raise NotInstalled("confession proof-text index",
                           "run scripts/download_confessions.py then scripts/import_confessions.py")

    docs = await db.confession_proof_docs()
    key = document.strip().lower()
    match = next((d for d in docs if d["doc_id"] == key), None) \
        or next((d for d in docs if key in d["doc_id"].lower() or key in d["doc_title"].lower()), None)
    if not match:
        avail = ", ".join(f"{d['doc_title']} ({d['doc_id']})" for d in docs)
        return text(f"No proof-text document matched '{document}'. Available: {avail}.")

    outline = await db.confession_proof_outline(match["doc_id"])
    if not section:
        # A whole document runs to thousands of verses (2,568 in the Larger Catechism), so list the
        # articles to choose from.
        total = sum(o["n"] for o in outline)
        lines = [f"## {match['doc_title']}: proof texts by article", "",
                 f"{len(outline)} articles carry {total:,} proof texts. Call again with a section to see one "
                 "article's proofs with the verse text.", ""]
        for o in outline:
            body = " ".join((o["section_text"] or "").split())
            lines.append(f"- **{o['section_label']}** ({o['n']}): {body[:70].rstrip()}{'…' if len(body) > 70 else ''}")
        return text("\n".join(lines))

    labels = _proof_sections(str(section), [o["section_label"] for o in outline])
    rows = await db.get_confession_proofs(match["doc_id"], labels) if labels else []
    if not rows:
        return text(f"No proof texts for {match['doc_title']}, section {section}. Leave the section out "
                    "to list the articles.")

    # The readable text of every cited verse, a range up to eight verses, in one query per translation.
    refs: dict[str, list[str]] = {}
    for r in rows:
        last = min(r["verse_end"] or r["verse_start"], r["verse_start"] + 7)
        tr = "WEB" if r["book"] in DEUTERO_BOOKS else "BSB"
        refs.setdefault(tr, []).extend(f"{r['book']}.{r['chapter']}.{v}" for v in range(r["verse_start"], last + 1))
    texts = {tr: await db.get_translation_verses(tr, sorted(set(rs))) for tr, rs in refs.items()}

    lines = [f"## {match['doc_title']} — Proof Texts ({section})", ""]
    current_label = None
    for r in rows:
        if r["section_label"] != current_label:
            current_label = r["section_label"]
            lines.append(f"\n### {current_label}")
            body = (r["section_text"] or "").strip()
            lines.append(body[:900].rstrip() + (" …" if len(body) > 900 else ""))
            lines.append("\n**Proof texts:**")
        tr = "WEB" if r["book"] in DEUTERO_BOOKS else "BSB"
        last = min(r["verse_end"] or r["verse_start"], r["verse_start"] + 7)
        verse_text = " ".join(t for t in (texts[tr].get(f"{r['book']}.{r['chapter']}.{v}")
                                          for v in range(r["verse_start"], last + 1)) if t)
        disp = _format_xref_target(f"{r['book']}.{r['chapter']}.{r['verse_start']}")
        if r["verse_end"] and r["verse_end"] != r["verse_start"]:
            disp += f"-{r['verse_end']}"
        if last < (r["verse_end"] or r["verse_start"]):
            verse_text += " …"
        lines.append(f"- [{r['marker']}] **{disp}**" + (f" — {verse_text}" if verse_text else ""))
    return text("\n".join(lines))


def _proof_sections(section: str, labels: list[str]) -> list[str]:
    """The article labels a section names: an exact label ('Q1', '1.2'), a bare question number
    ('1' is 'Q1' in a catechism), or a confession chapter ('1' is articles 1.1, 1.2, ...)."""
    s = section.strip()
    if s in labels:
        return [s]
    number = s[1:] if s[:1] in "Qq" else s
    if number.isdigit() and f"Q{number}" in labels:
        return [f"Q{number}"]
    nums = _section_numbers(s)   # '29.2', '29:2', 'chapter 29', 'ch. 29 para 2'
    if nums and nums[1] is not None:
        return [f"{nums[0]}.{nums[1]}"] if f"{nums[0]}.{nums[1]}" in labels else []
    if nums:
        return [label for label in labels if label.startswith(f"{nums[0]}.")]
    return []


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
        raise NotInstalled("devotional library", "run scripts/download_devotionals.py then scripts/import_devotionals.py")

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
        raise NotInstalled("parallel-passage index", "run scripts/download_theologai.py then scripts/import_theologai.py")
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

def _preload_native_modules() -> None:
    """Import the native extensions tool calls need before stdio starts reading. On Windows, loading
    a native module (numpy, through sqlite-vec and model2vec) while the stdin reader thread waits on
    the pipe stalls until the next message arrives, so the first tool call would hang and its
    deadline could not fire. Both are optional; a missing one only turns its feature off."""
    for module in ("sqlite_vec", "model2vec"):
        with contextlib.suppress(ImportError):
            importlib.import_module(module)


async def run_stdio_server():
    """Run the MCP server over stdio."""
    _preload_native_modules()
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
