"""
Database layer for the Study Bible MCP server.

Uses SQLite with async access via aiosqlite.
"""

import json
import os
import re
import sqlite3
from collections import deque
from pathlib import Path
from typing import Any

import aiosqlite
import logging

logger = logging.getLogger("study-bible-mcp")

# Canonical book abbreviation map — used by _normalize_reference() and importable by server.py
BOOK_ABBREV_MAP = {
    "genesis": "Gen", "gen": "Gen",
    "exodus": "Exo", "exod": "Exo", "ex": "Exo",
    "leviticus": "Lev", "lev": "Lev",
    "numbers": "Num", "num": "Num",
    "deuteronomy": "Deu", "deut": "Deu", "dt": "Deu",
    "joshua": "Jos", "josh": "Jos",
    "judges": "Jdg", "judg": "Jdg",
    "ruth": "Rut",
    "1 samuel": "1Sa", "1sam": "1Sa", "1 sam": "1Sa",
    "2 samuel": "2Sa", "2sam": "2Sa", "2 sam": "2Sa",
    "1 kings": "1Ki", "1kgs": "1Ki", "1 kgs": "1Ki",
    "2 kings": "2Ki", "2kgs": "2Ki", "2 kgs": "2Ki",
    "1 chronicles": "1Ch", "1chr": "1Ch", "1 chr": "1Ch",
    "2 chronicles": "2Ch", "2chr": "2Ch", "2 chr": "2Ch",
    "ezra": "Ezr",
    "nehemiah": "Neh", "neh": "Neh",
    "esther": "Est", "esth": "Est",
    "job": "Job",
    "psalms": "Psa", "psalm": "Psa", "ps": "Psa",
    "proverbs": "Pro", "prov": "Pro", "pr": "Pro",
    "ecclesiastes": "Ecc", "eccl": "Ecc",
    "song of solomon": "Sng", "song": "Sng", "sos": "Sng",
    "isaiah": "Isa", "isa": "Isa",
    "jeremiah": "Jer", "jer": "Jer",
    "lamentations": "Lam", "lam": "Lam",
    "ezekiel": "Ezk", "ezek": "Ezk", "eze": "Ezk",
    "daniel": "Dan", "dan": "Dan",
    "hosea": "Hos", "hos": "Hos",
    "joel": "Jol",
    "amos": "Amo",
    "obadiah": "Oba", "obad": "Oba",
    "jonah": "Jon",
    "micah": "Mic", "mic": "Mic",
    "nahum": "Nam", "nah": "Nam",
    "habakkuk": "Hab", "hab": "Hab",
    "zephaniah": "Zep", "zeph": "Zep",
    "haggai": "Hag", "hag": "Hag",
    "zechariah": "Zec", "zech": "Zec",
    "malachi": "Mal", "mal": "Mal",
    "matthew": "Mat", "matt": "Mat", "mt": "Mat",
    "mark": "Mrk", "mk": "Mrk",
    "luke": "Luk", "lk": "Luk",
    "john": "Jhn", "jn": "Jhn",
    "acts": "Act",
    "romans": "Rom", "rom": "Rom",
    "1 corinthians": "1Co", "1cor": "1Co", "1 cor": "1Co",
    "2 corinthians": "2Co", "2cor": "2Co", "2 cor": "2Co",
    "galatians": "Gal", "gal": "Gal",
    "ephesians": "Eph", "eph": "Eph",
    "philippians": "Php", "phil": "Php",
    "colossians": "Col", "col": "Col",
    "1 thessalonians": "1Th", "1thess": "1Th", "1 thess": "1Th",
    "2 thessalonians": "2Th", "2thess": "2Th", "2 thess": "2Th",
    "1 timothy": "1Ti", "1tim": "1Ti", "1 tim": "1Ti",
    "2 timothy": "2Ti", "2tim": "2Ti", "2 tim": "2Ti",
    "titus": "Tit",
    "philemon": "Phm", "phlm": "Phm",
    "hebrews": "Heb", "heb": "Heb",
    "james": "Jas", "jas": "Jas",
    "1 peter": "1Pe", "1pet": "1Pe", "1 pet": "1Pe",
    "2 peter": "2Pe", "2pet": "2Pe", "2 pet": "2Pe",
    "1 john": "1Jn", "1jn": "1Jn",
    "2 john": "2Jn", "2jn": "2Jn",
    "3 john": "3Jn", "3jn": "3Jn",
    "jude": "Jud",
    "revelation": "Rev", "rev": "Rev",
    # Deuterocanon / apocrypha. The readable text is bundled in the WEB
    # translation only; "judith" is listed explicitly so it no longer collapses
    # onto Jude ("Jud") via the [:3] fallback.
    "tobit": "Tob", "tob": "Tob",
    "judith": "Jdt", "jdt": "Jdt",
    "wisdom": "Wis", "wisdom of solomon": "Wis", "wis": "Wis",
    "sirach": "Sir", "ecclesiasticus": "Sir", "sir": "Sir",
    "baruch": "Bar", "bar": "Bar",
    "1 maccabees": "1Ma", "1 macc": "1Ma", "1macc": "1Ma", "1ma": "1Ma",
    "2 maccabees": "2Ma", "2 macc": "2Ma", "2macc": "2Ma", "2ma": "2Ma",
    "3 maccabees": "3Ma", "3 macc": "3Ma", "3macc": "3Ma", "3ma": "3Ma",
    "4 maccabees": "4Ma", "4 macc": "4Ma", "4macc": "4Ma", "4ma": "4Ma",
    "1 esdras": "1Es", "1esd": "1Es", "1 esd": "1Es", "1es": "1Es",
    "2 esdras": "2Es", "2esd": "2Es", "2 esd": "2Es", "2es": "2Es",
    "prayer of manasseh": "Man", "manasseh": "Man", "man": "Man",
    "greek esther": "Esg", "additions to esther": "Esg", "esg": "Esg",
}

# OSIS book tokens as used in the theology.db `refs` column (Gen/Exod/Matt/1Cor/Heb/…) — distinct
# from the internal codes above (Exo/Mat/1Co/…). Used by theology_by_ref + reference detection so a
# book/verse question can surface the grounding work tagged to it. (osis, [names/abbrevs]).
_OSIS_BOOKS = [
    ("Gen", ["genesis", "gen"]), ("Exod", ["exodus", "exod", "ex"]), ("Lev", ["leviticus", "lev"]),
    ("Num", ["numbers", "num"]), ("Deut", ["deuteronomy", "deut", "dt"]), ("Josh", ["joshua", "josh"]),
    ("Judg", ["judges", "judg"]), ("Ruth", ["ruth"]),
    ("1Sam", ["1 samuel", "1samuel", "1 sam", "1sam"]), ("2Sam", ["2 samuel", "2samuel", "2 sam", "2sam"]),
    ("1Kgs", ["1 kings", "1kings", "1 kgs", "1kgs"]), ("2Kgs", ["2 kings", "2kings", "2 kgs", "2kgs"]),
    ("1Chr", ["1 chronicles", "1chronicles", "1 chron", "1chr"]),
    ("2Chr", ["2 chronicles", "2chronicles", "2 chron", "2chr"]),
    ("Ezra", ["ezra"]), ("Neh", ["nehemiah", "neh"]), ("Esth", ["esther", "esth"]), ("Job", ["job"]),
    ("Ps", ["psalms", "psalm", "ps", "psa"]), ("Prov", ["proverbs", "prov"]),
    ("Eccl", ["ecclesiastes", "eccl", "eccles"]), ("Song", ["song of solomon", "song of songs", "song", "canticles"]),
    ("Isa", ["isaiah", "isa"]), ("Jer", ["jeremiah", "jer"]), ("Lam", ["lamentations", "lam"]),
    ("Ezek", ["ezekiel", "ezek"]), ("Dan", ["daniel", "dan"]), ("Hos", ["hosea", "hos"]),
    ("Joel", ["joel"]), ("Amos", ["amos"]), ("Obad", ["obadiah", "obad"]), ("Jonah", ["jonah", "jon"]),
    ("Mic", ["micah", "mic"]), ("Nah", ["nahum", "nah"]), ("Hab", ["habakkuk", "hab"]),
    ("Zeph", ["zephaniah", "zeph"]), ("Hag", ["haggai", "hag"]), ("Zech", ["zechariah", "zech"]),
    ("Mal", ["malachi", "mal"]),
    ("Matt", ["matthew", "matt", "mt"]), ("Mark", ["mark", "mk"]), ("Luke", ["luke", "lk"]),
    ("John", ["john", "jn"]), ("Acts", ["acts"]), ("Rom", ["romans", "rom"]),
    ("1Cor", ["1 corinthians", "1corinthians", "1 cor", "1cor"]),
    ("2Cor", ["2 corinthians", "2corinthians", "2 cor", "2cor"]),
    ("Gal", ["galatians", "gal"]), ("Eph", ["ephesians", "eph"]), ("Phil", ["philippians", "phil"]),
    ("Col", ["colossians", "col"]),
    ("1Thess", ["1 thessalonians", "1thessalonians", "1 thess", "1thess"]),
    ("2Thess", ["2 thessalonians", "2thessalonians", "2 thess", "2thess"]),
    ("1Tim", ["1 timothy", "1timothy", "1 tim", "1tim"]), ("2Tim", ["2 timothy", "2timothy", "2 tim", "2tim"]),
    ("Titus", ["titus"]), ("Phlm", ["philemon", "phlm", "philem"]), ("Heb", ["hebrews", "heb"]),
    ("Jas", ["james", "jas"]), ("1Pet", ["1 peter", "1peter", "1 pet", "1pet"]),
    ("2Pet", ["2 peter", "2peter", "2 pet", "2pet"]),
    ("1John", ["1 john", "1john", "1 jn"]), ("2John", ["2 john", "2john", "2 jn"]),
    ("3John", ["3 john", "3john", "3 jn"]), ("Jude", ["jude"]), ("Rev", ["revelation", "rev", "apocalypse"]),
]
_NAME_TO_OSIS = {name: osis for osis, names in _OSIS_BOOKS for name in names}
_OSIS_TO_NAME = {osis: names[0] for osis, names in _OSIS_BOOKS}

