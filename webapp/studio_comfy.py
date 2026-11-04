"""
ComfyUI on Baseten, the studio's self-hosted route (docs/decisions/0017). The deployment in
baseten/comfyui is a plain ComfyUI server on one GPU that scales to zero when idle. The studio
sends it an API-format workflow and fetches the finished file, all through Baseten's pass-through
route, so a new workflow needs no redeploy.

Nothing leaves the GPU replica but the finished file. Uploads and results sit on its scratch disk
until it shuts down, minutes after the last job, and each job's history is deleted once fetched.
"""
from __future__ import annotations

import math
import os
from urllib.parse import urlencode

import httpx

from webapp.studio_services import MAX_IMAGE, AccountError, StudioError, _need_key, _short

MODEL_ENV = "BASETEN_COMFY_MODEL_ID"
COLD_START = 1300   # Baseten holds a request up to 1200 s while a replica wakes
READY_WAIT = 8      # a readiness probe gives up this soon, so a check never waits out a cold start

# MiniMax H3 from a first frame or from words alone, the files Comfy's own template loads
# (baseten/comfyui/config.yaml).
H3_FILES = {
    "model": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
    "turbo": "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
    "text": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "video_vae": "minimax_h3_video_vae_int8_convrot.safetensors",
    "audio_vae": "minimax_h3_audio_vae_fp32.safetensors",
}
H3_FPS = 24
H3_AREA = 1344 * 768  # the model's 768p frame
H3_TURBO_STEPS = 8


def h3_frames(seconds: float) -> int:
    """Frames for a clip of about this length. H3 takes 17k + 5 frames at 24 fps: 124 is 5 s, 243 is 10 s."""
    n = max(5, round(seconds * H3_FPS))
    return n + (5 - n % 17) % 17


def h3_size(width: int, height: int) -> tuple[int, int]:
    """A 768p frame with the first frame's shape. H3 stretches the first frame to the canvas, so the
    canvas follows the picture. Sides are multiples of 32."""
    ratio = width / height
    w = math.sqrt(H3_AREA * ratio)
    return max(256, round(w / 32) * 32), max(256, round(w / ratio / 32) * 32)


def h3_video(prompt: str, image: str | None, width: int, height: int, seconds: float, seed: int) -> dict:
    """The API-format workflow: Comfy's MiniMax H3 template with the 8-step Turbo LoRA on,
    flattened. `image` is the name ComfyUI gave the uploaded first frame, or None for words alone."""
    gen = {"prompt": prompt, "width": width, "height": height, "length": h3_frames(seconds),
           "clip": ["4", 0], "vae": ["5", 0]}
    wf = {
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": H3_FILES["model"], "weight_dtype": "default"}},
        "3": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"lora_name": H3_FILES["turbo"], "strength_model": 1.0, "model": ["2", 0]}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": H3_FILES["text"], "type": "minimax", "device": "default"}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": H3_FILES["video_vae"]}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": H3_FILES["audio_vae"]}},
        "7": {"class_type": "MiniMaxH3ImageToVideo", "inputs": gen},
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "10": {"class_type": "BasicScheduler",
               "inputs": {"scheduler": "simple", "steps": H3_TURBO_STEPS, "denoise": 1.0, "model": ["3", 0]}},
        "11": {"class_type": "BasicGuider", "inputs": {"model": ["3", 0], "conditioning": ["7", 0]}},
        "12": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["8", 0], "guider": ["11", 0], "sampler": ["9", 0], "sigmas": ["10", 0],
                          "latent_image": ["7", 1]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["5", 0]}},
        "14": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["12", 0], "vae": ["6", 0]}},
        "15": {"class_type": "CreateVideo",
               "inputs": {"fps": H3_FPS, "bit_depth": 8, "color_space": "sRGB", "codec": "none",
                          "images": ["13", 0], "audio": ["14", 0]}},
        "16": {"class_type": "SaveVideo",
               "inputs": {"filename_prefix": "studio/h3", "format": "auto", "format.codec": "auto", "codec": "auto",
                          "video": ["15", 0]}},
    }
    if image:
        wf["1"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        gen["first_frame"] = ["1", 0]
    return wf


def _model() -> str:
    _need_key("baseten")
    return os.environ[MODEL_ENV]


def _base() -> str:
    return f"https://model-{_model()}.api.baseten.co/environments/production/sync"


def headers() -> dict:
    return {"Authorization": f"Bearer {_need_key('baseten')}"}


def file_url(file: dict) -> str:
    """Where one saved result is fetched from. It needs headers()."""
    query = {"filename": file["filename"], "subfolder": file.get("subfolder", ""), "type": "output"}
    return f"{_base()}/view?{urlencode(query)}"


def _account_trouble(r: httpx.Response) -> None:
    if r.status_code in (401, 403):
        raise AccountError("Baseten did not accept the API key, or the account needs a payment method.", 502)
    if r.status_code == 429:
        raise AccountError("Baseten is busy. Try again in a moment.", 503, down=False)


async def _call(method: str, path: str, *, timeout: float = 60.0, **kw) -> httpx.Response:
    auth = headers()
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=20.0)) as client:
        r = await client.request(method, _base() + path, headers=auth, **kw)
    _account_trouble(r)
    return r


