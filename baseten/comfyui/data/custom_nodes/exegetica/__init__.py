"""The Image Studio's own ComfyUI nodes on the maker's GPU (docs/decisions/0017-image-studio.md).

ExegeticaRewrite turns a short request into a detailed prompt with an abliterated Qwen3-8B
(Josiefied), which does not refuse. It runs as the first step of the same ComfyUI job as the
image or video, so ComfyUI's one-job-at-a-time queue keeps it from competing with a render for
GPU memory. Its output feeds the generation node's prompt and is also returned in the job's
history, so the studio can show the rewrite beside the maker's own words. The model loads once
into CPU memory, moves to the GPU only while it writes, and moves back after.

ExegeticaTail and ExegeticaJoin extend a clip: the tail (its last frames and the matching end of
its soundtrack) is anchored at the start of a new H3 clip, and the join puts the whole old clip
and the new frames after the overlap into one video.
"""
from __future__ import annotations

import logging
import os
import re
import threading

MODEL_DIR = "/models/rewriter"
PICTURE = re.compile(r"<?\b[Pp]icture\s+([1-9])\b>?")   # "Picture 2" becomes H3's <Picture 2>
THINKING = re.compile(r"<think>.*?</think>", re.S)
MAX_NEW_TOKENS = 400

logger = logging.getLogger("exegetica_nodes")
_lock = threading.Lock()
_loaded: dict = {}


def _model():
    if not _loaded:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        _loaded["tokenizer"] = AutoTokenizer.from_pretrained(MODEL_DIR)
        _loaded["model"] = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).eval()
        _loaded["bytes"] = sum(p.numel() * p.element_size() for p in _loaded["model"].parameters())
        logger.info("rewriter loaded: %.1f GB", _loaded["bytes"] / 1e9)
    return _loaded["tokenizer"], _loaded["model"], _loaded["bytes"]


def rewrite(system: str, prompt: str, seed: int) -> str:
    import torch

    import comfy.model_management as mm

    with _lock:
        tokenizer, model, size = _model()
        device = mm.get_torch_device()
        mm.free_memory(size + 2 * 1024 ** 3, device)   # room for the weights and a short generation
        model.to(device)
        try:
            # return_dict asks every transformers version for the same shape: ids and their mask
            enc = tokenizer.apply_chat_template(
                [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                add_generation_prompt=True, enable_thinking=False, return_tensors="pt", return_dict=True)
            ids, mask = enc["input_ids"].to(device), enc["attention_mask"].to(device)
            torch.manual_seed(seed % 2 ** 32)
            with torch.inference_mode():
                out = model.generate(input_ids=ids, attention_mask=mask, max_new_tokens=MAX_NEW_TOKENS,
                                     do_sample=True, temperature=0.7, top_p=0.8, top_k=20,
                                     pad_token_id=tokenizer.eos_token_id)
            text = tokenizer.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
        finally:
            model.to("cpu")
            mm.soft_empty_cache(force=True)
    return " ".join(THINKING.sub("", text).split()) or prompt


class ExegeticaRewrite:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "system": ("STRING", {"multiline": True}),
            "prompt": ("STRING", {"multiline": True}),
            "picture_tags": ("BOOLEAN", {"default": False}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
        }}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = "exegetica"

    def run(self, system, prompt, picture_tags, seed):
        text = rewrite(system, prompt, seed)
        if picture_tags:
            text = PICTURE.sub(lambda m: f"<Picture {m.group(1)}>", text)
        return {"ui": {"text": [text]}, "result": (text,)}


def _wave(audio, rate: int, channels: int):
    """An audio's waveform on the CPU at this sample rate and channel count, or None."""
    import comfy.audio

    if audio is None:
        return None
    wave = audio["waveform"].float().cpu()
    if audio["sample_rate"] != rate:
        wave = comfy.audio.resample(wave, audio["sample_rate"], rate)
    if wave.shape[1] != channels:
        wave = wave.mean(1, keepdim=True).expand(-1, channels, -1) if channels > 1 else wave.mean(1, keepdim=True)
    return wave


class ExegeticaTail:
    """The last `frames` frames of a clip, the end of its soundtrack that plays under them, and the
    clip's size on H3's 32-pixel grid."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",), "fps": ("FLOAT", {"default": 24.0}),
                             "frames": ("INT", {"default": 22, "min": 1, "max": 1000})},
                "optional": {"audio": ("AUDIO",)}}

    RETURN_TYPES = ("IMAGE", "AUDIO", "INT", "INT")
    RETURN_NAMES = ("frames", "audio", "width", "height")
    FUNCTION = "run"
    CATEGORY = "exegetica"

    def run(self, images, fps, frames, audio=None):
        tail = images[-frames:]
        tail_audio = None
        if audio is not None:
            keep = max(1, round(frames / fps * audio["sample_rate"]))
            tail_audio = {"waveform": audio["waveform"][..., -keep:], "sample_rate": audio["sample_rate"]}
        height, width = images.shape[1], images.shape[2]
        return tail, tail_audio, width - width % 32, height - height % 32


class ExegeticaJoin:
    """The whole first clip, then the second clip from the end of the overlap on, as one clip. The
    second clip's frames are scaled to the first's size if they differ, and the sound follows the
    pictures, with silence where a clip has none."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"first": ("IMAGE",), "then": ("IMAGE",), "fps": ("FLOAT", {"default": 24.0}),
                             "overlap": ("INT", {"default": 22, "min": 0, "max": 1000})},
                "optional": {"first_audio": ("AUDIO",), "then_audio": ("AUDIO",)}}

    RETURN_TYPES = ("IMAGE", "AUDIO")
    RETURN_NAMES = ("images", "audio")
    FUNCTION = "run"
    CATEGORY = "exegetica"

    def run(self, first, then, fps, overlap, first_audio=None, then_audio=None):
        import torch

        import comfy.utils

        after = then[overlap:].to(first.device, first.dtype)
        if after.shape[1:3] != first.shape[1:3]:
            after = comfy.utils.common_upscale(after.movedim(-1, 1), first.shape[2], first.shape[1],
                                               "bilinear", "center").movedim(1, -1)
        images = torch.cat([first, after], 0)
        if first_audio is None and then_audio is None:
            return images, None
        model = then_audio or first_audio
        rate, channels = model["sample_rate"], model["waveform"].shape[1]
        head = _wave(first_audio, rate, channels)
        if head is None:
            head = torch.zeros(1, channels, round(first.shape[0] / fps * rate))
        tail = _wave(then_audio, rate, channels)
        if tail is None:
            tail = torch.zeros(1, channels, round(after.shape[0] / fps * rate))
        else:
            tail = tail[..., round(overlap / fps * rate):]
        return images, {"waveform": torch.cat([head[:1], tail[:1]], -1), "sample_rate": rate}


NODE_CLASS_MAPPINGS = {"ExegeticaRewrite": ExegeticaRewrite, "ExegeticaTail": ExegeticaTail,
                       "ExegeticaJoin": ExegeticaJoin}
NODE_DISPLAY_NAME_MAPPINGS = {"ExegeticaRewrite": "Exegetica prompt rewrite", "ExegeticaTail": "Exegetica clip tail",
                              "ExegeticaJoin": "Exegetica join clips"}
