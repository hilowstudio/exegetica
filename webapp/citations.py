"""
What a reply drew on, held in memory for one run (the citation hook, proposal Layer 2 step 8 and
Layer 5 steps 5 and 8).

`Recorder` wraps the tool bridge and keeps every tool result of one run, in memory only, never
stored. Three checks use what it holds, together with the Bible translations bundled in
study_bible.db:

- the reply check exempts a quotation from its conduct patterns only when this run's tool results
  or the bundled Bible text hold it (webapp/reply_check.py), so wrapping a claim of affection in
  quotation marks no longer gets it past the check;
- a chat reply that consulted no library tool is labeled, and quotations that neither the library
  results nor the bundled Bible text hold are noted under the reply (`chat_note`);
- a Generator document gets a report of the references checked and the quotations not found
  (`generator_report`).

These checks say only what was found where. A quotation not found may still be accurate (ESV
wording, for one, is never stored here), and a reference that exists may still be the wrong one.
"""
from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from pathlib import Path

from studybible_mcp.database import StudyBibleDB

NO_SOURCE = "No library source was consulted."

_ROOT = Path(__file__).resolve().parent.parent
_TRANSLATIONS = ("BSB", "KJV", "WEB", "ASV", "YLT")


class Recorder:
    """The tool bridge, with each successful result of this run kept for the checks below."""

    def __init__(self, bridge) -> None:
        self._bridge = bridge
        self.outputs: list[str] = []
        self.calls = 0

    @property
    def tools(self):
        return self._bridge.tools

    def __getattr__(self, name):  # anything else the providers or routes read from the bridge
        return getattr(self._bridge, name)

    async def call(self, name: str, args: dict):
        out, is_error = await self._bridge.call(name, args)
        self.calls += 1
        if not is_error and out:
            self.outputs.append(out)
        return out, is_error


