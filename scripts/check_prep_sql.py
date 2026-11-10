"""Check the Prep Room's SQL (webapp/prep.py) against a real Postgres without touching real tables:
make a throwaway schema in DATABASE_URL's database, create `users` and the Prep Room tables there
from scripts/schema.sql, run every store function, then drop the schema.

    python scripts/check_prep_sql.py

Reads DATABASE_URL and LIBRARY_ENC_KEY from .env. Spends nothing; writes nothing outside the
throwaway schema."""
from __future__ import annotations

import asyncio
import re
import secrets
import ssl
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

import asyncpg  # noqa: E402

from webapp import account, db, excerpts, prep  # noqa: E402


def _tables(sql: str) -> str:
    """The users table and everything from the Prep Room section of schema.sql."""
    users = re.search(r"create table if not exists users \(.*?\);", sql, re.S).group(0)
    prep_part = sql[sql.index("-- The Prep Room ("):]
    stand_ins = ("create table library_extractions (id uuid primary key, kind text, title text, creator text,"
                 " source_url text);\ncreate table library_items (user_id uuid, extraction_id uuid, notes text,"
                 " tags text[], added_at timestamptz);")
    return users + "\n" + stand_ins + "\n" + prep_part


def _direct(dsn: str) -> str:
    """Neon's pooled endpoint (host '...-pooler...') runs in transaction mode and drops session
    settings such as search_path between transactions; the direct endpoint keeps them."""
    return dsn.replace("-pooler.", ".")


