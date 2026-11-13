"""Transcripts and moments (webapp/transcripts.py, webapp/excerpts.py, decision 0026): the timed formats, the
stamps past an hour, the words cut for an excerpt, YouTube links, and who may reach the routes. No network."""
import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from webapp import auth, db, excerpts, transcripts

VTT = """WEBVTT

00:00:01.000 --> 00:00:04.500
<v Tim>In the beginning was the Word,

00:00:04.500 --> 00:00:08.000
<v Jon>and the Word was with God &amp; was God.

01:02:03.000 --> 01:02:05.000
<v Tim>Late in the episode.
"""


def test_vtt_keeps_times_in_seconds_speakers_as_numbers_and_unescapes_text():
    segs = transcripts.parse_vtt(VTT)
    assert [s["start"] for s in segs] == [1.0, 4.5, 3723.0]
    assert segs[1]["text"] == "and the Word was with God & was God."
    assert [s["speaker"] for s in segs] == [0, 1, 0]
    assert transcripts.parse_srt("1\n00:00:01,000 --> 00:00:02,500\nHello\n")[0]["end"] == 2.5


def test_json_reads_seconds_unless_the_field_says_milliseconds():
    secs = transcripts.parse_json({"segments": [{"startTime": 150.5, "endTime": 152, "body": "Booths", "speaker": "A"}]})
    assert secs[0]["start"] == 150.5          # a large number of seconds is never taken for milliseconds
    ms = transcripts.parse_json({"segments": [{"startTimeMs": 150500, "endTimeMs": 152000, "body": "Booths"}]})
    assert ms[0]["start"] == 150.5
    words = transcripts.parse_json([{"startTime": i, "endTime": i + 1, "body": w} for i, w in enumerate("a b c d".split())])
    assert len(words) == 1 and words[0]["text"] == "a b c d"     # a word-level file becomes phrases


def test_youtube_timed_text_is_milliseconds_and_never_stamped_zero():
    segs = transcripts.parse_json3({"events": [{"tStartMs": 62000, "dDurationMs": 3000, "segs": [{"utf8": "Jesus &amp; "}, {"utf8": "the feast"}]}]})
    assert segs == [{"start": 62.0, "end": 65.0, "text": "Jesus & the feast", "speaker": None}]
    assert transcripts.as_text(segs).startswith("[1:02] ")


def test_stamps_past_the_hour_and_reading_them_back():
    assert transcripts.stamp(59) == "0:59" and transcripts.stamp(7230) == "2:00:30"
    assert transcripts.parse_stamp("2:14") == 134 and transcripts.parse_stamp("1:02:03") == 3723
    assert transcripts.parse_stamp("2m") is None and transcripts.parse_stamp("") is None


def test_an_excerpt_is_the_words_spoken_between_its_times():
    segs = transcripts.parse_vtt(VTT)
    assert transcripts.cut(segs, 5.0, 7.0) == "and the Word was with God & was God."
    assert "Late" not in transcripts.cut(segs, 0, 8)


def test_caption_tracks_prefer_english_by_a_person():
    tracks = [{"languageCode": "en", "kind": "asr", "baseUrl": "a"}, {"languageCode": "fr", "baseUrl": "b"},
              {"languageCode": "en-GB", "baseUrl": "c"}]
    assert transcripts._pick(tracks)["baseUrl"] == "c"
    page = 'x"captionTracks":[{"baseUrl":"https://www.youtube.com/api/timedtext?v=1","languageCode":"en"}],"audio"'
    assert transcripts._caption_tracks(page)[0]["languageCode"] == "en"


def test_youtube_links_open_at_the_moment():
    item = {"source_url": "https://youtu.be/G-2e9mMf7E8?si=x"}
    assert excerpts.link_at(item, 134.9) == "https://www.youtube.com/watch?v=G-2e9mMf7E8&t=134s"
    assert excerpts._youtube_id("https://www.youtube.com/watch?v=G-2e9mMf7E8&list=1") == "G-2e9mMf7E8"
    assert excerpts.link_at({"source_url": "https://feeds.example/rss"}, 5) is None


