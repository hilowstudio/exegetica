"""
Image Studio: images and short videos, each run on whichever service is cheapest that day, for
the maker's login only for now (docs/decisions/0017).

Its shape follows what tbio.ai's image tool turned out to do (studied 2026-11-02), keeping the
parts that worked and fixing the one that did not:

- Every model is one entry in MODELS: what it can do (create, edit, video), what it accepts, and
  the services that run it (`routes`). Each route says how that service is asked, what it
  listed as its price, and where its live price is read (webapp/studio_prices.py).
- Each morning the studio reads every service's price into a book in R2. A run goes to the
  cheapest service that is set up, not turned away today, and able to make what was asked. If
  that service turns the account away (no credit, a refused key), the run moves to the next.
  The maker can also pick a service himself.
- "Rewrite my prompt" expands a short request into a detailed one with one cheap text-model call
  before drawing, as tbio's text model did ("an apple on a table" became about 700 characters).
  The rewritten prompt is shown, never hidden, so a model's own unseen prompt expansion is
  switched off wherever its service allows.
- tbio kept images at public, unsigned links. Here each service is asked to keep as little as it
  can (webapp/studio_services.py), and everything lands in the app's private R2 bucket, served
  only to the signed-in owner. Deleting an item deletes it from R2; deleting the account deletes
  the whole folder.
- An image comes back in one request, except on the maker's own GPU, which may first have to wake.
  A video takes minutes, so it (and a GPU still) is saved as pending with the service's job id. The server follows it until the service is done, and the page asks /check
  too, which picks the job up again after a restart. Then the file is copied into R2 like an
  image.
- Who may use it is decided on the server (auth.is_admin), never by anything the browser sends.

Nothing here runs for students or teachers until the maker widens `may_use`.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import os
import io
import re
import secrets
import time
import uuid

from starlette.responses import HTMLResponse, JSONResponse, Response

from webapp import auth, metrics, r2
from webapp import studio_comfy as comfy
from webapp import studio_prices as prices
from webapp import studio_services as svc
from webapp.studio_services import (MAX_IMAGE, MAX_VIDEO, SERVICES, AccountError, Refused,  # noqa: F401
                                    StudioError, _download, _short)

logger = logging.getLogger("study-bible-web.studio")

REWRITE_MODEL = "claude-haiku-5-5"

# Image sizes for every image model; a route with its own `sizes` maps each shape to one it accepts.
SHAPES = {
    "square": {"label": "Square", "size": (1024, 1024), "ratio": "1:1"},
    "portrait": {"label": "Portrait", "size": (768, 1024), "ratio": "3:4"},
    "landscape": {"label": "Landscape", "size": (1024, 768), "ratio": "4:3"},
    "tall": {"label": "Tall", "size": (576, 1024), "ratio": "9:16"},
    "wide": {"label": "Wide", "size": (1024, 576), "ratio": "16:9"},
}
KONTEXT_SIZES = {"square": (1024, 1024), "portrait": (880, 1184), "landscape": (1184, 880),
                 "tall": (752, 1392), "wide": (1392, 752)}   # the only sizes Kontext takes on Runware
VIDEO_RATIOS = {"wide": "16:9", "landscape": "4:3", "square": "1:1", "portrait": "3:4", "tall": "9:16"}
H3_SIZES = {"wide": (1344, 768), "landscape": (1024, 768), "square": (768, 768),
            "portrait": (768, 1024), "tall": (768, 1344)}   # MiniMax H3's 768p sizes on Runware
H3_STILL_SIZES = {"square": (1024, 1024), "portrait": (864, 1152), "landscape": (1152, 864),
                  "tall": (768, 1344), "wide": (1344, 768)}   # about a megapixel, sides on H3's 32-pixel grid

# A route's `price` is what the service listed when the route was written (2026-11-03): `unit` is
# per image, per megapixel (`mp`), per 1024x1024 image scaled by size and steps (`1k`, Runware's
# measured runs at `ref_steps`), or per second, with `usd_audio` where sound costs more. The book
# replaces `usd` and `usd_audio` with each day's reading of `source`.
# A model's `audio` is the sound checkbox's default, or None when it offers no choice. A route's
# `audio_at` is where the choice goes in that service's request; `audio: "always"` marks a route
# that makes sound with no way to turn it off. `quiet` turns off the model's own hidden prompt
# expansion. A video route's `sizes` are pixel sizes on Runware, ratios or pixel strings
# elsewhere. fal and WaveSpeed run a video from a first frame at a second endpoint
# (`model_frame`), reading the image from `frame_key`; `frame_sets_shape` is False where the
# frame endpoint still wants a shape.
MODELS = {
    # ---------------------------------------------------------------- images
    "flux-schnell": {
        "does": ("create",), "label": "FLUX schnell", "note": "Fast. A few seconds.", "steps": 4,
        "routes": {
            "fal": {"model": "fal-ai/flux/schnell", "price": {"unit": "mp", "usd": 0.003},
                    "source": {"fal": "fal-ai/flux/schnell"}},
            "runware": {"model": "runware:100@1", "price": {"unit": "1k", "usd": 0.0013, "ref_steps": 4},
                        "source": {"runware": "bfl-flux-1-schnell", "measured": "1024x1024 · 4 steps"}},
        }},
    "flux-dev": {
        "does": ("create",), "label": "FLUX dev", "note": "Quality. Slower, with a steps slider.",
        "steps": 28, "max_steps": 50,
        "routes": {
            "fal": {"model": "fal-ai/flux/dev", "price": {"unit": "mp", "usd": 0.025},
                    "source": {"fal": "fal-ai/flux/dev"}},
            "runware": {"model": "runware:101@1", "price": {"unit": "1k", "usd": 0.0038, "ref_steps": 28},
                        "source": {"runware": "bfl-flux-1-dev", "measured": "1024x1024 · 28 steps"}},
        }},
    "flux-kontext": {
        "does": ("edit",), "label": "FLUX Kontext", "note": "Changes an image from an instruction.",
        "routes": {
            "fal": {"model": "fal-ai/flux-pro/kontext", "price": {"unit": "image", "usd": 0.04},
                    "source": {"fal": "fal-ai/flux-pro/kontext"}},
            "runware": {"model": "bfl:3@1", "sizes": KONTEXT_SIZES, "price": {"unit": "image", "usd": 0.04},
                        "quiet": {"providerSettings": {"bfl": {"promptUpsampling": False, "safetyTolerance": 2}}},
                        "source": {"runware": "bfl-flux-1-kontext-pro", "rate": ""}},
        }},
    "flux2-klein": {
        "does": ("create", "edit"), "label": "FLUX.2 klein 9B", "note": "Fast and very cheap. Also edits.", "steps": 4,
        "routes": {
            "runware": {"model": "runware:400@2", "price": {"unit": "1k", "usd": 0.00078, "ref_steps": 4},
                        "source": {"runware": "bfl-flux-2-klein-9b", "measured": "1024x1024 · 4 steps"}},
        }},
    "qwen-turbo": {
        "does": ("create", "edit"), "label": "Qwen-Image 2.1 Turbo",
        "note": "The model behind tbio's \"Image 2\", quick version. Also edits.",
        "routes": {
            "runware": {"model": "alibaba:qwen-image@2.1-turbo", "price": {"unit": "image", "usd": 0.0141},
                        "quiet": {"settings": {"promptExtend": False}},
                        "source": {"runware": "alibaba-qwen-image-2-1-turbo", "rate": ""}},
        }},
    "qwen-pro": {
        "does": ("create", "edit"), "label": "Qwen-Image 2.1 Pro",
        "note": "The model behind tbio's \"Image 2\" at full quality. About a minute.",
        "routes": {
            "runware": {"model": "alibaba:qwen-image@2.1-pro", "price": {"unit": "image", "usd": 0.075},
                        "quiet": {"settings": {"promptExtend": False}},
                        "source": {"runware": "alibaba-qwen-image-2-1-pro", "rate": ""}},
        }},
    "h3-still": {
        "does": ("create",), "label": "MiniMax H3 still",
        "note": "One frame from the H3 video model, drawn on your own GPU. A minute or two more when the GPU "
                "is asleep.",
        "steps": 30, "max_steps": 50,
        "routes": {
            # The maker's GPU (webapp/studio_comfy.py) is this model's only service, so it runs without
            # being picked. Priced per 1024x1024 image at 30 steps from the time a warm GPU took to
            # render and return one, measured 2026-11-04.
            "baseten": {"model": "comfyui/minimax-h3-still", "sizes": H3_STILL_SIZES,
                        "price": {"unit": "1k", "usd": 0.018, "ref_steps": 30},
                        "source": {"usd_hour": 6.50, "render_seconds": 10, "clip_seconds": 1}},
        }},
    # ---------------------------------------------------------------- video
    "hunyuan-video": {
        "does": ("video",), "label": "Hunyuan Video 1.5",
        "note": "Tencent's video model, from the makers of tbio's engine. 480p, no sound.",
        "seconds": (5, 8), "sizes": ("wide", "tall"), "audio": None, "start_image": True,
        "routes": {
            "fal": {"model": "fal-ai/hunyuan-video-v1.5/text-to-video",
                    "model_frame": "fal-ai/hunyuan-video-v1.5/image-to-video", "frame_key": "image_url",
                    "frame_sets_shape": False, "seconds": (5,), "duration_key": None,
                    "sizes": {"wide": "16:9", "tall": "9:16"},
                    "extra": {"resolution": "480p", "num_frames": 121, "enable_prompt_expansion": False,
                              "enable_safety_checker": True},
                    "price": {"unit": "second", "usd": 0.075},
                    "source": {"fal": "fal-ai/hunyuan-video-v1.5/text-to-video"}},
            "wavespeed": {"model": "wavespeed-ai/hunyuan-video-1.5/text-to-video",
                          "model_frame": "wavespeed-ai/hunyuan-video-1.5/image-to-video", "frame_key": "image",
                          "frame_extra": {"resolution": "480p"}, "sizes": {"wide": "832*480", "tall": "480*832"},
                          "price": {"unit": "second", "usd": 0.02},
                          "source": {"wavespeed": "wavespeed-ai/hunyuan-video-1.5/text-to-video", "per": 5,
                                     "inputs": {"prompt": "price check", "size": "832*480", "duration": 5}}},
        }},
    "wan-3": {
        "does": ("video",), "label": "Wan 3.0", "note": "Alibaba's video model, 720p.",
        "seconds": (5, 10), "sizes": ("wide", "landscape", "square", "portrait", "tall"), "audio": True,
        "start_image": True,
        "routes": {
            "fal": {"model": "alibaba/wan-3.0/text-to-video", "model_frame": "alibaba/wan-3.0/image-to-video",
                    "frame_key": "start_image_url", "sizes": VIDEO_RATIOS, "audio_at": ("audio",),
                    "extra": {"resolution": "720p", "enable_safety_checker": True, "enable_prompt_expansion": False},
                    "price": {"unit": "second", "usd": 0.10},
                    "source": {"fal": "alibaba/wan-3.0/text-to-video", "factor": 2}},   # fal's base rate is 480p
            "runware": {"model": "alibaba:wan@3.0", "resolution": "720p",
                        "sizes": {"wide": (1280, 720), "landscape": (1104, 832), "square": (960, 960),
                                  "portrait": (832, 1104), "tall": (720, 1280)},
                        "audio_at": ("settings", "audio"), "quiet": {"settings": {"promptExtend": False}},
                        "price": {"unit": "second", "usd": 0.10},
                        "source": {"runware": "alibaba-wan3-0", "rate": "720p"}},
            # Replicate's Wan 3 has no sound switch, and Wan 3.0 makes sound unless told not to.
            "replicate": {"model": "alibaba/wan-3", "frame_key": "image", "sizes": VIDEO_RATIOS, "audio": "always",
                          "extra": {"resolution": "720p", "enable_prompt_expansion": False},
                          "price": {"unit": "second", "usd": 0.07},
                          "source": {"replicate": "alibaba/wan-3", "criteria": {"target resolution": "720p"}}},
        }},
    "gemini-omni": {
        "does": ("video",), "label": "Gemini Omni Flash 1.1", "note": "Google's video model, 720p.",
        "seconds": (4, 6, 8), "sizes": ("wide", "tall"), "audio": None, "start_image": True,
        "routes": {
            "fal": {"model": "google/gemini-omni-flash/v1.1/text-to-video",
                    "model_frame": "google/gemini-omni-flash/v1.1/image-to-video", "frame_key": "image_url",
                    "frame_sets_shape": False, "sizes": {"wide": "16:9", "tall": "9:16"},
                    "extra": {"resolution": "720p"}, "price": {"unit": "second", "usd": 0.10},
                    "source": {"fal": "google/gemini-omni-flash/v1.1/text-to-video", "factor": 10 / 3}},  # base is 360p
        }},
    "kling-4": {
        "does": ("video",), "label": "Kling 4.0", "note": "720p, no sound.",
        "seconds": (5, 10), "sizes": ("wide", "square", "tall"), "audio": None, "start_image": True,
        "routes": {
            "fal": {"model": "kling/v4/text-to-video", "model_frame": "kling/v4/image-to-video",
                    "frame_key": "start_image_url", "sizes": {"wide": "16:9", "square": "1:1", "tall": "9:16"},
                    "extra": {"resolution": "720p"}, "price": {"unit": "second", "usd": 0.157},
                    "source": {"fal": "kling/v4/text-to-video"}},
            "runware": {"model": "klingai:kling-video@4.0", "resolution": "720p",
                        "sizes": {"wide": (1280, 720), "square": (940, 940), "tall": (720, 1280)},
                        "price": {"unit": "second", "usd": 0.157},
                        "source": {"runware": "klingai-video-4-0", "rate": "720p · No video input"}},
        }},
    "h3": {
        "does": ("video",), "label": "MiniMax H3",
        "note": "Among the best-ranked video models, open or closed. 768p with sound. Leave \"Rewrite my words\" on, "
                "since this model depends on a detailed prompt. 15 seconds and a last frame run on your own GPU only.",
        "seconds": (5, 10, 15), "sizes": ("wide", "landscape", "square", "portrait", "tall"), "audio": None,
        "start_image": True, "end_image": True,
        "routes": {
            "fal": {"model": "minimax/h3/text-to-video", "model_frame": "minimax/h3/image-to-video",
                    "frame_key": "image_url", "sizes": VIDEO_RATIOS, "seconds": (5, 10),
                    "extra": {"resolution": "768P", "prompt_expansion_mode": "disabled", "enable_safety_checker": True},
                    "price": {"unit": "second", "usd": 0.06},
                    "source": {"fal": "minimax/h3/text-to-video", "factor": 1.2}},   # fal's base rate is 480p
            "runware": {"model": "minimax:h3@0", "resolution": "768p", "sizes": H3_SIZES, "seconds": (5, 10),
                        "quiet": {"settings": {"promptExpansion": "disabled"}},
                        "price": {"unit": "second", "usd": 0.08},
                        "source": {"runware": "minimax-h3", "rate": "768p"}},
            # The maker's own GPU (baseten/comfyui, webapp/studio_comfy.py). `manual`: it runs only
            # when picked, since waking it adds a minute or two and its idle minutes are not in this
            # price. The price is the H100's hourly rate times the render time on a warm GPU, measured
            # 2026-11-04 for a 5-second clip. Longer clips take more per second.
            "baseten": {"model": "comfyui/minimax-h3-fl2va", "sizes": H3_SIZES, "manual": True, "end_image": True,
                        "price": {"unit": "second", "usd": 0.03},
                        "source": {"usd_hour": 6.50, "render_seconds": 80, "clip_seconds": 5}},
        }},
    "h3-ref": {
        "does": ("video",), "label": "MiniMax H3 from pictures",
        "note": "Your own GPU only. Give it up to nine pictures of people, things or places, and name them in your "
                "words as Picture 1, Picture 2 and on. You can also set a first frame, a last frame, and pictures "
                "the video passes through at set seconds. 768p with sound, about three minutes for 5 seconds.",
        "seconds": (5, 10, 15), "sizes": ("wide", "landscape", "square", "portrait", "tall"), "audio": None,
        "start_image": True, "end_image": True, "refs": comfy.H3_MAX_REFS, "pins": 3,
        "routes": {
            # The reference model at its full 20 steps: 188 seconds for a 5-second clip with two pictures
            # and one pinned, measured 2026-11-04 on a GPU that had not yet loaded this model.
            "baseten": {"model": "comfyui/minimax-h3-ref2va", "sizes": H3_SIZES, "end_image": True,
                        "frame_sets_shape": False,
                        "price": {"unit": "second", "usd": 0.07},
                        "source": {"usd_hour": 6.50, "render_seconds": 188, "clip_seconds": 5}},
        }},
    "h3-max-turbo": {
        "does": ("video",), "label": "MiniMax H3 Max Turbo", "note": "The cheapest video here. A faster tuning of H3, 768p.",
        "seconds": (5, 10), "sizes": ("wide", "landscape", "square", "portrait", "tall"), "audio": None,
        "start_image": True,
        "routes": {
            "fal": {"model": "minimax/h3-max-turbo/text-to-video", "model_frame": "minimax/h3-max-turbo/image-to-video",
                    "frame_key": "image_url", "sizes": VIDEO_RATIOS,
                    "extra": {"resolution": "768P", "prompt_expansion_mode": "disabled", "enable_safety_checker": True},
                    "price": {"unit": "second", "usd": 0.04},
                    "source": {"fal": "minimax/h3-max-turbo/text-to-video", "factor": 1.6}},   # base rate is 480p
            "runware": {"model": "minimax:h3@max-turbo", "resolution": "768p", "sizes": H3_SIZES,
                        "quiet": {"settings": {"promptExpansion": "disabled"}},
                        "price": {"unit": "second", "usd": 0.04},
                        "source": {"runware": "minimax-h3-max-turbo", "rate": "768p"}},
        }},
    "kling-3": {
        "does": ("video",), "label": "Kling 3.0 Standard", "note": "720p. Sound costs half again as much.",
        "seconds": (5, 10), "sizes": ("wide", "square", "tall"), "audio": False, "start_image": True,
        "routes": {
            "runware": {"model": "klingai:kling-video@3-standard",
                        "sizes": {"wide": (1280, 720), "square": (960, 960), "tall": (720, 1280)},
                        "audio_at": ("providerSettings", "klingai", "sound"),
                        "price": {"unit": "second", "usd": 0.084, "usd_audio": 0.126},
                        "source": {"runware": "klingai-video-3-0-standard", "rate": "720p · no audio",
                                   "rate_audio": "720p · audio"}},
        }},
    "seedance-fast": {
        "does": ("video",), "label": "Seedance 2.0 Fast", "note": "720p. Sound at no extra cost.",
        "seconds": (5, 10), "sizes": ("wide", "landscape", "square", "portrait", "tall"), "audio": True,
        "start_image": True,
        "routes": {
            "runware": {"model": "bytedance:seedance@2.0-fast", "resolution": "720p",
                        "sizes": {"wide": (1280, 720), "landscape": (1112, 834), "square": (960, 960),
                                  "portrait": (834, 1112), "tall": (720, 1280)},
                        "audio_at": ("settings", "audio"), "price": {"unit": "second", "usd": 0.13},
                        "source": {"runware": "bytedance-seedance-2-0-fast", "rate": "720p"}},
        }},
    "veo-fast": {
        "does": ("video",), "label": "Veo 3.1 Fast",
        "note": "Google's Veo, 720p. Google always rewrites the prompt for this one.",
        "seconds": (4, 6, 8), "sizes": ("wide", "tall"), "audio": True, "start_image": True,
        "routes": {
            "runware": {"model": "google:3@3", "resolution": "720p", "sizes": {"wide": (1280, 720), "tall": (720, 1280)},
                        "audio_at": ("providerSettings", "google", "generateAudio"),
                        "price": {"unit": "second", "usd": 0.10, "usd_audio": 0.15},
                        "source": {"runware": "google-veo-3-1-fast", "rate": "720p / 1080p",
                                   "rate_audio": "720p / 1080p · with audio"}},
        }},
}
DEFAULTS = {"create": "flux-schnell", "edit": "flux-kontext", "video": "h3-max-turbo"}

MAX_PROMPT = 2000
MAX_UPLOAD = 8 * 1024 * 1024
SOURCE_SECONDS = 3600          # how long a queued video job may read its first frame from R2
EDIT_SAFETY = "2"              # Kontext's default on fal: 1 is strictest, 5 most permissive
RUNWARE_VIDEO_TTL = 86400      # Runware drops a video's link after a day, time enough to pick it up
RUNWARE_IMAGE_WAIT = 180       # an image still running after Runware's 120-second hold is polled this long
DOWN_FOR = 6 * 3600            # a service that turned the account away is skipped this long
FOLLOW = True                  # the server follows each video to the end, page open or not
FOLLOW_EVERY = 10
FOLLOW_FOR = 45 * 60
AUTO_REFRESH = True            # a stale price book is refreshed on the next visit
INDEX_LIMIT = 500

REWRITE = {
    "create": (
        "You turn a short image request into one detailed prompt for an image model. Keep the subject "
        "and intent exactly as asked. Add concrete detail: the setting, composition and framing, "
        "lighting, color palette, medium or style, and mood. Add no words, letters, logos, or "
        "signatures to the picture unless the request asks for them, and no people it does not "
        "mention. Write one paragraph under 120 words. Reply with the prompt only."),
    "edit": (
        "You turn a short request to change an image into one precise instruction for an image-editing "
        "model. Say exactly what to change, and say that everything else stays as it is. One or two "
        "sentences. Reply with the instruction only."),
    "video": (
        "You turn a short video request into one detailed prompt for a video model. Keep the subject "
        "and intent exactly as asked. Describe what happens over the few seconds of the clip: the "
        "action and movement, where the camera is and how it moves, the setting, lighting, and style, "
        "and the sound if it fits. Add no words, letters, logos, or people the request does not "
        "mention. Write one paragraph under 120 words. Reply with the prompt only."),
    "animate": (
        "You turn a short request to animate a still image into one prompt for a video model that "
        "starts from that image. Describe the motion to add: what moves and how, and how the camera "
        "moves. Say that the scene and its subjects stay as they are in the image. One to three "
        "sentences. Reply with the prompt only."),
    "reference": (
        "You turn a short video request into one detailed prompt for a video model that is shown "
        "reference pictures named Picture 1, Picture 2 and on. Keep each such name exactly as written "
        "wherever the request uses it, and keep the subject and intent exactly as asked. Describe what "
        "happens over the few seconds of the clip: the action and movement, where the camera is and "
        "how it moves, the setting, lighting, and style, and the sound if it fits. Add no words, "
        "letters, logos, or people the request does not mention. Write one paragraph under 120 words. "
        "Reply with the prompt only."),
}

_DATA_URL = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,(.+)$", re.S)
_PICTURE = re.compile(r"<?\b[Pp]icture\s+([1-9])\b>?")   # "Picture 2" becomes H3's <Picture 2>
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "video/mp4": "mp4"}
_TYPE = {v: k for k, v in _EXT.items()}
_ID = re.compile(r"^[0-9a-f]{32}$")
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
_locks: dict[str, asyncio.Lock] = {}
_job_locks: dict[str, asyncio.Lock] = {}
_down: dict[str, tuple[float, str]] = {}


def may_use(user) -> bool:
    """The maker's login only, for now: the library admin allowlist (LIBRARY_ADMIN_EMAILS)."""
    return auth.is_admin(user)


