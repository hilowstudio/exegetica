"""Google Classroom by share link (decision 0030): what the share sends, that no Google script loads, which places
offer it, and the page a student reaches from a Classroom link before choosing the class."""
import types
import uuid
from pathlib import Path

from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, shelf_docs, shelves

ROOT = Path(__file__).resolve().parent.parent / "webapp"
JS = ROOT / "static" / "js"
ME = "00000000-0000-0000-0000-00000000000a"


def _js(name):
    return (JS / name).read_text(encoding="utf-8")


def test_the_share_sends_classroom_only_a_link_and_a_title():
    p = _js("passage.js")
    assert '"https://classroom.google.com/share?url=" + encodeURIComponent(url)' in p
    assert '"&title=" + encodeURIComponent(title)' in p
    assert "w.opener = null" in p                                   # the share window can't reach back into the page
    for f in list(JS.glob("*.js")) + list((ROOT / "templates").rglob("*.html")):
        assert "apis.google.com/js/platform.js" not in f.read_text(encoding="utf-8"), f.name   # no Google script


def test_each_place_offers_the_share_its_own_way():
    assert "share: b && b.reference ? null : {url: location.origin + location.pathname + location.hash" in _js("reader.js")
    assert "share:{shelf:true,title:r.title}" in _js("generate.js")          # a resource: the class shelf's student copy
    assert "share: b.dataset.classCopy ?" in _js("doc.js")
    s = _js("shelves.js")
    assert 'label: "Share to Classroom…"' in s and "share: {shelf: true, title: d.title}" in s
    assert '"/?passage=" + encodeURIComponent(r)' in _js("passage.js")
    assert '"/?passage="+encodeURIComponent(v.reference)' in _js("memory.js")


def _setup(monkeypatch, role, row, taken=None):
    user = {"id": ME, "role": role, "email": "pat@example.org", "name": "Pat"}
    monkeypatch.setattr(auth, "current_user", lambda request: user if role else None)
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u.get("role") == "teacher")
    monkeypatch.setattr(auth, "is_admin", lambda u: False)

    async def fetchrow(sql, *a):
        return row if "course_key is not null" in sql else None

    async def unreadable(u, i):
        return None
    monkeypatch.setattr(shelf_docs, "db", types.SimpleNamespace(ready=lambda: True, fetchrow=fetchrow))
    monkeypatch.setattr(shelf_docs, "readable_by", unreadable)
    saved = {}

    async def courses(uid):
        return list(taken or [])

    async def set_courses(uid, keys):
        saved["keys"] = keys
    monkeypatch.setattr(shelves, "student_courses", courses)
    monkeypatch.setattr(shelves, "set_student_courses", set_courses)
    return saved


def _row(course="bible-2", audience="students"):
    return {"id": uuid.uuid4(), "course_key": course, "audience": audience, "label": "Pop Quiz: John 7"}


def test_a_student_from_classroom_is_offered_the_class(monkeypatch):
    row = _row()
    saved = _setup(monkeypatch, "student", row, taken=["lit-11"])
    c = TestClient(appmod.app)
    page = c.get(f"/read/doc/{row['id']}").text
    assert "Pop Quiz: John 7" in page and f'action="/read/doc/{row["id"]}/join"' in page and "Add Bible II and open it" in page
    r = c.post(f"/read/doc/{row['id']}/join", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/read/doc/{row['id']}"
    assert saved["keys"] == ["lit-11", "bible-2"]                   # added to the student's own choice, nothing removed


def test_a_teachers_only_item_or_a_class_without_student_logins_is_never_offered(monkeypatch):
    row = _row(audience="teachers")
    saved = _setup(monkeypatch, "student", row)
    c = TestClient(appmod.app)
    page = c.get(f"/read/doc/{row['id']}").text
    assert "join" not in page and "That isn't on your shelves." in page
    c.post(f"/read/doc/{row['id']}/join", follow_redirects=False)
    assert "keys" not in saved
    younger = next(k["key"] for k in shelves.courses_for(True) if k["key"] not in {x["key"] for x in shelves.courses_for(False)})
    row = _row(course=younger)
    saved = _setup(monkeypatch, "student", row)
    assert "join" not in TestClient(appmod.app).get(f"/read/doc/{row['id']}").text


def test_signed_out_the_link_offers_sign_in_and_comes_back(monkeypatch):
    row = _row()
    _setup(monkeypatch, None, row)
    page = TestClient(appmod.app).get(f"/read/doc/{row['id']}").text
    assert "It's on a class shelf in the Living Library." in page or "It&#39;s on a class shelf" in page
    assert f"/auth/login?next=/read/doc/{row['id']}" in page and "Pop Quiz" not in page   # no title to a stranger