@pytest.fixture
def client(monkeypatch):
    who = {"user": None}
    monkeypatch.setattr(auth, "current_user", lambda request: who["user"])
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u.get("role") == "teacher")
    monkeypatch.setattr(db, "ready", lambda: False)
    one = "00000000-0000-0000-0000-0000000000aa"
    app = Starlette(routes=[
        Route("/m/{id}", excerpts.moments), Route("/e/{id}", excerpts.episode_list),
        Route("/t/{id}", excerpts.fetch_transcript, methods=["POST"]),
        Route("/x/{id}", excerpts.save_excerpt, methods=["POST"]),
        Route("/d/{id}", excerpts.delete_excerpt, methods=["DELETE"])])
    return TestClient(app), who, one


def test_only_teachers_reach_moments_and_saving_says_when_it_is_down(client):
    c, who, one = client
    calls = [("get", f"/m/{one}"), ("get", f"/e/{one}"), ("post", f"/t/{one}"), ("post", f"/x/{one}"), ("delete", f"/d/{one}")]
    for user, code in ((None, 403), ({"role": "student"}, 403), ({"role": "teacher", "id": one}, 503)):
        who["user"] = user
        for method, url in calls:
            assert c.request(method.upper(), url, json={}).status_code == code, (user, url)


# ------------------------------------------------------------------ Gemini transcription (decision 0028)
import asyncio  # noqa: E402

from webapp import metrics, usage  # noqa: E402


def test_gemini_segments_are_ordered_timed_and_speakers_counted_from_zero():
    data = {"segments": [{"t": "0:00", "speaker": 1, "text": "In the beginning"},
                         {"t": "0:31", "speaker": 2, "text": "was the Word"},
                         {"t": "0:20", "speaker": 1, "text": "out of order, dropped"},
                         {"t": "soon", "text": "no time, dropped"},
                         {"t": "1:02:03", "speaker": 1, "text": "past the hour"}]}
    segs = transcripts._segments_from_model(data)
    assert [(s["start"], s["end"], s["speaker"]) for s in segs] == [(0, 31, 0), (31, 3723, 1), (3723, 3738, 0)]
    assert transcripts.cost({"in": 1_000_000, "out": 0}, "gemini-3.5-flash-lite") == 0.30


class _DB:
    def __init__(self):
        self.sql = []

    async def execute(self, sql, *a):
        self.sql.append((" ".join(sql.split())[:40], a))
        return "INSERT 0 1"


def _run(monkeypatch, gemini):
    rows, counted, fake = [], [], _DB()
    monkeypatch.setattr(transcripts, "gemini_youtube", gemini)
    monkeypatch.setattr(excerpts.db, "execute", fake.execute)
    monkeypatch.setattr(metrics, "record", lambda r: rows.append(r))

    async def add(uid, usd):
        counted.append((uid, usd))
    monkeypatch.setattr(usage, "transcribe_add", add)
    out = asyncio.run(excerpts.run(key="yt:G-2e9mMf7E8", kind="video", user_id="u1", video_id="G-2e9mMf7E8"))
    return out, fake.sql, rows, counted


def test_a_finished_transcript_is_kept_and_its_cost_recorded(monkeypatch):
    segs = [{"start": 0, "end": 5, "text": "a", "speaker": None}, {"start": 5, "end": 9, "text": "b", "speaker": None}]

    async def gemini(video_id):
        return segs, "transcribed by Gemini (test)", {"in": 40000, "out": 3000}
    out, sql, rows, counted = _run(monkeypatch, gemini)
    assert out["status"] == "done"
    assert sql[0][0].startswith("insert into library_transcripts") and sql[1][0].startswith("delete from library_tra")
    assert rows[0]["route"] == "library:transcribe" and rows[0]["outcome"] == "complete" and rows[0]["est_usd"] > 0
    assert counted == [("u1", pytest.approx(transcripts.cost({"in": 40000, "out": 3000})))]


