"""
The outside services Media Studio calls (docs/decisions/0017): their keys, their errors, and one
small client each. Every client asks its service to keep as little as it can.

- fal: no request history, generated files deleted after ten minutes (images) or two hours
  (videos), and a finished video's files deleted at once when the key allows.
- Runware: images come back inline, so Runware never hosts them; a video's link expires after
  a day.
- WaveSpeed: a finished prediction is deleted once the studio has its copy.
- Replicate: deletes an API prediction's inputs and outputs after an hour on its own.
- Baseten: the maker's own GPU running ComfyUI (webapp/studio_comfy.py). Files sit on its
  scratch disk until it shuts down, and each job's history is deleted once the file is saved.

A service that turns the account away (bad key, no credit, too busy) raises AccountError, which
tells the studio nothing was made and the next service may be tried.
"""
from __future__ import annotations

import json
import logging
import os
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("study-bible-web.studio")

FAL_RUN = "https://fal.run"
FAL_QUEUE = "https://queue.fal.run"
FAL_API = "https://api.fal.ai/v1"
RUNWARE_API = "https://api.runware.ai/v1"
WAVESPEED_API = "https://api.wavespeed.ai/api/v3"
REPLICATE_API = "https://api.replicate.com/v1"

SERVICES = {
    "fal": {"label": "fal", "env": ("FAL_API_KEY", "FAL_KEY")},
    "runware": {"label": "Runware", "env": ("RUNWARE_API_KEY",)},
    "wavespeed": {"label": "WaveSpeed", "env": ("WAVESPEED_API_KEY",)},
    "replicate": {"label": "Replicate", "env": ("REPLICATE_API_TOKEN",)},
    # `needs`: more settings the service cannot run without
    "baseten": {"label": "Baseten (your GPU)", "env": ("BASETEN_API_KEY",), "needs": ("BASETEN_COMFY_MODEL_ID",)},
}

MAX_IMAGE = 25 * 1024 * 1024
MAX_VIDEO = 200 * 1024 * 1024
FAL_KEEP_SECONDS = 600         # fal deletes an image after this; ours is in R2 by then
FAL_VIDEO_KEEP_SECONDS = 7200  # and a video after this; fal holds a finished job's result for an hour


class StudioError(Exception):
    """A request the studio refuses or cannot finish, with the line to show and a status."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message, self.status = message, status


class Refused(StudioError):
    """The service's safety check blocked the result. It was made, so it is paid for."""

    def __init__(self) -> None:
        super().__init__("The service's safety check blocked this. Try a different description.", 422)


class AccountError(StudioError):
    """The service turned the account away before making anything. `down` means it will keep
    doing so for a while (key or credit), so the studio skips it; a busy service is not down."""

    def __init__(self, message: str, status: int, down: bool = True) -> None:
        super().__init__(message, status)
        self.down = down


def _key(service: str) -> str | None:
    s = SERVICES[service]
    if not all(os.environ.get(name) for name in s.get("needs", ())):
        return None
    return next((os.environ[name] for name in s["env"] if os.environ.get(name)), None)


def setting_names(service: str) -> str:
    s = SERVICES[service]
    return " and ".join((s["env"][0],) + s.get("needs", ()))


def _need_key(service: str) -> str:
    key = _key(service)
    if not key:
        raise StudioError(f"{SERVICES[service]['label']} needs {setting_names(service)} on this server.", 503)
    return key


def _short(text) -> str:
    """A service's error message, trimmed for the page. It is the maker's own prompt if echoed."""
    return " ".join(str(text or "").split())[:240]


def _detail(data) -> str:
    """The reason in a service's error body: a `detail` string, a list of field problems, or an
    `error` or `message` string or object."""
    if not isinstance(data, dict):
        return ""
    err = data.get("error")
    detail = (data.get("detail") or (err.get("message") if isinstance(err, dict) else err)
              or data.get("message") or "")
    if isinstance(detail, list):
        detail = "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail)
    return _short(detail)


def _out_of_credit(service: str) -> AccountError:
    s = SERVICES[service]
    return AccountError(f"The {s['label']} account is out of credit. Add credit there, then try again.", 402)


def _bad_key(service: str) -> AccountError:
    return AccountError(f"{SERVICES[service]['label']} did not accept the API key.", 502)


def _busy(service: str) -> AccountError:
    return AccountError(f"{SERVICES[service]['label']} is busy. Try again in a moment.", 503, down=False)


async def _download(url: str, limit: int = MAX_IMAGE, headers: dict | None = None) -> bytes:
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=20.0), follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
    if r.status_code != 200 or len(r.content) > limit:
        raise StudioError("The finished file could not be fetched from the service.", 502)
    return r.content


# -------------------------------------------------------------------------------------------
# fal
# -------------------------------------------------------------------------------------------

def _fal_headers(keep_seconds: int) -> dict:
    """fal is asked to keep no request history and to delete the files it makes after
    `keep_seconds` (fal's defaults are 90 days and forever)."""
    return {"Authorization": f"Key {_need_key('fal')}", "X-Fal-Store-IO": "0",
            "X-Fal-Object-Lifecycle-Preference": json.dumps({"expiration_duration_seconds": keep_seconds})}


def _fal_account_trouble(r: httpx.Response) -> None:
    if r.status_code == 403 and "TOP_UP" in r.text:
        raise _out_of_credit("fal")
    if r.status_code in (401, 403):
        raise _bad_key("fal")
    if r.status_code == 429:
        raise _busy("fal")


