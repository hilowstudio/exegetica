"""A teacher's uploads and links in the Living Library (decision 0029, phase 3): what each is filed as, who may read
one, that students can't upload, and that the reading view escapes the text. The SQL itself is checked by
scripts/check_prep_sql.py."""
import asyncio
import types
import uuid

from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, prep, shelf_docs, shelves

ME = "00000000-0000-0000-0000-00000000000a"
OTHER = "00000000-0000-0000-0000-00000000000b"


def _as(monkeypatch, role):
    user = {"id": ME, "role": role, "name": "Pat Teacher", "email": "pat@example.org"}
    monkeypatch.setattr(auth, "current_user", lambda request: user)
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u.get("role") == "teacher")
    monkeypatch.setattr(auth, "is_admin", lambda u: False)
    async def nothing(*a):
        return None                           # no row by that id (the Classroom join offer looks one up)
    monkeypatch.setattr(shelf_docs, "db", types.SimpleNamespace(ready=lambda: True, fetchrow=nothing))
    return user


def test_an_upload_is_filed_as_the_kind_of_thing_it_is():
    assert shelf_docs.guess_type(800, "", True) == "article"                  # a saved page
    assert shelf_docs.guess_type(60_000, "Watson.epub", False) == "book"
    assert shelf_docs.guess_type(400, "John 7 study guide.docx", False) == "handout"
    assert shelf_docs.guess_type(400, "Feast notes.txt", False) == "handout"
    assert shelf_docs.guess_type(400, "letter.pdf", False) == "document"
    assert set(shelf_docs.TYPES) == {"book", "article", "handout", "document", "sermon"}   # sermon: a talk written down


def test_students_never_upload(monkeypatch):
    _as(monkeypatch, "student")
    c = TestClient(appmod.app)
    some = "/api/shelf/docs/" + str(uuid.uuid4())
    assert c.post("/api/shelf/upload", files={"file": ("a.txt", b"word " * 50)}).status_code == 403
    assert c.post("/api/shelf/link", json={"url": "https://example.org/a"}).status_code == 403
    assert c.patch(some, json={"title": "X"}).status_code == 403
    assert c.delete(some).status_code == 403
    assert c.post(some + "/suggest", json={"basis": "Published 1692"}).status_code == 403


def test_an_upload_must_be_a_file_exegetica_reads(monkeypatch):
    _as(monkeypatch, "teacher")
    c = TestClient(appmod.app)
    r = c.post("/api/shelf/upload", files={"file": ("photo.jpg", b"\xff\xd8\xff")})
    assert r.status_code == 400 and "PDF" in r.json()["error"]


def test_a_video_or_podcast_link_goes_to_its_own_tab(monkeypatch):
    _as(monkeypatch, "teacher")
    c = TestClient(appmod.app)
    for url in ("https://www.youtube.com/watch?v=abc", "https://youtu.be/abc", "https://podcasts.apple.com/us/podcast/x"):
        r = c.post("/api/shelf/link", json={"url": url})
        assert r.status_code == 400 and "Video or Podcast tab" in r.json()["error"], url


def _row(**k):
    base = {"id": uuid.uuid4(), "user_id": None, "course_key": None, "audience": None, "kind": "upload",
            "ref": {"type": "handout"}, "label": "John 7 study guide", "added_by": uuid.UUID(OTHER)}
    return {**base, **k}