# -------------------------------------------------------------------------------------------
# Choosing a service: today's price for each route that can make what was asked
# -------------------------------------------------------------------------------------------

def _mark_down(service: str, why: str) -> None:
    _down[service] = (time.monotonic() + DOWN_FOR, why)


def _is_down(service: str) -> str | None:
    hit = _down.get(service)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    _down.pop(service, None)
    return None


def _image_size(route: dict, shape: str) -> tuple[int, int]:
    return (route.get("sizes") or {}).get(shape) or SHAPES[shape]["size"]


def route_cost(model_id: str, service: str, shape: str = "square", steps: int | None = None,
               seconds: int | None = None, audio: bool | None = False, book: dict | None = None) -> float:
    """Dollars for one image or video on one service, before the prompt rewrite."""
    m, route = MODELS[model_id], MODELS[model_id]["routes"][service]
    price = prices.current(book or {}, f"{model_id}:{service}", route["price"])
    unit = route["price"]["unit"]
    if unit == "second":
        rate = price.get("usd_audio") if audio and price.get("usd_audio") else price["usd"]
        return round(rate * (seconds or m["seconds"][0]), 4)
    w, h = _image_size(route, shape)
    if unit == "mp":
        usd = price["usd"] * w * h / 1_000_000
    elif unit == "1k":
        usd = price["usd"] * (w * h / 1024 ** 2) * ((steps or m["steps"]) / route["price"]["ref_steps"])
    else:
        usd = price["usd"]
    return round(usd, 4)


