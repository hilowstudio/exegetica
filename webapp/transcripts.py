"""Transcripts for the Living Library's videos and podcast episodes (decisions 0026 and 0028): first from free,
published sources (a feed's own <podcast:transcript> files, and YouTube's caption tracks when it hands them
over), then, when a teacher asks, written by a service: Deepgram for a podcast episode, Gemini watching a public
YouTube video. The design follows Podcatch's (a ranked choice of timed formats, segments in seconds, [M:SS]
stamps that become [H:MM:SS] past the hour; Deepgram with its settings for audio), with two of its faults fixed:
caption times are already seconds, and caption text is HTML-unescaped. Public broadcast transcripts may be stored
and shared (docs/sources/living-library-plan.md).

YouTube's caption links now need a token only its own player can make, so they come back empty for most
videos; the maker chose Gemini for those (2026-11-09) and Gemini 3.8 Flash after a side-by-side test (2026-11-13).
Gemini is told to transcribe, never to summarize. Podcasts always go to Deepgram (the maker, 2026-11-13): one pass of Gemini over
an hour of audio came back empty, cut short, looping or with its clock misread.

A segment is {"start": float seconds, "end": float seconds, "text": str, "speaker": int | None}."""
from __future__ import annotations

import html
import json
import os
import re
import tempfile
from xml.etree import ElementTree as ET

import httpx

_UA = {"User-Agent": "Exegetica-LivingLibrary/1.0 (+https://exegetica.app)"}
_PODCAST_NS = "{https://podcastindex.org/namespace/1.0}"
_ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
MAX_BYTES = 12 * 1024 * 1024


def stamp(seconds: float) -> str:
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def parse_stamp(text: str) -> float | None:
    """'2:14', '1:02:14' or '134' to seconds; None when it isn't a time."""
    parts = (text or "").strip().split(":")
    if not parts or not all(p.strip().isdigit() for p in parts) or len(parts) > 3:
        return None
    total = 0
    for p in parts:
        total = total * 60 + int(p)
    return float(total)


def as_text(segments: list[dict], every: float = 30.0) -> str:
    """The transcript as lines that each start with a stamp, a new line about every `every` seconds."""
    lines, cur, start = [], [], None
    for s in segments:
        if start is None:
            start = s["start"]
        cur.append(s["text"].strip())
        if s["end"] - start >= every:
            lines.append(f"[{stamp(start)}] " + " ".join(cur))
            cur, start = [], None
    if cur:
        lines.append(f"[{stamp(start or 0)}] " + " ".join(cur))
    return "\n".join(line for line in lines if line.strip())


def cut(segments: list[dict], start: float, end: float, pad: float = 0.3, limit: int = 2000) -> str:
    """The words spoken between two times (Podcatch's snips, from segments rather than word timings)."""
    words = " ".join(s["text"].strip() for s in segments if s["end"] >= start - pad and s["start"] <= end + pad)
    words = re.sub(r"\s+", " ", words).strip()
    return words if len(words) <= limit else words[:limit].rsplit(" ", 1)[0] + " …"


# ------------------------------------------------------------------------------------- parsers
def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t or ""))).strip()


def _clock(t: str) -> float:
    """'00:01:02.500' or '01:02,500' or '62.5' to seconds."""
    t = t.strip().replace(",", ".")
    parts = t.split(":")
    out = 0.0
    for p in parts:
        out = out * 60 + float(p)
    return out


def parse_vtt(text: str) -> list[dict]:
    segs, speakers = [], {}
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        lines = [x for x in block.split("\n") if x.strip()]
        for i, line in enumerate(lines):
            m = re.match(r"\s*([\d:.,]+)\s*-->\s*([\d:.,]+)", line)
            if not m:
                continue
            body = " ".join(lines[i + 1:])
            who = re.match(r"<v\s+([^>]+)>", body)
            spk = speakers.setdefault(who.group(1).strip(), len(speakers)) if who else None
            words = _clean(body)
            if words:
                segs.append({"start": _clock(m.group(1)), "end": _clock(m.group(2)), "text": words, "speaker": spk})
            break
    return segs