def test_who_may_read_an_upload(monkeypatch):
    rows = {}

    async def fetchrow(sql, item):
        return rows.get(item)
    monkeypatch.setattr(shelf_docs, "db", types.SimpleNamespace(ready=lambda: True, fetchrow=fetchrow))
    teaches, takes = set(), []

    async def _teaches(user, course):
        return course in teaches

    async def _takes(uid):
        return list(takes)
    monkeypatch.setattr(shelves, "_teaches", _teaches)
    monkeypatch.setattr(shelves, "student_courses", _takes)
    me = {"id": ME}
    own = _row(user_id=uuid.UUID(ME))
    others = _row(user_id=uuid.UUID(OTHER))
    for_students = _row(course_key="bible-2", audience="students")
    for_teachers = _row(course_key="bible-2", audience="teachers")
    for r in (own, others, for_students, for_teachers):
        rows[r["id"]] = r

    def can(r, user=me):
        return asyncio.run(shelf_docs.readable_by(user, r["id"])) is not None

    assert can(own) and not can(others)                       # an upload is its teacher's alone
    assert not can(own, None)                                  # and never a guest's
    assert not can(for_students) and not can(for_teachers)     # a class shelf is for its class
    takes.append("bible-2")
    assert can(for_students) and not can(for_teachers)         # a student of the class: what's marked for students
    takes.clear(); teaches.add("bible-2")
    assert can(for_students) and can(for_teachers)             # a teacher of the class: all of it


def test_the_reading_view_escapes_the_text_and_leaves_the_title_to_the_heading(monkeypatch):
    out = shelf_docs._paragraphs("John 7 Study Guide\n\nRead <script>alert(1)</script> John 7:37.\n\nTwo\n\nThree",
                                 "John 7 study guide")
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert not out.startswith("<p>John 7") and out.count("<p>") == 3
    one_a_line = shelf_docs._paragraphs("Name\nFirst question?\nSecond question?")
    assert one_a_line.count("<p>") == 3                        # a short handout, one line a paragraph

    user = _as(monkeypatch, "teacher")
    item = uuid.uuid4()
    origin = str(uuid.uuid4())

    async def readable(u, i):
        return _row(id=item, course_key="bible-2", audience="students",
                    ref={"type": "handout", "origin": origin}) if u is user and i == item else None

    async def text_of(i):
        return "Read <b>John 7:37-39</b> aloud.\n\nThen the next.\n\nAnd last."
    monkeypatch.setattr(shelf_docs, "readable_by", readable)
    monkeypatch.setattr(shelf_docs, "text_of", text_of)
    c = TestClient(appmod.app)
    r = c.get(f"/read/doc/{item}")
    assert r.status_code == 200
    assert "&lt;b&gt;John 7:37-39&lt;/b&gt;" in r.text and "<b>John" not in r.text
    assert "Save to…" in r.text and f'data-origin="{origin}"' in r.text    # a class copy is known by its teacher's copy
    assert c.get(f"/read/doc/{uuid.uuid4()}").status_code != 200
    assert c.get("/read/doc/not-an-id").status_code != 200


def test_a_class_shelf_shows_a_shared_upload_as_its_kind():
    placed = [{"id": "1", "course": "bible-2", "audience": "students", "kind": "upload",
               "ref": {"type": "handout", "origin": "o"}, "label": "John 7 study guide", "added_by": "me"},
              {"id": "2", "course": "bible-2", "audience": "teachers", "kind": "link",
               "ref": {"type": "article", "url": "https://example.org/a", "site": "example.org", "origin": "p"},
               "label": "Living Water", "added_by": "other", "added_name": "Sam Rivera"}]
    t, = shelves.class_shelves(["bible-2"], {}, True, placed, {}, "me")
    docs = {a["label"]: a["doc"] for a in t["added"]}
    assert docs["John 7 study guide"]["type"] == "handout" and docs["Living Water"]["site"] == "example.org"
    # one teacher's copy is one thing on a shelf, however it got there
    assert shelves._key_of("upload", placed[0]["ref"]) == "o"
    assert "upload" in shelves.PLACEABLE and "link" in shelves.PLACEABLE


def test_a_unit_holds_a_shelf_upload_once():
    assert prep.SAME_SOURCE["upload"] == "shelf"
    shelf = str(uuid.uuid4())
    assert prep.clean_ref("upload", {"filename": "a.docx", "format": "docx", "shelf": shelf}).get("shelf") == shelf
    assert "shelf" not in prep.clean_ref("upload", {"filename": "a.docx", "format": "docx", "shelf": "abc"})
