"""The Prep Room's format list (/prep-room/formats, webapp/about.py): every format the Prep Room offers
is filed under a subject and listed, and a withheld one never is. No network."""
import html

from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import generator


def test_every_format_is_filed_under_a_subject():
    filed = {f for groups in generator._catalog["subjects"].values() for spec in groups.values()
             for f in spec.get("formats", [])}
    assert set(generator.FORMATS) <= filed, sorted(set(generator.FORMATS) - filed)


def test_the_page_lists_every_format_by_subject_and_no_withheld_one():
    r = TestClient(appmod.app).get("/prep-room/formats")
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-cache"
    for f in generator.FORMATS.values():
        assert html.escape(f["name"]) in r.text, f["id"]
    for subject in generator._catalog["subjects"]:
        assert f"<h2>{html.escape(subject)}</h2>" in r.text
    withheld = {f["id"]: f for f in generator._catalog["formats"]}
    for fid in generator.WITHHELD_FORMATS:
        assert html.escape(withheld[fid]["name"]) not in r.text, fid


def test_the_page_follows_the_house_voice_with_no_dashes():
    text = TestClient(appmod.app).get("/prep-room/formats").text
    assert "—" not in text and "–" not in text