parse_srt = parse_vtt          # the same cue shape once commas are read as decimal points


def parse_json(data) -> list[dict]:
    """The Podcasting 2.0 JSON transcript. Times are seconds; a value named *Ms is milliseconds. (A bare large
    number once read as seconds scrambled Podcatch's first minutes, so only the *Ms names are milliseconds.)"""
    items = data.get("segments") if isinstance(data, dict) else data
    segs, speakers = [], {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if "startTimeMs" in it or "startMs" in it:
            start = float(it.get("startTimeMs", it.get("startMs", 0))) / 1000
            end = float(it.get("endTimeMs", it.get("endMs", start * 1000))) / 1000
        else:
            start = float(it.get("startTime", it.get("start", 0)) or 0)
            end = float(it.get("endTime", it.get("end", start)) or start)
        words = _clean(it.get("body") or it.get("text") or "")
        who = it.get("speaker")
        spk = speakers.setdefault(str(who), len(speakers)) if who not in (None, "") else None
        if words:
            segs.append({"start": start, "end": max(end, start), "text": words, "speaker": spk})
    return _merge_words(segs)


def _merge_words(segs: list[dict]) -> list[dict]:
    """A word-level transcript (about one word a segment) grouped into phrases of up to ~12 seconds."""
    if not segs or sum(len(s["text"].split()) for s in segs) / len(segs) > 1.6:
        return segs
    out = []
    for s in segs:
        if out and s["start"] - out[-1]["start"] < 12 and s["speaker"] == out[-1]["speaker"]:
            out[-1]["text"] += " " + s["text"]
            out[-1]["end"] = s["end"]
        else:
            out.append(dict(s))
    return out


def parse_json3(data: dict) -> list[dict]:
    """YouTube's timed text in json3: tStartMs and dDurationMs are milliseconds."""
    segs = []
    for ev in data.get("events") or []:
        words = _clean("".join(s.get("utf8", "") for s in ev.get("segs") or []))
        if words:
            start = ev.get("tStartMs", 0) / 1000
            segs.append({"start": start, "end": start + ev.get("dDurationMs", 0) / 1000, "text": words, "speaker": None})
    return segs


# ------------------------------------------------------------------------------------- podcasts
_RANK = {"application/json": 0, "text/vtt": 1, "application/x-subrip": 2, "application/srt": 2, "text/srt": 2}


async def episodes(feed_url: str, limit: int = 60) -> list[dict]:
    """A show's newest episodes: guid, title, date, audio link, and any published transcript files."""
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        r = await client.get(feed_url, headers=_UA)
    r.raise_for_status()
    root = ET.fromstring(r.content[:MAX_BYTES])
    out = []
    for item in root.findall("./channel/item")[:limit]:
        enc = item.find("enclosure")
        guid = (item.findtext("guid") or (enc.get("url") if enc is not None else "") or item.findtext("title") or "").strip()
        out.append({
            "guid": guid[:300],
            "title": (item.findtext("title") or "").strip()[:300],
            "date": (item.findtext("pubDate") or "").strip()[:40],
            "duration": (item.findtext(_ITUNES_NS + "duration") or "").strip()[:12],
            "audio": enc.get("url") if enc is not None else None,
            "transcripts": sorted(({"url": t.get("url"), "type": (t.get("type") or "").lower()}
                                   for t in item.findall(_PODCAST_NS + "transcript") if t.get("url")),
                                  key=lambda t: _RANK.get(t["type"], 9)),
        })
    return out


async def episode_transcript(files: list[dict]) -> tuple[list[dict], str] | None:
    """The best published transcript with timings: JSON, then VTT, then SRT. (segments, format) or None."""
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        for f in files:
            kind = f.get("type") or ""
            if kind not in _RANK:
                continue
            try:
                r = await client.get(f["url"], headers=_UA)
                if r.status_code != 200 or len(r.content) > MAX_BYTES:
                    continue
                if kind == "application/json":
                    segs = parse_json(json.loads(r.content))
                else:
                    segs = parse_vtt(r.text)
            except Exception:  # noqa: BLE001  (one bad file never stops the next)
                continue
            if len(segs) >= 5:
                return segs, kind
    return None


# ------------------------------------------------------------------------------------- YouTube
_YT_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/130.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}