# ---------------------------------------------------------------------------------------------
# Text: normalizing, quotations, references
# ---------------------------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Lowercase letters and digits separated by single spaces, for comparing wording."""
    text = unicodedata.normalize("NFKC", text or "").lower().replace("’", "").replace("'", "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


_QUOTE = re.compile(r"“([^”]{3,}?)”|\"([^\"\n]{3,}?)\"")
_BLOCKQUOTE = re.compile(r"(?:^[ \t]*>[ \t]?.*(?:\n|$))+", re.M)
_SPLIT = re.compile(r"\s*(?:\.\.\.|…|\[[^\]]*\])\s*")   # ellipses and editorial brackets


def quotations(text: str, min_words: int = 6) -> list[tuple[str, int, int]]:
    """(quotation, start, end) for each quoted span and blockquote of at least min_words words."""
    found = []
    for m in _QUOTE.finditer(text or ""):
        q = m.group(1) or m.group(2)
        if len(q.split()) >= min_words:
            found.append((q, m.start(), m.end()))
    for m in _BLOCKQUOTE.finditer(text or ""):
        q = re.sub(r"^[ \t]*>[ \t]?", "", m.group(0), flags=re.M).strip()
        q = re.sub(r"[*_]{1,2}", "", q)
        if len(q.split()) >= min_words:
            found.append((q, m.start(), m.end()))
    return found


def _fragments(quote: str) -> list[str]:
    """The quotation's normalized pieces of three words or more, split at ellipses and brackets."""
    return [f for f in (normalize(p) for p in _SPLIT.split(quote)) if len(f.split()) >= 3]


_REFERENCE = re.compile(
    r"(?<![\w:])((?:[1-4]\s?)?[A-Z][a-z]+(?:\s+of\s+[A-Z][a-z]+)?)\.?\s+(\d{1,3}):(\d{1,3})"
    r"(?:\s*[-–]\s*(\d{1,3})(?!:))?")


def references(text: str) -> list[dict]:
    """Scripture references written as Book chapter:verse, with the internal code where the book is known."""
    out = []
    for m in _REFERENCE.finditer(text or ""):
        book, chapter, v1, v2 = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        code = StudyBibleDB._normalize_reference(None, f"{book} {chapter}:{v1}").split(".")[0]
        out.append({"text": m.group(0), "code": code, "chapter": chapter, "v1": v1,
                    "v2": int(v2) if v2 and int(v2) > v1 else v1, "start": m.start(), "end": m.end()})
    return out


def _hint_for(quote_start: int, quote_end: int, refs: list[dict]) -> dict | None:
    """The reference written just after a quotation, or just before it ("John 3:16 says, “…”")."""
    after = [r for r in refs if 0 <= r["start"] - quote_end <= 30]
    before = [r for r in refs if 0 <= quote_start - r["end"] <= 60]
    return (after or before or [None])[0]


# ---------------------------------------------------------------------------------------------
# The bundled Bible text
# ---------------------------------------------------------------------------------------------

def _bible_path() -> Path | None:
    env = os.environ.get("STUDY_BIBLE_DB")
    path = Path(env) if env else _ROOT / "db" / "study_bible.db"
    return path if path.exists() else None


class Bible:
    """Read-only lookups in study_bible.db. A connection per call, so any thread may use it."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._codes: set[str] | None = None

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)

    def codes(self) -> set[str]:
        """The book codes the bundled text knows."""
        if self._codes is None:
            with self._connect() as c:
                self._codes = {b for (b,) in c.execute("SELECT DISTINCT book FROM translations")}
        return self._codes

    def verse_exists(self, code: str, chapter: int, verse: int) -> bool:
        ref = f"{code}.{chapter}.{verse}"
        with self._connect() as c:
            return bool(c.execute("SELECT 1 FROM translations WHERE translation IN ('BSB', 'WEB') AND reference = ? "
                                  "LIMIT 1", (ref,)).fetchone())

    def _passages(self, c: sqlite3.Connection, code: str, chapter: int, first: int, last: int) -> list[str]:
        refs = [f"{code}.{chapter}.{v}" for v in range(max(1, first), last + 1)]
        marks = ",".join("?" * len(refs))
        out = []
        for tr in _TRANSLATIONS:
            rows = c.execute(f"SELECT verse, text FROM translations WHERE translation = ? AND reference IN ({marks}) "
                             "ORDER BY verse", (tr, *refs)).fetchall()
            if rows:
                out.append(normalize(" ".join(t for _, t in rows)))
        return out

    def holds(self, fragment: str, hint: dict | None = None) -> bool:
        """Whether a normalized fragment appears in a bundled translation, near the hinted reference
        if one is given, else anywhere (found by three-word windows, then checked with the verses
        around each candidate)."""
        with self._connect() as c:
            if hint and hint["code"] in self.codes():
                if any(fragment in p for p in self._passages(c, hint["code"], hint["chapter"],
                                                             hint["v1"] - 1, hint["v2"] + 1)):
                    return True
            words = fragment.split()
            starts = sorted({0, max(0, len(words) // 2 - 1), max(0, len(words) - 3)})
            seen: set[tuple] = set()
            for s in starts:
                window = " ".join(words[s:s + 3])
                for tr, ref in c.execute("SELECT translation, reference FROM translations WHERE text LIKE ? LIMIT 30",
                                         (f"%{window}%",)):
                    code, chapter, verse = ref.split(".")
                    key = (tr, code, chapter, verse)
                    if key in seen:
                        continue
                    seen.add(key)
                    refs = [f"{code}.{chapter}.{v}" for v in range(max(1, int(verse) - 2), int(verse) + 3)]
                    rows = c.execute(f"SELECT text FROM translations WHERE translation = ? AND reference IN "
                                     f"({','.join('?' * len(refs))}) ORDER BY verse", (tr, *refs)).fetchall()
                    if fragment in normalize(" ".join(t for (t,) in rows)):
                        return True
        return False


_bible: Bible | None = None


def bible() -> Bible | None:
    """The bundled Bible text, or None where this server has no study_bible.db."""
    global _bible
    if _bible is None:
        path = _bible_path()
        _bible = Bible(path) if path else None
    return _bible


# ---------------------------------------------------------------------------------------------
# Is a quotation held somewhere?
# ---------------------------------------------------------------------------------------------

class Held:
    """Texts a quotation may come from, normalized once as they grow."""

    def __init__(self, texts: list[str]) -> None:
        self.texts = texts
        self._seen = 0
        self._joined = ""

    def has(self, fragment: str) -> bool:
        if self._seen != len(self.texts):
            self._joined = " | ".join(normalize(t) for t in self.texts)
            self._seen = len(self.texts)
        return fragment in self._joined


def found(quote: str, held: Held, local: Bible | None = None, hint: dict | None = None) -> bool:
    """Whether every piece of a quotation is in the held texts or the bundled Bible."""
    pieces = _fragments(quote)
    if not pieces:
        return True   # too short to say anything about
    return all(held.has(p) or (local is not None and local.holds(p, hint)) for p in pieces)


_BIBLE_MIN_WORDS = 6   # the bundled Bible vouches only for a quotation this long


def quote_check(run: Recorder, local: Bible | None = None):
    """For the reply check: a quotation passes only when this run's tool results hold it, or, at six
    words or more, the bundled Bible text does. A short phrase like "I love you" occurs in Scripture
    (John 21:15), so the Bible alone cannot vouch for it, and a quotation too short to compare fails.
    Earlier tool results in the transcript are left out, since the browser supplies them."""
    held = Held(run.outputs)

    def ok(quote: str) -> bool:
        pieces = _fragments(quote) or [p for p in [normalize(quote)] if p]
        return bool(pieces) and all(
            held.has(p) or (local is not None and len(p.split()) >= _BIBLE_MIN_WORDS and local.holds(p))
            for p in pieces)
    return ok


# ---------------------------------------------------------------------------------------------
# The note under a chat reply, and the Generator report
# ---------------------------------------------------------------------------------------------

def _snippet(quote: str, words: int = 8) -> str:
    parts = quote.split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def unfound(text: str, held: Held, local: Bible | None, min_words: int = 6) -> tuple[int, list[str]]:
    """(quotations checked, snippets of those found nowhere)."""
    refs = references(text)
    quotes = quotations(text, min_words)
    missing = [_snippet(q) for q, s, e in quotes if not found(q, held, local, _hint_for(s, e, refs))]
    return len(quotes), list(dict.fromkeys(missing))   # a quotation repeated is listed once


def chat_note(reply: str, run: Recorder, earlier: list[str], local: Bible | None) -> str | None:
    """The line shown under a chat reply, or None. A reply that used no library tool says so. One that
    did lists quotations neither the library results (this run's and the study's earlier ones) nor
    the bundled Bible text hold."""
    if not reply.strip():
        return None
    if not run.outputs:
        return NO_SOURCE
    _, missing = unfound(reply, Held(run.outputs + earlier), local)
    if not missing:
        return None
    listed = ", ".join(f"“{m}”" for m in missing[:3])
    if len(missing) == 1:
        return f"Not found in the library results or the bundled Bible text: {listed}."
    return f"{len(missing)} quotations were not found in the library results or the bundled Bible text: {listed}."


def generator_report(document: str, held_texts: list[str], local: Bible | None) -> dict:
    """References checked against the bundled Bible, and quotations found in neither this run's
    sources (its prompt material and tool results) nor the bundled Bible text. It never blocks a
    download and never calls anything verified."""
    refs = references(document)
    checked, missing_refs = 0, []
    if local is not None:
        known = local.codes()
        for r in refs:
            if r["code"] not in known:
                continue   # a book this check cannot name is left out of the count
            checked += 1
            if not (local.verse_exists(r["code"], r["chapter"], r["v1"])
                    and local.verse_exists(r["code"], r["chapter"], r["v2"])):
                missing_refs.append(r["text"])
    quotes, not_found = unfound(document, Held(held_texts), local, min_words=5)
    return {"type": "report", "references": checked, "missing_references": sorted(set(missing_refs)),
            "quotations": quotes, "quotations_not_found": not_found}