# Single-chapter books are conventionally cited by verse alone ("Jude 3" =
# Jude 1:3, "Obadiah 15" = Obadiah 1:15). Internally they are stored with
# chapter 1, so a bare "Book N" must be read as verse N of chapter 1.
# Prayer of Manasseh (Man) and Psalm 151 (Ps2) are single-chapter deuterocanon.
SINGLE_CHAPTER_BOOKS = {"Oba", "Phm", "2Jn", "3Jn", "Jud", "Man", "Ps2"}

# The 14 deuterocanonical books carried by the WEB translation (and no other
# bundled translation). Used to auto-route deuterocanon references to WEB.
DEUTERO_BOOKS = {
    "Tob", "Jdt", "Wis", "Sir", "Bar", "1Ma", "2Ma", "3Ma", "4Ma",
    "1Es", "2Es", "Man", "Esg", "Ps2",
}

# Additions the WEB text folds into an existing book/chapter instead of giving
# them their own code. Name -> (internal book code, chapter). Cited by verse,
# e.g. "Susanna 5" -> Dan 13:5, "Letter of Jeremiah 3" -> Baruch 6:3,
# "Psalm 151:2" -> Ps2 1:2.
DEUTERO_FOLDED = {
    "susanna": ("Dan", 13),
    "bel and the dragon": ("Dan", 14), "bel": ("Dan", 14),
    "prayer of azariah": ("Dan", 3),
    "song of the three holy children": ("Dan", 3), "song of the three": ("Dan", 3),
    "letter of jeremiah": ("Bar", 6), "epistle of jeremiah": ("Bar", 6),
    "psalm 151": ("Ps2", 1), "ps 151": ("Ps2", 1), "psalm151": ("Ps2", 1),
}


def resolve_folded_ref(reference: str) -> tuple[str, int, int, int] | None:
    """Resolve a folded deuterocanon citation to (code, chapter, v_start, v_end).

    'Susanna 5' -> ('Dan', 13, 5, 5); 'Letter of Jeremiah 3-4' -> ('Bar', 6, 3, 4);
    'Psalm 151' -> ('Ps2', 1, 1, 999); 'Psalm 151:2' -> ('Ps2', 1, 2, 2).
    Returns None if the reference is not a folded deuterocanon unit.
    """
    low = " ".join(reference.strip().lower().split())
    for name, (code, chap) in DEUTERO_FOLDED.items():
        if low == name:
            return (code, chap, 1, 999)
        if low.startswith(name):
            rest = low[len(name):].strip().lstrip(":").strip()
            # Accept a verse ("Susanna 5"), a range ("... 5-7"), or a
            # chapter:verse form whose chapter is the folded one ("Susanna 1:5").
            m = re.match(r"^(?:\d+:)?(\d+)(?:-(\d+))?$", rest)
            if m:
                v1 = int(m.group(1))
                v2 = int(m.group(2)) if m.group(2) else v1
                return (code, chap, v1, v2)
    return None


