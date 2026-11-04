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

# MiniMax H3, the files Comfy's own templates load (baseten/comfyui/config.yaml): `model` makes a
# video from words, first and last frames, or a still; `ref_model` makes one from reference pictures
# and pictures pinned at set moments.
H3_FILES = {
    "model": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
    "ref_model": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
    "turbo": "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
    "text": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "video_vae": "minimax_h3_video_vae_int8_convrot.safetensors",
    "audio_vae": "minimax_h3_audio_vae_fp32.safetensors",
}
H3_FPS = 24
H3_AREA = 1344 * 768  # the model's 768p frame
H3_TURBO_STEPS = 8
H3_REF_STEPS = 20     # Comfy's reference template; its only speed LoRA is a 0.1 preview
H3_MAX_REFS = 9       # MiniMaxH3ReferenceToVideo takes ref_image_0 to ref_image_8
H3_OVERLAP = 22       # frames of the old clip anchored at the start of an extension (17k + 5, under a second)

# P-H3-Image, from Pruna's own LoRA workflows (PrunaAI/P-H3-Image-Comfy): the LoRA on H3's fl2va
# weights, both flow shifts at 1.0, its own text encoder and VAE, and 8 steps on a fixed grid.
PH3_FILES = {
    "lora": "p-h3-image_lora_bf16.safetensors",
    "text": "p-h3-image_text_encoder_int8_convrot.safetensors",
    "vae": "p-h3-image_vae_int8_convrot.safetensors",
}
PH3_SIGMAS = "1.0, 0.984753, 0.967905, 0.951688, 0.925372, 0.881923, 0.810083, 0.528718, 0.0"
PH3_EDIT_AREA = 4_000_000   # Pruna scales the image being edited to 4 megapixels
PH3_MAX_REFS = 7            # the image to edit plus seven more


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


def _loaders(model: str) -> dict:
    return {
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": H3_FILES[model], "weight_dtype": "default"}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": H3_FILES["text"], "type": "minimax", "device": "default"}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": H3_FILES["video_vae"]}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": H3_FILES["audio_vae"]}},
    }


def _sample_and_save(model: list, conditioning: list, latent: list, steps: int, seed: int) -> dict:
    """Sampling, decoding and the saved clip, shared by both video workflows (nodes 8 to 16)."""
    return {
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "10": {"class_type": "BasicScheduler",
               "inputs": {"scheduler": "simple", "steps": steps, "denoise": 1.0, "model": model}},
        "11": {"class_type": "BasicGuider", "inputs": {"model": model, "conditioning": conditioning}},
        "12": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["8", 0], "guider": ["11", 0], "sampler": ["9", 0], "sigmas": ["10", 0],
                          "latent_image": latent}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["5", 0]}},
        "14": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["12", 0], "vae": ["6", 0]}},
        "15": {"class_type": "CreateVideo",
               "inputs": {"fps": H3_FPS, "bit_depth": 8, "color_space": "sRGB", "codec": "none",
                          "images": ["13", 0], "audio": ["14", 0]}},
        "16": {"class_type": "SaveVideo",
               "inputs": {"filename_prefix": "studio/h3", "format": "auto", "format.codec": "auto", "codec": "auto",
                          "video": ["15", 0]}},
    }