async def wake() -> None:
    """Ask Baseten to start the GPU now. It takes a minute or two from cold."""
    auth, model = headers(), _model()
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
        r = await client.post(f"https://model-{model}.api.baseten.co/production/wake", headers=auth)
    _account_trouble(r)


async def ready() -> bool:
    """Whether ComfyUI answers now. A cold GPU holds the request, so this gives up quickly."""
    try:
        r = await _call("GET", "/system_stats", timeout=READY_WAIT)
    except (httpx.TimeoutException, httpx.TransportError):
        return False
    return r.status_code == 200


async def upload(data: bytes, name: str) -> str:
    """Put a first frame in ComfyUI's input folder. Waits out a cold start. Returns its name there."""
    if len(data) > MAX_IMAGE:
        raise StudioError("That image is too large.")
    r = await _call("POST", "/upload/image", timeout=COLD_START,
                    files={"image": (name, data)}, data={"overwrite": "true"})
    if r.status_code != 200:
        # 422: ComfyUI refused it, so asking again will not help; anything else may pass next time
        raise StudioError(f"ComfyUI did not take the image: {_short(r.text) or r.status_code}.",
                          422 if r.status_code == 400 else 502)
    got = r.json()
    return f"{got['subfolder']}/{got['name']}" if got.get("subfolder") else got["name"]


async def queue(workflow: dict) -> str:
    """Start a workflow. Returns ComfyUI's prompt id."""
    r = await _call("POST", "/prompt", timeout=COLD_START, json={"prompt": workflow})
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200 or not body.get("prompt_id"):
        reason = body.get("error", {}).get("message") if isinstance(body.get("error"), dict) else body.get("error")
        raise StudioError(f"ComfyUI refused the workflow: {_short(reason or r.text) or r.status_code}.",
                          422 if r.status_code == 400 else 502)
    return body["prompt_id"]


async def status(prompt_id: str) -> tuple[str, list[dict], str]:
    """(state, saved files, reason). State is running, done or failed. A job in neither the queue
    nor the history was lost when the GPU restarted."""
    r = await _call("GET", f"/history/{prompt_id}")
    if r.status_code != 200:
        raise StudioError("ComfyUI could not be reached. Still waiting on the video.", 502)
    entry = r.json().get(prompt_id)
    if not entry:
        q = await _call("GET", "/queue")
        jobs = (q.json().get("queue_running") or []) + (q.json().get("queue_pending") or []) if q.status_code == 200 else None
        if jobs is None:
            raise StudioError("ComfyUI could not be reached. Still waiting on the video.", 502)
        if any(len(j) > 1 and j[1] == prompt_id for j in jobs):
            return "running", [], ""
        return "failed", [], "The GPU restarted before the video finished."
    st = entry.get("status") or {}
    if st.get("status_str") == "error":
        reason = next((m[1].get("exception_message") for m in st.get("messages", [])
                       if m[0] == "execution_error" and isinstance(m[1], dict)), "")
        return "failed", [], _short(reason) or "ComfyUI stopped with an error."
    if not st.get("completed"):
        return "running", [], ""
    files = [f for out in (entry.get("outputs") or {}).values() for f in out.get("images", [])
             if f.get("type") == "output"]
    return ("done", files, "") if files else ("failed", [], "ComfyUI finished without saving a file.")


async def forget(prompt_id: str) -> None:
    """Drop the job from ComfyUI's history once the studio has its copy."""
    await _call("POST", "/history", json={"delete": [prompt_id]})
