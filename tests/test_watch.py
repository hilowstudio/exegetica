"""Class videos (decision 0034): a video on a class shelf opens a watch page inside Exegetica, for the people whose
shelf it is on. Exegetica's own copy plays from a short-lived link handed out after that check; any other video waits
behind a play button and then plays in YouTube's privacy-enhanced player. A clip keeps its start and end, the owner's
credit shows, the shelf tile opens the page, and the privacy page says how class videos travel."""
import asyncio
import re
import uuid
from pathlib import Path

from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, r2, shelves, watch

ROOT = Path(__file__).resolve().parent.parent
SID = "6b1f2c1e-8f4a-4d7e-9d1a-3c2b1a0f9e8d"
STUDENT = {"id": "11111111-1111-1111-1111-111111111111", "email": "s@school.test", "role": "student"}


def _row(hosted=True, audience="students", start=None, end=None, credit=None):
    meta = {"meta": "4:56"}
    if hosted:
        meta["hosted"] = {"key": "video/abc.mp4", "length": "4:56", "seconds": 296, "captions": "video/abc.vtt"}
    if credit:
        meta["credit"] = credit
    ref = {"item_id": "abc"}
    if start is not None:
        ref["start"] = start
    if end is not None:
        ref["end"] = end
    return {"id": uuid.UUID(SID), "course_key": "bible-2", "audience": audience, "ref": ref, "label": "Water of Life",
            "video_id": "abc", "title": "Water of Life", "creator": "BibleProject",
            "cover_url": "/api/library/cover/abc" if hosted else "https://i.ytimg.com/vi/PgmAkM39Zt4/hqdefault.jpg",
            "source_url": "https://www.youtube.com/watch?v=PgmAkM39Zt4", "source_meta": meta}


def _as(monkeypatch, user, row=None):
    monkeypatch.setattr(auth, "current_user", lambda request: user)

    async def place(u, item_id):
        return row
    monkeypatch.setattr(watch, "placement", place)


def test_signed_out_there_is_no_page_and_no_file(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: None)
    client = TestClient(appmod.app)
    assert client.get(f"/watch/{SID}").status_code == 403
    assert client.get(f"/api/watch/{SID}/video", follow_redirects=False).status_code == 404
    assert client.get(f"/api/watch/{SID}/captions").status_code == 404


def test_a_student_sees_only_what_is_placed_for_students_in_their_own_classes(monkeypatch):
    rows = {"row": None}

    async def fetchrow(sql, *a):
        return rows["row"]

    async def classes_of(user):
        return ["bible-2"]
    monkeypatch.setattr(watch.db, "ready", lambda: True)
    monkeypatch.setattr(watch.db, "fetchrow", fetchrow)
    monkeypatch.setattr(shelves, "classes_of", classes_of)
    monkeypatch.setattr(shelves, "is_teacher", lambda u: u.get("role") == "teacher")
    rows["row"] = _row(audience="teachers")
    assert asyncio.run(watch.placement(STUDENT, uuid.UUID(SID))) is None                       # a teachers' video
    assert asyncio.run(watch.placement({**STUDENT, "role": "teacher"}, uuid.UUID(SID))) is not None
    rows["row"] = _row(audience="students")
    assert asyncio.run(watch.placement(STUDENT, uuid.UUID(SID))) is not None
    rows["row"] = {**_row(), "course_key": "algebra-1"}                                       # not their class
    assert asyncio.run(watch.placement(STUDENT, uuid.UUID(SID))) is None


def test_exegeticas_copy_plays_on_the_page_with_its_clip_credit_and_captions(monkeypatch):
    _as(monkeypatch, STUDENT, _row(start=156, end=189, credit="Courtesy of Tyndale House"))
    page = TestClient(appmod.app).get(f"/watch/{SID}")
    assert page.status_code == 200
    assert f'src="/api/watch/{SID}/video"' in page.text and f'src="/api/watch/{SID}/captions"' in page.text
    assert 'data-start="156"' in page.text and 'data-end="189"' in page.text and "2:36–3:09" in page.text
    assert "Courtesy of Tyndale House" in page.text and 'poster="/api/library/cover/abc"' in page.text
    assert "youtube" not in page.text.lower()


