"""Read-only access to db/social_sciences.db (built by scripts/socialsci/build_social_sciences_db.py)."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import aiosqlite

logger = logging.getLogger("socialsci-mcp")

SOURCES = {
    "documents": ("avalon", "nara", "ilga", "govinfo", "wikisource", "cap"),
    "speeches": ("miller-center",),
    "narratives": ("docsouth",),
    "books": ("reading-room",),
}
STOPWORDS = set("""a an the and or but of to in on at by for with from as is are was were be been being do does did
done why what when where who whom whose which how that this these those it its into about than then there their
they them he she his her we our you your i me my not no so if can could would should will shall may might""".split())
SOURCES["primary"] = SOURCES["documents"] + SOURCES["speeches"] + SOURCES["narratives"]
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_or_int(s: str | int | None) -> str | None:
    """'XIV' / '14' / 14 -> '14'."""
    if s is None or str(s).strip() == "":
        return None
    s = str(s).strip().upper().removeprefix("ARTICLE").removeprefix("AMENDMENT").removeprefix("SECTION").strip(" .")
    if s.isdigit():
        return str(int(s))
    if re.fullmatch(r"[IVXLC]+", s):
        total = 0
        for i, ch in enumerate(s):
            v = ROMAN[ch]
            total += -v if i + 1 < len(s) and ROMAN[s[i + 1]] > v else v
        return str(total)
    return s.lower()


def get_db_path() -> Path:
    env = os.environ.get("SOCIAL_SCIENCES_DB")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "db" / "social_sciences.db"


class SocialSciencesDB:
    _model = None

    def __init__(self, path: Path):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self.has_vec = False

    async def connect(self) -> None:
        uri = f"file:{self.path.resolve().as_posix()}?mode=ro&immutable=1"
        self.conn = await aiosqlite.connect(uri, uri=True)
        self.conn.row_factory = aiosqlite.Row
        try:
            import sqlite_vec
            await self.conn.enable_load_extension(True)
            await self.conn.load_extension(sqlite_vec.loadable_path())
            await self.conn.enable_load_extension(False)
            async with self.conn.execute("select value from meta where key='vec_model'") as cur:
                self.has_vec = bool(await cur.fetchone())
        except Exception:  # noqa: BLE001
            logger.info("semantic layer off (sqlite-vec or vectors absent)")

    async def all(self, sql: str, params=()) -> list[dict]:
        async with self.conn.execute(sql, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def one(self, sql: str, params=()) -> dict | None:
        async with self.conn.execute(sql, params) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None

    # ---- search ----------------------------------------------------------
    @staticmethod
    def _fts(query: str) -> str | None:
        """Content words ANDed (question words and other stopwords dropped, so 'why did the southern
        states secede' searches southern + states + secede)."""
        toks = [t for t in re.findall(r"[A-Za-z0-9']+", query or "") if t.lower() not in STOPWORDS]
        return " ".join(f'"{t}"' for t in toks) or None

    @staticmethod
    def _filters(source: str | None, year_from, year_to) -> tuple[str, list]:
        sql, params = "", []
        srcs = SOURCES.get((source or "").lower())
        if srcs:
            sql += f" and d.source in ({','.join('?' * len(srcs))})"
            params += list(srcs)
        if year_from:
            sql += " and d.year >= ?"
            params.append(int(year_from))
        if year_to:
            sql += " and d.year <= ?"
            params.append(int(year_to))
        return sql, params

    async def keyword(self, query: str, source=None, year_from=None, year_to=None, limit=8) -> list[dict]:
        expr = self._fts(query)
        if not expr:
            return []
        fsql, fparams = self._filters(source, year_from, year_to)
        sql = ("select p.id, p.doc_id, p.text, d.title, d.author, d.year, d.date, d.source, d.collection, d.url, d.citation, "
               "bm25(passages_fts, 4.0, 1.0) as score from passages_fts join passages p on p.id = passages_fts.rowid "
               "join documents d on d.id = p.doc_id where passages_fts match ?" + fsql +
               " order by score limit ?")
        return await self.all(sql, [expr, *fparams, limit])

    async def phrase(self, query: str, source=None, year_from=None, year_to=None, limit=8) -> list[dict]:
        """Passages containing the query's words as one exact phrase: finds a quotation's source."""
        toks = re.findall(r"[A-Za-z0-9']+", query or "")
        if len(toks) < 3:
            return []
        fsql, fparams = self._filters(source, year_from, year_to)
        sql = ("select p.id, p.doc_id, p.text, d.title, d.author, d.year, d.date, d.source, d.collection, d.url, d.citation, "
               "bm25(passages_fts, 4.0, 1.0) as score from passages_fts join passages p on p.id = passages_fts.rowid "
               "join documents d on d.id = p.doc_id where passages_fts match ?" + fsql +
               # the official text first (National Archives), then other primary sources, then books
               " order by (d.source = 'reading-room'), (d.source <> 'nara'), coalesce(d.year, 9999), score limit ?")
        return await self.all(sql, ['"' + " ".join(toks) + '"', *fparams, limit])

    @classmethod
    def model(cls):
        if cls._model is None:
            from model2vec import StaticModel
            cls._model = StaticModel.from_pretrained("minishlab/potion-retrieval-32M")
        return cls._model

    async def semantic(self, query: str, source=None, year_from=None, year_to=None, limit=8) -> list[dict]:
        if not self.has_vec or not (query or "").strip():
            return []
        import numpy as np
        v = self.model().encode([query])[0].astype(np.float32)
        v /= float(np.linalg.norm(v)) or 1.0
        q8 = np.clip(np.round(v * 127.0), -127, 127).astype(np.int8).tobytes()
        fsql, fparams = self._filters(source, year_from, year_to)
        k = min(400, limit * 40) if fsql else limit  # over-fetch: the filter applies after the KNN
        sql = ("select p.id, p.doc_id, p.text, d.title, d.author, d.year, d.date, d.source, d.collection, d.url, d.citation, "
               "v.distance as score from passages_vec v join passages p on p.id = v.id join documents d on d.id = p.doc_id "
               "where v.emb match vec_int8(?) and v.k = ?" + fsql + " order by v.distance limit ?")
        return await self.all(sql, [q8, k, *fparams, limit])

    async def hybrid(self, query: str, source=None, year_from=None, year_to=None, limit=8) -> list[dict]:
        """Search everything, primary sources first: the history books hold most of the passages, so
        an unfiltered search would let them crowd out the documents, speeches and narratives."""
        if (source or "all").lower() in SOURCES:
            return await self._hybrid(query, source, year_from, year_to, limit)
        primary = await self._hybrid(query, "primary", year_from, year_to, limit)
        books = await self._hybrid(query, "books", year_from, year_to, limit)
        out, i = [], 0
        while len(out) < limit and (i < len(primary) or i < len(books)):
            out += primary[i:i + 1] + books[i:i + 1]
            i += 1
        return out[:limit]

    async def _hybrid(self, query: str, source=None, year_from=None, year_to=None, limit=8) -> list[dict]:
        """Reciprocal-rank fusion of keyword (BM25) and meaning (vector) results."""
        kw = await self.keyword(query, source, year_from, year_to, limit * 2)
        sem = await self.semantic(query, source, year_from, year_to, limit * 2)
        fused: dict[int, dict] = {}
        for r, row in enumerate(await self.phrase(query, source, year_from, year_to, limit)):
            fused[row["id"]] = {**row, "rrf": 1.0 / (1 + r)}  # an exact quotation outranks everything
        for rank_list in (kw, sem):
            for r, row in enumerate(rank_list):
                e = fused.setdefault(row["id"], {**row, "rrf": 0.0})
                e["rrf"] += 1.0 / (60 + r)
        out = sorted(fused.values(), key=lambda x: -x["rrf"])
        seen_docs: dict[int, int] = {}
        picked = []
        for row in out:  # at most two passages per document, so one long book can't crowd out the rest
            if seen_docs.get(row["doc_id"], 0) >= 2:
                continue
            seen_docs[row["doc_id"]] = seen_docs.get(row["doc_id"], 0) + 1
            picked.append(row)
            if len(picked) >= limit:
                break
        return picked

    # ---- documents -------------------------------------------------------
    async def find_documents(self, title: str | None = None, source=None, author: str | None = None,
                             year_from=None, year_to=None, limit=20) -> list[dict]:
        fsql, fparams = self._filters(source, year_from, year_to)
        sql = "select d.id, d.title, d.author, d.year, d.date, d.source, d.collection, d.url, d.words from documents d where 1=1" + fsql
        params = list(fparams)
        for word in re.findall(r"[A-Za-z0-9']+", title or ""):
            sql += " and d.title like ?"
            params.append(f"%{word}%")
        if author:
            sql += " and d.author like ?"
            params.append(f"%{author}%")
        sql += " order by (d.source = 'reading-room'), (d.source <> 'nara'), length(d.title) limit ?"
        params.append(limit)
        return await self.all(sql, params)

    async def document(self, doc_id: int) -> dict | None:
        return await self.one("select * from documents where id=?", (doc_id,))

    async def document_passages(self, doc_id: int, start: int = 0, count: int = 6) -> list[dict]:
        return await self.all("select seq, text from passages where doc_id=? and seq>=? order by seq limit ?",
                              (doc_id, start, count))

    # ---- Constitution Test texts ------------------------------------------
    async def sections(self, code: str, part: str | None = None, number=None, sub=None) -> list[dict]:
        sql, params = "select part, number, sub, heading, text from sections where code=?", [code]
        if part:
            sql += " and part=?"
            params.append(part)
        if number is not None:
            sql += " and number=?"
            params.append(roman_or_int(number))
        if sub is not None:
            sql += " and sub=?"
            params.append(roman_or_int(sub))
        return await self.all(sql + " order by sort", params)

    async def stats(self) -> dict:
        rows = await self.all("select source, count(*) n from documents group by source")
        return {r["source"]: r["n"] for r in rows}
