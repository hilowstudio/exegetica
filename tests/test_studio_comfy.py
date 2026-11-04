"""ComfyUI on Baseten (webapp/studio_comfy.py): each H3 workflow (words and frames, reference
pictures and pinned frames, a still) is wired whole, sized to the first frame or the chosen shape,
and asks only for files the deployment mounts; ComfyUI's replies are read as running, done or
failed, and a job the GPU lost on restart is not waited on forever. Baseten is a stand-in here; no
network, no cost."""
import asyncio
from pathlib import Path

import httpx
import pytest

from webapp import studio_comfy as comfy
from webapp.studio_services import StudioError

CONFIG = Path(__file__).resolve().parents[1] / "baseten" / "comfyui" / "config.yaml"
OUTPUTS = {"LoadImage": 2, "UNETLoader": 1, "LoraLoaderModelOnly": 1, "CLIPLoader": 1, "VAELoader": 1,
           "MiniMaxH3ImageToVideo": 2, "MiniMaxH3ReferenceToVideo": 2, "MiniMaxH3AddGuide": 1,
           "RandomNoise": 1, "KSamplerSelect": 1, "BasicScheduler": 1, "BasicGuider": 1,
           "SamplerCustomAdvanced": 2, "VAEDecode": 1, "VAEDecodeAudio": 1, "CreateVideo": 1, "SaveVideo": 1,
           "CLIPTextEncode": 1, "EmptyLatentImage": 1, "LTXVSeparateAVLatent": 2, "SaveImage": 0}


def wired_whole(wf: dict) -> None:
    for node in wf.values():
        assert node["class_type"] in OUTPUTS
        for value in node["inputs"].values():
            if isinstance(value, list):
                src, slot = value
                assert src in wf and slot < OUTPUTS[wf[src]["class_type"]]


def test_clip_lengths_land_on_the_models_frame_grid():
    assert comfy.h3_frames(5) == 124 and comfy.h3_frames(10) == 243 and comfy.h3_frames(15) == 362
    assert all(comfy.h3_frames(s) % 17 == 5 for s in range(1, 16))


def test_the_canvas_follows_the_first_frames_shape_at_768p():
    assert comfy.h3_size(1920, 1080) == (1344, 768)
    assert comfy.h3_size(1080, 1920) == (768, 1344)
    assert comfy.h3_size(800, 800) == (1024, 1024)
    for w, h in [(1000, 700), (640, 1137), (4000, 3000)]:
        cw, ch = comfy.h3_size(w, h)
        assert cw % 32 == 0 and ch % 32 == 0 and abs(cw / ch - w / h) < 0.06


@pytest.mark.parametrize("image", ["frame.png", None])
def test_the_workflow_is_wired_whole_and_turbo_is_on(image):
    wf = comfy.h3_video("a lighthouse at dusk", image, 1344, 768, 10, 7)
    wired_whole(wf)
    gen = wf["7"]["inputs"]
    assert (gen["prompt"], gen["width"], gen["height"], gen["length"]) == ("a lighthouse at dusk", 1344, 768, 243)
    assert ("first_frame" in gen) == ("1" in wf) == bool(image)
    assert wf["8"]["inputs"]["noise_seed"] == 7
    assert wf["10"]["inputs"]["steps"] == 8 and wf["3"]["inputs"]["lora_name"] == comfy.H3_FILES["turbo"]
    assert wf["11"]["inputs"]["model"] == ["3", 0]


def test_a_last_frame_ends_the_clip_with_or_without_a_first():
    wf = comfy.h3_video("the door closes", None, 1344, 768, 5, 1, last="end.png")
    wired_whole(wf)
    gen = wf["7"]["inputs"]
    assert gen["last_frame"] == ["17", 0] and wf["17"]["inputs"]["image"] == "end.png" and "first_frame" not in gen


def test_reference_pictures_and_pinned_frames_ride_the_reference_model_at_full_steps():
    wf = comfy.h3_refs("<Picture 1> waves at <Picture 2>", ["ann.png", "dog.png"],
                       [("start.png", 0), ("mid.png", 60), ("end.png", -1)], 1344, 768, 5, 9)
    wired_whole(wf)
    assert wf["2"]["inputs"]["unet_name"] == comfy.H3_FILES["ref_model"] and "3" not in wf   # no speed LoRA
    gen = wf["7"]["inputs"]
    assert gen["ref_images.ref_image_0"] == ["101", 0] and gen["ref_images.ref_image_1"] == ["102", 0]
    assert wf["101"]["inputs"]["image"] == "ann.png" and gen["length"] == 124
    # each pinned frame chains onto the last, and the guider samples from the end of the chain
    assert [wf[n]["inputs"]["frame_idx"] for n in ("301", "302", "303")] == [0, 60, -1]
    assert wf["301"]["inputs"]["positive"] == ["7", 0] and wf["303"]["inputs"]["positive"] == ["302", 0]
    assert wf["11"]["inputs"]["conditioning"] == ["303", 0] and wf["10"]["inputs"]["steps"] == comfy.H3_REF_STEPS