def _fits(m: dict, route: dict, mode: str, shape: str, seconds: int | None, audio: bool | None,
          framed: bool, ending: bool = False) -> str | None:
    """Why a route cannot make what was asked, or None if it can."""
    if mode != "video":
        return None if mode in route.get("does", m["does"]) else "edits on another service only"
    if framed and not route.get("start_image", m.get("start_image")):
        return "starts from words only"
    if ending and not route.get("end_image"):
        return "takes no last frame"
    if not (framed and route.get("frame_sets_shape", True)) and shape not in route["sizes"]:
        return "makes other shapes"
    if seconds not in route.get("seconds", m["seconds"]):
        return "makes other lengths"
    if audio is False and route.get("audio") == "always":
        return "always adds sound"
    return None


def candidates(model_id: str, mode: str, shape: str, seconds: int | None, audio: bool | None,
               framed: bool, steps: int | None, book: dict, ending: bool = False) -> list[dict]:
    """Every service for a model, cheapest first, each with its price and whether it can run."""
    m = MODELS[model_id]
    out = []
    for service, route in m["routes"].items():
        why = (None if svc._key(service) else "not set up") or _is_down(service) \
            or _fits(m, route, mode, shape, seconds, audio, framed, ending)
        out.append({"service": service, "label": SERVICES[service]["label"], "route": route, "usable": why is None,
                    "reason": why, "frame_sets_shape": route.get("frame_sets_shape", True),
                    "auto": not route.get("manual"),
                    "usd": route_cost(model_id, service, shape, steps, seconds, audio, book)})
    return sorted(out, key=lambda c: (not c["usable"], c["usd"]))