def h3_video(prompt: str, image: str | None, width: int, height: int, seconds: float, seed: int,
             last: str | None = None) -> dict:
    """The API-format workflow: Comfy's MiniMax H3 template with the 8-step Turbo LoRA on,
    flattened. `image` and `last` are the names ComfyUI gave the uploaded first and last frames,
    or None. With neither, the video comes from words alone."""
    gen = {"prompt": prompt, "width": width, "height": height, "length": h3_frames(seconds),
           "clip": ["4", 0], "vae": ["5", 0]}
    wf = _loaders("model") | {
        "3": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"lora_name": H3_FILES["turbo"], "strength_model": 1.0, "model": ["2", 0]}},
        "7": {"class_type": "MiniMaxH3ImageToVideo", "inputs": gen},
    } | _sample_and_save(["3", 0], ["7", 0], ["7", 1], H3_TURBO_STEPS, seed)
    if image:
        wf["1"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        gen["first_frame"] = ["1", 0]
    if last:
        wf["17"] = {"class_type": "LoadImage", "inputs": {"image": last}}
        gen["last_frame"] = ["17", 0]
    return wf


def h3_refs(prompt: str, refs: list[str], pinned: list[tuple[str, int]], width: int, height: int,
            seconds: float, seed: int) -> dict:
    """Comfy's reference-to-video and multi-frame templates, flattened, at their full 20 steps.
    `refs` are uploaded pictures the prompt names <Picture 1>, <Picture 2> and on. `pinned` holds
    (uploaded picture, frame index) pairs that anchor the video at those frames, -1 being the last."""
    gen = {"prompt": prompt, "width": width, "height": height, "length": h3_frames(seconds),
           "ref_image_size": "match", "clip": ["4", 0], "vae": ["5", 0], "audio_vae": ["6", 0]}
    wf = _loaders("ref_model") | {"7": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": gen}}
    for i, name in enumerate(refs[:H3_MAX_REFS]):
        wf[str(101 + i)] = {"class_type": "LoadImage", "inputs": {"image": name}}
        gen[f"ref_images.ref_image_{i}"] = [str(101 + i), 0]
    positive = ["7", 0]
    for i, (name, frame) in enumerate(pinned):
        wf[str(201 + i)] = {"class_type": "LoadImage", "inputs": {"image": name}}
        wf[str(301 + i)] = {"class_type": "MiniMaxH3AddGuide",
                            "inputs": {"positive": positive, "latent": ["7", 1], "vae": ["5", 0], "audio_vae": ["6", 0],
                                       "image": [str(201 + i), 0], "frame_idx": frame}}
        positive = [str(301 + i), 0]
    return wf | _sample_and_save(["2", 0], positive, ["7", 1], H3_REF_STEPS, seed)


def h3_still(prompt: str, width: int, height: int, steps: int, seed: int) -> dict:
    """Comfy's MiniMax H3 text-to-image template, flattened: the video model draws one frame at
    full steps, with no Turbo LoRA, and the frame is saved as a PNG."""
    loaders = _loaders("model")
    del loaders["6"]   # a still has no sound
    return loaders | {
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 0]}},
        "8": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "10": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "11": {"class_type": "BasicScheduler", "inputs": {"scheduler": "simple", "steps": steps, "denoise": 1.0,
                                                          "model": ["2", 0]}},
        "12": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["7", 0]}},
        "13": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["9", 0], "guider": ["12", 0], "sampler": ["10", 0], "sigmas": ["11", 0],
                          "latent_image": ["8", 0]}},
        "14": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["13", 0]}},
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["5", 0]}},
        "16": {"class_type": "SaveImage", "inputs": {"filename_prefix": "studio/h3_still", "images": ["15", 0]}},
    }


def h3_extend(prompt: str, video: str, seconds: float, seed: int) -> dict:
    """An existing clip carried on: its last H3_OVERLAP frames and their sound anchored at the
    start of a new H3 clip of `seconds` (Turbo LoRA on, as in h3_video), then the whole old clip and
    the new frames after the overlap joined into one video. `video` is the uploaded clip's name.
    The new clip takes the old one's size."""
    gen = {"prompt": prompt, "width": ["31", 2], "height": ["31", 3], "length": h3_frames(seconds),
           "clip": ["4", 0], "vae": ["5", 0]}
    wf = _loaders("model") | {
        "3": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"lora_name": H3_FILES["turbo"], "strength_model": 1.0, "model": ["2", 0]}},
        "7": {"class_type": "MiniMaxH3ImageToVideo", "inputs": gen},
        "29": {"class_type": "LoadVideo", "inputs": {"file": video}},
        "30": {"class_type": "GetVideoComponents", "inputs": {"video": ["29", 0]}},
        "31": {"class_type": "ExegeticaTail",
               "inputs": {"images": ["30", 0], "audio": ["30", 1], "fps": ["30", 2], "frames": H3_OVERLAP}},
        "32": {"class_type": "MiniMaxH3AddGuide",
               "inputs": {"positive": ["7", 0], "latent": ["7", 1], "vae": ["5", 0], "audio_vae": ["6", 0],
                          "image": ["31", 0], "audio": ["31", 1], "frame_idx": 0}},
        "33": {"class_type": "ExegeticaJoin",
               "inputs": {"first": ["30", 0], "first_audio": ["30", 1], "then": ["13", 0], "then_audio": ["14", 0],
                          "fps": ["30", 2], "overlap": H3_OVERLAP}},
    } | _sample_and_save(["3", 0], ["32", 0], ["7", 1], H3_TURBO_STEPS, seed)
    wf["15"]["inputs"] |= {"images": ["33", 0], "audio": ["33", 1]}
    return wf


def ph3_size(width: int, height: int, area: int = PH3_EDIT_AREA) -> tuple[int, int]:
    """The size an image to edit is scaled to, up or down: about `area` pixels with its own shape,
    sides on the 32-pixel grid."""
    scale = math.sqrt(area / (width * height))
    return max(32, round(width * scale / 32) * 32), max(32, round(height * scale / 32) * 32)


