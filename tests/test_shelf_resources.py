"""Prep Room resources on shelves (decision 0029, phase 4): what a resource is called on a shelf, that an answer key
never reaches students, that a student is sent the student copy alone, that saves name who sees them, and that the
Prep Room's routes stay teacher-only. The SQL itself is checked by scripts/check_prep_sql.py."""
import types
import uuid
from pathlib import Path

from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, shelf_docs, shelf_resources, shelves

ME = "00000000-0000-0000-0000-00000000000a"
STATIC = Path(__file__).resolve().parent.parent / "webapp" / "static"
QUIZ = """# Pop Quiz: John 7

Name: ____

1. Where was Jesus teaching?

**Standards:** BIB.7.3.3.4

## Teaching Notes

Point students to Leviticus 23.

---

## Answer Key

1. In the temple.
"""


def _as(monkeypatch, role):
    user = {"id": ME, "role": role, "name": "Pat Teacher", "email": "pat@example.org"}
    monkeypatch.setattr(auth, "current_user", lambda request: user)
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u.get("role") == "teacher")
    monkeypatch.setattr(auth, "is_admin", lambda u: False)
    return user


def test_a_resource_is_named_by_its_kind():
    assert shelf_resources.kind_word("quiz") == "Quiz"
    assert shelf_resources.kind_word("study_guide") == "Study Guide"
    assert shelf_resources.kind_word("no_such_kind") == "Resource"
    assert shelves._key_of("resource", {"resource_id": "r1", "n": 4}) == "r1"      # one resource, whatever its version
    assert "resource" in shelves.PLACEABLE


def test_an_answer_key_never_reaches_students():
    assert shelf_resources.keys_only("answer_key", "# Key\n\n1. A\n2. B\n3. C, the longest of the answers here\n")
    assert shelf_resources.keys_only("quiz", "# Quiz\n\n## Answer Key\n\n1. In the temple, during the feast, at noon.\n")
    assert not shelf_resources.keys_only("quiz", QUIZ)
    assert shelf_resources._shelf_title("Pop Quiz (copy)") == "Pop Quiz"          # a copy put in place keeps the name


def test_a_student_is_sent_the_student_copy_alone(monkeypatch):
    item = uuid.uuid4()
    monkeypatch.setattr(shelf_docs, "db", types.SimpleNamespace(ready=lambda: True, fetchrow=None))

    async def readable(u, i):
        return {"id": item, "user_id": None, "course_key": "bible-2", "audience": "students", "kind": "resource",
                "ref": {"resource_id": str(uuid.uuid4()), "kind_word": "Quiz", "n": 3}, "label": "Pop Quiz: John 7",
                "added_by": None} if i == item else None

    async def text_of(i):
        return QUIZ
    monkeypatch.setattr(shelf_docs, "readable_by", readable)
    monkeypatch.setattr(shelf_docs, "text_of", text_of)
    _as(monkeypatch, "student")
    page = TestClient(appmod.app).get(f"/read/doc/{item}").text
    assert "Where was Jesus teaching" in page
    assert "In the temple" not in page and "Teaching Notes" not in page and "BIB.7.3.3.4" not in page   # not even in the source
    assert 'id="docAud"' not in page and "prepdoc.js" in page and "handout.css" in page

    async def no_owner(*a):
        return None
    monkeypatch.setattr(shelf_docs, "db", types.SimpleNamespace(ready=lambda: True, fetchrow=no_owner))
    _as(monkeypatch, "teacher")
    page = TestClient(appmod.app).get(f"/read/doc/{item}").text
    assert "In the temple" in page and 'id="docAud"' in page                     # the class's teachers see both copies


def test_the_prep_rooms_sends_are_for_teachers(monkeypatch):
    _as(monkeypatch, "student")
    c = TestClient(appmod.app)
    rid = str(uuid.uuid4())
    assert c.post(f"/api/prep/resources/{rid}/copy").status_code == 403
    assert c.post(f"/api/prep/resources/{rid}/replace", json={"original": rid}).status_code == 403
    assert c.put(f"/api/shelf/resources/{rid}").status_code == 403
    assert c.post("/api/shelf/class/bible-2/items", json={"kind": "resource", "ref": {"resource_id": rid}}).status_code == 403


def test_a_class_shelf_shows_a_resource_by_its_kind_and_no_names_to_students():
    placed = [{"id": "1", "course": "bible-2", "audience": "students", "kind": "resource",
               "ref": {"resource_id": "r", "kind_word": "Quiz", "n": 3}, "label": "Pop Quiz", "added_by": "me",
               "added_name": "Pat Teacher"}]
    t, = shelves.class_shelves(["bible-2"], {}, True, placed, {}, "me")
    s, = shelves.class_shelves(["bible-2"], {}, False, placed, {}, "me")
    assert t["added"][0]["doc"] == {"type": "resource", "kind_word": "Quiz", "title": "Pop Quiz", "n": 3}
    assert "added_name" not in s["added"][0]


def test_every_save_on_a_shelved_resource_says_who_sees_it():
    js = (STATIC / "js" / "generate.js").read_text(encoding="utf-8")
    for save in ('savedToast("Saved your edits as version', 'savedToast("Saved the change as version',
                 'savedToast("Brought back version'):
        assert save in js, save
    assert 'see it now.",{undo:()=>restore(before,true)}' in js           # Undo brings back the version before
    assert "see it at once." in js and "see them at once." in js           # the revise box and Edit say so first
    assert ", which \"+esc(who)+\" see" in js                               # an older version names what students see
    assert '{label:"Make a copy",act:()=>copyRes(r)}' in js
    passage = (STATIC / "js" / "passage.js").read_text(encoding="utf-8")
    assert "opts.units === false" in passage                               # a resource's Save to lists shelves alone
    # the Student view and the class's copy are drawn by one renderer
    page = (STATIC.parent / "templates" / "generate.html").read_text(encoding="utf-8")
    assert "prepdoc.js" in page and "handout.css" in page and "function studentCopy(" not in js