def _caption_tracks(page: str) -> list[dict]:
    i = page.find('"captionTracks":')
    if i < 0:
        return []
    s, depth = page[i + 16:], 0
    for j, ch in enumerate(s):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[:j + 1])
                except ValueError:
                    return []
    return []


def _pick(tracks: list[dict]) -> dict | None:
    """English made by a person, then English made automatically, then anything made by a person."""
    def rank(t):
        en = (t.get("languageCode") or "").startswith("en")
        auto = t.get("kind") == "asr"
        return (0 if en and not auto else 1 if en else 2 if not auto else 3)
    return min(tracks, key=rank) if tracks else None


async def youtube(video_id: str) -> tuple[list[dict], str] | None:
    """A video's captions when YouTube hands them over. Since 2025 the caption links on the watch page usually
    come back empty without a token only YouTube's own player can make, so this mostly returns None; it is kept
    so a video whose captions do come through gets them."""
    if not re.fullmatch(r"[\w-]{11}", video_id or ""):
        return None
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        page = await client.get(f"https://www.youtube.com/watch?v={video_id}&hl=en", headers=_YT_UA)
        track = _pick(_caption_tracks(page.text))
        if not track or not track.get("baseUrl", "").startswith("https://www.youtube.com/"):
            return None
        r = await client.get(track["baseUrl"] + "&fmt=json3", headers=_YT_UA)
        if r.status_code != 200 or not r.text.strip():
            return None
        segs = parse_json3(r.json())
    kind = "youtube captions" + (" (automatic)" if track.get("kind") == "asr" else "")
    return (segs, kind) if len(segs) >= 5 else None


# ------------------------------------------------------------------------- Gemini, for YouTube (decision 0028)
# Gemini 3.8 Flash (the maker, 2026-11-13). On a 43-minute video it and 3.1 Pro Preview both ran the full length
# with times a second apart; Flash keeps the speaker's exact words at a fifth of Pro's price. 3.5 Flash-Lite broke
# off unreadably on the long video, 2.5 Pro is closed to new users, and 3.5 Transcribe is audio-only and refuses a
# YouTube link, the one thing Exegetica hands Gemini, since the video itself is never downloaded.
MODEL = os.environ.get("TRANSCRIBE_MODEL", "gemini-3.8-flash")
# Dollars per million tokens: (input, output, input past LONG_TOKENS, output past LONG_TOKENS), as reported
# for each model's paid tier. An hour of video at low resolution is about 330,000 tokens. 3.8 Flash's rate is
# reported as introductory through 2026-12-31, then $1.50 and $7.50.
PRICES = {"gemini-3.8-flash": (0.75, 3.75, 0.75, 3.75), "gemini-3.1-pro-preview": (2.0, 12.0, 4.0, 18.0),
          "gemini-3.5-flash-lite": (0.30, 2.50, 0.30, 2.50)}
LONG_TOKENS = 200_000
MAX_SECONDS = 2 * 3600           # the longest video or episode Exegetica will transcribe
MAX_AUDIO_BYTES = 300 * 1024 * 1024
PROMPT = (
    "Transcribe the speech in this recording, word for word, in the language it is spoken. Do not summarize, "
    "shorten, correct or comment, and do not describe what is on screen. Start a new segment at least every "
    "30 seconds, and whenever the speaker changes. Give each segment's start time as M:SS (or H:MM:SS past an "
    "hour), measured from the start of the recording, and number the speakers in the order they first speak. "
    "Where nothing is spoken for a while, write one segment reading [music] or [no speech]. Reply with JSON only: "
    '{"segments": [{"t": "0:00", "speaker": 1, "text": "..."}]}'
)


