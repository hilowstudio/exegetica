"""The Living Library's shelves (decision 0029): who may pick which classes, what a class shelf shows each person,
and that the shelves ask for a sign-in. The SQL itself is checked by scripts/check_prep_sql.py."""
import pytest
from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, shelves, yorkville


def test_a_student_picks_only_from_the_grades_with_logins():
    student = {c["key"] for c in shelves.courses_for(False)}
    teacher = {c["key"] for c in shelves.courses_for(True)}
    assert student < teacher                                     # middle-school courses are for teachers alone
    for c in yorkville.courses():
        assert (c["key"] in student) == (shelves._top_grade(c["grades"]) >= 9), c


def _course_with(state):
    for c in yorkville.courses():
        if any(w["state"] == state for w in yorkville.works([c["key"]])):
            return c["key"]
    pytest.skip(f"no course has a {state} work")


def test_a_class_shelf_shows_what_each_person_can_open():
    key = _course_with("outline")
    works = [w for w in yorkville.works([key])]
    text = next((w for w in works if w.get("slug")), None)
    items = {text["slug"]: {"slug": text["slug"], "title": text["title"]}} if text else {}
    teacher, = shelves.class_shelves([key], items, teacher=True)
    student, = shelves.class_shelves([key], items, teacher=False)
    assert teacher["key"] == key and len(teacher["works"]) == len(works)
    states_t = {w["state"] for w in teacher["works"]}
    states_s = {w["state"] for w in student["works"]}
    assert "outline" in states_t and "outline" not in states_s     # an outline is a teacher's tool
    assert {w["state"] for w in student["works"] if not w["book"]} <= {"print"}   # what a student can't open is named, not linked
    if text:
        assert any(w["state"] == "text" and w["book"]["slug"] == text["slug"] for w in student["works"])


def test_the_shelves_ask_for_a_sign_in(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: None)
    c = TestClient(appmod.app)
    assert c.get("/api/shelf/home").status_code == 401
    assert c.put("/api/shelf/books/jane-austen_pride-and-prejudice").status_code == 401
    assert c.get("/api/shelf/books").json() == {"slugs": [], "signed": False}


def test_a_class_shelf_names_who_added_an_item_to_teachers_alone():
    placed = [{"id": "1", "course": "bible-2", "audience": "students", "kind": "book", "ref": {"slug": "x"},
               "label": "X", "added_by": "me", "added_name": "Pat Teacher"},
              {"id": "2", "course": "bible-2", "audience": "students", "kind": "video", "ref": {"item_id": "v", "start": 36},
               "label": "V", "added_by": "other", "added_name": "Sam Rivera"}]
    items = {"x": {"slug": "x", "title": "X"}}
    videos = {"v": {"title": "V", "sub": "", "thumbnail": None, "url": "https://www.youtube.com/watch?v=abc"}}
    t, = shelves.class_shelves(["bible-2"], items, True, placed, videos, "me")
    s, = shelves.class_shelves(["bible-2"], items, False, placed, videos, "me")
    assert t["added"][0]["yours"] and t["added"][1]["added_name"] == "Sam Rivera"
    assert all("added_name" not in a and "yours" not in a for a in s["added"])        # a student sees no names
    v = s["added"][1]["video"]                                                       # a moment opens the watch page (0034),
    assert v["url"] == "/watch/2" and v["start"] == 36                                    # which starts it at its second


def test_a_moment_at_the_start_is_not_the_whole_video():
    assert shelves._key_of("video", {"item_id": "v", "start": 0}) != shelves._key_of("video", {"item_id": "v"})
    assert shelves._key_of("book", {"slug": "x"}) == "x"


def test_class_shelves_are_filled_by_teachers(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "00000000-0000-0000-0000-000000000001", "role": "student"})
    monkeypatch.setattr(auth, "is_teacher", lambda u: False)
    monkeypatch.setattr(auth, "is_admin", lambda u: False)
    c = TestClient(appmod.app)
    assert c.post("/api/shelf/class/bible-2/items", json={"kind": "book", "ref": {"slug": "x"}}).status_code == 403
    assert c.delete("/api/shelf/items/00000000-0000-0000-0000-000000000002").status_code == 403
    assert c.get("/api/shelf/held?kind=book&key=x").status_code == 403


def test_a_teachers_one_save_to_holds_their_own_shelf():
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / "webapp" / "static" / "js" / "reader.js").read_text(encoding="utf-8")
    assert 'if(!Covers.signed() || ub) return;' in js and 'mine: {label: "Your books"' in js
