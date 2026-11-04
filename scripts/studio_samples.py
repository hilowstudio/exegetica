#!/usr/bin/env python3
"""
The Media Studio's sample set: every image model on the same prompts, and every editing model on
the same edits, so the page can show what each model does instead of describing it. Writes small
WebP files and a manifest (time and cost per image) to webapp/static/studio-samples/.

Each image costs what the service charges (about $3 for the whole set on 2026-11-04), and the two
GPU models wake the maker's Baseten GPU. Run it again when a model is added or changed:

    .venv/Scripts/python.exe scripts/studio_samples.py [--only model,model] [--skip-gpu]
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from PIL import Image  # noqa: E402

from webapp import studio  # noqa: E402
from webapp import studio_comfy as comfy  # noqa: E402
from webapp import studio_prices as prices  # noqa: E402
from webapp import studio_services as svc  # noqa: E402

OUT = ROOT / "webapp" / "static" / "studio-samples"
SIZE = 768   # the long side of each saved sample

# Each prompt tests one thing models get wrong in different ways; the first four (STRIP) are the ones a
# model's card shows. The edits run on images the set itself made.
STRIP = ["person", "words", "details", "imagination"]
PROMPTS = [
    {"key": "person", "label": "A person, hands busy",
     "text": "A woman sitting on a porch step, tying the laces of her running shoes, morning light."},
    {"key": "imagination", "label": "Imagination in a style",
     "text": "An alien screaming at a grocery store cashier, painted as a 1950s pulp magazine cover."},
    {"key": "portrait", "label": "A face",
     "text": "Close-up portrait photograph of an elderly fisherman with weathered skin and a grey beard, wearing a "
             "yellow raincoat, soft overcast light, a harbor softly blurred behind him."},
    {"key": "hands", "label": "Hands",
     "text": "Photograph of two hands kneading bread dough on a floured wooden table, flour dust in the air, warm "
             "morning window light."},
    {"key": "words", "label": "Words in the picture",
     "text": "A hand-painted wooden sign above a bakery storefront that reads \"FRESH BREAD DAILY\", rustic lettering, "
             "a quiet morning street."},
    {"key": "landscape", "label": "A landscape",
     "text": "Wide photograph of a misty pine valley at sunrise, a river winding through it, golden light breaking "
             "through the fog."},
    {"key": "illustration", "label": "An illustration",
     "text": "Children's book watercolor illustration of a fox reading a book under a large mushroom in a rainy "
             "forest, soft pastel colors."},
    {"key": "product", "label": "A product shot",
     "text": "Studio product photograph of a ceramic coffee mug with a speckled blue glaze on a white background, "
             "soft shadow, crisp detail."},
    {"key": "details", "label": "Many details at once",
     "text": "A red bicycle leaning against a green door, a black cat sitting in the bicycle's front basket, a potted "
             "sunflower to the left of the door, and three blue windows above it."},
    {"key": "painting", "label": "A painting style",
     "text": "Oil painting in the manner of a 17th-century Dutch master: a shepherd boy resting with his sheep on a "
             "hillside at dusk, warm low light."},
]
EDITS = [
    {"key": "night", "label": "Day to night", "base": "words",
     "text": "Make it night, with warm light glowing from the bakery windows. Keep everything else the same."},
    {"key": "recolor", "label": "Change one thing", "base": "portrait",
     "text": "Change the yellow raincoat to a dark green raincoat. Keep everything else the same."},
    {"key": "sketch", "label": "Change the style", "base": "landscape",
     "text": "Turn this photograph into a pencil sketch."},
    {"key": "remove", "label": "Take something out", "base": "details",
     "text": "Remove the cat from the bicycle basket. Keep everything else the same."},
]
BASE_MODEL = "qwen-pro"   # the edits start from this model's pictures, so every editor gets the same one


def _webp(data: bytes) -> tuple[bytes, tuple[int, int]]:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    full = im.size
    im.thumbnail((SIZE, SIZE), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=82, method=5)
    return out.getvalue(), full


def _png_uri(data: bytes) -> str:
    out = io.BytesIO()
    Image.open(io.BytesIO(data)).convert("RGB").save(out, "PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode()


async def _paid(model_id: str, mode: str, prompt: str, source_png: bytes | None, book: dict) -> tuple[bytes, float, str]:
    """One image from the cheapest service that runs this model, through the studio's own clients.
    Edits go to Runware, which takes the picture inline."""
    m = studio.MODELS[model_id]
    shape, _, _, steps = studio._settings(m, mode, {"shape": "square"})
    options = [o for o in studio.candidates(model_id, mode, shape, None, None, bool(source_png), steps, book)
               if o["usable"] and o["service"] in studio.IMAGE_MAKERS and (not source_png or o["service"] == "runware")]
    if not options:
        raise RuntimeError(f"no service for {model_id} {mode}")
    o = options[0]
    source = {"key": None, "data_uri": _png_uri(source_png)} if source_png else None
    made = await studio.IMAGE_MAKERS[o["service"]](o["route"], prompt, shape, steps, source)
    cost = made.get("cost") if isinstance(made.get("cost"), (int, float)) and made["cost"] > 0 else o["usd"]
    return made["data"], round(cost, 4), o["service"]


async def _gpu(workflow: dict, label: str) -> bytes:
    pid = await comfy.queue(workflow)
    while True:
        await asyncio.sleep(3)
        state, files, reason, _ = await comfy.status(pid)
        if state == "failed":
            raise RuntimeError(f"{label}: {reason}")
        if state == "done":
            break
    data = await svc._download(comfy.file_url(files[0]), svc.MAX_VIDEO, comfy.headers())
    await comfy.forget(pid)
    return data


async def main(only: set[str], skip_gpu: bool, wanted: set[str] = frozenset(), no_edits: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "samples.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest |= {"prompts": [p for k in STRIP for p in PROMPTS if p["key"] == k] + [p for p in PROMPTS if p["key"] not in STRIP],
                 "strip": STRIP, "edits": EDITS, "base_model": BASE_MODEL, "made": time.strftime("%Y-%m-%d")}
    results = manifest.setdefault("results", {})
    book = await prices.load()
    creators = [k for k, m in studio.MODELS.items() if "create" in m["does"]]
    editors = [k for k, m in studio.MODELS.items() if "edit" in m["does"]]
    gpu_models = {k for k, m in studio.MODELS.items() if "baseten" in m["routes"] and "video" not in m["does"]}
    if only:
        creators, editors = [k for k in creators if k in only], [k for k in editors if k in only]
    if no_edits:
        editors = []
    prompts = [p for p in PROMPTS if not wanted or p["key"] in wanted]
    edits = [e for e in EDITS if not wanted or e["key"] in wanted]
    if skip_gpu:
        creators, editors = [k for k in creators if k not in gpu_models], [k for k in editors if k not in gpu_models]
    if (set(creators) | set(editors)) & gpu_models:
        await comfy.wake()
        while not await comfy.ready():
            await asyncio.sleep(10)
        print("GPU ready", flush=True)

    bases: dict[str, bytes] = {}
    spent = 0.0

    async def save(model_id: str, key: str, data: bytes, seconds: float, usd: float, service: str) -> None:
        nonlocal spent
        small, full = _webp(data)
        path = OUT / model_id / f"{key}.webp"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(small)
        results.setdefault(model_id, {})[key] = {"file": f"{model_id}/{key}.webp", "seconds": round(seconds, 1),
                                                 "usd": usd, "service": service, "size": list(full)}
        spent += usd
        print(f"{model_id:12} {key:12} {seconds:5.1f} s  ${usd:.4f}  {service}", flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    for model_id in creators:
        for p in prompts:
            t = time.monotonic()
            try:
                if model_id in gpu_models:
                    w, h = studio.MODELS[model_id]["routes"]["baseten"]["sizes"]["square"]
                    seed = random.randrange(2 ** 48)
                    wf = (comfy.h3_still(p["text"], w, h, studio.MODELS[model_id]["steps"], seed) if model_id == "h3-still"
                          else comfy.ph3_image(p["text"], w, h, seed))
                    data = await _gpu(wf, f"{model_id} {p['key']}")
                    took = time.monotonic() - t
                    usd = studio.route_cost(model_id, "baseten", "square", studio.MODELS[model_id].get("steps"), None, None, book)
                    service = "baseten"
                else:
                    data, usd, service = await _paid(model_id, "create", p["text"], None, book)
                    took = time.monotonic() - t
            except Exception as e:  # noqa: BLE001  one refused or failed image leaves a gap, not a stop
                print(f"{model_id:12} {p['key']:12} FAILED {type(e).__name__}: {str(e)[:160]}", flush=True)
                continue
            if model_id == BASE_MODEL:
                bases[p["key"]] = data
            await save(model_id, p["key"], data, took, usd, service)

    if editors and not bases:
        for e in edits:   # an earlier run's base pictures, when this run made none
            path = OUT / BASE_MODEL / f"{e['base']}.webp"
            if path.exists():
                bases[e["base"]] = path.read_bytes()
    for model_id in editors:
        for e in edits:
            base = bases.get(e["base"])
            if not base:
                continue
            t = time.monotonic()
            try:
                if model_id in gpu_models:   # scaled to about 4 megapixels first, as the studio does
                    size = Image.open(io.BytesIO(base)).size
                    name = await comfy.upload(studio._scaled_png(base, comfy.ph3_size(*size)), f"sample-{e['base']}.png")
                    wf = comfy.ph3_image(e["text"], 0, 0, random.randrange(2 ** 48), [name])
                    data = await _gpu(wf, f"{model_id} {e['key']}")
                    took = time.monotonic() - t
                    usd, service = studio.route_cost(model_id, "baseten", "square", None, None, None, book), "baseten"
                else:
                    data, usd, service = await _paid(model_id, "edit", e["text"], base, book)
                    took = time.monotonic() - t
            except Exception as err:  # noqa: BLE001
                print(f"{model_id:12} {e['key']:12} FAILED {type(err).__name__}: {str(err)[:160]}", flush=True)
                continue
            await save(model_id, "edit-" + e["key"], data, took, usd, service)
    print(f"spent about ${spent:.2f}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="comma-separated model ids")
    ap.add_argument("--skip-gpu", action="store_true", help="leave out the models that run on the maker's GPU")
    ap.add_argument("--prompts", default="", help="comma-separated prompt and edit keys (default: all)")
    ap.add_argument("--no-edits", action="store_true", help="make only pictures from words")
    a = ap.parse_args()
    asyncio.run(main({x for x in a.only.split(",") if x}, a.skip_gpu, {x for x in a.prompts.split(",") if x}, a.no_edits))