def _runnable(options: list[dict], pinned: str | None) -> list[dict]:
    """The services a run may use: the pinned one, or else every usable one that is not manual."""
    return [o for o in options if o["usable"] and (o["service"] == pinned if pinned else o["auto"])]


def estimate(model_id: str, shape: str = "square", steps: int | None = None, seconds: int | None = None,
             audio: bool | None = False, service: str | None = None, book: dict | None = None) -> float:
    """Dollars on one service, or on the cheapest one that lists the model."""
    services = [service] if service else list(MODELS[model_id]["routes"])
    return min(route_cost(model_id, s, shape, steps, seconds, audio, book) for s in services)


def price_routes() -> dict[str, tuple[str, dict]]:
    return {f"{mid}:{service}": (service, route) for mid, m in MODELS.items() for service, route in m["routes"].items()}


async def refresh_prices() -> dict:
    """Read every service's price for today (also run each morning by Inngest, studio-prices)."""
    return await prices.refresh(price_routes())


_refreshing: set[asyncio.Task] = set()


def _refresh_done(task: asyncio.Task) -> None:
    _refreshing.discard(task)
    if not task.cancelled() and task.exception():
        logger.warning("studio price refresh failed: %r", task.exception())


def _refresh_soon() -> None:
    if AUTO_REFRESH and not _refreshing:
        task = asyncio.get_running_loop().create_task(refresh_prices())
        _refreshing.add(task)
        task.add_done_callback(_refresh_done)


# -------------------------------------------------------------------------------------------
# Storage: one private folder per user in R2, with an index of what is in it
# -------------------------------------------------------------------------------------------

def _folder(user) -> str:
    return f"studio/{user['id']}/"


async def _read_index(user) -> list[dict]:
    raw = await r2.get_bytes_async(_folder(user) + "index.json")
    try:
        return json.loads(raw) if raw else []
    except ValueError:
        logger.warning("studio index unreadable; starting a new one")
        return []


async def _write_index(user, items: list[dict]) -> None:
    await r2.put_bytes_async(_folder(user) + "index.json", json.dumps(items[:INDEX_LIMIT]).encode(),
                             "application/json")


def _lock(user) -> asyncio.Lock:
    return _locks.setdefault(user["id"], asyncio.Lock())


async def _save_item(user, item: dict, new: bool = False) -> bool:
    """Put a new entry at the top of the index, or replace an existing one where it is. False if
    the entry is gone, as when a video is deleted while it is being fetched."""
    async with _lock(user):
        items = await _read_index(user)
        at = next((n for n, i in enumerate(items) if i["id"] == item["id"]), None)
        if new:
            items.insert(0, item)
        elif at is None:
            return False
        else:
            items[at] = item
        await _write_index(user, items)
        return True


# -------------------------------------------------------------------------------------------
# The prompt rewrite
# -------------------------------------------------------------------------------------------