def test_a_failed_transcript_says_why_and_never_raises(monkeypatch):
    async def gemini(video_id):
        raise transcripts.TranscribeError("This video is longer than two hours, the most Exegetica transcribes.")
    out, sql, rows, counted = _run(monkeypatch, gemini)
    assert out == {"status": "failed", "error": "This video is longer than two hours, the most Exegetica transcribes."}
    assert sql[0][0].startswith("update library_transcribe_jobs") and "two hours" in sql[0][1][1]
    assert rows[0]["outcome"] == "provider_error" and counted == [("u1", 0.0)]

    async def broken(video_id):
        raise RuntimeError("socket")
    out, sql, _, _ = _run(monkeypatch, broken)
    assert out["error"] == excerpts.FAILED       # a raw error never reaches the teacher


def test_a_capped_teacher_or_a_running_job_starts_nothing(monkeypatch):
    item = {"id": "x", "kind": "video", "title": "T", "source_url": "https://youtu.be/G-2e9mMf7E8"}
    started = []

    async def job_running(key):
        return {"status": "running", "error": None}
    monkeypatch.setattr(excerpts, "_job", job_running)
    monkeypatch.setattr(excerpts, "run", lambda **k: started.append(k))
    assert asyncio.run(excerpts._start("u1", item, "yt:G-2e9mMf7E8", None))["job"]["status"] == "running"

    async def no_job(key):
        return None

    async def capped(uid):
        return usage.TRANSCRIBE_CAPPED
    monkeypatch.setattr(excerpts, "_job", no_job)
    monkeypatch.setattr(usage, "transcribe_check", capped)
    assert asyncio.run(excerpts._start("u1", item, "yt:G-2e9mMf7E8", None))["missing"] == usage.TRANSCRIBE_CAPPED
    assert started == []


def test_the_transcription_job_is_registered_without_retries():
    from webapp import inngest_app
    assert inngest_app.transcribe_fn in inngest_app.functions


# ------------------------------------------------------------------ Deepgram for episodes; Gemini Pro for videos (0028, 2026-11-13)
def test_gemini_3_8_flash_watches_videos_and_a_pro_models_long_inputs_cost_more():
    assert transcripts.MODEL == "gemini-3.8-flash"
    assert transcripts.cost({"in": 330_000, "out": 20_000}) == pytest.approx(0.2475 + 0.075)   # about an hour of video
    pro = "gemini-3.1-pro-preview"
    assert transcripts.cost({"in": 100_000, "out": 10_000}, pro) == pytest.approx(0.20 + 0.12)
    assert transcripts.cost({"in": 330_000, "out": 20_000}, pro) == pytest.approx(1.32 + 0.36)


DG = {"metadata": {"duration": 125.5}, "results": {"channels": [{"alternatives": [{"transcript": "…", "paragraphs": {"paragraphs": [
    {"speaker": 0, "sentences": [{"text": "In the beginning was the Word.", "start": 0.4, "end": 2.9},
                                 {"text": "  ", "start": 3.0, "end": 3.1}]},
    {"speaker": 1, "sentences": [{"text": "And the Word was with God.", "start": 3.2, "end": 5.0}]}]}}]}]}}


def test_deepgram_sentences_become_timed_segments_with_speakers():
    assert transcripts._segments_from_deepgram(DG) == [
        {"start": 0.4, "end": 2.9, "text": "In the beginning was the Word.", "speaker": 0},
        {"start": 3.2, "end": 5.0, "text": "And the Word was with God.", "speaker": 1}]
    assert transcripts._segments_from_deepgram({}) == []
    assert transcripts.deepgram_cost(600) == pytest.approx(10 * transcripts.DEEPGRAM_USD_PER_MIN)


