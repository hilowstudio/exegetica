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
                 " source_url text, cover_url text, source_meta jsonb not null default '{}'::jsonb);\ncreate table library_items (user_id uuid, extraction_id uuid, notes text,"
                 " tags text[], added_at timestamptz, unique (user_id, extraction_id));")
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

        # the Living Library's shelves (decision 0029)
        from webapp import shelves
        await shelves.shelve_book(me, "jane-austen_pride-and-prejudice", "Pride and Prejudice")
        await shelves.shelve_book(me, "jane-austen_pride-and-prejudice", "Pride and Prejudice")     # twice is once
        await shelves.shelve_book(me, "charles-dickens_great-expectations", "Great Expectations")
        check(await shelves.shelved(me) == ["charles-dickens_great-expectations", "jane-austen_pride-and-prejudice"],
              "shelve two books, newest first, a second shelving changing nothing")
        await shelves.unshelve_book(me, "charles-dickens_great-expectations")
        check(await shelves.shelved(me) == ["jane-austen_pride-and-prejudice"] and await shelves.shelved(other) == [],
              "take one off, and another person's shelf stays empty")
        await shelves.set_student_courses(other, ["bible-2", "lit-11"])
        await shelves.set_student_courses(other, ["lit-11", "hist-us"])
        check(sorted(await shelves.student_courses(other)) == ["hist-us", "lit-11"], "a student's classes are replaced as a set")
        mine = await account.collect(me)
        check([r["ref"]["slug"] for r in mine["your_shelf"]] == ["jane-austen_pride-and-prejudice"]
              and "classes_you_take" in mine, "the data download carries the shelf and the classes taken")

        # class shelves (decision 0029, phase 2): one per course, filled by its teachers, outliving them
        from webapp import auth as _auth, teacher_courses
        _auth.is_teacher = lambda u: bool(u)
        leaver = uuid.uuid4()
        await db.execute(f"insert into {schema}.users (id, google_sub, email, role) values ($1, $2, $3, 'teacher')",
                         leaver, str(leaver), "l@school.test")
        T = {me: {"id": str(me), "email": "t@school.test"}, other: {"id": str(other), "email": "o@school.test"},
             leaver: {"id": str(leaver), "email": "l@school.test"}}
        for who in T.values():
            await teacher_courses.set_course(who["email"], "bible-2", True)
        book = await shelves.place(T[me], "bible-2", "book", {"slug": "jane-austen_pride-and-prejudice"}, "students", "")
        check(isinstance(book, dict) and book["audience"] == "students", "a teacher puts a Reading Room book on a class shelf")
        check(await shelves.place(T[other], "bible-2", "book", {"slug": "jane-austen_pride-and-prejudice"}, "students", "")
              == "Pride and Prejudice is already on that class shelf.", "the same book twice is refused, whoever adds it")
        check(await shelves.place(T[me], "lit-11", "book", {"slug": "jane-austen_pride-and-prejudice"}, "students", "")
              == "Choose that class in your classes first.", "a teacher places only on the classes they teach")
        vid = uuid.uuid4()
        await db.execute(f"insert into {schema}.library_extractions (id, kind, title, creator, source_url) values "
                         "($1, 'video', 'Gospel of John, Part 1', 'BibleProject', 'https://www.youtube.com/watch?v=G-2e9mMf7E8')", vid)
        whole = await shelves.place(T[leaver], "bible-2", "video", {"item_id": str(vid)}, "students", "")
        moment = await shelves.place(T[leaver], "bible-2", "video", {"item_id": str(vid), "start": 0, "end": 30,
                                                                       "note": "The Word made flesh"}, "teachers", "")
        check(isinstance(whole, dict) and isinstance(moment, dict), "a whole video and a moment at 0:00 are two placements")
        seen = await shelves.placements(["bible-2"], students_only=True)
        check(sorted(p_["kind"] for p_ in seen) == ["book", "video"] and all(p_["audience"] == "students" for p_ in seen),
              "students see only what is marked for them")
        held = await shelves.class_holding(T[other], "book", "jane-austen_pride-and-prejudice")
        check(held and held[0]["key"] == "bible-2" and held[0]["holds"]["id"] == book["id"], "a teacher's classes show where a book already is")
        off = await shelves.take_off(T[other], uuid.UUID(book["id"]))
        check(isinstance(off, dict) and off["returned"] and "jane-austen_pride-and-prejudice" in await shelves.shelved(me),
              "another teacher takes it off, and the book goes back to the shelf of the one who added it")
        check(await shelves.set_audience(T[me], uuid.UUID(whole["id"]), "teachers") is True
              and len(await shelves.placements(["bible-2"], students_only=True)) == 0, "a teacher keeps an item for teachers")
        await db.execute(f"delete from {schema}.users where id = $1", leaver)
        left = await shelves.placements(["bible-2"], students_only=False)
        check(len(left) == 2 and all(p_["added_by"] is None for p_ in left),
              "the class keeps what a departed teacher added, with nothing that names them")
        off = await shelves.take_off(T[me], uuid.UUID(left[0]["id"]))
        check(isinstance(off, dict) and not off["returned"], "with no account to return it to, taking it off deletes it")
        mine_out = await account.collect(me)
        check("placed_on_class_shelves" in mine_out, "the data download lists what you placed on class shelves")

        # a teacher's uploads and links (decision 0029, phase 3): kept encrypted, copied to a class, returned
        from webapp import shelf_docs
        text = "The feast of booths lasted seven days. " * 40
        up = await shelf_docs._store(me, "upload", {"type": "handout", "title": "John 7 guide", "filename": "g.docx",
                                                    "format": "docx"}, "John 7 guide", text)
        lk = await shelf_docs._store(me, "link", {"type": "article", "title": "Living Water", "url": "https://example.org/w",
                                                  "site": "example.org"}, "Living Water", text)
        check(isinstance(up, dict) and up["words"] == 280 and await shelf_docs.text_of(uuid.UUID(up["id"])) == text
              and await db.fetchval("select position(convert_to('booths', 'UTF8') in ct) from shelf_texts where item_id = $1",
                                    uuid.UUID(up["id"])) == 0,
              "an upload's text is kept, encrypted")
        check([d["title"] for d in await shelf_docs.mine(me)] == ["Living Water", "John 7 guide"] and await shelf_docs.mine(other) == [],
              "a teacher's uploads and links are theirs, newest first")
        check(await shelf_docs.readable_by(T[other], uuid.UUID(up["id"])) is None
              and await shelf_docs.readable_by(T[me], uuid.UUID(up["id"])) is not None, "no one else reads a teacher's own upload")
        shared = await shelves.place(T[me], "bible-2", "upload", {"item_id": up["id"]}, "students", "")
        check(isinstance(shared, dict) and shared["ref"]["origin"] == up["id"]
              and await shelf_docs.text_of(uuid.UUID(shared["id"])) == text, "a shared upload's class copy keeps its own text")
        check(await shelves.place(T[other], "bible-2", "upload", {"item_id": shared["id"]}, "students", "")
              == "John 7 guide is already on that class shelf.", "the class copy shared again is refused as the same thing")
        pupil = uuid.uuid4()
        await db.execute(f"insert into {schema}.users (id, google_sub, email, role) values ($1, $2, $3, 'student')",
                         pupil, str(pupil), "p@school.test")
        await shelves.set_student_courses(pupil, ["bible-2"])
        P = {"id": str(pupil), "email": "p@school.test"}
        check(await shelf_docs.readable_by(P, uuid.UUID(shared["id"])) is not None
              and await shelf_docs.readable_by(P, uuid.UUID(up["id"])) is None, "a student of the class reads the class copy alone")
        await shelves.set_audience(T[me], uuid.UUID(shared["id"]), "teachers")
        check(await shelf_docs.readable_by(P, uuid.UUID(shared["id"])) is None, "kept for teachers, it closes to students")
        await db.execute("delete from shelf_items where id = $1", uuid.UUID(up["id"]))      # as the Delete in its menu
        check(await shelf_docs.text_of(uuid.UUID(shared["id"])) == text and await shelf_docs.text_of(uuid.UUID(up["id"])) is None,
              "deleting the teacher's own copy leaves the class's")
        off = await shelves.take_off(T[other], uuid.UUID(shared["id"]))
        back = [d for d in await shelf_docs.mine(me) if d["title"] == "John 7 guide"]
        check(isinstance(off, dict) and off["returned"] and len(back) == 1 and await shelf_docs.text_of(uuid.UUID(back[0]["id"])) == text,
              "taken off by another teacher, it goes back to the one who shared it, text and all")
        pl2 = await shelves.place(T[me], "bible-2", "link", {"item_id": lk["id"]}, "students", "")
        await shelves.take_off(T[other], uuid.UUID(pl2["id"]))
        check(sum(d["title"] == "Living Water" for d in await shelf_docs.mine(me)) == 1,
              "when the teacher still has their own copy, nothing is duplicated")
        unit_copy = await prep.add_source(me, uid_, "upload", {"filename": "g.docx", "format": "docx", "shelf": back[0]["id"]},
                                          "John 7 guide", text=text)
        check(isinstance(unit_copy, dict) and await prep.add_source(me, uid_, "upload", {"filename": "g.docx", "format": "docx",
              "shelf": back[0]["id"]}, "John 7 guide", text=text) == "John 7 guide is already in this unit.",
              "a unit holds a shelf upload once")

        class Req:
            def __init__(self, user, pid, method="POST", body=None, form=None):
                self.user, self.path_params, self.method, self._b, self._f = user, {"id": str(pid)}, method, body or {}, form or {}

            async def json(self):
                return self._b

            async def form(self):
                return self._f
        maker = {"id": str(uuid.uuid4()), "email": "maker@school.test"}
        _auth.current_user = lambda r: r.user
        _auth.is_admin = lambda u: u is maker
        bk = await shelf_docs._store(me, "upload", {"type": "book", "title": "A Body of Divinity", "author": "Thomas Watson"},
                                     "A Body of Divinity", text)
        r1 = await shelf_docs.suggest(Req(T[me], bk["id"], body={"basis": "Published 1692"}))
        r2 = await shelf_docs.suggest(Req(T[me], bk["id"], body={"basis": "Published 1692"}))
        r3 = await shelf_docs.suggest(Req(T[other], bk["id"], body={"basis": "Published 1692"}))
        waiting = await shelf_docs.pending()
        check(r1.status_code == 200 and r2.status_code == 400 and r3.status_code == 404 and len(waiting) == 1
              and waiting[0]["words"] == 280 and [d["suggested"] for d in await shelf_docs.mine(me) if d["id"] == bk["id"]] == ["pending"],
              "a teacher suggests their own book once, and the maker sees it waiting")
        got = await shelf_docs.decide(Req(maker, waiting[0]["id"], method="GET"))
        done = await shelf_docs.decide(Req(maker, waiting[0]["id"], form={"decision": "approved"}))
        check(got.body.decode() == text and done.status_code == 303
              and (await shelf_docs.pending())[0]["status"] == "approved"
              and [d["suggested"] for d in await shelf_docs.mine(me) if d["id"] == bk["id"]] == ["approved"],
              "the maker downloads the text and approves it, and the teacher's shelf says so")
        nope = await shelf_docs.decide(Req(T[me], waiting[0]["id"], form={"decision": "declined"}))
        check(nope.status_code == 404 and (await shelf_docs.pending())[0]["status"] == "approved", "only the maker decides")

        # Prep Room resources on shelves (decision 0029, phase 4): the class sees the newest version, keys stay with
        # teachers, a copy takes the original's place, and the class keeps its copy when the resource goes
        from webapp import shelf_resources
        quiz = "# Pop Quiz\n\n1. Where was Jesus teaching?\n\n## Answer Key\n\n1. In the temple, in the middle of the feast.\n"
        rid = uuid.UUID(await prep.create_resource(me, uid_, "quiz", "Pop Quiz", {"grade_band": "secondary"}))
        await prep.add_version(me, rid, quiz, "draft")
        on = await shelves.place(T[me], "bible-2", "resource", {"resource_id": str(rid)}, "students", "")
        item = uuid.UUID(on["id"]) if isinstance(on, dict) else None
        check(item and on["ref"]["n"] == 1 and on["ref"]["kind_word"] == "Quiz" and not on["ref"]["keys_only"]
              and await shelf_docs.text_of(item) == quiz, "a teacher puts a resource on a class shelf, its newest version with it")
        check(await shelves.place(T[other], "bible-2", "resource", {"resource_id": str(rid)}, "students", "")
              == "That resource isn't in your Prep Room.", "only its own teacher shelves a resource")
        quiz2 = quiz.replace("Where was", "Where did") .replace("teaching?", "teach?")
        await prep.add_version(me, rid, quiz2, "edit")
        row = await db.fetchrow("select ref from shelf_items where id = $1", item)
        check(await shelf_docs.text_of(item) == quiz2 and row["ref"]["n"] == 2, "a save reaches the class shelf in the same transaction")
        check(await shelf_docs.readable_by(P, item) is not None, "a student of the class can open it (the page sends the student copy)")
        key = uuid.UUID(await prep.create_resource(me, uid_, "answer_key", "Key", {}))
        await prep.add_version(me, key, "# Key\n\n1. In the temple, in the middle of the feast of booths.\n", "draft")
        kp = await shelves.place(T[me], "bible-2", "resource", {"resource_id": str(key)}, "students", "")
        check(isinstance(kp, dict) and kp["audience"] == "teachers"
              and isinstance(await shelves.set_audience(T[me], uuid.UUID(kp["id"]), "students"), str)
              and await shelf_docs.readable_by(P, uuid.UUID(kp["id"])) is None, "an answer key goes to the teachers and stays there")
        held = await shelf_resources.on_shelves([rid])
        check([h["name"] for h in held[str(rid)]] == ["Sophomore Bible: Gospel of John"] and held[str(rid)][0]["audience"] == "students",
              "a resource knows which class shelves hold it")
        cp = await prep.copy_resource(me, rid)
        cid = uuid.UUID(cp["id"])
        got = await prep.get_resource(me, cid)
        check(got["title"] == "Pop Quiz (copy)" and got["version"]["document"] == quiz2 and got["settings"]["copy_of"] == str(rid)
              and not (await shelf_resources.on_shelves([cid])).get(str(cid)), "make a copy: the newest version, in the same unit, on no shelf")
        await prep.add_version(me, cid, quiz2 + "\n2. Who was amazed?\n", "edit")
        check(await shelf_docs.text_of(item) == quiz2, "reworking the copy leaves the class's copy alone")
        swapped = await shelf_resources.replace(T[me], cid, rid)
        row = await db.fetchrow("select ref, label from shelf_items where id = $1", item)
        check(swapped == ["Sophomore Bible: Gospel of John"] and row["ref"]["resource_id"] == str(cid) and row["label"] == "Pop Quiz"
              and "Who was amazed" in await shelf_docs.text_of(item), "the copy takes the original's place, keeping its name")
        await prep.add_version(me, rid, quiz, "restore")
        check("Who was amazed" in await shelf_docs.text_of(item), "the original, off the shelf, no longer reaches the class")
        back = await shelf_resources.replace(T[me], rid, cid)
        row = await db.fetchrow("select ref from shelf_items where id = $1", item)
        check(back == ["Sophomore Bible: Gospel of John"] and row["ref"]["resource_id"] == str(rid) and await shelf_docs.text_of(item) == quiz,
              "Undo puts the original back")
        await prep.update_resource(me, rid, "Pop Quiz on John 7", None, False)
        await shelf_resources.rename(rid, "Pop Quiz on John 7")
        check(await db.fetchval("select label from shelf_items where id = $1", item) == "Pop Quiz on John 7", "a rename reaches the shelf")
        r1 = await shelf_resources.own_shelf(Req(T[me], rid, method="PUT"))
        await shelf_resources.own_shelf(Req(T[me], rid, method="PUT"))
        mine_res = await shelf_resources.mine(me)
        check(r1.status_code == 200 and [m["id"] for m in mine_res] == [str(rid)] and mine_res[0]["href"].endswith(f"/r/{rid}")
              and (await shelf_resources.own_shelf(Req(T[other], rid, method="PUT"))).status_code == 404,
              "a teacher puts their own resource on their own shelf, once")
        await shelf_resources.own_shelf(Req(T[me], rid, method="DELETE"))
        check(await shelf_resources.mine(me) == [], "and takes it off, leaving it in its unit")
        await prep.delete_resource(me, rid)
        check(await shelf_docs.text_of(item) == quiz and await db.fetchval("select 1 from shelf_items where id = $1", item),
              "deleting the resource leaves the class its last version")

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