class TranscribeError(Exception):
    """A plain sentence a teacher can read: why there is no transcript."""


def _segments_from_model(data) -> list[dict]:
    items = (data or {}).get("segments") if isinstance(data, dict) else data
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        start = parse_stamp(str(it.get("t") or it.get("start") or ""))
        words = _clean(str(it.get("text") or ""))
        if start is None or not words or (out and start < out[-1]["start"]):
            continue
        spk = it.get("speaker")
        out.append({"start": start, "end": start, "text": words,
                    "speaker": int(spk) - 1 if isinstance(spk, int) and spk > 0 else None})
    for a, b in zip(out, out[1:]):
        a["end"] = b["start"]
    if out:
        out[-1]["end"] = out[-1]["start"] + 15
    return out


def cost(usage: dict, model: str = MODEL) -> float:
    pin, pout, lin, lout = PRICES.get(model, PRICES["gemini-3.1-pro-preview"])   # an unknown model: the dearest
    if usage.get("in", 0) > LONG_TOKENS:
        pin, pout = lin, lout
    return usage.get("in", 0) * pin / 1e6 + usage.get("out", 0) * pout / 1e6


async def _generate(parts: list, model: str) -> tuple[list[dict], dict]:
    from google import genai
    from google.genai import types
    client = genai.Client()
    resp = await client.aio.models.generate_content(
        model=model, contents=types.Content(role="user", parts=parts),
        config=types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=60000,
                                           media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
                                           thinking_config=types.ThinkingConfig(thinking_level="low")))
    um = resp.usage_metadata
    usage = {"in": um.prompt_token_count or 0,
             "out": (um.candidates_token_count or 0) + (getattr(um, "thoughts_token_count", 0) or 0)}
    reason = str(getattr(resp.candidates[0], "finish_reason", "")) if resp.candidates else ""
    if "MAX_TOKENS" in reason:
        raise TranscribeError("The recording is too long to transcribe in one pass.")
    try:
        segs = _segments_from_model(json.loads(resp.text or ""))
    except ValueError:
        segs = []
    if len(segs) < 2:
        raise TranscribeError("Gemini returned no usable transcript for this recording.")
    return segs, usage