async def main():
    schema = "prep_check_" + secrets.token_hex(4)
    ddl = _tables((ROOT / "scripts" / "schema.sql").read_text(encoding="utf-8"))
    dsn = _direct(db._clean_dsn(db.dsn()))
    admin = await asyncpg.connect(dsn, ssl=ssl.create_default_context())
    await admin.execute(f"create schema {schema}")
    ok = True
    try:
        # asyncpg runs RESET ALL whenever a connection returns to its pool, so a search_path set once in
        # `init` lasts one query (that sent this check's DDL to public once), and Neon's proxy ignores it
        # as a startup setting. `setup` sets it again on every acquire; the guards below stop any write
        # if it ever doesn't hold.
        async def setup(conn):
            await conn.execute(f"set search_path to {schema}")
        db._pool = await asyncpg.create_pool(dsn, ssl=ssl.create_default_context(), min_size=1, max_size=1,
                                             init=db._init_conn, setup=setup)
        for _ in range(2):                                   # twice: the second acquire follows a reset
            if await db.fetchval("select current_schema()") != schema:
                raise SystemExit("the connection isn't pointed at the throwaway schema; stopping before any write")
        async def holders():                                 # the schemas that hold a prep_units table
            rows = await db.fetch("select n.nspname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                                  "where c.relname = 'prep_units'")
            return {r["nspname"] for r in rows}
        before = await holders()                             # production's own (public) since the Prep Room shipped
        await db.execute(ddl)
        if schema in before or await holders() != before | {schema} or await db.fetchval("select current_schema()") != schema:
            raise SystemExit("the tables didn't land in the throwaway schema alone; stopping before any write")

        me, other = uuid.uuid4(), uuid.uuid4()
        for uid, email in ((me, "t@school.test"), (other, "o@school.test")):
            await db.execute(f"insert into {schema}.users (id, google_sub, email, role) "
                             "values ($1, $2, $3, 'teacher')", uid, str(uid), email)

        def check(cond, what):
            nonlocal ok
            print(("ok   " if cond else "FAIL ") + what)
            ok = ok and bool(cond)

        unit = await prep.create_unit(me, "John 7 and 8", "bible-2", "secondary")
        uid_ = uuid.UUID(unit["id"])
        check(unit["title"] == "John 7 and 8" and unit["objectives"] == [], "create a unit")
        s1 = await prep.add_source(me, uid_, "passage", {"ref": "John 7:14-24", "translation": "ESV"}, "John 7:14-24")
        s2 = await prep.add_source(me, uid_, "upload", {"filename": "notes.docx", "format": "docx"},
                                   "notes.docx", text="The feast of booths. " * 50)
        check(isinstance(s1, dict) and s2["words"] == 200, "add a passage and an encrypted upload")
        check(await prep.add_source(other, uid_, "passage", {"ref": "John 1"}, "John 1") is None,
              "another teacher can't add to it")
        again = await prep.add_source(me, uid_, "passage", {"ref": "John 7:14-24", "translation": "ESV"}, "John 7:14-24")
        check(again == "John 7:14-24 is already in this unit.", "the same passage twice is refused plainly")
        item, m1, m2 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        lib = await prep.add_source(me, uid_, "library", {"item_id": item, "excerpts": [m1]}, "Gospel of John, Part 1")
        joined = await prep.add_source(me, uid_, "library", {"item_id": item, "excerpts": [m2]}, "Gospel of John, Part 1")
        check(isinstance(joined, dict) and joined["merged"] and joined["id"] == lib["id"]
              and joined["ref"]["excerpts"] == [m1, m2] and joined["before"]["excerpts"] == [m1],
              "a second moment joins its item, and keeps the earlier ref for an undo")
        check(await prep.add_source(me, uid_, "library", {"item_id": item, "excerpts": [m2]}, "x")
              == "That moment is already in this unit.", "the same moment twice is refused")
        check(await prep.remove_source(me, uuid.UUID(lib["id"])), "remove the joined item again")
        held = await prep.holding(me, "passage", "John 7:14-24")
        check(list(held) == [unit["id"]] and held[unit["id"]]["source"] == s1["id"], "the units holding a passage are found")
        check(await prep.holding(other, "passage", "John 7:14-24") == {}, "another teacher's units aren't searched")
        objs = prep.clean_objectives([{"id": "B.1", "t": "x", "a": {"scripture": ["John 7:37"]}}])
        check(await prep.update_unit(me, uid_, {"objectives": objs, "notes": "Period 3"}), "update objectives")
        check(not await prep.update_unit(other, uid_, {"notes": "x"}), "another teacher can't update it")
        got = await prep.get_unit(me, uid_)
        check(got["objectives"][0]["a"]["scripture"] == ["John 7:37"] and len(got["sources"]) == 2,
              "read the unit back with anchors and sources")
        check(await prep.get_unit(other, uid_) is None, "another teacher can't read it")
        texts = await prep.sources_for_draft(me, uid_)
        check(texts[1]["text"].startswith("The feast of booths."), "decrypt an upload for a draft")
        check(await prep.sources_for_draft(other, uid_) == [], "another teacher gets no source text")

        rid = uuid.UUID(await prep.create_resource(me, uid_, "quiz", "Quiz · John 7", {"variant": "pop_quiz"}))
        check(await prep.create_resource(other, uid_, "quiz", "x", {}) is None, "can't make a resource in another's unit")
        prep.MAX_VERSIONS = 3
        ns = [await prep.add_version(me, rid, f"# Draft {i}", "draft" if i == 1 else "revise", instruction=f"v{i}")
              for i in range(1, 6)]
        check(ns == [1, 2, 3, 4, 5], "versions number in order")
        res = await prep.get_resource(me, rid)
        check([v["n"] for v in res["versions"]] == [5, 4, 3] and res["version"]["document"] == "# Draft 5",
              "only the newest versions are kept, newest shown")
        old = await prep.get_resource(me, rid, 3)
        check(old["version"]["document"] == "# Draft 3", "open an older version")
        check(await prep.add_version(other, rid, "x", "edit") is None, "another teacher can't add a version")
        check(await prep.get_resource(other, rid) is None, "another teacher can't read a resource")
        quick = uuid.UUID(await prep.create_resource(me, None, "worksheet", "Quick sheet", {}))
        check(len(await prep.list_resources(me, quick=True)) == 1, "a quick resource lists outside units")
        check(await prep.update_resource(me, quick, "Renamed", uid_, True), "move a quick resource into a unit")
        units = await prep.list_units(me)
        check(units[0]["n_sources"] == 2 and units[0]["n_resources"] == 2, "unit counts")
        check(await prep.remove_source(me, uuid.UUID(s1["id"])), "remove a source")

        await db.execute(f"insert into {schema}.teacher_courses (email, course_key) values ('t@school.test', 'bible-2')")
        # Empty stand-ins for the other stores the export reads, so the whole export runs here.
        await db.execute("""
            create table memory_state (user_id uuid, state jsonb, updated_at timestamptz);
            create table chat_state (user_id uuid, state jsonb, updated_at timestamptz);
            create table cover_prefs (user_id uuid, prefs jsonb, updated_at timestamptz);
            create table reading_state (user_id uuid, book_slug text, section_number int, pages jsonb,
                                        updated_at timestamptz);
            create table library_source_texts (user_id uuid, extraction_id uuid, source_format text,
                                               acquisition text, char_count int, created_at timestamptz);""")
        # A video on the shelf, its transcript and a moment saved from it (webapp/excerpts.py).
        vid = uuid.uuid4()
        await db.execute(f"insert into {schema}.library_extractions (id, kind, title, source_url) values "
                         "($1, 'video', 'Booths', 'https://youtu.be/G-2e9mMf7E8')", vid)
        await db.execute(f"insert into {schema}.library_items (user_id, extraction_id) values ($1, $2)", me, vid)
        await db.execute(f"insert into {schema}.library_transcripts (key, title, segments, source) values "
                         "('yt:G-2e9mMf7E8', 'Booths', $1, 'test')",
                         [{"start": 60, "end": 70, "text": "Living water.", "speaker": None}])
        item = await excerpts._item(me, vid)
        check(item and (await excerpts._transcript("yt:G-2e9mMf7E8"))["segments"][0]["start"] == 60,
              "a shelf item and its stored transcript read back")
        check(await excerpts._item(other, vid) is None, "another teacher's shelf doesn't hold it")
        await db.execute(f"insert into {schema}.library_excerpts (user_id, extraction_id, start_s, end_s, quote) "
                         "values ($1, $2, 60, 70, 'Living water.')", me, vid)
        got = await excerpts.for_item(me, vid, None)
        check(got == [{"at": "1:00–1:10", "text": '"Living water."'}], "a moment comes to a draft with its place")
        check("[1:00] Living water." in (await excerpts.transcript_for_draft(item)), "the transcript reaches a draft")
        data = await account.collect(me)
        check(len(data["library_moments"]) == 1, "the data export carries the teacher's moments")

        # A Gemini transcript's job (decision 0028), with Gemini replaced so nothing is spent.
        from webapp import transcripts
        started = []

        async def fake_run(**payload):
            started.append(payload)
        real_run, excerpts.run = excerpts.run, fake_run
        try:
            out = await excerpts._start(me, dict(item, kind="video"), "yt:XgslCbXOOIE", None)
            check(out["job"]["status"] == "running" and await excerpts._job("yt:XgslCbXOOIE") ==
                  {"status": "running", "error": None}, "asking for a transcript marks its job running")
            again = await excerpts._start(me, dict(item, kind="video"), "yt:XgslCbXOOIE", None)
            check(again["job"]["status"] == "running", "a second ask while it runs starts nothing new")
            await asyncio.sleep(0)
            check(len(started) == 1, "only one job was started")
            await db.execute(f"update {schema}.library_transcribe_jobs set updated_at = now() - interval '20 minutes'")
            check(await excerpts._job("yt:XgslCbXOOIE") is None, "a job running far too long counts as dead")
        finally:
            excerpts.run = real_run

        async def fake_gemini(video_id):
            return ([{"start": 0, "end": 4, "text": "In the beginning", "speaker": 0},
                     {"start": 4, "end": 8, "text": "was the Word", "speaker": 0}], "test", {"in": 10, "out": 2})
        real_gemini, transcripts.gemini_youtube = transcripts.gemini_youtube, fake_gemini
        try:
            done = await excerpts.run(key="yt:XgslCbXOOIE", kind="video", user_id=str(me), video_id="XgslCbXOOIE")
        finally:
            transcripts.gemini_youtube = real_gemini
        check(done["status"] == "done" and (await excerpts._transcript("yt:XgslCbXOOIE"))["segments"][1]["text"]
              == "was the Word" and await excerpts._job("yt:XgslCbXOOIE") is None,
              "a finished job keeps its transcript and clears its row")
        check(len(data["prep_units"]) == 1 and len(data["prep_resources"]) == 2
              and data["prep_resources"][0]["versions"] and data["courses_you_teach"],
              "the data export carries units, resources, versions and courses")
        check("feast" not in str(data), "the export doesn't repeat an upload's text")

        check(await prep.delete_unit(me, uid_), "delete the unit")
        left = await db.fetchval("select count(*) from prep_resources")
        check(left == 0, "its resources and versions go with it")
    finally:
        if db._pool:
            await db._pool.close()
            db._pool = None
        await admin.execute(f"drop schema {schema} cascade")
        await admin.close()
    print("all good" if ok else "SOMETHING FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
