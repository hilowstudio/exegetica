"""The Prep Room's saved work (webapp/prep.py, decision 0026): who may reach it, what a source may
hold, objectives keeping their anchors, and the account export and delete covering it. No database:
the SQL itself is checked against a throwaway schema by scripts/check_prep_sql.py."""
import asyncio
import uuid

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from webapp import account, auth, db, prep

STUDENT = {"id": "00000000-0000-0000-0000-000000000001", "email": "s@school.test", "role": "student"}
TEACHER = {"id": "00000000-0000-0000-0000-000000000002", "email": "t@school.test", "role": "teacher"}
SOME = "00000000-0000-0000-0000-0000000000aa"

ROUTES = [
    ("GET", "/api/prep/units", prep.units_list, "/api/prep/units"),
    ("POST", "/api/prep/units", prep.unit_create, "/api/prep/units"),
    ("GET", "/api/prep/units/{id}", prep.unit_get, f"/api/prep/units/{SOME}"),
    ("PATCH", "/api/prep/units/{id}", prep.unit_update, f"/api/prep/units/{SOME}"),
    ("DELETE", "/api/prep/units/{id}", prep.unit_delete, f"/api/prep/units/{SOME}"),
    ("POST", "/api/prep/units/{id}/sources", prep.source_add, f"/api/prep/units/{SOME}/sources"),
    ("PATCH", "/api/prep/sources/{id}", prep.source_update, f"/api/prep/sources/{SOME}"),
    ("DELETE", "/api/prep/sources/{id}", prep.source_remove, f"/api/prep/sources/{SOME}"),
    ("GET", "/api/prep/resources/{id}", prep.resource_get, f"/api/prep/resources/{SOME}"),
    ("PATCH", "/api/prep/resources/{id}", prep.resource_update, f"/api/prep/resources/{SOME}"),
    ("DELETE", "/api/prep/resources/{id}", prep.resource_delete, f"/api/prep/resources/{SOME}"),
    ("POST", "/api/prep/resources/{id}/versions", prep.resource_save, f"/api/prep/resources/{SOME}/versions"),
]


@pytest.fixture
def client(monkeypatch):
    who = {"user": None}
    monkeypatch.setattr(auth, "current_user", lambda request: who["user"])
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u.get("role") == "teacher")
    monkeypatch.setattr(db, "ready", lambda: False)
    app = Starlette(routes=[Route(path, fn, methods=[m]) for m, path, fn, _ in ROUTES])
    return TestClient(app), who


@pytest.mark.parametrize("method,_p,_f,url", ROUTES)
def test_students_and_signed_out_visitors_are_turned_away(client, method, _p, _f, url):
    c, who = client
    for user in (None, STUDENT):
        who["user"] = user
        r = c.request(method, url, json={})
        assert r.status_code == 403, (method, url, user)


@pytest.mark.parametrize("method,_p,_f,url", ROUTES)
def test_a_teacher_hears_plainly_when_saving_is_down(client, method, _p, _f, url):
    c, who = client
    who["user"] = TEACHER
    r = c.request(method, url, json={})
    assert r.status_code == 503 and r.json()["error"] == prep.UNAVAILABLE


def test_each_kind_of_source_keeps_only_what_it_needs():
    assert prep.clean_ref("book", {"slug": "homer_the-odyssey-fagles", "coverage": {"through": "4"},
                                   "text": "smuggled"}) == {"slug": "homer_the-odyssey-fagles",
                                                            "coverage": {"through": 4}}
    assert prep.clean_ref("passage", {"ref": "John 7:14-24"}) == {"ref": "John 7:14-24", "translation": "ESV"}
    assert prep.clean_ref("link", {"url": "javascript:alert(1)"}) is None
    assert prep.clean_ref("library", {"item_id": "not-a-uuid"}) is None
    item = str(uuid.uuid4())
    assert prep.clean_ref("library", {"item_id": item, "excerpts": ["x", item]}) == {
        "item_id": item, "excerpts": [item]}
    assert prep.clean_ref("outline", {"key": "reveal-math-course-2", "parts": ["Module 3"]}) == {
        "key": "reveal-math-course-2", "parts": ["Module 3"]}
    assert prep.clean_ref("book", {}) is None
    assert prep.clean_ref("sermon", {"x": 1}) is None


def test_objectives_keep_their_anchors():
    """The old Prep Room dropped each objective's Scripture and standard anchors before the model."""
    picked = [{"id": "BIB.1.2.3", "t": "Explain the purpose of John's signs", "g": 10, "c": 3,
               "a": {"scripture": ["John 20:30-31"], "standards": ["ACSI BIB 4"], "other": ["x"]}}]
    out = prep.clean_objectives(picked)
    assert out[0]["a"] == {"scripture": ["John 20:30-31"], "standards": ["ACSI BIB 4"]}
    assert out[0]["g"] == 10 and out[0]["t"].startswith("Explain")
    assert prep.clean_objectives([{"t": "no id"}] * 3) == []
    assert len(prep.clean_objectives([{"id": f"X{i}"} for i in range(40)])) == prep.MAX_OBJECTIVES


def test_the_data_export_includes_the_prep_room(monkeypatch):
    async def fetchrow(sql, *a):
        return None

    async def fetch(sql, *a):
        return []
    monkeypatch.setattr(db, "fetchrow", fetchrow)
    monkeypatch.setattr(db, "fetch", fetch)
    data = asyncio.run(account.collect(uuid.uuid4()))
    for key in ("prep_units", "prep_resources", "courses_you_teach"):
        assert key in data


class _Conn:
    def __init__(self, log):
        self.log = log

    async def execute(self, sql, *a):
        self.log.append(" ".join(sql.split())[:60])
        return "DELETE 1"

    def transaction(self):
        class _Tx:
            async def __aenter__(s):
                return s

            async def __aexit__(s, *exc):
                return False
        return _Tx()


class _Pool:
    def __init__(self, log):
        self.log = log

    def acquire(self):
        conn = _Conn(self.log)

        class _Acq:
            async def __aenter__(s):
                return conn

            async def __aexit__(s, *exc):
                return False
        return _Acq()


def test_deleting_an_account_drops_its_courses_in_the_same_transaction(monkeypatch):
    log = []
    monkeypatch.setattr(db, "pool", lambda: _Pool(log))
    monkeypatch.setattr(account.r2, "configured", lambda: False)
    asyncio.run(account.remove(uuid.uuid4(), "T@School.test"))
    assert any(s.startswith("delete from teacher_courses") for s in log)
    assert log[-1].startswith("delete from users")
