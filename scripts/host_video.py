"""Host a class video in Exegetica's own storage (decision 0034).

  host_video.py <file> --item <catalog id> [--captions <file.vtt>] [--credit "Courtesy of …"] [--write]
  host_video.py <file> --new --title "…" --creator "…" [--url <the owner's page>] [same options] [--write]
  host_video.py --remove --item <catalog id> [--write]

Only for a video whose owner has allowed hosting, or a copy the teacher owns where the owner allows it (the list is in
0034). The file comes from the owner, the owner's own download page or the teacher's copy, never from YouTube itself.

What it does:
- converts the file to a web MP4 (H.264 and AAC, at most 1280 wide, moov at the front so it plays as it loads); a file
  that is already one is copied as it is, with only its index moved to the front
- takes a still from about a tenth of the way in
- uploads the video to r2://<bucket>/video/<id>.mp4 and the still to covers/<id> (the Library's cover route serves it)
- records the copy on the catalog entry: source_meta.hosted, an optional source_meta.credit, and the cover

--new makes the catalog entry first (and puts it on the maker's own Living Library shelf), for a video that isn't in
the Library yet. --remove deletes the copy and its record, for when an owner withdraws permission.
Dry run unless --write. Nothing here calls a model.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from webapp import auth, db, library_store, r2  # noqa: E402

MAX_W = 1280


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        sys.exit(f"{name} isn't on PATH; install FFmpeg first.")
    return path


def probe(path: Path) -> dict:
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    if not v:
        sys.exit(f"{path.name} has no video stream.")
    a = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    return {"seconds": float(info["format"].get("duration") or v.get("duration") or 0), "width": int(v.get("width") or 0),
            "height": int(v.get("height") or 0), "audio": bool(a), "vcodec": v.get("codec_name"),
            "acodec": (a or {}).get("codec_name"), "pix_fmt": v.get("pix_fmt")}


def web_ready(info: dict) -> bool:
    """Already H.264 (4:2:0) with AAC or no sound, at most MAX_W wide: copied as it is, only the index moved up front."""
    return (info["vcodec"] == "h264" and info["pix_fmt"] in ("yuv420p", None) and info["width"] <= MAX_W
            and (not info["audio"] or info["acodec"] == "aac"))


def length(seconds: float) -> str:
    t = int(round(seconds))
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def convert(src: Path, dst: Path, info: dict) -> None:
    if web_ready(info):
        subprocess.run([tool("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a?",
                        "-c", "copy", "-movflags", "+faststart", str(dst)], check=True)
        return
    has_audio = info["audio"]
    cmd = [tool("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-vf", f"scale='min({MAX_W},iw)':-2",
           "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-profile:v", "high", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac", "-b:a", "128k"] if has_audio else ["-an"]
    cmd += ["-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)


def still(src: Path, dst: Path, at: float) -> None:
    subprocess.run([tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{at:.1f}", "-i", str(src), "-frames:v", "1",
                    "-vf", f"scale='min({MAX_W},iw)':-2", "-q:v", "3", str(dst)], check=True)


async def maker_id(conn) -> uuid.UUID:
    email = sorted(auth._admin_emails())[0]
    return await conn.fetchval("select id from users where lower(email) = $1", email)


async def main(a) -> None:
    if not r2.configured():
        sys.exit("R2 is not configured (R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / bucket).")
    await db.init_pool()
    async with db.pool().acquire() as conn:
        if a.new:
            item = {"type": "video", "url": a.url, "title": a.title, "sub": a.creator}
            key = library_store._dedup_key("video", item)
            row = await conn.fetchrow("select id, title, source_meta from library_extractions where kind = 'video' and dedup_key = $1", key)
            exid = row["id"] if row else None
            print(("existing" if row else "new") + f" catalog entry: {a.title} ({a.creator}) key {key}")
        else:
            exid = uuid.UUID(a.item)
            row = await conn.fetchrow("select id, title, source_meta from library_extractions where id = $1 and kind = 'video'", exid)
            if not row:
                sys.exit(f"No video {exid} in the Living Library catalog.")
            print(f"catalog entry: {row['title']} ({exid})")
        meta = dict((row or {}).get("source_meta") or {}) if row else {}

        if a.remove:
            h = meta.get("hosted") or {}
            keys = [k for k in (h.get("key"), h.get("captions")) if k]
            print("would delete" if not a.write else "deleting", keys, "and the hosted record")
            if a.write:
                for k in keys:
                    await r2.delete_async(k)
                meta.pop("hosted", None)
                await conn.execute("update library_extractions set source_meta = $2, updated_at = now() where id = $1", exid, meta)
                print("REMOVED")
            return

        src = Path(a.file)
        if not src.is_file():
            sys.exit(f"No file at {src}")
        info = probe(src)
        print(f"source: {src.name}, {length(info['seconds'])}, {info['width']}x{info['height']}, "
              f"{src.stat().st_size / 1e6:.0f} MB{'' if info['audio'] else ', no audio'}")
        if not a.write:
            print("dry run: would " + ("copy it as it is (already web-ready)" if web_ready(info) else "convert it to a web MP4")
                  + ", take a still, upload both"
                  + (" and the captions" if a.captions else "") + ", and record the copy" + (f" with credit {a.credit!r}" if a.credit else ""))
            return

        if exid is None:
            uid = await maker_id(conn)
            exid = await conn.fetchval(
                """insert into library_extractions (kind, dedup_key, title, creator, source_url, source_meta, seeded_by_user_id)
                   values ('video', $1, $2, $3, $4, $5, $6) returning id""",
                library_store._dedup_key("video", {"url": a.url, "title": a.title, "sub": a.creator}),
                a.title, a.creator or "", a.url, {"meta": length(info["seconds"]), "accent": library_store._DEFAULT_ACCENT}, uid)
            await conn.execute("insert into library_items (user_id, extraction_id) values ($1, $2) on conflict do nothing", uid, exid)
            print("made catalog entry", exid)

        with tempfile.TemporaryDirectory() as tmp:
            web, pic = Path(tmp) / "web.mp4", Path(tmp) / "still.jpg"
            print("copying as it is (already web-ready)…" if web_ready(info) else "converting…", flush=True)
            convert(src, web, info)
            out = probe(web)
            still(web, pic, max(1.0, out["seconds"] / 10))
            vkey = f"video/{exid}.mp4"
            print(f"uploading {web.stat().st_size / 1e6:.0f} MB to r2://{r2._bucket()}/{vkey}", flush=True)
            await r2.upload_file_async(vkey, str(web), content_type="video/mp4")
            await r2.put_bytes_async(f"covers/{exid}", pic.read_bytes(), "image/jpeg")
            ckey = None
            if a.captions:
                ckey = f"video/{exid}.vtt"
                await r2.put_bytes_async(ckey, Path(a.captions).read_bytes(), "text/vtt")
            meta["hosted"] = {"key": vkey, "seconds": round(out["seconds"], 1), "length": length(out["seconds"]),
                              "width": out["width"], "height": out["height"], "bytes": web.stat().st_size,
                              "captions": ckey, "from_file": src.name}
            meta["meta"] = length(out["seconds"])
            if a.credit:
                meta["credit"] = a.credit
            await conn.execute("""update library_extractions set source_meta = $2, cover_url = $3, updated_at = now()
                                  where id = $1""", exid, meta, f"/api/library/cover/{exid}")
        print(f"HOSTED {exid}: {meta['hosted']['length']}, {meta['hosted']['width']}x{meta['hosted']['height']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", nargs="?")
    p.add_argument("--item")
    p.add_argument("--new", action="store_true")
    p.add_argument("--title")
    p.add_argument("--creator")
    p.add_argument("--url")
    p.add_argument("--captions")
    p.add_argument("--credit")
    p.add_argument("--remove", action="store_true")
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    if args.remove and not args.item:
        p.error("--remove needs --item")
    if not args.remove and (not args.file or not (args.item or (args.new and args.title))):
        p.error("give a file and --item, or --new with --title")
    asyncio.run(main(args))