async def rewrite(prompt: str, purpose: str) -> tuple[str, float]:
    """(the rewritten prompt, its estimated cost). One short call to a small model."""
    from anthropic import AsyncAnthropic

    from webapp.providers import _usd

    client = AsyncAnthropic()
    msg = await client.messages.create(
        model=REWRITE_MODEL, max_tokens=400, system=REWRITE[purpose],
        messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    usage = {"input": msg.usage.input_tokens, "output": msg.usage.output_tokens, "cache_read": 0, "cache_write": 0}
    return (text or prompt), _usd(REWRITE_MODEL, usage)


def _nest(task: dict, path: tuple, value) -> None:
    """Set task[a][b][c] = value, making the inner objects as needed."""
    for part in path[:-1]:
        task = task.setdefault(part, {})
    task[path[-1]] = value


def _merge(task: dict, extra: dict) -> None:
    for k, v in extra.items():
        if isinstance(v, dict):
            _merge(task.setdefault(k, {}), v)
        else:
            task[k] = v


# -------------------------------------------------------------------------------------------
# One image, on the chosen service
# -------------------------------------------------------------------------------------------

async def _image_fal(route: dict, prompt: str, shape: str, steps: int | None, source: dict | None) -> dict:
    if source:
        body = {"prompt": prompt, "image_url": r2.presign_get(source["key"], svc.FAL_KEEP_SECONDS),
                "aspect_ratio": SHAPES[shape]["ratio"], "safety_tolerance": EDIT_SAFETY,
                "output_format": "jpeg", "num_images": 1}
    else:
        w, h = _image_size(route, shape)
        body = {"prompt": prompt, "image_size": {"width": w, "height": h}, "num_inference_steps": steps,
                "num_images": 1, "enable_safety_checker": True, "output_format": "jpeg"}
    result = await svc.fal_run(route["model"], body)
    images = result.get("images") or []
    if not images:
        raise StudioError("The image service returned no image.", 502)
    if any(result.get("has_nsfw_concepts") or []):
        raise Refused()
    image = images[0]
    return {"data": await _download(image["url"]), "content_type": image.get("content_type") or "image/jpeg",
            "width": image.get("width"), "height": image.get("height"), "seed": result.get("seed"), "cost": None}


async def _image_runware(route: dict, prompt: str, shape: str, steps: int | None, source: dict | None) -> dict:
    """Runware returns the image inline (base64), so it never hosts a copy to expire."""
    w, h = _image_size(route, shape)
    task_uuid = str(uuid.uuid4())
    task = {"taskType": "imageInference", "taskUUID": task_uuid, "model": route["model"], "positivePrompt": prompt,
            "width": w, "height": h, "outputType": "base64Data", "outputFormat": "JPG", "includeCost": True,
            "safety": {"checkContent": True}}
    if steps and route["price"].get("ref_steps"):
        task["steps"] = steps
    if source:
        task["inputs"] = {"referenceImages": [source["data_uri"]]}
    _merge(task, route.get("quiet") or {})
    row, err = svc.runware_result(await svc.runware_call([task]), task_uuid)
    deadline = time.monotonic() + RUNWARE_IMAGE_WAIT
    while not err and (not row or row.get("status") == "processing") and time.monotonic() < deadline:
        await asyncio.sleep(3)
        row, err = svc.runware_result(await svc.runware_call([{"taskType": "getResponse", "taskUUID": task_uuid}]),
                                      task_uuid, strict=True)
    if err:
        raise StudioError(f"Runware could not make this image: {_short(err.get('message')) or 'no reason given'}.", 502)
    if not row or not row.get("imageBase64Data"):
        raise StudioError("Runware took too long and returned no image.", 502)
    if row.get("NSFWContent"):
        raise Refused()
    try:
        data = base64.b64decode(row["imageBase64Data"], validate=True)
    except (binascii.Error, ValueError):
        raise StudioError("Runware returned an image that could not be read.", 502) from None
    return {"data": data, "content_type": "image/jpeg", "width": w, "height": h, "seed": row.get("seed"),
            "cost": row.get("cost")}


IMAGE_MAKERS = {"fal": _image_fal, "runware": _image_runware}


# -------------------------------------------------------------------------------------------
# One video: start it on the chosen service, then check on it until the service is done
# -------------------------------------------------------------------------------------------

def _pixel_size(data: bytes) -> tuple[int, int] | None:
    from PIL import Image
    try:
        return Image.open(io.BytesIO(data)).size
    except Exception:  # noqa: BLE001
        return None


async def _start_gpu(model_id: str, route: dict, prompt: str, shape: str, seconds: int | None, steps: int | None,
                     source: dict | None, end: dict | None = None, refs: list[dict] = (),
                     pins: list[tuple[dict, float]] = ()) -> dict:
    """Wake the maker's GPU and note the job. From cold it takes a minute or two, so the first
    check that finds it up hands ComfyUI the job (_poll_gpu). Pictures stay in R2 until then."""
    await comfy.wake()
    return {"service": "baseten", "workflow": model_id, "prompt": prompt, "seconds": seconds, "steps": steps,
            "size": list(route["sizes"][shape]), "frame": source["key"] if source else None,
            "end": end["key"] if end else None, "refs": [r["key"] for r in refs],
            "pins": [[p["key"], at] for p, at in pins], "seed": secrets.randbelow(2 ** 48)}


async def _send_picture(key: str, what: str) -> tuple[str, tuple[int, int]]:
    """Copy one picture from R2 to ComfyUI. Returns its name there and its pixel size."""
    data = await r2.get_bytes_async(key)
    size = _pixel_size(data) if data else None
    if not size:
        raise StudioError(f"The {what} is gone or could not be read.", 422)
    return await comfy.upload(data, key.rsplit("/", 1)[-1]), size


async def _gpu_workflow(job: dict) -> dict:
    """The ComfyUI workflow for a saved job, with its pictures uploaded."""
    (w, h), kind = job["size"], job.get("workflow", "h3")
    if kind == "h3-still":
        return comfy.h3_still(job["prompt"], w, h, job["steps"], job["seed"])
    first = await _send_picture(job["frame"], "first frame") if job.get("frame") else None
    last = await _send_picture(job["end"], "last frame") if job.get("end") else None
    if kind == "h3-ref":
        refs = [(await _send_picture(key, f"Picture {n + 1}"))[0] for n, key in enumerate(job.get("refs") or [])]
        frames = comfy.h3_frames(job["seconds"])
        pinned = [(first[0], 0)] if first else []
        for key, at in job.get("pins") or []:
            pinned.append(((await _send_picture(key, "picture at a set second"))[0],
                           min(max(1, round(at * comfy.H3_FPS)), frames - 2)))
        if last:
            pinned.append((last[0], -1))
        return comfy.h3_refs(job["prompt"], refs, pinned, w, h, job["seconds"], job["seed"])
    if first:
        w, h = comfy.h3_size(*first[1])   # the canvas follows the first frame's shape
    return comfy.h3_video(job["prompt"], first and first[0], w, h, job["seconds"], job["seed"], last and last[0])


async def _poll_gpu(job: dict) -> dict:
    """_poll_video for the maker's GPU, for videos and stills alike."""
    if not job.get("comfy"):
        if not await comfy.ready():
            return {"status": "pending", "progress": None}   # the GPU is still waking
        try:
            prompt_id = await comfy.queue(await _gpu_workflow(job))
        except StudioError as e:
            if e.status == 422:
                return {"status": "failed", "error": e.message}
            raise   # ComfyUI was unreachable; the next check asks again
        return {"status": "pending", "progress": None, "job": job | {"comfy": prompt_id}}
    state, files, reason = await comfy.status(job["comfy"])
    if state == "running":
        return {"status": "pending", "progress": None}
    if state == "failed":
        return {"status": "failed", "error": reason}
    return {"status": "done", "url": comfy.file_url(files[0]), "headers": comfy.headers(), "cost": None,
            "ext": files[0]["filename"].rsplit(".", 1)[-1].lower()}


async def _start_video(service: str, route: dict, prompt: str, shape: str, seconds: int, audio: bool | None,
                       source: dict | None) -> dict:
    """Send the job and return what is needed to ask about it later."""
    if service == "runware":
        task_uuid = str(uuid.uuid4())
        task = {"taskType": "videoInference", "taskUUID": task_uuid, "model": route["model"], "positivePrompt": prompt,
                "duration": seconds, "deliveryMethod": "async", "includeCost": True, "ttl": RUNWARE_VIDEO_TTL,
                "outputFormat": "MP4", "safety": {"checkContent": True}}
        if source:
            task["inputs"] = {"frameImages": [source["data_uri"]]}   # the image's own shape sets the video's
            if route.get("resolution"):
                task["resolution"] = route["resolution"]
        else:
            task["width"], task["height"] = route["sizes"][shape]
        if audio is not None and route.get("audio_at"):
            _nest(task, route["audio_at"], bool(audio))
        _merge(task, route.get("quiet") or {})
        _, err = svc.runware_result(await svc.runware_call([task]), task_uuid)
        if err:
            raise StudioError(f"Runware would not start this video: {_short(err.get('message')) or 'no reason given'}.", 502)
        return {"service": "runware", "task": task_uuid}

    if service == "wavespeed":
        body = {"prompt": prompt, "duration": seconds}
        if source:
            body[route["frame_key"]] = r2.presign_get(source["key"], SOURCE_SECONDS)
            body |= route.get("frame_extra") or {}
        else:
            body["size"] = route["sizes"][shape]
        data = await svc.wavespeed_call("POST", "/" + (route["model_frame"] if source else route["model"]), body)
        if not data.get("id"):
            raise StudioError("WaveSpeed did not start the video.", 502)
        return {"service": "wavespeed", "prediction": data["id"]}

    if service == "replicate":
        body = {"prompt": prompt, "duration": seconds} | (route.get("extra") or {})
        if source:
            body[route["frame_key"]] = r2.presign_get(source["key"], SOURCE_SECONDS)
        else:
            body["aspect_ratio"] = route["sizes"][shape]
        code, data = await svc.replicate_call("POST", f"{svc.REPLICATE_API}/models/{route['model']}/predictions",
                                              {"input": body})
        if code >= 400 or not data.get("id"):
            raise StudioError(f"Replicate would not start this video: {svc._detail(data) or 'no reason given'}.", 502)
        return {"service": "replicate", "prediction": data["id"],
                "get": (data.get("urls") or {}).get("get") or f"{svc.REPLICATE_API}/predictions/{data['id']}"}

    body = {"prompt": prompt} | (route.get("extra") or {})   # fal
    if route.get("duration_key", "duration"):
        body[route.get("duration_key", "duration")] = seconds
    if source:
        # the queue may hold the job a while before a runner reads the frame
        body[route["frame_key"]] = r2.presign_get(source["key"], SOURCE_SECONDS)
    if not source or not route.get("frame_sets_shape", True):
        body["aspect_ratio"] = route["sizes"][shape]
    if audio is not None and route.get("audio_at"):
        _nest(body, route["audio_at"], bool(audio))
    status, data = await svc.fal_queue("POST", f"{svc.FAL_QUEUE}/{route['model_frame'] if source else route['model']}", body)
    if status >= 400 or not data.get("request_id") or not data.get("status_url") or not data.get("response_url"):
        raise StudioError(f"fal would not start this video: {svc._detail(data) or 'no reason given'}.", 502)
    return {"service": "fal", "request": data["request_id"], "status_url": data["status_url"],
            "response_url": data["response_url"]}


async def _poll_video(job: dict) -> dict:
    """{"status": "pending" | "done" | "failed" | "refused", ...}. A pending job may carry
    `progress`; a done one carries `url` (and `headers` when the file needs the key) and `cost`,
    and `prompt` when the model says what prompt it used. A pending one carries `job` when the job
    itself changed and must be saved."""
    service = job["service"]
    if service == "baseten":
        return await _poll_gpu(job)

    if service == "runware":
        body = await svc.runware_call([{"taskType": "getResponse", "taskUUID": job["task"]}])
        row, err = svc.runware_result(body, job["task"], strict=True)
        if err:
            return {"status": "failed", "error": _short(err.get("message")) or "The service gave no reason."}
        if body.get("errors") and not row:
            raise StudioError("Runware could not be reached. Still waiting on the video.", 502)
        if not row or row.get("status") == "processing" or not row.get("videoURL"):
            return {"status": "pending", "progress": (row or {}).get("progress")}
        if row.get("NSFWContent"):
            return {"status": "refused", "cost": row.get("cost")}
        return {"status": "done", "url": row["videoURL"], "cost": row.get("cost")}

    if service == "wavespeed":
        data = await svc.wavespeed_call("GET", f"/predictions/{job['prediction']}/result")
        status = data.get("status")
        if status in ("created", "processing", None):
            return {"status": "pending", "progress": None}
        outputs = [o for o in data.get("outputs") or [] if isinstance(o, str) and o.startswith("http")]
        if status == "completed" and outputs:
            return {"status": "done", "url": outputs[0], "cost": None}
        return {"status": "failed", "error": _short(data.get("error")) or "The service gave no reason."}

    if service == "replicate":
        code, data = await svc.replicate_call("GET", job["get"])
        if code == 404:
            return {"status": "failed", "error": "Replicate no longer has this video."}
        if code >= 400:
            raise StudioError("Replicate could not be reached. Still waiting on the video.", 502)
        status = data.get("status")
        if status in ("starting", "processing"):
            return {"status": "pending", "progress": None}
        output = data.get("output")
        url = output[0] if isinstance(output, list) and output else output
        if status == "succeeded" and isinstance(url, str) and url.startswith("http"):
            return {"status": "done", "url": url, "headers": svc.replicate_file_headers(url), "cost": None}
        return {"status": "failed", "error": _short(data.get("error")) or "The service gave no reason."}

    code, status = await svc.fal_queue("GET", job["status_url"])   # fal
    if code == 404:
        return {"status": "failed", "error": "fal no longer has this request."}
    if code >= 400:
        raise StudioError("fal could not be reached. Still waiting on the video.", 502)
    if status.get("status") != "COMPLETED":
        return {"status": "pending", "progress": None}
    if status.get("error"):
        return {"status": "failed", "error": _short(status["error"])}
    code, result = await svc.fal_queue("GET", job["response_url"])
    if code == 200 and (result.get("video") or {}).get("url"):
        return {"status": "done", "url": result["video"]["url"], "cost": None,
                "prompt": _short(result.get("actual_prompt")) if result.get("actual_prompt") else None}
    if code == 404:
        return {"status": "failed", "error": "fal no longer has the result. It keeps a finished video for an hour."}
    if code == 400:
        return {"status": "pending", "progress": None}
    return {"status": "failed", "error": svc._detail(result) or "The service gave no reason."}


async def _forget_at_service(job: dict) -> None:
    """Ask the service to delete its copy now that ours is saved. Runware's link expires on its
    own (RUNWARE_VIDEO_TTL) and Replicate deletes an API prediction after an hour."""
    if job.get("service") == "fal":
        await svc.fal_delete_files(job["request"])
    elif job.get("service") == "baseten" and job.get("comfy"):
        try:
            await comfy.forget(job["comfy"])
        except Exception:  # noqa: BLE001
            logger.warning("ComfyUI history could not be cleared", exc_info=True)
    elif job.get("service") == "wavespeed":
        try:
            await svc.wavespeed_call("POST", "/predictions/delete", {"ids": [job["prediction"]]})
        except Exception:  # noqa: BLE001
            logger.warning("wavespeed video could not be deleted at the service", exc_info=True)


def _record_video(item: dict, outcome: str) -> None:
    route = "studio:video" if item.get("kind", "video") == "video" else "studio"   # a still from the GPU waits too
    metrics.record(metrics.row(route=route, key_source="server", outcome=outcome,
                               est_usd=item.get("est_usd") or 0.0,
                               duration_ms=max(0, time.time() - item["created"]) * 1000))


async def check(user, item_id: str) -> dict | None:
    """Ask the service about one pending video, and save it into R2 when it is done."""
    lock = _job_locks.setdefault(item_id, asyncio.Lock())
    async with lock:
        item = next((i for i in await _read_index(user) if i["id"] == item_id), None)
        if not item or item.get("status") != "pending":
            _job_locks.pop(item_id, None)
            return public(item) if item else None
        state = await _poll_video(item["job"])
        if state["status"] == "pending":
            if state.get("job"):
                item = item | {"job": state["job"]}
                if not await _save_item(user, item):
                    _job_locks.pop(item_id, None)
                    return None   # deleted while it was being started
            return public(item) | {"progress": state.get("progress")}

        # What the service charged, when it says; otherwise the price at the start for a made
        # video, and nothing for one that failed.
        cost = state.get("cost") if isinstance(state.get("cost"), (int, float)) and state["cost"] > 0 else None
        if cost is None and state["status"] != "failed":
            cost = item.get("quoted_usd") or 0.0
        paid = round((item.get("rewrite_usd") or 0.0) + (cost or 0.0), 4)
        if state["status"] in ("failed", "refused"):
            refused = state["status"] == "refused"
            item = item | {"status": "failed", "est_usd": paid,
                           "error": "The service's safety check blocked this video." if refused else state["error"]}
            if await _save_item(user, item):
                _record_video(item, "refused" if refused else "provider_error")
            _job_locks.pop(item_id, None)
            return public(item)

        data = await _download(state["url"], MAX_VIDEO, state.get("headers"))
        ext = state.get("ext") if state.get("ext") in _TYPE else "mp4" if item.get("kind") == "video" else "png"
        key = f"{_folder(user)}{item_id}.{ext}"
        await r2.put_bytes_async(key, data, _TYPE[ext])
        item = item | {"status": "ready", "key": key, "est_usd": paid, "bytes": len(data)}
        if state.get("prompt"):
            item["service_prompt"] = state["prompt"]
        if not await _save_item(user, item):
            await r2.delete_async(key)   # deleted while it was being fetched
            _job_locks.pop(item_id, None)
            return None
        _record_video(item, "complete")
        await _forget_at_service(item["job"])
        _job_locks.pop(item_id, None)
        return public(item)


_followers: set[asyncio.Task] = set()


def _follow_later(user, item_id: str) -> None:
    if FOLLOW:
        task = asyncio.get_running_loop().create_task(_follow(user, item_id))
        _followers.add(task)
        task.add_done_callback(_followers.discard)


async def _follow(user, item_id: str) -> None:
    """Check on one video every FOLLOW_EVERY seconds until it is saved, fails, or is deleted, so a
    closed page loses nothing. fal and Replicate hold a finished result for only an hour."""
    deadline = time.monotonic() + FOLLOW_FOR
    while time.monotonic() < deadline:
        await asyncio.sleep(FOLLOW_EVERY)
        try:
            item = await check(user, item_id)
        except StudioError:
            continue   # the service was busy or unreachable; ask again next time
        except Exception:  # noqa: BLE001
            logger.warning("studio follower failed a check", exc_info=True)
            continue
        if not item or item["status"] != "pending":
            return


# -------------------------------------------------------------------------------------------
# Making one image or starting one video
# -------------------------------------------------------------------------------------------

def _pick(req: dict) -> tuple[str, str]:
    """(mode, model id) from the request, falling back to each mode's default model."""
    mode = req.get("mode") if req.get("mode") in DEFAULTS else ("edit" if req.get("source") else "create")
    model_id = req.get("model")
    if model_id not in MODELS or mode not in MODELS[model_id]["does"]:
        model_id = DEFAULTS[mode]
    return mode, model_id


def _settings(m: dict, mode: str, req: dict) -> tuple[str, int | None, bool | None, int | None]:
    """(shape, seconds, audio, steps) from the request, each within what the model offers."""
    if mode == "video":
        shape = req.get("shape") if req.get("shape") in m["sizes"] else m["sizes"][0]
        asked = str(req.get("seconds") or "")
        seconds = int(asked) if asked.isdigit() and int(asked) in m["seconds"] else m["seconds"][0]
        audio = None if m.get("audio") is None else bool(req["audio"]) if "audio" in req else m["audio"]
        return shape, seconds, audio, None
    shape = req.get("shape") if req.get("shape") in SHAPES else "square"
    steps = m.get("steps")
    if m.get("max_steps"):
        try:
            steps = max(1, min(int(req.get("steps") or m["steps"]), m["max_steps"]))
        except (TypeError, ValueError):
            pass
    return shape, None, None, steps


def _no_service(m: dict, options: list[dict], pinned: str | None) -> StudioError:
    if pinned:
        option = next((o for o in options if o["service"] == pinned), None)
        if option and option["reason"] == "not set up":
            return _need_key_error(pinned)
        if option:
            return StudioError(f"{m['label']} on {option['label']} {option['reason']}. Pick another service.")
        return StudioError(f"{SERVICES[pinned]['label']} does not run {m['label']}.")
    if all(o["reason"] == "not set up" for o in options):
        names = ", ".join(svc.setting_names(o["service"]) for o in options)
        return StudioError(f"{m['label']} needs a key on this server: {names}.", 503)
    reasons = "; ".join(f"{o['label']} {o['reason'] or 'runs only when picked'}" for o in options)
    return StudioError(f"No service here can make {m['label']} with these settings ({reasons}).")


def _need_key_error(service: str) -> StudioError:
    try:
        svc._need_key(service)
    except StudioError as e:
        return e
    return StudioError(f"{SERVICES[service]['label']} is not available.", 503)


async def make(user, req: dict) -> dict:
    """Make one image, or start one video, on the cheapest service that can, and return its
    index entry."""
    prompt = " ".join(str(req.get("prompt") or "").split())
    if not prompt:
        raise StudioError("Describe what you want.")
    if len(prompt) > MAX_PROMPT:
        raise StudioError(f"Keep the description under {MAX_PROMPT:,} characters.")
    mode, model_id = _pick(req)
    m = MODELS[model_id]
    video = mode == "video"
    source_req = req.get("source") or None
    if mode == "edit" and not source_req:
        raise StudioError("Choose an image to edit.")
    if video and source_req and not m.get("start_image"):
        raise StudioError(f"{m['label']} starts from a description only. Remove the first frame or pick another model.")
    if not video:
        source_req = source_req if mode == "edit" else None
    shape, seconds, audio, steps = _settings(m, mode, req)
    end_req, refs_req, pins_req = _more_pictures(m, req, seconds) if video else (None, [], [])
    book = await prices.load()
    service_pin = req.get("service") if req.get("service") in m["routes"] else None
    options = candidates(model_id, mode, shape, seconds, audio, bool(source_req), steps, book, bool(end_req))
    usable = _runnable(options, service_pin)
    if not usable:
        raise _no_service(m, options, service_pin)
    if not r2.configured():
        raise StudioError("Image Studio needs R2 storage on this server.", 503)

    item_id = uuid.uuid4().hex
    folder = _folder(user)
    started = time.monotonic()
    usd = 0.0
    outcome = "provider_error"
    record = True
    source, uploads = None, []

    async def picture(asked, slot: str) -> dict:
        got = await _source(user, asked, item_id, slot)
        if got["uploaded"]:
            uploads.append(got)
        return got
    try:
        source = await picture(source_req, "source") if source_req else None
        end = await picture(end_req, "last") if end_req else None
        refs = [await picture(r, f"ref{n + 1}") for n, r in enumerate(refs_req)]
        pins = [(await picture(p, f"at{n + 1}"), at) for n, (p, at) in enumerate(pins_req)]

        used = prompt
        if req.get("rewrite"):
            purpose = "reference" if m.get("refs") else ("animate" if source else "video") if video else mode
            used, rewrite_usd = await rewrite(prompt, purpose)
            usd += rewrite_usd
        if m.get("refs"):
            used = _PICTURE.sub(lambda p: f"<Picture {p.group(1)}>", used)

        base = {"id": item_id, "created": int(time.time()), "kind": "video" if video else "image",
                "mode": {"create": "generate", "edit": "edit", "video": "video"}[mode],
                "model_id": model_id, "engine": m["label"], "prompt": prompt, "prompt_used": used,
                "rewritten": used != prompt, "shape": shape,
                "source_id": source_req.get("id") if isinstance(source_req, dict) else None,
                # an uploaded picture belongs to this item and goes when it does; an earlier studio
                # image used as a picture stays
                "source_key": source["key"] if source and source["uploaded"] else None,
                "upload_keys": [p["key"] for p in uploads if p is not source]}

        # The cheapest service first; one that turns the account away hands the run to the next.
        turned_away = None
        for option in usable:
            service, route = option["service"], option["route"]
            try:
                if service == "baseten":
                    job = await _start_gpu(model_id, route, used, shape, seconds, steps, source, end, refs, pins)
                elif video:
                    job = await _start_video(service, route, used, shape, seconds, audio, source)
                else:
                    made = await IMAGE_MAKERS[service](route, used, shape, steps, source)
            except AccountError as e:
                if e.down:
                    _mark_down(service, "turned the account away today")
                turned_away = e
                continue
            except Refused:
                outcome = "refused"
                usd += option["usd"]
                raise
            break
        else:
            raise turned_away
        base |= {"service": service, "model": route["model"]}

        if video or service == "baseten":
            size = route["sizes"][shape]
            framed = source and route.get("frame_sets_shape", True)
            w, h = size if isinstance(size, tuple) and not framed else (None, None)
            item = base | {"status": "pending", "job": job, "width": w, "height": h, "rewrite_usd": round(usd, 6),
                           "quoted_usd": option["usd"], "est_usd": round(usd + option["usd"], 4)}
            item |= {"seconds": seconds, "audio": audio} if video else {"steps": steps}
            await _save_item(user, item, new=True)
            record = False   # the row is written when the job finishes (check)
            _follow_later(user, item_id)
            return public(item)

        content_type = made["content_type"] if made["content_type"] in _EXT else "image/jpeg"
        key = f"{folder}{item_id}.{_EXT[content_type]}"
        await r2.put_bytes_async(key, made["data"], content_type)
        cost = made.get("cost")
        usd += cost if isinstance(cost, (int, float)) and cost > 0 else option["usd"]
        item = base | {"status": "ready", "key": key, "steps": steps, "width": made.get("width"),
                       "height": made.get("height"), "seed": made.get("seed"), "est_usd": round(usd, 4)}
        await _save_item(user, item, new=True)
        outcome = "complete"
        return public(item)
    except BaseException:
        for upload in uploads:
            await r2.delete_async(upload["key"])   # an upload for an item that was never made
        raise
    finally:
        if record:
            metrics.record(metrics.row(route="studio:video" if video else "studio", key_source="server",
                                       outcome=outcome, est_usd=round(usd, 6),
                                       duration_ms=(time.monotonic() - started) * 1000))


def _more_pictures(m: dict, req: dict, seconds: int) -> tuple[dict | None, list, list]:
    """(last frame, reference pictures, pictures pinned at a second) asked for a video, each
    checked against what the model takes. A pinned second falls strictly inside the clip."""
    end, refs, pins = req.get("end") or None, req.get("refs") or [], req.get("pins") or []
    if not isinstance(refs, list) or not isinstance(pins, list):
        raise StudioError("Those pictures could not be read.")
    if end and not m.get("end_image"):
        raise StudioError(f"{m['label']} takes no last frame. Remove it or pick another model.")
    if refs and len(refs) > m.get("refs", 0):
        raise StudioError(f"{m['label']} takes no reference pictures." if not m.get("refs")
                          else f"{m['label']} takes up to {m['refs']} pictures.")
    if pins and len(pins) > m.get("pins", 0):
        raise StudioError(f"{m['label']} takes no pictures at set seconds." if not m.get("pins")
                          else f"{m['label']} takes up to {m['pins']} pictures at set seconds.")
    timed = []
    for pin in pins:
        try:
            at = float(pin.get("at")) if isinstance(pin, dict) else None
        except (TypeError, ValueError):
            at = None
        if at is None or not 0 < at < seconds:
            raise StudioError(f"Set each picture's second between 0 and {seconds}.")
        timed.append((pin.get("source"), at))
    return end, refs, timed


async def _source(user, source, item_id: str, slot: str = "source") -> dict:
    """The image to edit or animate: one of the user's own studio images, or an upload. Returned
    as its R2 key, its type, and a data URI for the services that take the image inline. `slot`
    names an uploaded copy, since one video can carry several pictures."""
    if not isinstance(source, dict):
        raise StudioError("Choose an image to start from.")
    if source.get("id"):
        sid = str(source["id"])
        found = next((i for i in await _read_index(user) if i["id"] == sid), None)
        if not found or found.get("kind", "image") != "image" or found.get("status", "ready") != "ready":
            raise StudioError("That image is not in your studio.", 404)
        data = await r2.get_bytes_async(found["key"])
        if not data:
            raise StudioError("That image is not in your studio.", 404)
        content_type = _TYPE.get(found["key"].rsplit(".", 1)[-1], "image/jpeg")
        key, uploaded = found["key"], False
    else:
        m = _DATA_URL.match(str(source.get("data_url") or ""))
        if not m:
            raise StudioError("Upload a PNG, JPEG, or WebP image.")
        try:
            data = base64.b64decode(m.group(2), validate=True)
        except (binascii.Error, ValueError):
            raise StudioError("That upload could not be read.") from None
        if len(data) > MAX_UPLOAD:
            raise StudioError("Upload an image under 8 MB.")
        content_type = m.group(1)
        key, uploaded = f"{_folder(user)}{item_id}-{slot}.{_EXT[content_type]}", True
        await r2.put_bytes_async(key, data, content_type)
    return {"key": key, "uploaded": uploaded, "content_type": content_type,
            "data_uri": f"data:{content_type};base64,{base64.b64encode(data).decode()}"}


def public(item: dict) -> dict:
    """An index entry as the page sees it: no storage keys or job ids."""
    out = {k: v for k, v in item.items()
           if k not in ("key", "source_key", "upload_keys", "job", "rewrite_usd", "quoted_usd")}
    out.setdefault("kind", "image")
    out.setdefault("status", "ready")
    out.setdefault("service", "fal")
    out["service_label"] = SERVICES.get(out["service"], {}).get("label", out["service"])
    out["url"] = f"/api/studio/image/{item['id']}" if out["status"] == "ready" else None
    out["ext"] = item["key"].rsplit(".", 1)[-1] if item.get("key") else None
    return out


# -------------------------------------------------------------------------------------------
# Routes. Anyone who may not use the studio gets a plain 404, so it does not announce itself.
# -------------------------------------------------------------------------------------------

def _user_or_404(request):
    user = auth.current_user(request)
    return user if may_use(user) else None


def _not_found():
    return JSONResponse({"error": "not found"}, status_code=404)


async def page(request):
    if not _user_or_404(request):
        return HTMLResponse("Not found", status_code=404)
    path = os.path.join(os.path.dirname(__file__), "static", "studio.html")
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers={"Cache-Control": "no-store"})


