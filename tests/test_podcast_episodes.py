"""Podcast episodes, the player and saving many things at once (decision 0031): an episode is kept apart from its show,
its audio address never reaches a browser, the relay reaches only the public internet, a class shelf holds an episode
and never a whole show, a listener's place stays in their browser, and the privacy page says how the audio travels."""
import asyncio
from pathlib import Path

from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, library, library_store, listen, shelves

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "webapp" / "static" / "js"


def test_an_episode_is_kept_apart_from_its_show():
    show = {"title": "Renewing Your Mind", "sub": "Ligonier", "feed": "https://feeds.example/rym.xml"}
    ep = {**show, "title": "Born Again", "episode": {"guid": "abc-123"}}
    assert library_store._dedup_key("podcast", show) == "https://feeds.example/rym.xml"
    assert library_store._dedup_key("podcast", ep) == "https://feeds.example/rym.xml#abc-123"


def test_an_episode_keeps_only_a_web_audio_address_and_never_sends_it_back():
    meta = library_store.episode_meta({"guid": "g", "audio": "file:///etc/passwd", "seconds": "x"}, "Show")
    assert meta["audio"] is None and meta["seconds"] is None and meta["show"] == "Show"
    meta = library_store.episode_meta({"guid": "g", "audio": "https://dts.podtrac.com/redirect.mp3/x.mp3", "seconds": 300}, "Show")
    row = {"kind": "podcast", "extraction_id": "e", "title": "Born Again", "creator": "Show", "cover_url": None,
           "source_url": "https://feeds.example/rym.xml", "source_meta": {"episode": meta}, "status": None}
    client = library_store._to_client(row)
    assert client["episode"]["guid"] == "g" and "audio" not in client["episode"]


def test_a_class_shelf_never_hands_a_browser_the_audio_address():
    ref = {"item_id": "e", "guid": "g", "ep": {"title": "T", "audio": "https://host/a.mp3", "feed": "https://host/f.xml"}}
    out = shelves._public_ref("podcast", ref)
    assert "audio" not in out["ep"] and "feed" not in out["ep"] and out["ep"]["title"] == "T"
    assert ref["ep"]["audio"]                                       # the stored ref keeps it for the relay
    assert shelves._public_ref("video", {"item_id": "v"}) == {"item_id": "v"}


def test_episodes_and_their_moments_are_told_apart_on_a_class_shelf():
    k = shelves._key_of
    assert k("podcast", {"item_id": "s", "guid": "a"}) != k("podcast", {"item_id": "s", "guid": "b"})
    assert k("podcast", {"item_id": "s", "guid": "a"}) != k("podcast", {"item_id": "s", "guid": "a", "start": 0})
    assert "podcast" in shelves.PLACEABLE


def test_a_whole_show_never_goes_on_a_class_shelf():
    src = (ROOT / "webapp" / "shelves.py").read_text(encoding="utf-8")
    assert "A class shelf takes an episode, not a whole show" in src


def test_the_relay_reaches_only_the_public_internet():
    for url in ("http://127.0.0.1:8100/", "http://localhost/x", "http://169.254.169.254/latest/meta-data",
                "http://10.0.0.5/a.mp3", "http://[fdaa::1]/a.mp3", "http://192.168.1.2/a.mp3", "file:///etc/passwd",
                "ftp://example.com/a.mp3", "http://app.internal/a.mp3"):
        assert not asyncio.run(listen._public(url)), url


def test_the_player_and_its_audio_are_for_the_class_alone(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: None)
    client = TestClient(appmod.app)
    page = client.get("/listen/6b1f2c1e-8f4a-4d7e-9d1a-3c2b1a0f9e8d")
    assert page.status_code == 403 and "Living Library" in page.text
    assert client.get("/api/listen/6b1f2c1e-8f4a-4d7e-9d1a-3c2b1a0f9e8d/audio").status_code == 404
    assert client.get("/api/library/item/6b1f2c1e-8f4a-4d7e-9d1a-3c2b1a0f9e8d/audio").status_code == 403


def test_a_listening_place_stays_in_the_browser():
    js = (JS / "listen.js").read_text(encoding="utf-8")
    assert "localStorage" in js and "fetch(" not in js and "XMLHttpRequest" not in js and "sendBeacon" not in js
    # storage can be blocked (a private window, managed Chromebooks): both helpers are guarded
    assert "function store(k,v){try{" in js and "function load(k){try{return localStorage" in js