class StudyBibleDB:
    """Async SQLite database interface for Bible study data."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        """Open a tuned, read-only connection to the prebuilt database.

        The shipped DB is built once and never written at runtime, so we open it
        immutable and memory-mapped with a real page cache. Without this, SQLite
        uses a ~2 MB cache and plain pread() calls against the ~800 MB file, which
        on a small shared vCPU (e.g. Fly shared-cpu-1x) makes cold queries slow.
        mmap pages are file-backed and reclaimable, so this is safe on 1 GB RAM.
        """
        try:
            uri = f"file:{self.db_path.resolve().as_posix()}?mode=ro&immutable=1"
            self.conn = await aiosqlite.connect(uri, uri=True)
        except Exception:
            # Fall back to a plain open if the path can't be expressed as a URI.
            self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        for pragma in (
            "PRAGMA query_only=ON",
            "PRAGMA mmap_size=536870912",   # 512 MB memory-map
            "PRAGMA cache_size=-65536",     # 64 MB page cache (negative = KiB)
            "PRAGMA temp_store=MEMORY",
        ):
            try:
                await self.conn.execute(pragma)
            except Exception:
                pass

        # Attach the theology grounding corpus (the R2-distributed theology.db) if present, so
        # its FTS5 full text + scripture refs are queryable at call time. Read-only/immutable;
        # absent file → self.has_theology stays False and grounding tools degrade gracefully.
        self.has_theology = False
        self.has_theology_vec = False
        theo = os.environ.get("THEOLOGY_DB") or str(self.db_path.parent / "theology.db")
        if Path(theo).exists():
            try:
                turi = f"file:{Path(theo).resolve().as_posix()}?mode=ro&immutable=1"
                await self.conn.execute(f"ATTACH DATABASE '{turi}' AS theology")
                self.has_theology = True
            except Exception:
                logging.getLogger("studybible-mcp").warning("could not attach theology.db at %s", theo)
        # Load sqlite-vec so the theology.db vec0 table (semantic layer) is queryable. Optional:
        # absent extension or vectors → keyword grounding (FTS) still works.
        if self.has_theology:
            try:
                import sqlite_vec

                await self.conn.enable_load_extension(True)
                await self.conn.load_extension(sqlite_vec.loadable_path())
                await self.conn.enable_load_extension(False)
                async with self.conn.execute("select count(*) from theology.theology_vecmeta") as cur:
                    if await cur.fetchone():
                        self.has_theology_vec = True
            except Exception:
                logging.getLogger("studybible-mcp").info("theology semantic layer off (sqlite-vec/vectors absent)")

    async def close(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    async def _fetchall(self, sql: str, params: tuple | list = ()) -> list[dict]:
        """Execute SQL and return all rows as dicts."""
        async with self.conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def _fetchone(self, sql: str, params: tuple | list = ()) -> dict | None:
        """Execute SQL and return one row as dict, or None."""
        async with self.conn.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    # ---- theology grounding corpus (attached theology.db; FTS5 over PD full texts) ----
    @staticmethod
    def _theology_fts_expr(query: str) -> str | None:
        """Turn a natural query into a safe FTS5 AND-of-terms expression (quoted tokens),
        stripping FTS operators so user input can't break or inject the MATCH."""
        toks = re.findall(r"[A-Za-z0-9']+", query or "")
        return " ".join(f'"{t}"' for t in toks) or None

    async def search_theology(self, query: str, author: str | None = None, limit: int = 8) -> list[dict]:
        """BM25 full-text search over the church's PD treasury, returning cited passages.
        Bare `theology_fts` is used for match/snippet/bm25; join tables are schema-qualified."""
        if not getattr(self, "has_theology", False):
            return []
        expr = self._theology_fts_expr(query)
        if not expr:
            return []
        sql = (
            "select w.author, w.title, t.text, t.refs, t.work_id, "
            "snippet(theology_fts, 0, '', '', ' … ', 18) as snippet "
            "from theology.theology_fts "
            "join theology.theology_texts t on t.id = theology_fts.rowid "
            "join theology.theology_works w on w.work_id = t.work_id "
            "where theology_fts match ?"
        )
        params: list = [expr]
        if author:
            sql += " and w.author like ?"
            params.append(f"%{author.strip().lower()}%")
        sql += " order by bm25(theology_fts) limit ?"
        params.append(max(1, min(int(limit or 8), 25)))
        return await self._fetchall(sql, params)

    _theo_model = None  # model2vec query-embedder, loaded once per process

    @classmethod
    def _theology_model(cls):
        if cls._theo_model is None:
            from model2vec import StaticModel
            cls._theo_model = StaticModel.from_pretrained("minishlab/potion-retrieval-32M")
        return cls._theo_model

    async def semantic_theology(self, query: str, limit: int = 8) -> list[dict]:
        """Semantic (fuzzy) recall over the treasury via sqlite-vec KNN — finds passages by meaning
        even when the exact term isn't used. Query embedded locally (model2vec), int8, one vec0 KNN."""
        if not getattr(self, "has_theology_vec", False) or not (query or "").strip():
            return []
        import numpy as np

        v = self._theology_model().encode([query])[0].astype(np.float32)
        n = float(np.linalg.norm(v)) or 1.0
        q8 = np.clip(np.round(v / n * 127.0), -127, 127).astype(np.int8).tobytes()
        sql = (
            "select w.author, w.title, p.text, p.work_id, v.distance "
            "from theology.theology_vec v "
            "join theology.theology_passages p on p.id = v.id "
            "join theology.theology_works w on w.work_id = p.work_id "
            "where v.emb match vec_int8(?) and v.k = ? "  # vec0 KNN needs an explicit k
            "order by v.distance"
        )
        return await self._fetchall(sql, [q8, max(1, min(int(limit or 8), 25))])

    async def theology_by_ref(self, osis_book: str, chapter: int | None = None,
                              verse: int | None = None, limit: int = 6) -> list[dict]:
        """Passages tagged (in `refs`) with a given Scripture reference — the bridge that makes a
        book/verse question surface the work devoted to it (e.g. 'Hebrews' -> Owen's Exposition).
        Dedicated commentaries (whose title names the book) rank first, then by document order."""
        if not getattr(self, "has_theology", False) or not osis_book:
            return []
        # refs are JSON like ["Bible:Heb.1.3"] / ["Bible:Heb.1.1-Heb.1.2"]; match by specificity.
        if verse is not None and chapter is not None:
            like = f'%"Bible:{osis_book}.{chapter}.{verse}%'
        elif chapter is not None:
            like = f'%"Bible:{osis_book}.{chapter}.%'
        else:
            like = f'%"Bible:{osis_book}.%'
        # One representative passage per work, so the *set* of works devoted to this reference
        # surfaces (Owen's Exposition among the other Hebrews commentaries), dedicated works
        # (whose title names the book) first.
        book_word = _OSIS_TO_NAME.get(osis_book, osis_book).lower()
        sql = (
            "select w.author, w.title, t.text, t.refs, t.work_id from ("
            "  select id, work_id, text, refs, "
            "         row_number() over (partition by work_id order by id) rn "
            "  from theology.theology_texts where refs like ?"
            ") t join theology.theology_works w on w.work_id = t.work_id "
            "where t.rn = 1 "
            "order by (case when lower(w.title) like ? then 0 else 1 end), t.work_id "
            "limit ?"
        )
        return await self._fetchall(sql, [like, f"%{book_word}%", max(1, min(int(limit or 6), 25))])

    async def _table_has_rows(self, table: str) -> bool:
        """Check if a table exists and has at least one row."""
        try:
            async with self.conn.execute(f"SELECT 1 FROM {table} LIMIT 1") as cursor:
                return await cursor.fetchone() is not None
        except Exception:
            return False

    # =========================================================================
    # Lexicon queries
    # =========================================================================
    
    @staticmethod
    def _normalize_strongs(strongs: str) -> str:
        """Normalize Strong's number to match DB format (e.g., G26 -> G0026)."""
        strongs = strongs.upper().strip()
        if len(strongs) >= 2 and strongs[0] in ("G", "H"):
            num = strongs[1:]
            return strongs[0] + num.zfill(4)
        return strongs

    async def get_lexicon_entry(self, strongs: str) -> dict | None:
        """Get a single lexicon entry by Strong's number."""
        strongs = self._normalize_strongs(strongs)
        return await self._fetchone("SELECT * FROM lexicon WHERE strongs = ?", (strongs,))
    
    async def search_lexicon(
        self,
        query: str,
        language: str | None = None,
        limit: int = 10
    ) -> list[dict]:
        """Search lexicon by definition, transliteration, or word."""
        query_lower = f"%{query.lower()}%"
        
        sql = """
            SELECT * FROM lexicon
            WHERE (
                LOWER(short_definition) LIKE ?
                OR LOWER(full_definition) LIKE ?
                OR LOWER(transliteration) LIKE ?
                OR LOWER(word) LIKE ?
                OR LOWER(abbott_smith_def) LIKE ?
            )
        """
        params = [query_lower, query_lower, query_lower, query_lower, query_lower]
        
        if language:
            sql += " AND language = ?"
            params.append(language.lower())
        
        sql += " ORDER BY usage_count DESC LIMIT ?"
        params.append(limit)
        return await self._fetchall(sql, params)
    
    async def get_related_words(self, strongs: str) -> list[dict]:
        """Get words related to a Strong's number."""
        entry = await self.get_lexicon_entry(strongs)
        if not entry or not entry.get('related_words'):
            return []
        
        try:
            related = json.loads(entry['related_words'])
            results = []
            for r in related:
                if isinstance(r, dict) and r.get('strongs'):
                    full_entry = await self.get_lexicon_entry(r['strongs'])
                    if full_entry:
                        results.append(full_entry)
            return results
        except Exception:
            return []
    
    # =========================================================================
    # Verse queries
    # =========================================================================
    
    def _normalize_reference(self, reference: str) -> str:
        """Normalize a Bible reference to database format ('John 3:16' -> 'Jhn.3.16').

        Also handles the verse-only citation form of single-chapter books
        ('Jude 3' -> 'Jud.1.3', 'Obadiah 15' -> 'Oba.1.15').
        """
        ref = reference.strip()

        # Folded deuterocanon units, e.g. "Susanna 5" -> Dan.13.5,
        # "Letter of Jeremiah 3" -> Bar.6.3, "Psalm 151:2" -> Ps2.1.2.
        folded = resolve_folded_ref(ref)
        if folded:
            code, chap, v1, _ = folded
            return f"{code}.{chap}.{v1}"

        # Chapter:verse form, e.g. "John 3:16", "1 Corinthians 13:4-7".
        match = re.match(r'^(\d?\s*[a-zA-Z]+)\s*(\d+):(\d+)(?:-\d+)?$', ref)
        if match:
            book, chapter, verse_start = match.group(1), match.group(2), match.group(3)
            book_abbr = BOOK_ABBREV_MAP.get(book.lower().strip(), book[:3].title())
            return f"{book_abbr}.{chapter}.{verse_start}"

        # Verse-only form of a single-chapter book, e.g. "Jude 3", "Philemon 6".
        match = re.match(r'^(\d?\s*[a-zA-Z]+)\s*(\d+)(?:-\d+)?$', ref)
        if match:
            book, num = match.group(1), match.group(2)
            book_abbr = BOOK_ABBREV_MAP.get(book.lower().strip(), book[:3].title())
            if book_abbr in SINGLE_CHAPTER_BOOKS:
                return f"{book_abbr}.1.{num}"

        return ref
    
    async def get_verse(self, reference: str) -> dict | None:
        """Get a verse by reference.

        Matches either the canonical (English) versification or the alternate
        (Hebrew/variant) versification exactly, so both 'Malachi 4:1' and the
        Hebrew 'Malachi 3:19' resolve to the same verse.
        """
        normalized = self._normalize_reference(reference)
        return (
            await self._fetchone("SELECT * FROM verses WHERE reference = ?", (normalized,))
            or await self._fetchone("SELECT * FROM verses WHERE ref_alt = ?", (normalized,))
        )
    
    async def get_verses_with_strongs(self, strongs: str, limit: int = 20) -> list[dict]:
        """Find verses containing a specific Strong's number."""
        strongs = self._normalize_strongs(strongs)
        return await self._fetchall(
            "SELECT * FROM verses WHERE word_data LIKE ? LIMIT ?",
            (f'%"{strongs}"%', limit),
        )
    
    # =========================================================================
    # Cross-reference queries
    # =========================================================================
    

    async def get_cross_references(
        self,
        reference: str,
        source_filter: str | None = None,
        limit: int = 8,
        min_strength: int | None = None,
    ) -> list[dict]:
        """Cross-references for a verse, from OpenBible.info (CC BY 4.0), ranked
        by community-vote weight (OpenBible's vote count is stored as `relevance`).

        Args:
            reference: verse reference, e.g. "John 3:16".
            source_filter: optional `type` to restrict to (currently only
                'openbible' is loaded).
            limit: max rows returned, highest-voted first.
            min_strength: if set, drop rows with relevance below this vote floor.
        """
        normalized = self._normalize_reference(reference)
        params: list = [normalized]
        clauses = ["source = ?"]
        if source_filter:
            clauses.append("type = ?")
            params.append(source_filter)
        if min_strength is not None:
            clauses.append("relevance >= ?")
            params.append(int(min_strength))
        params.append(limit)
        sql = f"""
            SELECT source, target, type, note, relevance
            FROM cross_references
            WHERE {' AND '.join(clauses)}
            ORDER BY relevance DESC, target
            LIMIT ?
        """
        return await self._fetchall(sql, params)

    async def get_thematic_references(self, theme: str) -> list[dict]:
        """Get references for a theological theme."""
        theme_lower = theme.lower().replace(" ", "_")
        return await self._fetchall(
            "SELECT * FROM thematic_references WHERE theme = ? OR theme LIKE ?",
            (theme_lower, f"%{theme_lower}%"),
        )
    
    # =========================================================================
    # Name queries
    # =========================================================================
    
    async def lookup_name(self, name: str, name_type: str | None = None) -> list[dict]:
        """Look up a biblical name."""
        name_pattern = f"%{name}%"
        if name_type:
            return await self._fetchall("SELECT * FROM names WHERE name LIKE ? AND type = ?", (name_pattern, name_type))
        return await self._fetchall("SELECT * FROM names WHERE name LIKE ?", (name_pattern,))
    
    # =========================================================================
    # Morphology queries
    # =========================================================================
    
    async def get_morphology(self, code: str, language: str = "greek") -> dict | None:
        """Get morphology parsing for a code."""
        return await self._fetchone("SELECT * FROM morphology WHERE code = ? AND language = ?", (code, language.lower()))

    # =========================================================================
    # Septuagint (LXX) text + versification mapping
    # =========================================================================

    async def has_lxx_data(self) -> bool:
        """Check whether the Greek LXX text has been imported."""
        return await self._table_has_rows("lxx_verses")

    async def get_lxx_verse(self, lxx_ref: str) -> dict | None:
        """Get the Greek LXX verse at an LXX-numbered reference ('Psa.50.1')."""
        return await self._fetchone(
            "SELECT * FROM lxx_verses WHERE reference = ?", (lxx_ref,)
        )

    async def lxx_to_standard(self, lxx_ref: str) -> str | None:
        """Map an LXX reference to its standard (English) reference, if it differs."""
        row = await self._fetchone(
            "SELECT standard_ref FROM versification_map WHERE lxx_ref = ?", (lxx_ref,)
        )
        return row["standard_ref"] if row else None

    async def standard_to_lxx(self, standard_ref: str) -> str | None:
        """Map a standard (English) reference to its LXX reference, if it differs."""
        row = await self._fetchone(
            "SELECT lxx_ref FROM versification_map WHERE standard_ref = ?", (standard_ref,)
        )
        return row["lxx_ref"] if row else None

    # =========================================================================
    # Readable translations
    # =========================================================================

    async def has_translations(self) -> bool:
        return await self._table_has_rows("translations")

    async def available_translations(self) -> list[str]:
        rows = await self._fetchall(
            "SELECT DISTINCT translation FROM translations ORDER BY translation"
        )
        return [r["translation"] for r in rows]

    async def get_translation_verse(self, translation: str, reference: str) -> dict | None:
        """Readable text of one verse in a translation (reference is 'Book.C.V')."""
        return await self._fetchone(
            "SELECT * FROM translations WHERE translation = ? AND reference = ?",
            (translation.upper(), reference),
        )

    async def get_translation_passage(
        self, translation: str, book: str, chapter: int,
        verse_start: int, verse_end: int,
    ) -> list[dict]:
        """Readable verses in a chapter range, ordered by verse."""
        return await self._fetchall(
            "SELECT reference, verse, text FROM translations "
            "WHERE translation = ? AND book = ? AND chapter = ? AND verse BETWEEN ? AND ? "
            "ORDER BY verse",
            (translation.upper(), book, chapter, verse_start, verse_end),
        )

    # =========================================================================
    # Word frequency / reader-mode vocabulary
    # =========================================================================

    async def has_word_frequency(self) -> bool:
        return await self._table_has_rows("word_frequency")

    async def get_verses_in_range(
        self, book: str, chapter: int, verse_start: int, verse_end: int,
    ) -> list[dict]:
        """Tagged (original-language) verses in a chapter range, ordered by verse."""
        return await self._fetchall(
            "SELECT reference, verse, word_data FROM verses "
            "WHERE book = ? AND chapter = ? AND verse BETWEEN ? AND ? ORDER BY verse",
            (book, chapter, verse_start, verse_end),
        )

    async def get_frequencies(self, strongs_list: list[str]) -> dict[str, int]:
        """Corpus occurrence counts for a set of Strong's numbers."""
        if not strongs_list:
            return {}
        uniq = list({s for s in strongs_list})
        placeholders = ",".join("?" for _ in uniq)
        rows = await self._fetchall(
            f"SELECT strongs, count FROM word_frequency WHERE strongs IN ({placeholders})",
            uniq,
        )
        return {r["strongs"]: r["count"] for r in rows}

    # =========================================================================
    # Commentaries
    # =========================================================================

    async def has_commentaries(self) -> bool:
        return await self._table_has_rows("commentaries")

    async def available_commentaries(self) -> list[dict]:
        return await self._fetchall(
            "SELECT DISTINCT source, source_name FROM commentaries ORDER BY source_name"
        )

    async def get_commentary(
        self, book: str, chapter: int, verse: int, sources: list[str] | None = None,
    ) -> list[dict]:
        """Commentary entries covering a verse (one per source), across sources."""
        sql = (
            "SELECT source, source_name, verse_start, verse_end, text FROM commentaries "
            "WHERE book = ? AND chapter = ? AND verse_start <= ? AND verse_end >= ?"
        )
        params: list = [book, chapter, verse, verse]
        if sources:
            sql += f" AND source IN ({','.join('?' for _ in sources)})"
            params += sources
        sql += " ORDER BY source_name"
        return await self._fetchall(sql, params)

    # =========================================================================
    # Patristic catena (church fathers)
    # =========================================================================

    async def has_catena(self) -> bool:
        return await self._table_has_rows("patristic_catena")

    async def count_catena(self, book: str, chapter: int, verse: int) -> int:
        row = await self._fetchone(
            "SELECT COUNT(*) AS c FROM patristic_catena "
            "WHERE book = ? AND chapter = ? AND verse_start <= ? AND verse_end >= ?",
            (book, chapter, verse, verse),
        )
        return row["c"] if row else 0

    async def get_catena(
        self, book: str, chapter: int, verse: int, limit: int = 8, father: str | None = None,
    ) -> list[dict]:
        """Church-father excerpts covering a verse, earliest first."""
        sql = (
            "SELECT father_name, father_category, year, verse_start, verse_end, "
            "quote, source_title, source_url, source FROM patristic_catena "
            "WHERE book = ? AND chapter = ? AND verse_start <= ? AND verse_end >= ?"
        )
        params: list = [book, chapter, verse, verse]
        if father:
            sql += " AND father_name LIKE ?"
            params.append(f"%{father}%")
        sql += " ORDER BY year IS NULL, year LIMIT ?"  # NULL years sort last, not as 'earliest'
        params.append(limit)
        return await self._fetchall(sql, params)

    # =========================================================================
    # Historical documents (creeds / confessions / catechisms)
    # =========================================================================

    async def has_historical_documents(self) -> bool:
        return await self._table_has_rows("historical_documents")

    async def list_historical_documents(self) -> list[dict]:
        return await self._fetchall(
            "SELECT doc_id, doc_title, doc_type, doc_date, tradition, COUNT(*) AS sections "
            "FROM historical_documents GROUP BY doc_id ORDER BY doc_title"
        )

    async def find_historical_doc_id(self, name: str) -> str | None:
        row = await self._fetchone(
            "SELECT doc_id FROM historical_documents "
            "WHERE LOWER(doc_title) LIKE ? OR doc_id LIKE ? LIMIT 1",
            (f"%{name.lower()}%", f"%{name.lower().replace(' ', '-')}%"),
        )
        return row["doc_id"] if row else None

    async def get_historical_document(self, doc_id: str) -> list[dict]:
        return await self._fetchall(
            "SELECT doc_title, doc_type, doc_date, tradition, section_num, section_label, content, topics "
            "FROM historical_documents WHERE doc_id = ? ORDER BY section_num",
            (doc_id,),
        )

    async def search_historical_documents(self, query: str, limit: int = 12) -> list[dict]:
        q = f"%{query.lower()}%"
        return await self._fetchall(
            "SELECT doc_title, tradition, section_label, content, topics FROM historical_documents "
            "WHERE LOWER(content) LIKE ? OR LOWER(topics) LIKE ? OR LOWER(section_label) LIKE ? "
            "ORDER BY doc_title, section_num LIMIT ?",
            (q, q, q, limit),
        )

    # =========================================================================
    # UBS parallel passages
    # =========================================================================

    async def has_parallel_passages(self) -> bool:
        return await self._table_has_rows("parallel_passages")

    async def get_parallel_passages(self, book: str, chapter: int, verse: int) -> list[dict]:
        """Return all members of every parallel group that contains a verse."""
        groups = await self._fetchall(
            "SELECT DISTINCT group_id FROM parallel_passages "
            "WHERE book = ? AND chapter = ? AND verse_start <= ? AND verse_end >= ?",
            (book, chapter, verse, verse),
        )
        if not groups:
            return []
        gids = [g["group_id"] for g in groups]
        placeholders = ",".join("?" for _ in gids)
        return await self._fetchall(
            f"SELECT group_id, ref_display, book, chapter, verse_start FROM parallel_passages "
            f"WHERE group_id IN ({placeholders}) ORDER BY group_id, id",
            gids,
        )

    # =========================================================================
    # Graph queries (Theographic Bible Metadata)
    # =========================================================================

    async def graph_find_person(self, name: str) -> list[dict]:
        """Find a person by name (fuzzy match).

        Orders by: exact name match first, then by number of aliases
        (more aliases = more prominent biblical figure), then family edges.
        """
        return await self._fetchall(
            """SELECT p.* FROM graph_people p
               LEFT JOIN (
                   SELECT from_person_id as pid, COUNT(*) as cnt FROM graph_family_edges GROUP BY from_person_id
                   UNION ALL
                   SELECT to_person_id, COUNT(*) FROM graph_family_edges GROUP BY to_person_id
               ) fe ON fe.pid = p.id
               WHERE LOWER(p.name) = LOWER(?)
                  OR LOWER(p.also_called) LIKE LOWER(?)
               GROUP BY p.id
               ORDER BY
                   CASE WHEN LOWER(p.name) = LOWER(?) THEN 0 ELSE 1 END,
                   LENGTH(COALESCE(p.also_called, '')) DESC,
                   COALESCE(SUM(fe.cnt), 0) DESC
               LIMIT 10""",
            (name, f"%{name}%", name),
        )

    async def graph_find_place(self, name: str) -> list[dict]:
        """Find a place by name (fuzzy match)."""
        return await self._fetchall(
            "SELECT * FROM graph_places WHERE LOWER(name) LIKE LOWER(?) LIMIT 10",
            (f"%{name}%",),
        )

    async def graph_get_ancestors(
        self, person_id: str, max_generations: int = 10
    ) -> list[dict]:
        """Get ancestors using recursive CTE."""
        return await self._fetchall("""
            WITH RECURSIVE ancestors AS (
                SELECT p.id, p.name, p.gender, p.birth_year, p.death_year,
                       0 as generation, 'self' as relationship
                FROM graph_people p WHERE p.id = ?

                UNION ALL

                SELECT p.id, p.name, p.gender, p.birth_year, p.death_year,
                       a.generation + 1,
                       e.relationship_type
                FROM ancestors a
                JOIN graph_family_edges e ON e.to_person_id = a.id
                JOIN graph_people p ON p.id = e.from_person_id
                WHERE e.relationship_type IN ('father_of', 'mother_of')
                  AND a.generation < ?
            )
            SELECT * FROM ancestors ORDER BY generation
        """, (person_id, max_generations))

    async def graph_get_descendants(
        self, person_id: str, max_generations: int = 10
    ) -> list[dict]:
        """Get descendants using recursive CTE."""
        return await self._fetchall("""
            WITH RECURSIVE descendants AS (
                SELECT p.id, p.name, p.gender, p.birth_year, p.death_year,
                       0 as generation, 'self' as relationship
                FROM graph_people p WHERE p.id = ?

                UNION ALL

                SELECT p.id, p.name, p.gender, p.birth_year, p.death_year,
                       d.generation + 1,
                       e.relationship_type
                FROM descendants d
                JOIN graph_family_edges e ON e.from_person_id = d.id
                JOIN graph_people p ON p.id = e.to_person_id
                WHERE e.relationship_type IN ('father_of', 'mother_of')
                  AND d.generation < ?
            )
            SELECT * FROM descendants ORDER BY generation
        """, (person_id, max_generations))

    async def graph_find_path(
        self, person1_id: str, person2_id: str, max_depth: int = 15
    ) -> list[dict]:
        """Find shortest relationship path between two people using Python-side BFS.

        Returns list of dicts with from_name, to_name, relationship_type for each step.
        """
        if person1_id == person2_id:
            return []

        # Build adjacency list from the (small) family edges table
        adjacency: dict[str, list[tuple[str, str]]] = {}  # person_id -> [(neighbor_id, rel_type)]
        async with self.conn.execute(
            "SELECT from_person_id, to_person_id, relationship_type FROM graph_family_edges"
        ) as cursor:
            for row in await cursor.fetchall():
                fid, tid, rel = row[0], row[1], row[2]
                adjacency.setdefault(fid, []).append((tid, rel))
                # Reverse edge for bidirectional traversal
                reverse_rel = rel
                if rel == "father_of" or rel == "mother_of":
                    reverse_rel = "child_of"
                elif rel == "child_of":
                    reverse_rel = "parent_of"
                adjacency.setdefault(tid, []).append((fid, reverse_rel))

        # BFS
        queue = deque([(person1_id, [person1_id])])
        visited = {person1_id}

        while queue:
            current, path = queue.popleft()
            if len(path) - 1 >= max_depth:
                continue

            for neighbor_id, rel_type in adjacency.get(current, []):
                if neighbor_id in visited:
                    continue
                new_path = path + [neighbor_id]
                if neighbor_id == person2_id:
                    # Reconstruct path with names and relationships
                    result = []
                    # Walk the path and find the relationship at each step
                    for i in range(len(new_path) - 1):
                        from_id = new_path[i]
                        to_id = new_path[i + 1]
                        # Find the relationship type for this edge
                        step_rel = "related_to"
                        for nid, rt in adjacency.get(from_id, []):
                            if nid == to_id:
                                step_rel = rt
                                break
                        result.append({
                            "current_id": from_id,
                            "next_id": to_id,
                            "relationship_type": step_rel,
                            "depth": i + 1,
                            "from_name": from_id,  # placeholder, resolved below
                            "to_name": to_id,       # placeholder, resolved below
                        })

                    # Resolve names
                    all_ids = list(set(new_path))
                    placeholders = ",".join("?" * len(all_ids))
                    name_map = {}
                    async with self.conn.execute(
                        f"SELECT id, name FROM graph_people WHERE id IN ({placeholders})",
                        all_ids
                    ) as cursor:
                        for row in await cursor.fetchall():
                            name_map[row[0]] = row[1]

                    for step in result:
                        step["from_name"] = name_map.get(step["current_id"], step["current_id"])
                        step["to_name"] = name_map.get(step["next_id"], step["next_id"])

                    return result

                visited.add(neighbor_id)
                queue.append((neighbor_id, new_path))

        return []  # No path found

    async def graph_get_family(self, person_id: str) -> dict:
        """Get immediate family of a person."""
        return {
            "parents": await self._fetchall(
                """SELECT p.*, e.relationship_type FROM graph_family_edges e
                   JOIN graph_people p ON p.id = e.from_person_id
                   WHERE e.to_person_id = ?
                     AND e.relationship_type IN ('father_of', 'mother_of')""",
                (person_id,),
            ),
            "children": await self._fetchall(
                """SELECT p.*, e.relationship_type FROM graph_family_edges e
                   JOIN graph_people p ON p.id = e.to_person_id
                   WHERE e.from_person_id = ?
                     AND e.relationship_type IN ('father_of', 'mother_of')""",
                (person_id,),
            ),
            "partners": await self._fetchall(
                """SELECT p.* FROM graph_family_edges e
                   JOIN graph_people p ON p.id = CASE
                       WHEN e.from_person_id = ? THEN e.to_person_id
                       ELSE e.from_person_id END
                   WHERE (e.from_person_id = ? OR e.to_person_id = ?)
                     AND e.relationship_type = 'partner_of'""",
                (person_id, person_id, person_id),
            ),
            "siblings": await self._fetchall(
                """SELECT p.* FROM graph_family_edges e
                   JOIN graph_people p ON p.id = CASE
                       WHEN e.from_person_id = ? THEN e.to_person_id
                       ELSE e.from_person_id END
                   WHERE (e.from_person_id = ? OR e.to_person_id = ?)
                     AND e.relationship_type = 'sibling_of'""",
                (person_id, person_id, person_id),
            ),
        }

    async def graph_get_person_events(self, person_id: str) -> list[dict]:
        """Get all events a person participated in."""
        return await self._fetchall(
            """SELECT e.* FROM graph_person_event_edges pe
               JOIN graph_events e ON e.id = pe.event_id
               WHERE pe.person_id = ?
               ORDER BY e.sort_key""",
            (person_id,),
        )

    async def graph_get_event_places(self, event_id: str) -> list[dict]:
        """Get all places where an event occurred."""
        return await self._fetchall(
            """SELECT p.* FROM graph_event_place_edges ep
               JOIN graph_places p ON p.id = ep.place_id
               WHERE ep.event_id = ?""",
            (event_id,),
        )

    async def graph_get_place_events(self, place_id: str) -> list[dict]:
        """Get all events at a place."""
        return await self._fetchall(
            """SELECT e.* FROM graph_event_place_edges ep
               JOIN graph_events e ON e.id = ep.event_id
               WHERE ep.place_id = ?
               ORDER BY e.sort_key""",
            (place_id,),
        )

    async def graph_get_place_people(self, place_id: str) -> dict:
        """Get people born/died at a place."""
        return {
            "born_here": await self._fetchall("SELECT * FROM graph_people WHERE birth_place_id = ?", (place_id,)),
            "died_here": await self._fetchall("SELECT * FROM graph_people WHERE death_place_id = ?", (place_id,)),
            "visited": [],
        }

    # Map from our DB abbreviations to Theographic abbreviations
    _THEOGRAPHIC_BOOK_MAP = {
        "1Ch": "1Chr", "1Co": "1Cor", "1Jn": "1John", "1Ki": "1Kgs",
        "1Pe": "1Pet", "1Sa": "1Sam", "1Th": "1Thess", "1Ti": "1Tim",
        "2Ch": "2Chr", "2Co": "2Cor", "2Jn": "2John", "2Ki": "2Kgs",
        "2Pe": "2Pet", "2Sa": "2Sam", "2Th": "2Thess", "2Ti": "2Tim",
        "3Jn": "3John", "Act": "Acts", "Amo": "Amos", "Deu": "Deut",
        "Ecc": "Eccl", "Est": "Esth", "Exo": "Exod", "Ezk": "Ezek",
        "Jdg": "Judg", "Jhn": "John", "Jol": "Joel", "Jon": "Jonah",
        "Jos": "Josh", "Jud": "Jude", "Luk": "Luke", "Mat": "Matt",
        "Mrk": "Mark", "Nam": "Nah", "Oba": "Obad", "Phm": "Phlm",
        "Php": "Phil", "Pro": "Prov", "Psa": "Ps", "Rut": "Ruth",
        "Sng": "Song", "Tit": "Titus", "Zec": "Zech", "Zep": "Zeph",
    }

    def _to_theographic_ref(self, ref: str) -> str:
        """Convert our DB verse reference format to Theographic format."""
        parts = ref.split(".")
        if parts:
            parts[0] = self._THEOGRAPHIC_BOOK_MAP.get(parts[0], parts[0])
        return ".".join(parts)

    async def graph_get_verse_entities(
        self, verse_ref: str
    ) -> dict:
        """Get all entities mentioned in a verse."""
        result = {"people": [], "places": [], "events": []}
        theo_ref = self._to_theographic_ref(verse_ref)

        async with self.conn.execute(
            """SELECT vm.entity_type, vm.entity_id,
                      COALESCE(p.name, pl.name, e.title) as entity_name
               FROM graph_verse_mentions vm
               LEFT JOIN graph_people p ON vm.entity_type = 'person' AND p.id = vm.entity_id
               LEFT JOIN graph_places pl ON vm.entity_type = 'place' AND pl.id = vm.entity_id
               LEFT JOIN graph_events e ON vm.entity_type = 'event' AND e.id = vm.entity_id
               WHERE vm.verse_ref = ?""",
            (theo_ref,)
        ) as cursor:
            for row in await cursor.fetchall():
                d = dict(row)
                if d["entity_type"] == "person":
                    result["people"].append(d)
                elif d["entity_type"] == "place":
                    result["places"].append(d)
                elif d["entity_type"] == "event":
                    result["events"].append(d)

        return result

    async def graph_get_chapter_entities(
        self, book: str, chapter: int
    ) -> dict:
        """Get all entities mentioned in a chapter."""
        result = {"people": [], "places": [], "events": []}
        theo_book = self._THEOGRAPHIC_BOOK_MAP.get(book, book)
        ref_pattern = f"{theo_book}.{chapter}.%"

        async with self.conn.execute(
            """SELECT DISTINCT vm.entity_type, vm.entity_id,
                      COALESCE(p.name, pl.name, e.title) as entity_name
               FROM graph_verse_mentions vm
               LEFT JOIN graph_people p ON vm.entity_type = 'person' AND p.id = vm.entity_id
               LEFT JOIN graph_places pl ON vm.entity_type = 'place' AND pl.id = vm.entity_id
               LEFT JOIN graph_events e ON vm.entity_type = 'event' AND e.id = vm.entity_id
               WHERE vm.verse_ref LIKE ?""",
            (ref_pattern,)
        ) as cursor:
            for row in await cursor.fetchall():
                d = dict(row)
                if d["entity_type"] == "person":
                    result["people"].append(d)
                elif d["entity_type"] == "place":
                    result["places"].append(d)
                elif d["entity_type"] == "event":
                    result["events"].append(d)

        return result

    async def graph_has_data(self) -> bool:
        """Check if graph tables have data."""
        return await self._table_has_rows("graph_people")

    # =========================================================================
    # Aquifer content queries
    # =========================================================================

    # Book abbreviation to 2-digit number for BBCCCVVV references
    _BOOK_ABBR_TO_NUM = {
        "Gen": "01", "Exo": "02", "Lev": "03", "Num": "04", "Deu": "05",
        "Jos": "06", "Jdg": "07", "Rut": "08", "1Sa": "09", "2Sa": "10",
        "1Ki": "11", "2Ki": "12", "1Ch": "13", "2Ch": "14", "Ezr": "15",
        "Neh": "16", "Est": "17", "Job": "18", "Psa": "19", "Pro": "20",
        "Ecc": "21", "Sng": "22", "Isa": "23", "Jer": "24", "Lam": "25",
        "Ezk": "26", "Dan": "27", "Hos": "28", "Jol": "29", "Amo": "30",
        "Oba": "31", "Jon": "32", "Mic": "33", "Nam": "34", "Hab": "35",
        "Zep": "36", "Hag": "37", "Zec": "38", "Mal": "39",
        "Mat": "40", "Mrk": "41", "Luk": "42", "Jhn": "43", "Act": "44",
        "Rom": "45", "1Co": "46", "2Co": "47", "Gal": "48", "Eph": "49",
        "Php": "50", "Col": "51", "1Th": "52", "2Th": "53", "1Ti": "54",
        "2Ti": "55", "Tit": "56", "Phm": "57", "Heb": "58", "Jas": "59",
        "1Pe": "60", "2Pe": "61", "1Jn": "62", "2Jn": "63", "3Jn": "64",
        "Jud": "65", "Rev": "66",
    }

    def _to_aquifer_ref(self, normalized_ref: str) -> str | None:
        """Convert normalized reference 'Gen.1.1' to Aquifer 8-digit format '01001001'."""
        parts = normalized_ref.split('.')
        if len(parts) != 3:
            return None
        book_num = self._BOOK_ABBR_TO_NUM.get(parts[0])
        if not book_num:
            return None
        try:
            chapter = int(parts[1])
            verse = int(parts[2])
            return f"{book_num}{chapter:03d}{verse:03d}"
        except (ValueError, IndexError):
            return None

    async def has_aquifer_data(self) -> bool:
        """Check if aquifer_content table exists and has data."""
        return await self._table_has_rows("aquifer_content")

    async def get_study_notes(self, reference: str) -> list[dict]:
        """Get study notes + translation notes for a verse reference.

        Fetches study_notes, translation_notes_uw, and translation_notes_sil
        for a specific verse. Matches both exact refs and ranges containing the verse.
        """
        normalized = self._normalize_reference(reference)
        aq_ref = self._to_aquifer_ref(normalized)
        if not aq_ref:
            return []

        return await self._fetchall("""
            SELECT * FROM aquifer_content
            WHERE resource_type IN ('study_notes', 'translation_notes_uw', 'translation_notes_sil')
              AND (
                start_ref = ?
                OR (start_ref <= ? AND end_ref >= ? AND is_range = 1)
              )
            ORDER BY resource_type, start_ref
        """, (aq_ref, aq_ref, aq_ref))

    async def get_chapter_study_notes(self, book: str, chapter: int) -> list[dict]:
        """Get all study notes for an entire chapter."""
        book_num = self._BOOK_ABBR_TO_NUM.get(book)
        if not book_num:
            return []

        return await self._fetchall("""
            SELECT * FROM aquifer_content
            WHERE resource_type IN ('study_notes', 'translation_notes_uw', 'translation_notes_sil')
              AND book = ?
              AND chapter_start = ?
            ORDER BY resource_type, start_ref
        """, (book, chapter))

    async def _search_aquifer_by_type(self, resource_type: str, query: str) -> list[dict]:
        """Search aquifer_content by type — exact title match then LIKE fallback."""
        exact = await self._fetchall(
            "SELECT * FROM aquifer_content WHERE resource_type = ? AND LOWER(title) = LOWER(?)",
            (resource_type, query),
        )
        if exact:
            return exact

        pattern = f"%{query}%"
        return await self._fetchall(
            """SELECT * FROM aquifer_content
               WHERE resource_type = ?
                 AND (LOWER(title) LIKE LOWER(?) OR LOWER(content_plain) LIKE LOWER(?))
               ORDER BY
                 CASE WHEN LOWER(title) LIKE LOWER(?) THEN 0 ELSE 1 END,
                 LENGTH(title)
               LIMIT 10""",
            (resource_type, pattern, pattern, pattern),
        )

    async def get_bible_dictionary(self, topic: str) -> list[dict]:
        """Search the Aquifer Bible dictionary by title or content."""
        return await self._search_aquifer_by_type("dictionary", topic)

    async def has_dictionaries(self) -> bool:
        return await self._table_has_rows("dictionaries")

    # =========================================================================
    # Confession proof-texts (verse <-> confession graph)
    # =========================================================================

    async def has_confession_proofs(self) -> bool:
        return await self._table_has_rows("confession_proof_texts")

    async def find_confessions_by_verse(
        self, book: str, chapter: int, verse: int,
    ) -> list[dict]:
        """Confession/catechism articles that cite a verse as a proof text."""
        return await self._fetchall(
            "SELECT doc_id, doc_title, section_label, section_text, marker, osis_ref "
            "FROM confession_proof_texts "
            "WHERE book = ? AND chapter = ? AND verse_start <= ? AND verse_end >= ? "
            "ORDER BY doc_title, section_label",
            (book, chapter, verse, verse),
        )

    async def get_confession_proofs(
        self, doc_id: str, section_label: str | None = None,
    ) -> list[dict]:
        """Proof texts for a confession document (optionally one article)."""
        sql = (
            "SELECT doc_id, doc_title, section_label, section_text, marker, osis_ref, "
            "book, chapter, verse_start, verse_end FROM confession_proof_texts WHERE doc_id = ?"
        )
        params: list = [doc_id]
        if section_label:
            sql += " AND section_label = ?"
            params.append(section_label)
        sql += " ORDER BY section_label, marker, id"
        return await self._fetchall(sql, params)

    async def confession_proof_docs(self) -> list[dict]:
        """Distinct documents that carry proof texts (id + title)."""
        return await self._fetchall(
            "SELECT doc_id, doc_title, COUNT(*) AS n FROM confession_proof_texts "
            "GROUP BY doc_id, doc_title ORDER BY doc_title"
        )

    # =========================================================================
    # Devotionals (verse-keyed daily readings)
    # =========================================================================

    async def has_devotionals(self) -> bool:
        return await self._table_has_rows("devotionals")

    async def get_devotionals_by_verse(
        self, book: str, chapter: int, verse: int, limit: int = 6,
    ) -> list[dict]:
        """Devotional readings anchored to a verse (or its chapter)."""
        return await self._fetchall(
            "SELECT source_name, title, key_ref, body FROM devotionals "
            "WHERE book = ? AND chapter = ? AND (verse = ? OR verse IS NULL) "
            "ORDER BY month, day LIMIT ?",
            (book, chapter, verse, limit),
        )

    async def get_devotionals_by_date(self, month: int, day: int) -> list[dict]:
        """Devotional readings for a calendar date (morning first)."""
        return await self._fetchall(
            "SELECT source_name, title, key_ref, body FROM devotionals "
            "WHERE month = ? AND day = ? "
            "ORDER BY CASE WHEN time_of_day = 'morning' THEN 0 ELSE 1 END",
            (month, day),
        )

    async def search_dictionaries(self, topic: str, limit: int = 6) -> list[dict]:
        """Search bundled PD dictionaries (Easton's, ISBE, ...) by headword."""
        pattern = f"%{topic}%"
        return await self._fetchall(
            "SELECT source, source_name, headword, body FROM dictionaries "
            "WHERE LOWER(headword) = LOWER(?) OR LOWER(headword) LIKE LOWER(?) "
            "ORDER BY CASE WHEN LOWER(headword) = LOWER(?) THEN 0 ELSE 1 END, "
            "LENGTH(headword) LIMIT ?",
            (topic, pattern, topic, limit),
        )

    async def get_key_terms(self, term: str) -> list[dict]:
        """Search FIA Key Terms by title or content."""
        return await self._search_aquifer_by_type("key_terms", term)

    async def search_aquifer_content(
        self,
        query: str,
        resource_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Generic full-text search across any Aquifer resource type."""
        pattern = f"%{query}%"
        params: list = [pattern, pattern]

        sql = """
            SELECT * FROM aquifer_content
            WHERE (LOWER(title) LIKE LOWER(?) OR LOWER(content_plain) LIKE LOWER(?))
        """

        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)

        sql += " ORDER BY CASE WHEN LOWER(title) LIKE LOWER(?) THEN 0 ELSE 1 END, LENGTH(title) LIMIT ?"
        params.extend([pattern, limit])

        return await self._fetchall(sql, params)

    # =========================================================================
    # ACAI entity queries
    # =========================================================================

    async def has_acai_data(self) -> bool:
        """Check if acai_entities table exists and has data."""
        return await self._table_has_rows("acai_entities")

    async def get_acai_entity(self, name: str) -> dict | None:
        """Get an ACAI entity by name (case-insensitive, fuzzy)."""
        exact = await self._fetchone(
            "SELECT * FROM acai_entities WHERE LOWER(name) = LOWER(?)", (name,)
        )
        if exact:
            return exact

        return await self._fetchone(
            "SELECT * FROM acai_entities WHERE LOWER(name) LIKE LOWER(?) ORDER BY reference_count DESC LIMIT 1",
            (f"%{name}%",),
        )



def create_schema(conn: sqlite3.Connection):
    """Create the database schema."""
    conn.executescript("""
        -- Lexicon table for Greek and Hebrew words
        CREATE TABLE IF NOT EXISTS lexicon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strongs TEXT UNIQUE NOT NULL,
            language TEXT NOT NULL,
            word TEXT,
            transliteration TEXT,
            pronunciation TEXT,
            short_definition TEXT,
            full_definition TEXT,
            etymology TEXT,
            usage_count INTEGER DEFAULT 0,
            semantic_domain TEXT,
            related_words TEXT,
            abbott_smith_def TEXT,
            nt_occurrences INTEGER,
            lxx_hebrew TEXT,
            synonyms TEXT,
            sense_hierarchy TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_lexicon_strongs ON lexicon(strongs);
        CREATE INDEX IF NOT EXISTS idx_lexicon_language ON lexicon(language);

        -- Verses table for tagged Bible text
        CREATE TABLE IF NOT EXISTS verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,   -- canonical (English) versification, e.g. 'Mal.4.1'
            ref_alt TEXT,                     -- alternate versification, e.g. 'Mal.3.19' (Hebrew), or NULL
            book TEXT,
            chapter INTEGER,
            verse INTEGER,
            text_english TEXT,
            text_original TEXT,
            word_data TEXT,
            section_end TEXT  -- 'paragraph' (NT), 'petuchah' (OT major), 'setumah' (OT minor), or NULL
        );
        CREATE INDEX IF NOT EXISTS idx_verses_reference ON verses(reference);
        CREATE INDEX IF NOT EXISTS idx_verses_ref_alt ON verses(ref_alt);
        CREATE INDEX IF NOT EXISTS idx_verses_book ON verses(book);

        -- Passages table (verses grouped by section markers)
        CREATE TABLE IF NOT EXISTS passages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_start TEXT NOT NULL,    -- e.g., "Mat.1.1"
            reference_end TEXT NOT NULL,      -- e.g., "Mat.1.17"
            book TEXT NOT NULL,
            start_verse_id INTEGER NOT NULL,
            end_verse_id INTEGER NOT NULL,
            text_combined TEXT NOT NULL,      -- Full passage text for embedding
            verse_count INTEGER NOT NULL,
            section_type TEXT,                -- 'paragraph', 'petuchah', 'setumah'
            FOREIGN KEY (start_verse_id) REFERENCES verses(id),
            FOREIGN KEY (end_verse_id) REFERENCES verses(id)
        );
        CREATE INDEX IF NOT EXISTS idx_passages_book ON passages(book);
        CREATE INDEX IF NOT EXISTS idx_passages_refs ON passages(reference_start, reference_end);

        -- Biblical names table
        CREATE TABLE IF NOT EXISTS names (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_original TEXT,
            type TEXT,
            description TEXT,
            refs TEXT,
            relationships TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_names_name ON names(name);
        CREATE INDEX IF NOT EXISTS idx_names_type ON names(type);

        -- Cross references
        -- type: 'ch' (Harrison/Romhild curated), 'tsk' (Treasury of Scripture
        -- Knowledge via openbible.info), or NULL for legacy/manual entries.
        -- relevance: per-source ranking signal — CH uses 0..3 (Orig*2+Circ),
        -- TSK uses raw vote counts. Higher = stronger.
        CREATE TABLE IF NOT EXISTS cross_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            type TEXT,
            note TEXT,
            relevance INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_xref_source ON cross_references(source);
        CREATE INDEX IF NOT EXISTS idx_xref_source_rank
            ON cross_references(source, type, relevance DESC);

        -- Thematic references
        CREATE TABLE IF NOT EXISTS thematic_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme TEXT NOT NULL,
            reference TEXT NOT NULL,
            note TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_theme_name ON thematic_references(theme);

        -- Morphology codes
        CREATE TABLE IF NOT EXISTS morphology (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            parsing TEXT,
            part_of_speech TEXT,
            person TEXT,
            number TEXT,
            tense TEXT,
            voice TEXT,
            mood TEXT,
            case_value TEXT,
            gender TEXT,
            UNIQUE(code, language)
        );
        CREATE INDEX IF NOT EXISTS idx_morph_code ON morphology(code);

        -- =====================================================================
        -- Graph tables (Theographic Bible Metadata)
        -- =====================================================================

        -- People nodes
        CREATE TABLE IF NOT EXISTS graph_people (
            id TEXT PRIMARY KEY,          -- e.g., "aaron_1"
            name TEXT NOT NULL,
            also_called TEXT,
            gender TEXT,
            birth_year INTEGER,
            death_year INTEGER,
            birth_place_id TEXT,
            death_place_id TEXT,
            description TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_graph_people_name ON graph_people(name);

        -- Place nodes
        CREATE TABLE IF NOT EXISTS graph_places (
            id TEXT PRIMARY KEY,          -- e.g., "eden_354"
            name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            feature_type TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_graph_places_name ON graph_places(name);

        -- Event nodes
        CREATE TABLE IF NOT EXISTS graph_events (
            id TEXT PRIMARY KEY,          -- event_id as text
            title TEXT NOT NULL,
            start_year INTEGER,
            duration TEXT,
            sort_key REAL
        );
        CREATE INDEX IF NOT EXISTS idx_graph_events_title ON graph_events(title);

        -- People group nodes
        CREATE TABLE IF NOT EXISTS graph_people_groups (
            name TEXT PRIMARY KEY,
            members TEXT                  -- JSON array of person IDs
        );

        -- Family relationship edges
        CREATE TABLE IF NOT EXISTS graph_family_edges (
            from_person_id TEXT NOT NULL,
            to_person_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,  -- father_of, mother_of, partner_of, sibling_of
            PRIMARY KEY (from_person_id, to_person_id, relationship_type)
        );
        CREATE INDEX IF NOT EXISTS idx_graph_family_from ON graph_family_edges(from_person_id);
        CREATE INDEX IF NOT EXISTS idx_graph_family_to ON graph_family_edges(to_person_id);

        -- Person-event participation edges
        CREATE TABLE IF NOT EXISTS graph_person_event_edges (
            person_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            PRIMARY KEY (person_id, event_id)
        );
        CREATE INDEX IF NOT EXISTS idx_graph_pe_person ON graph_person_event_edges(person_id);
        CREATE INDEX IF NOT EXISTS idx_graph_pe_event ON graph_person_event_edges(event_id);

        -- Event-place edges
        CREATE TABLE IF NOT EXISTS graph_event_place_edges (
            event_id TEXT NOT NULL,
            place_id TEXT NOT NULL,
            PRIMARY KEY (event_id, place_id)
        );
        CREATE INDEX IF NOT EXISTS idx_graph_ep_event ON graph_event_place_edges(event_id);
        CREATE INDEX IF NOT EXISTS idx_graph_ep_place ON graph_event_place_edges(place_id);

        -- Verse-entity mention links
        CREATE TABLE IF NOT EXISTS graph_verse_mentions (
            verse_ref TEXT NOT NULL,       -- e.g., "Gen.1.1" (matches verses.reference)
            entity_type TEXT NOT NULL,     -- person, place, event
            entity_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_graph_vm_ref ON graph_verse_mentions(verse_ref);
        CREATE INDEX IF NOT EXISTS idx_graph_vm_entity ON graph_verse_mentions(entity_type, entity_id);

        -- Person-group membership edges
        CREATE TABLE IF NOT EXISTS graph_person_group_edges (
            person_id TEXT NOT NULL,
            group_name TEXT NOT NULL,
            PRIMARY KEY (person_id, group_name)
        );
        CREATE INDEX IF NOT EXISTS idx_graph_pg_person ON graph_person_group_edges(person_id);
        CREATE INDEX IF NOT EXISTS idx_graph_pg_group ON graph_person_group_edges(group_name);

        -- =====================================================================
        -- Aquifer content (study notes, dictionary, translation notes, key terms)
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS aquifer_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            resource_type TEXT NOT NULL,
            title TEXT NOT NULL,
            book TEXT,
            book_num INTEGER,
            start_ref TEXT,
            end_ref TEXT,
            chapter_start INTEGER,
            verse_start INTEGER,
            chapter_end INTEGER,
            verse_end INTEGER,
            content TEXT NOT NULL,
            content_plain TEXT NOT NULL,
            is_range INTEGER DEFAULT 0,
            UNIQUE(content_id, resource_type)
        );
        CREATE INDEX IF NOT EXISTS idx_aq_type ON aquifer_content(resource_type);
        CREATE INDEX IF NOT EXISTS idx_aq_ref ON aquifer_content(resource_type, start_ref);
        CREATE INDEX IF NOT EXISTS idx_aq_book ON aquifer_content(resource_type, book, chapter_start);
        CREATE INDEX IF NOT EXISTS idx_aq_title ON aquifer_content(resource_type, title);

        -- =====================================================================
        -- ACAI entity annotations
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS acai_entities (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT,
            description TEXT,
            roles TEXT,
            father_id TEXT,
            mother_id TEXT,
            partners TEXT,
            offspring TEXT,
            siblings TEXT,
            referred_to_as TEXT,
            key_references TEXT,
            reference_count INTEGER,
            speeches_count INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_acai_type ON acai_entities(entity_type);
        CREATE INDEX IF NOT EXISTS idx_acai_name ON acai_entities(name);

        -- =====================================================================
        -- Greek Septuagint (Swete) text, keyed by LXX versification
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS lxx_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,   -- 'Book.Chapter.Verse' in LXX numbering
            book TEXT,
            chapter INTEGER,
            verse INTEGER,
            text_greek TEXT,                  -- Swete Greek (Public Domain)
            text_english TEXT                 -- Brenton English translation of the LXX (Public Domain)
        );
        CREATE INDEX IF NOT EXISTS idx_lxx_reference ON lxx_verses(reference);
        CREATE INDEX IF NOT EXISTS idx_lxx_book ON lxx_verses(book);

        -- =====================================================================
        -- Versification map: LXX numbering <-> standard (English) / base (Hebrew)
        -- Only divergent verses are stored; everything else is identity.
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS versification_map (
            lxx_ref TEXT PRIMARY KEY,   -- LXX-scheme reference
            standard_ref TEXT,          -- English-scheme reference (matches verses.reference)
            base_ref TEXT               -- common base (Hebrew/original) reference
        );
        CREATE INDEX IF NOT EXISTS idx_versemap_std ON versification_map(standard_ref);

        -- =====================================================================
        -- Readable modern translations (public-domain / open),
        -- English versification (aligns with verses.reference).
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation TEXT NOT NULL,        -- abbreviation, e.g. 'BSB', 'WEB', 'KJV'
            reference TEXT NOT NULL,          -- 'Book.Chapter.Verse'
            book TEXT,
            chapter INTEGER,
            verse INTEGER,
            text TEXT,
            UNIQUE(translation, reference)
        );
        CREATE INDEX IF NOT EXISTS idx_tr_ref ON translations(translation, reference);
        CREATE INDEX IF NOT EXISTS idx_tr_bcv ON translations(translation, book, chapter, verse);

        -- =====================================================================
        -- Public-domain commentaries (verse- or section-level).
        -- Each row covers a verse range [verse_start, verse_end] of a chapter.
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS commentaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,        -- commentary id, e.g. 'john-gill'
            source_name TEXT,            -- display name
            book TEXT,
            chapter INTEGER,
            verse_start INTEGER,         -- 0 = chapter introduction
            verse_end INTEGER,
            text TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_comm_lookup
            ON commentaries(book, chapter, verse_start, verse_end);
        CREATE INDEX IF NOT EXISTS idx_comm_source ON commentaries(source);

        -- =====================================================================
        -- Patristic catena: church-father comment excerpts keyed to verses
        -- (public-domain fathers only; HistoricalChristianFaith database).
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS patristic_catena (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            father_name TEXT,
            father_category TEXT,
            year INTEGER,               -- the father's approximate year (AD)
            book TEXT,
            chapter INTEGER,
            verse_start INTEGER,
            verse_end INTEGER,
            quote TEXT,
            source_title TEXT,
            source_url TEXT,
            source TEXT                 -- provenance: 'historical-christian-faith' | 'sermonindex'
        );
        CREATE INDEX IF NOT EXISTS idx_catena_lookup
            ON patristic_catena(book, chapter, verse_start, verse_end);

        -- =====================================================================
        -- Historical documents: creeds, confessions, catechisms (public domain).
        -- One row per section (a creed article, confession chapter, or catechism Q&A).
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS historical_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,        -- 'nicene-creed'
            doc_title TEXT,              -- 'The Nicene Creed'
            doc_type TEXT,               -- 'creed' | 'confession' | 'catechism'
            doc_date TEXT,
            tradition TEXT,              -- Ecumenical | Reformed | Lutheran | Anglican | Catholic | Orthodox
            section_num INTEGER,
            section_label TEXT,          -- section title or catechism question number
            content TEXT,
            topics TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_histdoc_doc ON historical_documents(doc_id);
        CREATE INDEX IF NOT EXISTS idx_histdoc_title ON historical_documents(doc_title);

        -- =====================================================================
        -- UBS parallel-passage groups (CC BY-SA 4.0). Each group_id ties together
        -- verses that are editorially parallel (Synoptic harmonies, OT-in-NT, ...).
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS parallel_passages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            book TEXT,
            chapter INTEGER,
            verse_start INTEGER,
            verse_end INTEGER,
            ref_display TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_parallel_lookup
            ON parallel_passages(book, chapter, verse_start, verse_end);
        CREATE INDEX IF NOT EXISTS idx_parallel_group ON parallel_passages(group_id);

        -- =====================================================================
        -- Word frequency: corpus occurrence count per Strong's number,
        -- materialized from verses.word_data (owned STEPBible tags). Powers
        -- reader-mode vocabulary (rarest words in a passage).
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS word_frequency (
            strongs TEXT PRIMARY KEY,   -- normalized Strong's, e.g. 'G3779'
            language TEXT,              -- 'greek' | 'hebrew'
            count INTEGER               -- occurrences across the tagged corpus
        );

        -- =====================================================================
        -- Public-domain Bible dictionaries / encyclopedias (headword-keyed).
        -- One row per article; multiple sources coexist (Easton's, ISBE, ...).
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS dictionaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,        -- 'eastons', 'isbe', ...
            source_name TEXT,            -- "Easton's Bible Dictionary"
            headword TEXT NOT NULL,
            body TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_dict_headword ON dictionaries(headword);
        CREATE INDEX IF NOT EXISTS idx_dict_source ON dictionaries(source);

        -- =====================================================================
        -- Confession proof-texts: the Scripture references a confession /
        -- catechism article cites, resolved to verse spans. Powers the
        -- verse<->confession graph (find_confessions_by_verse, get_confession_proofs).
        -- One row per (article, marker, cited reference).
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS confession_proof_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,        -- 'wcf', 'wsc', 'heidelberg-catechism'
            doc_title TEXT,              -- 'Westminster Confession of Faith'
            section_label TEXT,          -- 'Q1' (catechism) | '1.2' (chapter.article)
            section_text TEXT,           -- the article text or question + answer
            marker TEXT,                 -- footnote marker: 'a', 'b', ...
            osis_ref TEXT,               -- original OSIS citation
            book TEXT,
            chapter INTEGER,
            verse_start INTEGER,
            verse_end INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_cpt_verse
            ON confession_proof_texts(book, chapter, verse_start, verse_end);
        CREATE INDEX IF NOT EXISTS idx_cpt_doc
            ON confession_proof_texts(doc_id, section_label);

        -- =====================================================================
        -- Devotionals: verse-keyed daily readings (public domain). Each entry
        -- is anchored to a key verse and a calendar date. Clearly devotional,
        -- kept distinct from the exegesis tools.
        -- =====================================================================

        CREATE TABLE IF NOT EXISTS devotionals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,        -- 'morning-evening'
            source_name TEXT,            -- "Spurgeon's Morning and Evening"
            title TEXT,                  -- 'January 1 (Morning)'
            month INTEGER,
            day INTEGER,
            time_of_day TEXT,            -- 'morning' | 'evening' | NULL
            key_ref TEXT,                -- display reference, e.g. 'Joshua 5:12'
            book TEXT,                   -- resolved key verse (nullable)
            chapter INTEGER,
            verse INTEGER,
            body TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_devo_verse ON devotionals(book, chapter, verse);
        CREATE INDEX IF NOT EXISTS idx_devo_date ON devotionals(month, day);

    """)
    conn.commit()

    # Add Abbott-Smith columns to existing databases (idempotent)
    for col in [
        "abbott_smith_def TEXT",
        "nt_occurrences INTEGER",
        "lxx_hebrew TEXT",
        "synonyms TEXT",
        "sense_hierarchy TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE lexicon ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()

    # Add the Brenton English column to LXX databases built before it existed.
    try:
        conn.execute("ALTER TABLE lxx_verses ADD COLUMN text_english TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists (or table not yet created)
    conn.commit()