def _menu_entry(model_id: str, m: dict) -> dict:
    entry = {"id": model_id, "label": m["label"], "note": m["note"], "does": list(m["does"]),
             "services": list(m["routes"])}
    if "video" in m["does"]:
        entry |= {"seconds": list(m["seconds"]), "sizes": list(m["sizes"]), "audio": m.get("audio"),
                  "start_image": bool(m.get("start_image")), "end_image": bool(m.get("end_image")),
                  "refs": m.get("refs", 0), "pins": m.get("pins", 0)}
    else:
        entry |= {"steps": m.get("steps"), "max_steps": m.get("max_steps")}
    return entry


def _book_summary(book: dict) -> dict:
    return {"checked": book.get("checked"), "stale": prices.stale(book),
            "kept": sorted(rid for rid, e in (book.get("routes") or {}).items() if e.get("status") == "kept")}


async def config(request):
    if not _user_or_404(request):
        return _not_found()
    book = await prices.load()
    if prices.stale(book):
        _refresh_soon()
    services = {s: {"label": v["label"], "ready": bool(svc._key(s)), "env": svc.setting_names(s), "down": _is_down(s)}
                for s, v in SERVICES.items()}
    return JSONResponse({
        "ready": r2.configured() and any(s["ready"] for s in services.values()),
        "storage": r2.configured(),
        "services": services,
        "models": [_menu_entry(k, v) for k, v in MODELS.items()],
        "defaults": DEFAULTS,
        "shapes": {k: {"label": v["label"], "size": v["size"]} for k, v in SHAPES.items()},
        "prices": _book_summary(book),
    })