def test_deepgram_is_sent_the_link_and_the_audio_when_the_host_refuses(monkeypatch):
    import httpx
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.method, req.url.host, dict(req.url.params), req.headers.get("content-type")))
        if req.url.host == "api.deepgram.com" and req.headers.get("content-type") == "application/json":
            return httpx.Response(400, text='{"err_code":"REMOTE_CONTENT_ERROR","err_msg":"403 Forbidden"}')
        if req.url.host == "api.deepgram.com":
            assert req.read() == b"ID3audio"
            return httpx.Response(200, json=DG)
        return httpx.Response(200, content=b"ID3audio", headers={"content-type": "audio/mpeg"})
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    segs, source, used = asyncio.run(transcripts.deepgram_audio("https://cdn.show.test/ep1.mp3", "10:00"))
    assert [s["text"] for s in segs][0] == "In the beginning was the Word." and used == {"seconds": 125.5}
    assert source == "transcribed by Deepgram (nova-2)"
    assert [h for _, h, _, _ in seen] == ["api.deepgram.com", "cdn.show.test", "api.deepgram.com"]
    for _, host, params, _ in seen:
        if host == "api.deepgram.com":
            assert "mip_opt_out" not in params and params["model"] == "nova-2" and params["diarize"] == "true"
    with pytest.raises(transcripts.TranscribeError, match="two hours"):
        asyncio.run(transcripts.deepgram_audio("https://cdn.show.test/ep1.mp3", "2:30:00"))


def test_an_episode_goes_to_deepgram_and_never_to_gemini(monkeypatch):
    fake = _DB()
    rows, counted = [], []
    monkeypatch.setattr(excerpts.db, "execute", fake.execute)
    monkeypatch.setattr(metrics, "record", lambda r: rows.append(r))

    async def add(uid, usd):
        counted.append(usd)
    monkeypatch.setattr(usage, "transcribe_add", add)

    async def episodes(feed, limit=60):
        return [{"guid": "g1", "title": "Episode 1", "audio": "https://cdn.show.test/ep1.mp3", "duration": "41:20"}]

    async def deepgram(audio, duration):
        assert audio.endswith("ep1.mp3") and duration == "41:20"
        return [{"start": 0, "end": 3, "text": "a", "speaker": 0}, {"start": 3, "end": 6, "text": "b", "speaker": 0}], \
            "transcribed by Deepgram (nova-2)", {"seconds": 2480}

    async def no_gemini(*a, **k):
        raise AssertionError("an episode never goes to Gemini")
    monkeypatch.setattr(transcripts, "episodes", episodes)
    monkeypatch.setattr(transcripts, "deepgram_audio", deepgram)
    monkeypatch.setattr(transcripts, "gemini_youtube", no_gemini)
    out = asyncio.run(excerpts.run(key="ep:x:g1", kind="podcast", user_id="u1", feed_url="https://feed.test", guid="g1"))
    assert out["status"] == "done" and fake.sql[0][1][1] == "Episode 1"
    assert rows[0]["outcome"] == "complete" and counted == [pytest.approx(transcripts.deepgram_cost(2480))]
    assert not hasattr(transcripts, "gemini_audio")


def test_the_daily_transcript_limits_are_off_while_building_and_work_when_turned_back_on(monkeypatch):
    """The maker, 2026-11-13: no ceiling while the courses are built; the switch turns it back on."""
    async def over(sql, *a):
        return [{"who": usage.TRANSCRIBE_ALL, "turns": 99, "est_usd": 50.0}]
    monkeypatch.setattr(usage.db, "ready", lambda: True)
    monkeypatch.setattr(usage.db, "fetch", over)
    assert usage.TRANSCRIBE_CAPS_ON is False
    assert asyncio.run(usage.transcribe_check("u1")) is None
    monkeypatch.setattr(usage, "TRANSCRIBE_CAPS_ON", True)
    assert asyncio.run(usage.transcribe_check("u1")) == usage.TRANSCRIBE_ALL_CAPPED