def test_episode_search_asks_apple_for_episodes(monkeypatch):
    seen = {}

    class Resp:
        status_code = 200

        def json(self):
            return {"results": [
                {"trackName": "Chapter 3", "collectionName": "Gospel of John", "feedUrl": "https://f/x.xml", "episodeGuid": "g3",
                 "releaseDate": "2023-01-12T08:05:00Z", "trackTimeMillis": 4380000, "episodeUrl": "https://h/a.mp3",
                 "episodeContentType": "audio", "description": "Nicodemus"},
                {"trackName": "A video episode", "feedUrl": "https://f/y.xml", "episodeGuid": "v", "episodeContentType": "video"},
                {"trackName": "No feed", "episodeGuid": "n"}]}

    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, headers=None, params=None):
            seen.update(params); return Resp()

    monkeypatch.setattr(library.httpx, "AsyncClient", Client)
    out = asyncio.run(library.search_episodes("john 3"))
    assert seen["entity"] == "podcastEpisode" and seen["media"] == "podcast"
    assert [x["title"] for x in out] == ["Chapter 3"]               # audio episodes with a feed and a guid only
    assert out[0]["length"] == "1 hr 13 min" and out[0]["date"] == "2023-01-12" and out[0]["guid"] == "g3"


def test_select_is_a_teachers_and_saves_a_batch_with_one_undo():
    sel = (JS / "select.js").read_text(encoding="utf-8")
    assert 'main.hasAttribute("data-teacher")' in sel             # students don't send things anywhere
    assert "Shell.toast(say, done.length ? {undo:" in sel           # one message, one Undo for the batch
    assert 'role", "checkbox"' in sel and "aria-checked" in sel     # a real checkbox a keyboard reaches
    shelves_js = (JS / "shelves.js").read_text(encoding="utf-8")
    assert 'function sel(el, d){ if(teacher && d)' in shelves_js
    tpl = (ROOT / "webapp" / "templates" / "library.html").read_text(encoding="utf-8")
    assert 'id="select-open"' in tpl and "/static/js/select.js" in tpl


def test_remove_takes_a_batch_off_at_once_and_tells_the_server_after_its_undo():
    sel = (JS / "select.js").read_text(encoding="utf-8")
    assert 'class="sel-rm"' in sel
    # nothing reaches the server until the Undo has had its moment, and Undo only shows the tiles again
    assert "batch.t = setTimeout(function(){ send(batch); }, 6500);" in sel
    assert "clearTimeout(batch.t); forget(batch); hide(batch.keys, false);" in sel
    # leaving the page sends what was waiting; a refusal brings its tile back and says why
    assert "fetch(d.rm.url, {method: \"DELETE\", credentials: \"same-origin\", keepalive: true})" in sel
    assert 'hide(bad, false); Shell.toast("Couldn\'t remove "' in sel
    # Save to sends a thing once, though it was picked on a class shelf and on your own
    assert "var s = d.same || d.k; if(seen[s]) return false;" in sel


def test_each_tile_says_where_remove_takes_it_from_and_the_schools_list_stays():
    js = (JS / "shelves.js").read_text(encoding="utf-8")
    for url in ('"/api/shelf/items/" + a.id', '"/api/shelf/books/" + encodeURIComponent(b.slug)',
                '"/api/shelf/docs/" + d.id', '"/api/shelf/resources/" + r.id'):
        assert "url: " + url in js, url
    # the school's own book for a class has a place of its own and nothing to remove it with
    assert 'bookSel(w.book.slug, w.book.title, "work:" + course.key + ":" + w.book.slug))' in js
    # a removed tile stays hidden through any redraw until the server has it, then leaves the shelves' data
    assert 'document.addEventListener("shelf:gone"' in js and "if(d.dropped){" in js
    lib = (JS / "library.js").read_text(encoding="utf-8")
    assert 'rm:{url:"/api/library/shelf/"' in lib and 'document.addEventListener("shelf:gone"' in lib


def test_the_privacy_page_says_how_podcast_audio_travels():
    text = (ROOT / "docs" / "privacy.md").read_text(encoding="utf-8")
    assert "**Podcast audio.**" in text and "never the listener's device" in text
    assert "kept only in your own browser" in text