def test_pictures_alone_need_no_pinned_frames():
    wf = comfy.h3_refs("<Picture 1> walks a beach", ["ann.png"], [], 768, 1344, 10, 2)
    wired_whole(wf)
    assert wf["11"]["inputs"]["conditioning"] == ["7", 0] and not any(n.startswith("3") and len(n) == 3 for n in wf)


def test_a_still_is_one_frame_at_full_steps_saved_as_a_picture():
    wf = comfy.h3_still("an apple on a table", 1152, 864, 30, 4)
    wired_whole(wf)
    assert wf["8"]["inputs"] == {"width": 1152, "height": 864, "batch_size": 1}
    assert wf["11"]["inputs"]["steps"] == 30 and wf["12"]["inputs"]["model"] == ["2", 0]
    assert wf["16"]["class_type"] == "SaveImage" and "6" not in wf   # no sound, no audio decoder


def test_every_file_the_workflow_loads_is_one_the_deployment_mounts():
    mounted = CONFIG.read_text(encoding="utf-8")
    assert all(name in mounted for name in comfy.H3_FILES.values())


@pytest.fixture
def replies(monkeypatch):
    monkeypatch.setenv("BASETEN_API_KEY", "test-key")
    monkeypatch.setenv(comfy.MODEL_ENV, "abc123")
    seen = {"calls": [], "by_path": {}}

    async def fake_call(method, path, **kw):
        seen["calls"].append((method, path))
        return seen["by_path"].get(path.split("?")[0], httpx.Response(200, json={}))

    monkeypatch.setattr(comfy, "_call", fake_call)
    return seen


def test_history_reads_as_running_done_or_failed(replies):
    replies["by_path"]["/queue"] = httpx.Response(200, json={"queue_running": [[0, "p1", {}]], "queue_pending": []})
    assert asyncio.run(comfy.status("p1")) == ("running", [], "")

    replies["by_path"]["/queue"] = httpx.Response(200, json={"queue_running": [], "queue_pending": []})
    saved = {"filename": "h3_00001_.mp4", "subfolder": "studio", "type": "output"}
    replies["by_path"]["/history/p1"] = httpx.Response(200, json={"p1": {
        "status": {"status_str": "success", "completed": True},
        "outputs": {"16": {"images": [saved], "animated": [True]}}}})
    assert asyncio.run(comfy.status("p1")) == ("done", [saved], "")

    replies["by_path"]["/history/p1"] = httpx.Response(200, json={"p1": {"status": {
        "status_str": "error", "completed": False,
        "messages": [["execution_start", {}], ["execution_error", {"exception_message": "CUDA out of memory"}]]}}})
    assert asyncio.run(comfy.status("p1")) == ("failed", [], "CUDA out of memory")


def test_a_job_the_gpu_lost_on_restart_is_failed_not_waited_on(replies):
    replies["by_path"]["/queue"] = httpx.Response(200, json={"queue_running": [], "queue_pending": []})
    state, _, reason = asyncio.run(comfy.status("p1"))
    assert state == "failed" and "restarted" in reason


def test_a_job_that_finishes_between_the_two_questions_is_done_not_lost(replies):
    """Live on 2026-11-04 a 5-second still finished between the history and queue checks and was
    read as lost. The queue is now asked first, so the job is found in the history."""
    replies["by_path"]["/queue"] = httpx.Response(200, json={"queue_running": [], "queue_pending": []})
    saved = {"filename": "h3_still_00001_.png", "subfolder": "studio", "type": "output"}
    replies["by_path"]["/history/p1"] = httpx.Response(200, json={"p1": {
        "status": {"status_str": "success", "completed": True}, "outputs": {"16": {"images": [saved]}}}})
    assert asyncio.run(comfy.status("p1")) == ("done", [saved], "")
    assert replies["calls"] == [("GET", "/queue"), ("GET", "/history/p1")]


def test_a_refused_workflow_says_why_and_is_final(replies):
    replies["by_path"]["/prompt"] = httpx.Response(400, json={"error": {"type": "prompt_outputs_failed_validation",
                                                                      "message": "Value not in list: unet_name"}})
    with pytest.raises(StudioError) as e:
        asyncio.run(comfy.queue({}))
    assert "Value not in list" in e.value.message and e.value.status == 422


def test_without_the_deployment_id_nothing_is_sent(monkeypatch):
    monkeypatch.setenv("BASETEN_API_KEY", "test-key")
    monkeypatch.delenv(comfy.MODEL_ENV, raising=False)
    with pytest.raises(StudioError) as e:
        asyncio.run(comfy._call("GET", "/history/p1"))
    assert e.value.status == 503 and comfy.MODEL_ENV in e.value.message
