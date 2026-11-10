"""Teacher shelves (decision 0026): the Yorkville works and outlines, matching the school's book list to courses
and accounts without storing a name, and who may reach the routes. Made-up names and addresses only."""
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from webapp import auth, db, teacher_courses, yorkville

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import seed_teacher_courses as seed  # noqa: E402

WORKS = [
    {"key": "reveal-1", "title": "Reveal Math, Course 1", "isbns": ["9780076673728"], "courses": ["ms-math"]},
    {"key": "reveal-2", "title": "Reveal Math, Course 2", "isbns": ["9780076673742"], "courses": ["ms-math-7"]},
    {"key": "mission", "title": "History: The Mission of God", "isbns": [], "courses": ["ms-bible-7"]},
    {"key": "tebow", "title": "Tim Tebow: Through My Eyes", "isbns": [], "courses": ["ms-ela"]},
    {"key": "ag", "title": "Illinois Ag Education lessons", "aka": ["Illinois Ag Education"], "isbns": [], "courses": ["ag"]},
    {"key": "geo", "title": "Geometry (Illinois Edition)", "isbns": ["9780078884849"], "courses": ["geometry"]},
]


def test_a_tab_finds_its_courses_by_isbn_or_title_and_nothing_else():
    assert seed.courses_for(["Name of Text:", "Reveal Course 1", "978-0-07-667372-8"], WORKS) == {"ms-math"}
    # two ISBNs in neighbouring cells never run together, and an ISBN-10 finds its ISBN-13
    assert seed.courses_for(["978-0-07-888484-9", "978-0-321-64487-9"], WORKS) == {"geometry"}
    assert seed.courses_for(["0-07-888484-6"], WORKS) == {"geometry"}
    assert seed.courses_for(["Tim Tebow: Through My Eyes"], WORKS) == {"ms-ela"}
    assert seed.courses_for(["Illinois Ag Education", "Intro to Ag"], WORKS) == {"ag"}
    # a bare word before a colon ("History") never matches every history teacher
    assert seed.courses_for(["U.S. History", "World History"], WORKS) == set()


def test_a_tab_is_matched_to_exactly_one_account_or_none():
    emails = ["jdoe@school.test", "jane.doering@school.test", "asmith@school.test", "bsmith@school.test"]
    assert seed.account_for("Smith, Alex", emails) is None          # two Smiths: never guess
    assert seed.account_for("Doering, Jane", emails) == "jane.doering@school.test"
    assert seed.account_for("Music", emails) is None


def test_the_sheet_is_read_with_the_standard_library(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   '<sheet name="Doe, Jo" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                   'relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<si><t>Holes</t></si></sst>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/'
                   'main"><sheetData><row><c t="s"><v>0</v></c><c><v>9780440414803</v></c></row></sheetData></worksheet>')
    path = tmp_path / "book_list.xlsx"
    path.write_bytes(buf.getvalue())
    assert seed.sheets(path) == [("Doe, Jo", ["Holes", "9780440414803"])]


def test_no_name_is_kept_in_the_app_data():
    data = (ROOT / "webapp" / "data" / "yorkville.json").read_text(encoding="utf-8")
    assert "teacher" not in json.loads(data).get("about", "").lower().replace("teacher's copy", "")
    for w in json.loads(data)["works"]:
        assert set(w) <= {"key", "title", "author", "state", "slug", "outline", "isbns", "courses", "note", "aka"}


def test_every_work_has_a_course_and_every_outline_a_source():
    courses = {c["key"] for c in yorkville.courses()}
    for w in yorkville.works():
        assert w["courses"] and set(w["courses"]) <= courses, w["key"]
        if w["state"] == "outline":
            o = yorkville.outline(w["outline"])
            assert o["sources"] or not o["toc"], w["key"]
            for e in o["toc"]:
                assert e.get("basis") in (None, "page", "general")


@pytest.fixture
def client(monkeypatch):
    who = {"user": None}
    monkeypatch.setattr(auth, "current_user", lambda request: who["user"])
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u.get("role") == "teacher")
    monkeypatch.setattr(db, "ready", lambda: False)
    app = Starlette(routes=[Route("/c", teacher_courses.get), Route("/c", teacher_courses.change, methods=["POST"]),
                            Route("/o/{key}", teacher_courses.outline)])
    return TestClient(app), who


def test_only_teachers_reach_the_shelf_and_outlines(client):
    c, who = client
    for user in (None, {"role": "student"}):
        who["user"] = user
        assert c.get("/c").status_code == 403
        assert c.post("/c", json={"courses": []}).status_code == 403
        assert c.get("/o/route-66").status_code == 403
    who["user"] = {"role": "teacher", "email": "t@school.test"}
    d = c.get("/c").json()
    assert d["mine"] == [] and d["saving"] is False and len(d["courses"]) >= 37
    assert c.post("/c", json={"courses": ["bible-2"]}).status_code == 503
    assert c.get("/o/route-66").json()["outline"]["toc"]
    assert c.get("/o/..%2Fsecrets").status_code == 404
