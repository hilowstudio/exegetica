"""Read-only access to db/social_sciences.db (built by scripts/socialsci/build_social_sciences_db.py)."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import aiosqlite

logger = logging.getLogger("socialsci-mcp")

SOURCES = {
    "documents": ("avalon", "nara", "ilga", "govinfo", "wikisource", "cap", "gutenberg"),
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

    # ---- Phase 2: law (cases, statutes, Constitution Annotated, Congress, glossary) ----
    async def has_table(self, name: str) -> bool:
        return bool(await self.one("select 1 from sqlite_master where name=?", (name,)))

    async def _vec(self, table: str, query: str, k: int) -> list[tuple[int, float]]:
        if not self.has_vec or not await self.has_table(table):
            return []
        import numpy as np
        v = self.model().encode([query])[0].astype(np.float32)
        v /= float(np.linalg.norm(v)) or 1.0
        q8 = np.clip(np.round(v * 127.0), -127, 127).astype(np.int8).tobytes()
        rows = await self.all(f"select id, distance from {table} where emb match vec_int8(?) and k = ? order by distance", (q8, k))
        return [(r["id"], r["distance"]) for r in rows]

    CASE_COLS = ("c.id, c.name, c.short_name, c.cite, c.date, c.year, c.issue_area, c.vote, c.maj_writer, c.majority, "
                 "c.dissent, c.struck_down, c.overruled_precedent, c.importance, c.words")

    async def search_cases(self, query: str, issue_area=None, year_from=None, year_to=None, limit=8) -> list[dict]:
        """Keyword (opinion text) + meaning (case summaries), fused, then nudged toward landmark cases
        by the Caselaw Access Project's citation-importance percentile."""
        if not await self.has_table("cases"):
            return []
        filt, fp = "", []
        if issue_area:
            filt += " and c.issue_area like ?"
            fp.append(f"%{issue_area}%")
        if year_from:
            filt += " and c.year >= ?"
            fp.append(int(year_from))
        if year_to:
            filt += " and c.year <= ?"
            fp.append(int(year_to))
        scores: dict[int, float] = {}
        names = [t for t in re.findall(r"[A-Za-z0-9']+", query or "") if t.lower() not in STOPWORDS]
        if names:  # a case named in the query ("Brown v. Board") is found by its name first
            name_rows = await self.all(f"select {self.CASE_COLS} from cases c where " +
                                       " and ".join("(c.short_name like ? or c.name like ?)" for _ in names) + filt +
                                       " order by c.importance desc limit 5",
                                       [x for n in names for x in (f"%{n}%", f"%{n}%")] + fp)
            for r, row in enumerate(name_rows):
                scores[row["id"]] = scores.get(row["id"], 0) + 1.0 / (1 + r)
        expr = self._fts(query)
        if expr:
            # rank passages first (bm25 cannot run inside an aggregate), then take each case's best passage
            kw = await self.all("select x.case_id as id, min(x.s) as s from ("
                                "select p.case_id, bm25(case_passages_fts) as s from case_passages_fts "
                                "join case_passages p on p.id = case_passages_fts.rowid "
                                "where case_passages_fts match ? order by s limit 400) x "
                                "join cases c on c.id = x.case_id where 1=1" + filt + " group by x.case_id order by s limit ?",
                                [expr, *fp, limit * 4])
            for r, row in enumerate(kw):
                scores[row["id"]] = scores.get(row["id"], 0) + 1.0 / (60 + r)
        for r, (cid, _d) in enumerate(await self._vec("case_vec", query, limit * 6)):
            scores[cid] = scores.get(cid, 0) + 1.0 / (60 + r)
        if not scores:
            return []
        ids = list(scores)
        rows = await self.all(f"select {self.CASE_COLS} from cases c where c.id in ({','.join('?' * len(ids))})" + filt, [*ids, *fp])
        for row in rows:  # landmark cases rise; importance is a percentile (0-1)
            row["rank"] = scores[row["id"]] * (0.6 + 0.8 * (row["importance"] or 0))
        return sorted(rows, key=lambda r: -r["rank"])[:limit]

    async def find_case(self, ref: str) -> dict | None:
        """A case by id, U.S. Reports citation ('347 U.S. 483'), or name ('Marbury v. Madison')."""
        if not await self.has_table("cases"):
            return None
        ref = (ref or "").strip()
        if ref.isdigit():
            return await self.one(f"select {self.CASE_COLS}, c.head, c.scdb_id, c.chief, c.term from cases c where c.id=?", (int(ref),))
        m = re.match(r"(\d+)\s*U\.?\s*S\.?\s*(\d+)", ref)
        if m:
            row = await self.one(f"select {self.CASE_COLS}, c.head, c.scdb_id, c.chief, c.term from cases c where c.cite = ?",
                                 (f"{m.group(1)} U.S. {m.group(2)}",))
            if row:
                return row
        words = [t for t in re.findall(r"[A-Za-z0-9']+", ref) if t.lower() not in STOPWORDS and t.lower() != "v"]
        if not words:
            return None
        return await self.one(f"select {self.CASE_COLS}, c.head, c.scdb_id, c.chief, c.term from cases c where " +
                              " and ".join("(c.short_name like ? or c.name like ?)" for _ in words) +
                              " order by c.importance desc limit 1", [x for w in words for x in (f"%{w}%", f"%{w}%")])

    async def case_opinions(self, case_id: int) -> list[dict]:
        return await self.all("select seq, type, author, text from case_opinions where case_id=? order by seq", (case_id,))

    async def statute(self, citation: str) -> list[dict]:
        """Exact section by citation: '4 U.S.C. § 8', '18 USC 1001', '720 ILCS 5/12-3'."""
        if not await self.has_table("statutes"):
            return []
        c = (citation or "").strip()
        m = re.match(r"(\d+[A-Za-z]?)\s*U\.?\s*S\.?\s*C\.?\s*(?:§+|sec(?:tion)?\.?)?\s*([\w.-]+)", c, re.I)
        if m:
            return await self.all("select code, citation, heading, text from statutes where code='usc' and title=? and section=?",
                                  (m.group(1).lstrip("0"), m.group(2)))
        m = re.match(r"(\d+)\s*ILCS\s*([\d.]+)\s*/\s*([\w.-]+)", c, re.I)
        if m:
            return await self.all("select code, citation, heading, text from statutes where code='ilcs' and title=? and section=?",
                                  (m.group(1), f"{m.group(2)}/{m.group(3)}"))
        return []

    async def search_statutes(self, query: str, code=None, limit=8) -> list[dict]:
        if not await self.has_table("statutes"):
            return []
        expr = self._fts(query)
        if not expr:
            return []
        sql = ("select s.code, s.citation, s.heading, substr(s.text, 1, 1200) as text from statutes_fts "
               "join statutes s on s.id = statutes_fts.rowid where statutes_fts match ?")
        extra, ep = "", []
        if code in ("usc", "ilcs"):
            extra = " and s.code = ?"
            ep = [code]
        # section headings name what a section is about, so heading matches come first; then the full text
        head = await self.all(sql + extra + " order by bm25(statutes_fts, 2.0, 4.0, 1.0) limit ?",
                              [f"heading : ({expr})", *ep, limit])
        seen = {r["citation"] for r in head}
        rest = await self.all(sql + extra + " order by bm25(statutes_fts, 2.0, 4.0, 1.0) limit ?", [expr, *ep, limit * 2])
        return (head + [r for r in rest if r["citation"] not in seen])[:limit]

    async def conan(self, provision: str | None = None, essay_id: str | None = None, query: str | None = None, limit=6) -> list[dict]:
        if not await self.has_table("conan"):
            return []
        if essay_id:
            return await self.all("select essay_id, provision, title, text from conan where essay_id = ?", (essay_id,))
        if provision:
            return await self.all("select essay_id, provision, title, substr(text, 1, 400) as text from conan "
                                  "where provision = ? or provision like ? order by id", (provision, provision + ".%"))
        expr = self._fts(query or "")
        hits: dict[int, float] = {}
        if expr:
            for r, row in enumerate(await self.all("select rowid as id from conan_fts where conan_fts match ? "
                                                   "order by bm25(conan_fts, 4.0, 1.0) limit ?", (expr, limit * 3))):
                hits[row["id"]] = hits.get(row["id"], 0) + 1.0 / (60 + r)
        for r, (i, _d) in enumerate(await self._vec("conan_vec", query or "", limit * 3)):
            hits[i] = hits.get(i, 0) + 1.0 / (60 + r)
        ids = sorted(hits, key=lambda i: -hits[i])[:limit]
        if not ids:
            return []
        rows = await self.all(f"select id, essay_id, provision, title, substr(text, 1, 1200) as text from conan where id in ({','.join('?' * len(ids))})", ids)
        return sorted(rows, key=lambda r: -hits[r["id"]])

    async def legislators(self, name: str, state: str | None = None, limit=10) -> list[dict]:
        if not await self.has_table("legislators"):
            return []
        words = re.findall(r"[A-Za-z'-]+", name or "")
        sql = "select l.id, l.name, l.birthday, l.current from legislators l where " + " and ".join("l.name like ?" for _ in words)
        params = [f"%{w}%" for w in words]
        if state:
            sql += " and exists (select 1 from legislator_terms t where t.legislator_id = l.id and t.state = ?)"
            params.append(state.upper())
        people = await self.all(sql + " limit ?", [*params, limit]) if words else []
        for p in people:
            p["terms"] = await self.all("select type, state, district, party, start, end from legislator_terms "
                                        "where legislator_id = ? order by start", (p["id"],))
        execs = await self.all("select name, type, party, start, end, how from executives where " +
                               " and ".join("name like ?" for _ in words) + " order by start", [f"%{w}%" for w in words]) if words else []
        return [{"executive": execs}] + people if execs else people

    async def define(self, term: str, source: str | None = None, limit=4) -> list[dict]:
        if not await self.has_table("glossary"):
            return []
        src = {"blacks": "Black%", "webster": "Webster%"}.get((source or "").lower())
        sql = "select source, term, definition from glossary where term = ? collate nocase"
        params: list = [term.strip()]
        if src:
            sql += " and source like ?"
            params.append(src)
        rows = await self.all(sql + " limit ?", [*params, limit])
        if rows:
            return rows
        expr = self._fts(term)
        if not expr:
            return []
        sql = ("select g.source, g.term, g.definition from glossary_fts join glossary g on g.id = glossary_fts.rowid "
               "where glossary_fts match ?")
        params = [f"term : ({expr})"]
        if src:
            sql += " and g.source like ?"
            params.append(src)
        return await self.all(sql + " order by bm25(glossary_fts) limit ?", [*params, limit])