def ph3_image(prompt: str, width: int, height: int, seed: int, pictures: list[str] = ()) -> dict:
    """P-H3-Image, from Pruna's LoRA workflows flattened. With no pictures it draws from words at
    width x height. With pictures it edits the first, the others serving as <Picture 2> and on, at
    the first picture's size (width and height 0)."""
    gen = {"prompt": prompt, "width": width, "height": height, "clip": ["4", 0], "vae": ["5", 0]}
    wf = {
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": H3_FILES["model"], "weight_dtype": "default"}},
        "3": {"class_type": "LoraLoaderBypassModelOnly",
              "inputs": {"model": ["2", 0], "lora_name": PH3_FILES["lora"], "strength_model": 1.0}},
        "6": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["3", 0], "shift_video": 1.0, "shift_audio": 1.0}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": PH3_FILES["text"], "type": "minimax", "device": "default"}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": PH3_FILES["vae"]}},
        "7": {"class_type": "PH3ImageConditioning", "inputs": gen},
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "10": {"class_type": "ManualSigmas", "inputs": {"sigmas": PH3_SIGMAS}},
        "11": {"class_type": "BasicGuider", "inputs": {"model": ["6", 0], "conditioning": ["7", 0]}},
        "12": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["8", 0], "guider": ["11", 0], "sampler": ["9", 0], "sigmas": ["10", 0],
                          "latent_image": ["7", 1]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["5", 0]}},
        "16": {"class_type": "SaveImage", "inputs": {"filename_prefix": "studio/p_h3_image", "images": ["13", 0]}},
    }
    for n, name in enumerate(list(pictures)[:PH3_MAX_REFS + 1]):
        wf[str(101 + n)] = {"class_type": "LoadImage", "inputs": {"image": name}}
        gen[f"images.image_{n + 1}"] = [str(101 + n), 0]
    return wf


def rewritten(wf: dict, system: str, prompt: str, picture_tags: bool, seed: int) -> dict:
    """The workflow with the GPU's own prompt rewriter (node ExegeticaRewrite, a Qwen3-8B
    in baseten/comfyui/data/custom_nodes) as its first step: the rewrite feeds node 7's
    prompt and comes back in the job's history."""
    wf["20"] = {"class_type": "ExegeticaRewrite",
                "inputs": {"system": system, "prompt": prompt, "picture_tags": picture_tags, "seed": seed}}
    words = "text" if "text" in wf["7"]["inputs"] else "prompt"
    wf["7"]["inputs"][words] = ["20", 0]
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


async def upload(data: bytes, name: str, limit: int = MAX_IMAGE) -> str:
    """Put a picture, or a clip to extend, in ComfyUI's input folder. Waits out a cold start.
    Returns its name there."""
    if len(data) > limit:
        raise StudioError("That file is too large.")
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


async def status(prompt_id: str) -> tuple[str, list[dict], str, list[str]]:
    """(state, saved files, reason, texts the job returned, such as the rewritten prompt). State is
    running, done or failed. A job in neither the queue nor the history was lost when the GPU
    restarted. The queue is asked first: ComfyUI moves a finished job from the queue to the
    history in one step, so a job that ends between the two questions is found in the history
    (asked the other way round, a still that renders in five seconds was read as lost)."""
    q = await _call("GET", "/queue")
    if q.status_code != 200:
        raise StudioError("ComfyUI could not be reached. Still waiting on the GPU.", 502)
    jobs = (q.json().get("queue_running") or []) + (q.json().get("queue_pending") or [])
    if any(len(j) > 1 and j[1] == prompt_id for j in jobs):
        return "running", [], "", []
    r = await _call("GET", f"/history/{prompt_id}")
    if r.status_code != 200:
        raise StudioError("ComfyUI could not be reached. Still waiting on the GPU.", 502)
    entry = r.json().get(prompt_id)
    if not entry:
        return "failed", [], "The GPU restarted before the job finished.", []
    st = entry.get("status") or {}
    if st.get("status_str") == "error":
        reason = next((m[1].get("exception_message") for m in st.get("messages", [])
                       if m[0] == "execution_error" and isinstance(m[1], dict)), "")
        return "failed", [], _short(reason) or "ComfyUI stopped with an error.", []
    if not st.get("completed"):
        return "running", [], "", []
    outputs = (entry.get("outputs") or {}).values()
    files = [f for out in outputs for f in out.get("images", []) if f.get("type") == "output"]
    texts = [t for out in outputs for t in out.get("text", []) if isinstance(t, str)]
    return ("done", files, "", texts) if files else ("failed", [], "ComfyUI finished without saving a file.", [])


async def forget(prompt_id: str) -> None:
    """Drop the job from ComfyUI's history once the studio has its copy."""
    await _call("POST", "/history", json={"delete": [prompt_id]})
