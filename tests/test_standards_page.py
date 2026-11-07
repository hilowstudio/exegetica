"""The academic standards page (/prep-room/standards, webapp/about.py): every subject, strand, and
sub-topic of the spine is listed for anyone, objectives load from the API, and only a teacher gets
the links into the Prep Room. No network."""
import html

from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, generator


def _page(monkeypatch, user=None):
    monkeypatch.setattr(auth, "current_user", lambda request: user)
    return TestClient(appmod.app).get("/prep-room/standards")


def test_every_part_of_the_spine_is_listed(monkeypatch):
    r = _page(monkeypatch)
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-cache"
    text = r.text   # decode the page once; the response decodes it again on every access
    for s in generator.TREE["subjects"]:
        assert f'id="S-{s["id"]}"' in text and html.escape(s["name"]) in text
        for ss in s["sub_subjects"]:
            for tp in ss["topics"]:
                for st in tp.get("sub_topics", []):
                    assert f'data-st="{st["id"]}"' in text, st["id"]
    assert text.count("—") + text.count("–") == 0   # a count: comparing the whole page would take minutes


def test_only_a_teacher_gets_the_links_into_the_prep_room(monkeypatch):
    assert "/generate?standard=" not in _page(monkeypatch).text
    monkeypatch.setattr(auth, "is_teacher", lambda u: True)
    r = _page(monkeypatch, {"email": "t@school.test", "role": "teacher"})
    assert '/generate?standard=BIB.10.1.1"' in r.text


def test_a_sub_topics_objectives_come_from_the_api():
    r = TestClient(appmod.app).get("/api/standards/objectives?sub_topic=BIB.10.1.1")
    objs = r.json()["objectives"]
    assert objs and all({"id", "t", "g", "c", "u"} <= set(o) for o in objs)