async def fal_run(model: str, body: dict) -> dict:
    """One synchronous fal request, for an image."""
    headers = _fal_headers(FAL_KEEP_SECONDS)
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=20.0)) as client:
        r = await client.post(f"{FAL_RUN}/{model}", headers=headers, json=body)
    _fal_account_trouble(r)
    if r.status_code == 422 and "content_policy_violation" in r.text:
        raise Refused()   # fal's own check blocked the picture after making it
    if r.status_code >= 400:
        logger.warning("fal %s returned %s", model, r.status_code)   # the body can echo the prompt
        raise StudioError("The image service could not make this image.", 502)
    return r.json()


async def fal_queue(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    """One call to fal's queue (submit, status, or result): (status code, JSON body). The queue
    answers a model's own failure with the model's status code, so the caller reads it."""
    if not url.startswith(FAL_QUEUE + "/"):
        raise StudioError("fal gave an unexpected address for this video.", 502)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=20.0)) as client:
        r = await client.request(method, url, headers=_fal_headers(FAL_VIDEO_KEEP_SECONDS), json=body)
    _fal_account_trouble(r)
    try:
        data = r.json()
    except ValueError:
        data = {}
    return r.status_code, data if isinstance(data, dict) else {}


async def fal_delete_files(request_id: str) -> None:
    """Ask fal to delete a finished video's files now, ahead of FAL_VIDEO_KEEP_SECONDS. This needs
    a fal key with the FULL permission preset; with a narrower key it is refused, and the files
    expire on their own."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            r = await client.delete(f"{FAL_API}/models/requests/{request_id}/payloads",
                                    headers={"Authorization": f"Key {_need_key('fal')}"})
        if r.status_code >= 400:
            logger.info("fal kept a video's files until they expire (%s)", r.status_code)
    except Exception:  # noqa: BLE001
        logger.warning("fal video files could not be deleted at the service", exc_info=True)


# -------------------------------------------------------------------------------------------
# Runware
# -------------------------------------------------------------------------------------------

async def runware_call(tasks: list[dict]) -> dict:
    """One Runware request: a list of tasks in, {"data": [...], "errors": [...]} out. A failed task
    comes back in `errors` with its taskUUID, and the caller decides what that means."""
    key = _need_key("runware")
    async with httpx.AsyncClient(timeout=httpx.Timeout(150.0, connect=20.0)) as client:
        r = await client.post(RUNWARE_API, headers={"Authorization": f"Bearer {key}"}, json=tasks)
    if r.status_code == 401:
        raise _bad_key("runware")
    if r.status_code == 402:
        raise _out_of_credit("runware")
    if r.status_code == 429:
        raise _busy("runware")
    try:
        body = r.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        logger.warning("runware returned %s without a readable body", r.status_code)
        raise StudioError("Runware could not be reached. Try again in a moment.", 502)
    if r.status_code >= 400 and not body.get("errors"):
        logger.warning("runware returned %s", r.status_code)
        raise StudioError("Runware could not be reached. Try again in a moment.", 502)
    return body


def runware_result(body: dict, task_uuid: str, strict: bool = False) -> tuple[dict | None, dict | None]:
    """(this task's row in `data`, this task's row in `errors`). An error naming no task is about
    the request as a whole; `strict` leaves those out, for polls, where they are not the job's."""
    row = next((d for d in body.get("data") or [] if d.get("taskUUID") == task_uuid), None)
    named = (task_uuid,) if strict else (task_uuid, None)
    err = next((e for e in body.get("errors") or [] if e.get("taskUUID") in named), None)
    return row, err


# -------------------------------------------------------------------------------------------
# WaveSpeed: every answer is an envelope, {"code": 200, "message": ..., "data": {...}}
# -------------------------------------------------------------------------------------------

async def wavespeed_call(method: str, path: str, body: dict | None = None) -> dict:
    """One WaveSpeed request, returning the envelope's `data`."""
    key = _need_key("wavespeed")
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=20.0)) as client:
        r = await client.request(method, WAVESPEED_API + path, headers={"Authorization": f"Bearer {key}"}, json=body)
    try:
        env = r.json()
    except ValueError:
        env = {}
    env = env if isinstance(env, dict) else {}
    code = env.get("code") if isinstance(env.get("code"), int) else r.status_code
    message = str(env.get("message") or "")
    if 401 in (r.status_code, code):
        raise _bad_key("wavespeed")
    if 402 in (r.status_code, code) or re.search(r"balance|insufficient|credit", message, re.I):
        raise _out_of_credit("wavespeed")
    if 429 in (r.status_code, code):
        raise _busy("wavespeed")
    if r.status_code >= 400 or code != 200:
        raise StudioError(f"WaveSpeed could not do this: {_short(message) or 'no reason given'}.", 502)
    return env.get("data") if isinstance(env.get("data"), dict) else {}


# -------------------------------------------------------------------------------------------
# Replicate
# -------------------------------------------------------------------------------------------

async def replicate_call(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    """One Replicate API call: (status code, JSON body)."""
    if not url.startswith(REPLICATE_API + "/"):
        raise StudioError("Replicate gave an unexpected address for this video.", 502)
    key = _need_key("replicate")
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=20.0)) as client:
        r = await client.request(method, url, headers={"Authorization": f"Bearer {key}"}, json=body)
    if r.status_code == 401:
        raise _bad_key("replicate")
    if r.status_code == 402:
        raise _out_of_credit("replicate")
    if r.status_code == 429:
        raise _busy("replicate")
    try:
        data = r.json()
    except ValueError:
        data = {}
    return r.status_code, data if isinstance(data, dict) else {}


def replicate_file_headers(url: str) -> dict | None:
    """Replicate asks for the key on its own file links; no other host ever sees it."""
    host = urlparse(url).hostname or ""
    if host == "replicate.delivery" or host.endswith(".replicate.delivery") or host == "api.replicate.com":
        return {"Authorization": f"Bearer {_need_key('replicate')}"}
    return None