async def youtube_duration(video_id: str) -> int | None:
    """A public video's length in seconds, from the YouTube Data API (None when it can't say)."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return None
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get("https://www.googleapis.com/youtube/v3/videos",
                             params={"part": "contentDetails", "id": video_id, "key": key})
    items = r.json().get("items") if r.status_code == 200 else None
    if not items:
        return None
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", items[0]["contentDetails"].get("duration", ""))
    return (int(m[1] or 0) * 86400 + int(m[2] or 0) * 3600 + int(m[3] or 0) * 60 + int(m[4] or 0)) if m else None


async def gemini_youtube(video_id: str, model: str = MODEL) -> tuple[list[dict], str, dict]:
    """Gemini watches a public YouTube video by its link. (segments, source, usage)."""
    from google.genai import types
    secs = await youtube_duration(video_id)
    if secs and secs > MAX_SECONDS:
        raise TranscribeError("This video is longer than two hours, the most Exegetica transcribes.")
    parts = [types.Part(file_data=types.FileData(file_uri=f"https://www.youtube.com/watch?v={video_id}")),
             types.Part(text=PROMPT)]
    segs, usage = await _generate(parts, model)
    return segs, f"transcribed by Gemini ({model})", usage


def _seconds(duration: str | None) -> int | None:
    d = (duration or "").strip()
    if d.isdigit():
        return int(d)
    s = parse_stamp(d)
    return int(s) if s is not None else None




# ------------------------------------------------------------------------- Deepgram, for podcasts (decision 0028)
# Podcatch's settings (podcatch/inngest/functions/process-episode.ts). Left in Deepgram's model-improvement
# program, which may keep the audio to train on: it is always a public podcast, never a recording of a teacher or
# a student (the maker, 2026-11-13).
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_MODEL = "nova-2"
DEEPGRAM_PARAMS = {"model": DEEPGRAM_MODEL, "smart_format": "true", "punctuate": "true", "paragraphs": "true",
                   "diarize": "true"}
DEEPGRAM_USD_PER_MIN = 0.0043    # pay-as-you-go recorded audio, as reported; an estimate for /ops and the caps


def deepgram_cost(seconds: float) -> float:
    return max(0.0, seconds) / 60 * DEEPGRAM_USD_PER_MIN


def _segments_from_deepgram(result: dict) -> list[dict]:
    """Each sentence a segment, with Deepgram's own times and its paragraph's speaker."""
    alts = ((((result or {}).get("results") or {}).get("channels") or [{}])[0].get("alternatives") or [{}])
    out = []
    for p in ((alts[0].get("paragraphs") or {}).get("paragraphs") or []):
        for s in p.get("sentences") or []:
            words = _clean(str(s.get("text") or ""))
            if words and s.get("start") is not None:
                out.append({"start": float(s["start"]), "end": float(s.get("end") or s["start"]), "text": words,
                            "speaker": p.get("speaker") if isinstance(p.get("speaker"), int) else None})
    return out


def _refused(body: str) -> bool:
    return any(k in body for k in ("403", "REMOTE_CONTENT_ERROR", "Forbidden"))


async def deepgram_audio(audio_url: str, duration: str | None) -> tuple[list[dict], str, dict]:
    """Deepgram transcribes a podcast episode from its audio link. When the show's host refuses Deepgram, the audio
    is fetched here to a temporary file and sent from it, as Podcatch does. (segments, source, {"seconds"})."""
    secs = _seconds(duration)
    if secs and secs > MAX_SECONDS:
        raise TranscribeError("This episode is longer than two hours, the most Exegetica transcribes.")
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        raise TranscribeError("Transcripts can't be made on this server yet.")
    head = {"Authorization": f"Token {key}"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=900.0), follow_redirects=True) as http:
        r = await http.post(DEEPGRAM_URL, params=DEEPGRAM_PARAMS, headers=head, json={"url": audio_url})
        if r.status_code != 200 and _refused(r.text[:2000]):
            fd, path = tempfile.mkstemp(suffix=".audio")
            os.close(fd)
            try:
                mime, size = "audio/mpeg", 0
                async with http.stream("GET", audio_url, headers=_UA) as a:
                    if a.status_code != 200:
                        raise TranscribeError("The episode's audio didn't download. Try again later.")
                    mime = (a.headers.get("content-type") or mime).split(";")[0].strip()
                    with open(path, "wb") as f:
                        async for chunk in a.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_AUDIO_BYTES:
                                raise TranscribeError("This episode's audio is too large to transcribe.")
                            f.write(chunk)

                async def body():
                    with open(path, "rb") as f:
                        while chunk := f.read(1 << 20):
                            yield chunk
                r = await http.post(DEEPGRAM_URL, params=DEEPGRAM_PARAMS, content=body(),
                                    headers={**head, "Content-Type": mime if mime.startswith("audio/") else "audio/mpeg"})
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
    if r.status_code != 200:
        raise RuntimeError(f"Deepgram {r.status_code}: {r.text[:300]}")
    data = r.json()
    segs = _segments_from_deepgram(data)
    if len(segs) < 2:
        raise TranscribeError("Deepgram returned no usable transcript for this episode.")
    seconds = float(((data.get("metadata") or {}).get("duration")) or segs[-1]["end"])
    return segs, f"transcribed by Deepgram ({DEEPGRAM_MODEL})", {"seconds": seconds}