async def quote(request):
    """Today's price for what the page has set up, on each service, and the one a run would use."""
    if not _user_or_404(request):
        return _not_found()
    try:
        req = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "malformed request"}, status_code=400)
    if not isinstance(req, dict):
        return JSONResponse({"error": "malformed request"}, status_code=400)
    mode, model_id = _pick(req)
    m = MODELS[model_id]
    shape, seconds, audio, steps = _settings(m, mode, req)
    book = await prices.load()
    options = candidates(model_id, mode, shape, seconds, audio, bool(req.get("framed")), steps, book,
                         bool(req.get("ending")) and mode == "video")
    pinned = req.get("service") if req.get("service") in m["routes"] else None
    choice = next(iter(_runnable(options, pinned)), None)
    shown = ("service", "label", "usd", "usable", "reason", "frame_sets_shape", "auto")
    return JSONResponse({
        "model": model_id, "mode": mode,
        "choice": {k: choice[k] for k in shown} if choice else None,
        "why": None if choice else _no_service(m, options, pinned).message,
        "services": [{k: o[k] for k in shown} for o in options],
        "prices": _book_summary(book),
    })


async def refresh_prices_now(request):
    if not _user_or_404(request):
        return _not_found()
    book = await refresh_prices()
    return JSONResponse({"prices": _book_summary(book),
                         "routes": {rid: {k: e.get(k) for k in ("usd", "usd_audio", "status", "note")}
                                    for rid, e in book["routes"].items()}})