def test_a_video_exegetica_cant_host_waits_for_play_before_youtube_loads(monkeypatch):
    _as(monkeypatch, STUDENT, _row(hosted=False, start=156, end=189))
    page = TestClient(appmod.app).get(f"/watch/{SID}")
    assert page.status_code == 200
    assert "<iframe" not in page.text and "<video" not in page.text                         # nothing loads until play
    embed = re.search(r'data-embed="([^"]+)"', page.text).group(1).replace("&amp;", "&")
    assert embed.startswith("https://www.youtube-nocookie.com/embed/PgmAkM39Zt4?") and "start=156" in embed and "end=189" in embed
    assert "Nothing goes to YouTube until you press play" in page.text


def test_a_video_that_plays_only_on_its_owners_site_links_there(monkeypatch):
    row = {**_row(hosted=False), "source_url": "https://www.jesusfilm.org/watch/life-of-jesus-gospel-of-john.html/wedding-in-cana.html/english.html"}
    _as(monkeypatch, STUDENT, row)
    page = TestClient(appmod.app).get(f"/watch/{SID}")
    assert page.status_code == 200 and "Watch on jesusfilm.org" in page.text
    assert 'href="https://www.jesusfilm.org/watch/life-of-jesus-gospel-of-john.html/wedding-in-cana.html/english.html"' in page.text
    assert "<iframe" not in page.text and "<video" not in page.text and "data-embed" not in page.text
    assert watch._site("javascript:alert(1)") is None and watch._site("https://www.youtube.com/watch?v=abc") is None


def test_the_file_link_is_short_lived_and_never_cached(monkeypatch):
    _as(monkeypatch, STUDENT, _row())
    monkeypatch.setattr(r2, "configured", lambda: True)
    seen = {}

    def presign(key, expires=600):
        seen.update(key=key, expires=expires)
        return "https://r2.example/video/abc.mp4?sig=1"
    monkeypatch.setattr(r2, "presign_get", presign)
    r = TestClient(appmod.app).get(f"/api/watch/{SID}/video", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("https://r2.example/")
    assert "no-store" in r.headers["cache-control"] and seen["key"] == "video/abc.mp4" and seen["expires"] <= 6 * 3600


def test_a_video_without_a_copy_has_no_file(monkeypatch):
    _as(monkeypatch, STUDENT, _row(hosted=False))
    monkeypatch.setattr(r2, "configured", lambda: True)
    assert TestClient(appmod.app).get(f"/api/watch/{SID}/video", follow_redirects=False).status_code == 404


def test_a_class_shelf_tile_opens_the_watch_page_in_exegetica():
    placed = [{"id": SID, "course": "bible-2", "kind": "video", "audience": "students", "label": "Water of Life",
               "ref": {"item_id": "abc", "start": 156}}]
    videos = {"abc": {"title": "Water of Life", "sub": "BibleProject", "thumbnail": None,
                      "url": "https://www.youtube.com/watch?v=PgmAkM39Zt4"}}
    shelf = shelves.class_shelves(["bible-2"], {}, False, placed, videos)
    v = next(a for s in shelf for a in s["added"] if a["kind"] == "video")["video"]
    assert v["url"] == f"/watch/{SID}" and v["start"] == 156
    js = (ROOT / "webapp" / "static" / "js" / "shelves.js").read_text(encoding="utf-8")
    assert "Opens YouTube in a new tab" not in js


def test_the_privacy_page_says_how_class_videos_travel():
    text = (ROOT / "docs" / "privacy.md").read_text(encoding="utf-8")
    assert "**Class videos.**" in text and "Cloudflare" in text and "privacy-enhanced player" in text
    assert "only when someone presses play" in text


def _lum(hexc):
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def test_the_screen_note_reads_well_on_the_dark_screen():
    tokens = (ROOT / "webapp" / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
    screen = re.search(r"--screen:(#[0-9a-f]{6})", tokens).group(1)
    on = re.search(r"--on-screen:(#[0-9a-f]{6})", tokens).group(1)
    hi, lo = sorted((_lum(screen), _lum(on)), reverse=True)
    assert (hi + 0.05) / (lo + 0.05) >= 4.5