async def list_images(request):
    user = _user_or_404(request)
    if not user:
        return _not_found()
    return JSONResponse({"images": [public(i) for i in await _read_index(user)]})


async def generate(request):
    user = _user_or_404(request)
    if not user:
        return _not_found()
    try:
        req = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "malformed request"}, status_code=400)
    if not isinstance(req, dict):
        return JSONResponse({"error": "malformed request"}, status_code=400)
    try:
        return JSONResponse({"image": await make(user, req)})
    except StudioError as e:
        return JSONResponse({"error": e.message}, status_code=e.status)
    except Exception:  # noqa: BLE001
        logger.exception("studio generate failed")
        return JSONResponse({"error": "Something went wrong making that."}, status_code=500)


async def check_job(request):
    user = _user_or_404(request)
    image_id = request.path_params["image_id"]
    if not user or not _ID.match(image_id):
        return _not_found()
    try:
        item = await check(user, image_id)
    except StudioError as e:
        # the job is still pending; the page shows the line and keeps asking
        return JSONResponse({"error": e.message}, status_code=e.status)
    except Exception:  # noqa: BLE001
        logger.exception("studio check failed")
        return JSONResponse({"error": "Something went wrong checking on that video."}, status_code=500)
    return JSONResponse({"image": item}) if item else _not_found()


def _byte_range(header: str | None, size: int) -> tuple[int, int] | None | bool:
    """(first, last) byte for a Range header, None for no range, False for one that cannot be met."""
    m = _RANGE.match((header or "").strip())
    if not m or not (m.group(1) or m.group(2)):
        return None
    if m.group(1):
        first = int(m.group(1))
        last = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
    else:
        first, last = max(0, size - int(m.group(2))), size - 1
    return (first, last) if first <= last < size else False


async def image(request):
    """The file itself, image or video. Videos answer byte ranges, which Safari needs to play them."""
    user = _user_or_404(request)
    image_id = request.path_params["image_id"]
    if not user or not _ID.match(image_id):
        return _not_found()
    item = next((i for i in await _read_index(user) if i["id"] == image_id), None)
    got = await r2.get_object_async(item["key"]) if item and item.get("key") else None
    if not got:
        return _not_found()
    data, content_type = got
    headers = {"Cache-Control": "private, max-age=3600", "Accept-Ranges": "bytes"}
    span = _byte_range(request.headers.get("range"), len(data))
    if span is False:
        return Response(status_code=416, headers=headers | {"Content-Range": f"bytes */{len(data)}"})
    if span:
        first, last = span
        return Response(data[first:last + 1], status_code=206, media_type=content_type,
                        headers=headers | {"Content-Range": f"bytes {first}-{last}/{len(data)}"})
    return Response(data, media_type=content_type, headers=headers)


async def delete_image(request):
    """Delete one item. A video still being made is dropped from the studio; the service may
    still finish it, and charge for it."""
    user = _user_or_404(request)
    image_id = request.path_params["image_id"]
    if not user or not _ID.match(image_id):
        return _not_found()
    async with _lock(user):
        items = await _read_index(user)
        item = next((i for i in items if i["id"] == image_id), None)
        if not item:
            return _not_found()
        if item.get("key"):
            await r2.delete_async(item["key"])
        for key in [item.get("source_key"), *(item.get("upload_keys") or [])]:
            if key:
                await r2.delete_async(key)
        await _write_index(user, [i for i in items if i["id"] != image_id])
    return JSONResponse({"ok": True})
