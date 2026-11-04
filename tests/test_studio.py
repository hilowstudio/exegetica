"""Media Studio (webapp/studio.py): the maker's login only; each run on the cheapest service that is
set up and able, handed to the next when one turns the account away; each service called in the
shape its docs give, with the least retention each allows; images and videos kept in a private R2
folder; videos followed until done; cleanup when a run fails or an item is deleted. Every
service, the prompt rewrite, the price book, and R2 are stand-ins here; no network, no cost."""
import base64
import io
import json

import httpx
import pytest
from PIL import Image
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from webapp import auth, metrics, r2, studio, studio_prices
from webapp import studio_comfy as comfy
from webapp import studio_services as svc

ADMIN = {"id": "00000000-0000-0000-0000-0000000000aa", "email": "maker@school.test", "role": "teacher"}
TEACHER = {"id": "00000000-0000-0000-0000-0000000000bb", "email": "t@school.test", "role": "teacher"}
PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG fake bytes").decode()
JPEG_B64 = base64.b64encode(b"runware jpeg bytes").decode()
ALL = {"fal", "runware", "wavespeed", "replicate", "baseten"}


@pytest.fixture
def env(monkeypatch):
    seen = {"who": ADMIN, "store": {}, "fal": [], "queue": [], "runware": [], "wavespeed": [], "replicate": [],
            "downloads": [], "rows": [], "rewrites": [], "forgotten": [], "keys": {"fal", "runware"},
            "book": {"routes": {}}}
    monkeypatch.setattr(auth, "current_user", lambda request: seen["who"])
    monkeypatch.setattr(auth, "is_admin", lambda u: bool(u) and u["email"] == ADMIN["email"])
    monkeypatch.setattr(metrics, "record", lambda row: seen["rows"].append(row))
    monkeypatch.setattr(svc, "_key", lambda service: "test-key" if service in seen["keys"] else None)
    monkeypatch.setattr(studio, "FOLLOW", False)        # the page's checks drive videos here
    monkeypatch.setattr(studio, "AUTO_REFRESH", False)  # and no price check reaches out
    monkeypatch.setattr(studio, "_down", {})

    async def load(fresh=False):
        return seen["book"]
    monkeypatch.setattr(studio_prices, "load", load)

    store = seen["store"]
    monkeypatch.setattr(r2, "configured", lambda: True)

    async def get_bytes(key):
        return store.get(key, (None,))[0]

    async def put_bytes(key, data, content_type):
        store[key] = (data, content_type)

    async def delete(key):
        store.pop(key, None)

    async def get_object(key):
        return store.get(key)
    monkeypatch.setattr(r2, "get_bytes_async", get_bytes)
    monkeypatch.setattr(r2, "put_bytes_async", put_bytes)
    monkeypatch.setattr(r2, "delete_async", delete)
    monkeypatch.setattr(r2, "get_object_async", get_object)
    monkeypatch.setattr(r2, "presign_get", lambda key, expires=600: f"https://r2.test/{key}?signed&exp={expires}")

    def replying(name, default):
        async def fake(*args):
            seen[name].append(args if len(args) > 1 else args[0])
            reply = seen.get(name + "_reply")
            if isinstance(reply, Exception):
                raise reply
            return reply(*args) if reply else default(*args)
        return fake

    def fal_default(model, body):
        return {"images": [{"url": "https://fal.media/x.jpg", "width": 1024, "height": 1024, "content_type": "image/jpeg"}],
                "seed": 7, "has_nsfw_concepts": [False]}

    def queue_default(method, url, body=None):
        if method == "POST":
            return 200, {"status": "IN_QUEUE", "request_id": "req-1",
                         "status_url": f"{svc.FAL_QUEUE}/kling/v4/requests/req-1/status",
                         "response_url": f"{svc.FAL_QUEUE}/kling/v4/requests/req-1"}
        return 202, {"status": "IN_PROGRESS", "request_id": "req-1"}

    def runware_default(tasks):
        task = tasks[0]
        if task["taskType"] == "imageInference":
            return {"data": [{"taskType": "imageInference", "taskUUID": task["taskUUID"], "imageUUID": "u",
                              "imageBase64Data": JPEG_B64, "seed": 11, "cost": 0.0141, "NSFWContent": False}]}
        return {"data": [{"taskType": task["taskType"], "taskUUID": task["taskUUID"]}]}

    def wavespeed_default(method, path, body=None):
        if method == "POST" and path.startswith("/wavespeed-ai/"):
            return {"id": "ws-1", "status": "created"}
        if path == "/predictions/ws-1/result":
            return {"id": "ws-1", "status": "processing", "outputs": []}
        return {}

    def replicate_default(method, url, body=None):
        if method == "POST":
            return 201, {"id": "rp-1", "status": "starting", "urls": {"get": f"{svc.REPLICATE_API}/predictions/rp-1"}}
        return 200, {"id": "rp-1", "status": "processing"}

    async def fake_forget(request_id):
        seen["forgotten"].append(request_id)

    async def fake_download(url, limit=svc.MAX_IMAGE, headers=None):
        seen["downloads"].append((url, headers))
        if seen.get("download_fails"):
            raise svc.StudioError("The finished file could not be fetched from the service.", 502)
        return b"mp4 bytes 0123456789" if url.endswith(".mp4") else b"jpeg bytes"

    async def fake_rewrite(prompt, purpose):
        seen["rewrites"].append((prompt, purpose))
        return f"A detailed picture of {prompt}", 0.0003
    monkeypatch.setattr(svc, "fal_run", replying("fal", fal_default))
    monkeypatch.setattr(svc, "fal_queue", replying("queue", queue_default))
    monkeypatch.setattr(svc, "runware_call", replying("runware", runware_default))
    monkeypatch.setattr(svc, "wavespeed_call", replying("wavespeed", wavespeed_default))
    monkeypatch.setattr(svc, "replicate_call", replying("replicate", replicate_default))
    monkeypatch.setattr(svc, "fal_delete_files", fake_forget)
    monkeypatch.setattr(studio, "_download", fake_download)
    monkeypatch.setattr(studio, "rewrite", fake_rewrite)

    # The maker's GPU: ComfyUI on Baseten, awake once `comfy_ready` is set.
    seen.update(comfy=[], comfy_ready=False, comfy_state=("running", [], "", []))

    async def comfy_call(name, *args):
        seen["comfy"].append((name,) + args)
        if isinstance(seen.get("comfy_raise"), Exception) and name in ("upload", "queue"):
            raise seen["comfy_raise"]
    monkeypatch.setattr(comfy, "wake", lambda: comfy_call("wake"))

    async def ready():
        return seen["comfy_ready"]

    async def upload(data, name, limit=svc.MAX_IMAGE):
        await comfy_call("upload", data, name)
        return name

    async def queue(workflow):
        await comfy_call("queue", workflow)
        return "prompt-1"

    async def status(prompt_id):
        return seen["comfy_state"]
    monkeypatch.setattr(comfy, "ready", ready)
    monkeypatch.setattr(comfy, "upload", upload)
    monkeypatch.setattr(comfy, "queue", queue)
    monkeypatch.setattr(comfy, "status", status)
    monkeypatch.setattr(comfy, "forget", lambda prompt_id: comfy_call("forget", prompt_id))
    monkeypatch.setattr(comfy, "headers", lambda: {"Authorization": "Bearer test-key"})
    monkeypatch.setattr(comfy, "file_url", lambda f: "https://model-x.api.baseten.co/sync/view/" + f["filename"])

    app = Starlette(middleware=[Middleware(SessionMiddleware, secret_key="test")], routes=[
        Route("/api/studio/folders", studio.create_folder, methods=["POST"]),
        Route("/api/studio/folders/{folder_id}", studio.change_folder, methods=["PATCH"]),
        Route("/api/studio/folders/{folder_id}", studio.delete_folder, methods=["DELETE"]),
        Route("/api/studio/folders/{folder_id}/unlock", studio.unlock_folder, methods=["POST"]),
        Route("/api/studio/folders/{folder_id}/lock", studio.lock_folder, methods=["POST"]),
        Route("/api/studio/folders/{folder_id}/cover", studio.folder_cover),
        Route("/api/studio/items/move", studio.move_items, methods=["POST"]),
        Route("/api/studio/items/delete", studio.delete_items, methods=["POST"]),
        Route("/studio", studio.page),
        Route("/api/studio/config", studio.config),
        Route("/api/studio/quote", studio.quote, methods=["POST"]),
        Route("/api/studio/prices", studio.refresh_prices_now, methods=["POST"]),
        Route("/api/studio/images", studio.list_images),
        Route("/api/studio/generate", studio.generate, methods=["POST"]),
        Route("/api/studio/image/{image_id}", studio.image, methods=["GET"]),
        Route("/api/studio/image/{image_id}", studio.delete_image, methods=["DELETE"]),
        Route("/api/studio/image/{image_id}/check", studio.check_job),
    ])
    seen["client"] = TestClient(app)
    return seen


def make(env, **body):
    return env["client"].post("/api/studio/generate", json={"prompt": "an apple on a table", "rewrite": False, **body})


def check(env, item):
    return env["client"].get(f"/api/studio/image/{item['id']}/check")


def quote(env, **body):
    return env["client"].post("/api/studio/quote", json=body).json()


# ---------------------------------------------------------------- who can reach it
@pytest.mark.parametrize("who", [None, TEACHER])
def test_no_one_but_the_maker_can_find_it(env, who):
    env["who"] = who
    c = env["client"]
    some = "a" * 32
    for r in (c.get("/studio"), c.get("/api/studio/config"), c.get("/api/studio/images"), make(env),
              c.post("/api/studio/quote", json={}), c.post("/api/studio/prices"),
              c.get(f"/api/studio/image/{some}"), c.delete(f"/api/studio/image/{some}"),
              c.get(f"/api/studio/image/{some}/check")):
        assert r.status_code == 404
    assert env["fal"] == env["runware"] == env["queue"] == env["replicate"] == []


def test_the_menu_lists_each_model_once_with_its_services(env):
    env["keys"] = {"fal"}
    cfg = env["client"].get("/api/studio/config").json()
    assert cfg["ready"] is True and set(cfg["services"]) == ALL
    assert cfg["services"]["replicate"]["ready"] is False and cfg["services"]["replicate"]["env"] == "REPLICATE_API_TOKEN"
    wan = next(m for m in cfg["models"] if m["id"] == "wan-3")
    assert wan["services"] == ["fal", "runware", "replicate"] and wan["sizes"][0] == "wide"
    assert cfg["prices"]["checked"] is None and cfg["prices"]["stale"] is True


def test_every_image_model_has_a_sourced_card_and_every_task_a_model_that_does_it(env):
    images = {k for k, m in studio.MODELS.items() if "video" not in m["does"]}
    assert set(studio.CARDS) == images
    for model_id, card in studio.CARDS.items():
        assert card["best"] and card["good"] and card["weak"] and card["sources"], model_id
        assert all(s["url"].startswith("https://") and s["label"] for s in card["sources"]), model_id
        both = set(studio.MODELS[model_id]["does"]) == {"create", "edit"}
        assert both == all(k in card for k in ("best_edit", "good_edit", "weak_edit")), model_id
    for mode, tasks in studio.TASKS.items():
        assert tasks and len({t["key"] for t in tasks}) == len(tasks)
        assert all(mode in studio.MODELS[t["model"]]["does"] for t in tasks), mode
    cfg = env["client"].get("/api/studio/config").json()
    assert cfg["tasks"] == studio.TASKS
    menu = {m["id"]: m for m in cfg["models"]}
    assert menu["qwen-pro"]["card"] == studio.CARDS["qwen-pro"] and menu["qwen-pro"]["max_size"]
    assert not menu["wan-3"].get("card")


def test_the_sample_set_covers_every_image_model():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "webapp" / "static" / "studio-samples"
    samples = json.loads((root / "samples.json").read_text(encoding="utf-8"))
    for model_id, m in studio.MODELS.items():
        if "video" in m["does"]:
            continue
        made = samples["results"][model_id]
        if "create" in m["does"]:
            assert all(k in made for k in samples["strip"]), model_id
        if "edit" in m["does"]:
            assert all("edit-" + e["key"] in made for e in samples["edits"]), model_id
        assert all((root / x["file"]).is_file() for x in made.values()), model_id


# ---------------------------------------------------------------- choosing the service
def test_each_run_goes_to_the_cheapest_set_up_service(env):
    env["keys"] = ALL
    assert quote(env, mode="video", model="wan-3")["choice"]["service"] == "replicate"
    assert quote(env, mode="video", model="hunyuan-video")["choice"]["service"] == "wavespeed"
    assert quote(env, mode="create", model="flux-schnell")["choice"]["service"] == "runware"
    item = make(env, mode="video", model="wan-3").json()["image"]
    assert item["service"] == "replicate" and item["service_label"] == "Replicate" and env["replicate"]


def test_todays_prices_change_the_choice(env):
    env["keys"] = ALL
    env["book"] = {"routes": {"wan-3:fal": {"usd": 0.03, "status": "ok"}}}
    q = quote(env, mode="video", model="wan-3", seconds=10)
    assert q["choice"]["service"] == "fal" and q["choice"]["usd"] == pytest.approx(0.30)
    assert [s["service"] for s in q["services"]] == ["fal", "replicate", "runware"]


def test_a_chosen_service_is_used_even_when_dearer(env):
    env["keys"] = ALL
    make(env, mode="video", model="wan-3", service="fal")
    assert env["queue"] and not env["replicate"]


def test_a_service_that_turns_the_account_away_hands_the_run_to_the_next(env):
    env["keys"] = ALL
    env["replicate_reply"] = svc.AccountError("The Replicate account is out of credit.", 402)
    item = make(env, mode="video", model="wan-3").json()["image"]
    assert item["service"] == "fal" and len(env["replicate"]) == 1
    replicate = next(s for s in quote(env, mode="video", model="wan-3")["services"] if s["service"] == "replicate")
    assert replicate["usable"] is False and "turned the account away" in replicate["reason"]


def test_sound_off_skips_a_service_that_always_adds_sound(env):
    env["keys"] = ALL
    q = quote(env, mode="video", model="wan-3", audio=False)
    assert q["choice"]["service"] in ("fal", "runware")
    assert next(s for s in q["services"] if s["service"] == "replicate")["reason"] == "always adds sound"


def test_a_length_only_one_service_makes_goes_there(env):
    env["keys"] = {"fal"}
    r = make(env, mode="video", model="hunyuan-video", seconds=8)
    assert r.status_code == 400 and "makes other lengths" in r.json()["error"]
    env["keys"] = {"fal", "wavespeed"}
    assert make(env, mode="video", model="hunyuan-video", seconds=8).json()["image"]["service"] == "wavespeed"


def test_a_model_with_no_service_set_up_names_the_keys(env):
    env["keys"] = set()
    r = make(env, mode="video", model="wan-3")
    assert r.status_code == 503
    assert all(k in r.json()["error"] for k in ("FAL_API_KEY", "RUNWARE_API_KEY", "REPLICATE_API_TOKEN"))
    assert env["queue"] == env["runware"] == env["replicate"] == [] and env["rewrites"] == []


# ---------------------------------------------------------------- fal images
def test_a_fast_image_is_made_stored_privately_and_listed(env):
    r = make(env, model="flux-schnell", service="fal", shape="wide", steps=40)
    assert r.status_code == 200, r.text
    img = r.json()["image"]
    model, body = env["fal"][0]
    assert model == "fal-ai/flux/schnell"
    assert body["image_size"] == {"width": 1024, "height": 576} and body["num_inference_steps"] == 4
    assert body["enable_safety_checker"] is True and body["prompt"] == "an apple on a table"
    assert "key" not in img and "source_key" not in img and img["url"] == f"/api/studio/image/{img['id']}"
    assert img["est_usd"] == pytest.approx(0.003 * 1024 * 576 / 1e6, abs=1e-4)
    stored = [k for k in env["store"] if k.endswith(".jpg")]
    assert stored == [f"studio/{ADMIN['id']}/{img['id']}.jpg"]
    assert env["client"].get(img["url"]).content == b"jpeg bytes"
    assert [i["id"] for i in env["client"].get("/api/studio/images").json()["images"]] == [img["id"]]
    assert env["rows"][-1]["route"] == "studio" and env["rows"][-1]["outcome"] == "complete"


def test_quality_takes_the_steps_asked_within_its_limit(env):
    make(env, model="flux-dev", service="fal", steps=80)
    model, body = env["fal"][0]
    assert model == "fal-ai/flux/dev" and body["num_inference_steps"] == 50


def test_the_rewrite_is_used_and_shown_beside_the_original(env):
    img = make(env, model="flux-schnell", service="fal", rewrite=True).json()["image"]
    assert env["fal"][0][1]["prompt"] == "A detailed picture of an apple on a table"
    assert img["prompt"] == "an apple on a table" and img["rewritten"] is True
    assert env["rewrites"] == [("an apple on a table", "create")]


def test_an_uploaded_image_is_edited_and_goes_when_the_edit_is_deleted(env):
    img = make(env, mode="edit", model="flux-kontext", service="fal", prompt="make the apple green", shape="portrait",
               source={"data_url": PNG}).json()["image"]
    model, body = env["fal"][0]
    assert model == "fal-ai/flux-pro/kontext" and body["aspect_ratio"] == "3:4"
    assert body["image_url"].startswith("https://r2.test/studio/") and "-source.png" in body["image_url"]
    assert img["est_usd"] == pytest.approx(0.04)
    assert any(k.endswith("-source.png") for k in env["store"])
    assert env["client"].delete(img["url"]).status_code == 200
    assert not [k for k in env["store"] if k.endswith((".jpg", ".png"))]


def test_editing_an_earlier_image_leaves_that_image_in_place(env):
    first = make(env, model="flux-schnell", service="fal").json()["image"]
    edit = make(env, mode="edit", model="flux-kontext", service="fal", prompt="add a pear",
                source={"id": first["id"]}).json()["image"]
    env["client"].delete(edit["url"])
    assert env["client"].get(first["url"]).status_code == 200


def test_a_blocked_image_is_never_stored(env):
    env["fal_reply"] = lambda model, body: {"images": [{"url": "https://fal.media/black.jpg"}], "has_nsfw_concepts": [True]}
    r = make(env, model="flux-schnell", service="fal")
    assert r.status_code == 422 and "safety check" in r.json()["error"]
    assert not [k for k in env["store"] if k.endswith(".jpg")]
    assert env["rows"][-1]["outcome"] == "refused"


def test_a_failed_edit_removes_its_upload(env):
    env["download_fails"] = True
    r = make(env, mode="edit", model="flux-kontext", service="fal", prompt="make it green", source={"data_url": PNG})
    assert r.status_code == 502
    assert env["store"] == {}


def test_a_bad_upload_is_refused(env):
    r = make(env, mode="edit", source={"data_url": "data:text/html;base64,PGI+"})
    assert r.status_code == 400 and env["fal"] == env["runware"] == []


# ---------------------------------------------------------------- Runware images
def test_runware_returns_the_image_inline_with_its_own_prompt_expansion_off(env):
    img = make(env, model="qwen-turbo", shape="landscape").json()["image"]
    (task,) = env["runware"][0]
    assert task["taskType"] == "imageInference" and task["model"] == "alibaba:qwen-image@2.1-turbo"
    assert task["outputType"] == "base64Data"           # so Runware never hosts a copy
    assert task["safety"] == {"checkContent": True} and task["includeCost"] is True
    assert task["settings"] == {"promptExtend": False}  # the prompt sent is the prompt shown
    assert (task["width"], task["height"]) == (1024, 768) and "steps" not in task
    assert env["store"][f"studio/{ADMIN['id']}/{img['id']}.jpg"][0] == b"runware jpeg bytes"
    assert img["est_usd"] == pytest.approx(0.0141) and img["service"] == "runware"
    assert env["downloads"] == []


def test_runware_edits_from_the_image_inline(env):
    make(env, mode="edit", model="flux2-klein", prompt="make it green", source={"data_url": PNG})
    (task,) = env["runware"][0]
    assert task["inputs"] == {"referenceImages": [PNG]} and task["steps"] == 4


def test_runware_kontext_takes_its_own_sizes(env):
    make(env, mode="edit", model="flux-kontext", service="runware", shape="wide", source={"data_url": PNG})
    (task,) = env["runware"][0]
    assert (task["width"], task["height"]) == (1392, 752) and task["providerSettings"]["bfl"]["safetyTolerance"] == 2


def test_runware_flags_a_blocked_image(env):
    env["runware_reply"] = lambda tasks: {"data": [{"taskUUID": tasks[0]["taskUUID"], "imageBase64Data": JPEG_B64,
                                                     "NSFWContent": True}]}
    r = make(env, model="flux-dev", service="runware")
    assert r.status_code == 422 and not [k for k in env["store"] if k.endswith(".jpg")]


def test_an_all_black_image_counts_as_blocked(env):
    # Runware's FLUX schnell once sent a black frame with no flag set (2026-11-04)
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "black").save(buf, "JPEG")
    black = base64.b64encode(buf.getvalue()).decode()
    env["runware_reply"] = lambda tasks: {"data": [{"taskUUID": tasks[0]["taskUUID"], "imageBase64Data": black,
                                                     "NSFWContent": False}]}
    r = make(env, model="flux-schnell", service="runware")
    assert r.status_code == 422 and "safety check" in r.json()["error"]
    assert not [k for k in env["store"] if k.endswith(".jpg")]
    assert env["rows"][-1]["outcome"] == "refused"


def test_runware_says_why_it_would_not_make_an_image(env):
    env["runware_reply"] = lambda tasks: {"errors": [{"code": "invalidWidth", "message": "Width must be a multiple of 64.",
                                                       "taskUUID": tasks[0]["taskUUID"]}]}
    r = make(env, model="flux-dev", service="runware")
    assert r.status_code == 502 and "multiple of 64" in r.json()["error"]


# ---------------------------------------------------------------- video on Runware
def test_a_runware_video_starts_waits_and_lands_in_the_private_folder(env):
    r = make(env, mode="video", model="veo-fast", shape="tall", seconds=8, audio=True, rewrite=True)
    assert r.status_code == 200, r.text
    item = r.json()["image"]
    assert item["status"] == "pending" and item["url"] is None and "job" not in item
    assert env["rewrites"] == [("an apple on a table", "video")]
    (task,) = env["runware"][0]
    assert task["taskType"] == "videoInference" and task["model"] == "google:3@3"
    assert task["deliveryMethod"] == "async" and task["ttl"] == studio.RUNWARE_VIDEO_TTL
    assert (task["width"], task["height"]) == (720, 1280) and task["duration"] == 8
    assert task["providerSettings"] == {"google": {"generateAudio": True}}
    assert item["est_usd"] == pytest.approx(0.0003 + 0.15 * 8, abs=1e-4)
    assert env["rows"] == []   # the row waits for the video to finish

    progress = {"n": 40}

    def reply(tasks):
        t = tasks[0]
        if progress["n"] < 100:
            return {"data": [{"taskUUID": t["taskUUID"], "status": "processing", "progress": progress["n"]}]}
        return {"data": [{"taskUUID": t["taskUUID"], "status": "success", "videoURL": "https://vm.runware.ai/v.mp4",
                          "cost": 1.2}]}
    env["runware_reply"] = reply
    r = check(env, item)
    assert r.json()["image"]["status"] == "pending" and r.json()["image"]["progress"] == 40
    progress["n"] = 100
    done = check(env, item).json()["image"]
    assert done["status"] == "ready" and done["url"] == f"/api/studio/image/{item['id']}" and done["ext"] == "mp4"
    assert env["store"][f"studio/{ADMIN['id']}/{item['id']}.mp4"] == (b"mp4 bytes 0123456789", "video/mp4")
    assert done["est_usd"] == pytest.approx(1.2003, abs=1e-4)   # what Runware charged, plus the rewrite
    assert env["rows"][-1]["route"] == "studio:video" and env["rows"][-1]["outcome"] == "complete"
    assert check(env, item).json()["image"]["status"] == "ready" and len(env["downloads"]) == 1
    assert env["forgotten"] == []   # Runware's link expires on its own


def test_a_first_frame_replaces_the_size_and_the_rewrite_animates(env):
    first = make(env, model="flux-schnell", service="fal").json()["image"]
    make(env, mode="video", model="h3-max-turbo", service="runware", shape="wide", source={"id": first["id"]}, rewrite=True)
    (task,) = env["runware"][-1]
    assert task["inputs"] == {"frameImages": ["data:image/jpeg;base64," + base64.b64encode(b"jpeg bytes").decode()]}
    assert "width" not in task and task["resolution"] == "768p"
    assert task["settings"] == {"promptExpansion": "disabled"}
    assert env["rewrites"][-1][1] == "animate"


def test_a_failed_video_says_why_and_costs_nothing(env):
    item = make(env, mode="video", model="kling-3").json()["image"]
    assert env["runware"][0][0]["providerSettings"] == {"klingai": {"sound": False}}
    env["runware_reply"] = lambda tasks: {"errors": [{"code": "timeoutProvider", "message": "The provider timed out.",
                                                       "taskUUID": tasks[0]["taskUUID"]}]}
    failed = check(env, item).json()["image"]
    assert failed["status"] == "failed" and "timed out" in failed["error"] and failed["est_usd"] == 0
    assert env["rows"][-1]["outcome"] == "provider_error"


def test_a_runware_hiccup_while_waiting_leaves_the_video_pending(env):
    item = make(env, mode="video", model="kling-3").json()["image"]
    env["runware_reply"] = lambda tasks: {"errors": [{"code": "serviceOverloaded", "message": "Busy."}]}
    assert check(env, item).status_code == 502
    assert env["client"].get("/api/studio/images").json()["images"][0]["status"] == "pending"


# ---------------------------------------------------------------- video on fal
def _fal_done(result_code=200, result=None, status=None):
    def reply(method, url, body=None):
        if url.endswith("/status"):
            return 200, status or {"status": "COMPLETED", "request_id": "req-1"}
        return result_code, result if result is not None else {"video": {"url": "https://v3.fal.media/files/v.mp4"}}
    return reply


def test_a_fal_video_queues_waits_and_lands_in_the_private_folder(env):
    item = make(env, mode="video", model="kling-4", service="fal", shape="square", seconds=10).json()["image"]
    method, url, body = env["queue"][0]
    assert (method, url) == ("POST", f"{svc.FAL_QUEUE}/kling/v4/text-to-video")
    assert body == {"prompt": "an apple on a table", "resolution": "720p", "duration": 10, "aspect_ratio": "1:1"}
    assert item["status"] == "pending" and item["est_usd"] == pytest.approx(1.57)
    assert check(env, item).json()["image"]["status"] == "pending"
    assert env["queue"][-1][:2] == ("GET", f"{svc.FAL_QUEUE}/kling/v4/requests/req-1/status")
    env["queue_reply"] = _fal_done()
    done = check(env, item).json()["image"]
    assert done["status"] == "ready" and done["est_usd"] == pytest.approx(1.57)   # fal reports no cost; the quoted price
    assert env["queue"][-1][:2] == ("GET", f"{svc.FAL_QUEUE}/kling/v4/requests/req-1")
    assert env["store"][f"studio/{ADMIN['id']}/{item['id']}.mp4"][1] == "video/mp4"
    assert env["forgotten"] == ["req-1"]   # fal is asked to delete its copy once ours is saved


def test_a_fal_first_frame_goes_to_the_frame_endpoint_by_presigned_link(env):
    first = make(env, model="flux-schnell", service="fal").json()["image"]
    make(env, mode="video", model="gemini-omni", shape="tall", seconds=6, source={"id": first["id"]})
    method, url, body = env["queue"][0]
    assert url == f"{svc.FAL_QUEUE}/google/gemini-omni-flash/v1.1/image-to-video"
    assert body["image_url"].startswith("https://r2.test/studio/") and f"exp={studio.SOURCE_SECONDS}" in body["image_url"]
    assert body["aspect_ratio"] == "9:16"   # this endpoint still wants a shape
    make(env, mode="video", model="wan-3", service="fal", shape="tall", audio=False, source={"id": first["id"]})
    body = env["queue"][-1][2]
    assert "aspect_ratio" not in body and body["start_image_url"].startswith("https://r2.test/")   # Wan follows the frame
    assert body["audio"] is False and body["enable_prompt_expansion"] is False


def test_minimax_h3_goes_to_fal_at_768p_with_its_own_rewriting_off(env):
    item = make(env, mode="video", model="h3", shape="tall", seconds=10).json()["image"]
    method, url, body = env["queue"][0]
    assert url == f"{svc.FAL_QUEUE}/minimax/h3/text-to-video" and item["service"] == "fal"
    assert body == {"prompt": "an apple on a table", "resolution": "768P", "prompt_expansion_mode": "disabled",
                    "enable_safety_checker": True, "duration": 10, "aspect_ratio": "9:16"}
    assert item["est_usd"] == pytest.approx(0.60)
    first = make(env, model="flux-schnell", service="fal").json()["image"]
    make(env, mode="video", model="h3", source={"id": first["id"]})
    url, body = env["queue"][-1][1:]
    assert url == f"{svc.FAL_QUEUE}/minimax/h3/image-to-video"
    assert body["image_url"].startswith("https://r2.test/") and "aspect_ratio" not in body


def test_minimax_h3_on_runware_takes_its_own_sizes(env):
    make(env, mode="video", model="h3", service="runware", shape="portrait")
    (task,) = env["runware"][0]
    assert task["model"] == "minimax:h3@0" and (task["width"], task["height"]) == (768, 1024)
    assert task["settings"] == {"promptExpansion": "disabled"}


def test_hunyuan_on_fal_runs_by_frames_with_its_own_prompt_expansion_off(env):
    make(env, mode="video", model="hunyuan-video", service="fal")
    body = env["queue"][0][2]
    assert "duration" not in body and body["num_frames"] == 121 and body["enable_prompt_expansion"] is False


def test_a_failed_fal_video_says_why(env):
    item = make(env, mode="video", model="kling-4", service="fal").json()["image"]
    env["queue_reply"] = _fal_done(status={"status": "COMPLETED", "request_id": "req-1",
                                           "error": "Content policy violation.", "error_type": "bad_request"})
    failed = check(env, item).json()["image"]
    assert failed["status"] == "failed" and "Content policy" in failed["error"] and failed["est_usd"] == 0
    env["queue_reply"] = None
    item = make(env, mode="video", model="kling-4", service="fal").json()["image"]
    env["queue_reply"] = _fal_done(result_code=404, result={"detail": "not found"})
    assert "for an hour" in check(env, item).json()["image"]["error"]


# ---------------------------------------------------------------- video on WaveSpeed and Replicate
def test_a_wavespeed_video_is_saved_and_then_deleted_there(env):
    env["keys"] = {"fal", "wavespeed"}
    item = make(env, mode="video", model="hunyuan-video", shape="tall").json()["image"]
    method, path, body = env["wavespeed"][0]
    assert (method, path) == ("POST", "/wavespeed-ai/hunyuan-video-1.5/text-to-video")
    assert body == {"prompt": "an apple on a table", "duration": 5, "size": "480*832"}
    assert item["service"] == "wavespeed" and item["est_usd"] == pytest.approx(0.10)
    env["wavespeed_reply"] = lambda m, p, b=None: (
        {"id": "ws-1", "status": "completed", "outputs": ["https://d.wavespeed.ai/v.mp4"]} if p.endswith("/result") else {})
    done = check(env, item).json()["image"]
    assert done["status"] == "ready" and env["downloads"][-1] == ("https://d.wavespeed.ai/v.mp4", None)
    assert env["wavespeed"][-1] == ("POST", "/predictions/delete", {"ids": ["ws-1"]})


def test_a_wavespeed_first_frame_uses_its_frame_endpoint(env):
    env["keys"] = {"wavespeed"}
    make(env, mode="video", model="hunyuan-video", seconds=8, source={"data_url": PNG})
    method, path, body = env["wavespeed"][0]
    assert path == "/wavespeed-ai/hunyuan-video-1.5/image-to-video"
    assert body["image"].startswith("https://r2.test/") and body["resolution"] == "480p" and body["duration"] == 8
    assert "size" not in body


def test_a_replicate_video_is_fetched_with_the_key_on_replicates_own_host(env):
    env["keys"] = ALL
    item = make(env, mode="video", model="wan-3", shape="portrait", seconds=10).json()["image"]
    method, url, body = env["replicate"][0]
    assert (method, url) == ("POST", f"{svc.REPLICATE_API}/models/alibaba/wan-3/predictions")
    assert body == {"input": {"prompt": "an apple on a table", "duration": 10, "resolution": "720p",
                              "enable_prompt_expansion": False, "aspect_ratio": "3:4"}}
    assert item["est_usd"] == pytest.approx(0.70)
    env["replicate_reply"] = lambda m, u, b=None: (200, {"id": "rp-1", "status": "succeeded",
                                                         "output": "https://replicate.delivery/xyz/out.mp4"})
    assert check(env, item).json()["image"]["status"] == "ready"
    assert env["downloads"][-1] == ("https://replicate.delivery/xyz/out.mp4", {"Authorization": "Bearer test-key"})


def test_replicate_sends_its_key_to_no_other_host(env):
    env["keys"] = ALL
    assert svc.replicate_file_headers("https://replicate.delivery/a.mp4") == {"Authorization": "Bearer test-key"}
    assert svc.replicate_file_headers("https://evil.example/replicate.delivery/a.mp4") is None


# ---------------------------------------------------------------- the rest of a video's life
def test_a_text_only_model_refuses_a_first_frame(env, monkeypatch):
    monkeypatch.setitem(studio.MODELS, "kling-4", studio.MODELS["kling-4"] | {"start_image": False})
    r = make(env, mode="video", model="kling-4", source={"data_url": PNG})
    assert r.status_code == 400 and "description only" in r.json()["error"] and env["queue"] == []


async def test_the_server_follows_a_video_with_no_page_open(env, monkeypatch):
    monkeypatch.setattr(studio, "FOLLOW_EVERY", 0)
    item = await studio.make(ADMIN, {"prompt": "waves at dawn", "mode": "video", "model": "kling-4", "service": "fal"})
    calls = {"n": 0}

    def reply(method, url, body=None):
        calls["n"] += 1
        return _fal_done()(method, url, body) if calls["n"] > 2 else (202, {"status": "IN_QUEUE"})
    env["queue_reply"] = reply
    await studio._follow(ADMIN, item["id"])
    saved = (await studio._read_index(ADMIN))[0]
    assert saved["status"] == "ready" and saved["key"].endswith(".mp4")


def test_deleting_a_pending_video_stops_the_studio_waiting_for_it(env):
    item = make(env, mode="video", model="veo-fast").json()["image"]
    assert env["client"].delete(f"/api/studio/image/{item['id']}").status_code == 200
    assert check(env, item).status_code == 404


def test_a_video_answers_byte_ranges(env):
    item = make(env, mode="video", model="veo-fast").json()["image"]
    env["runware_reply"] = lambda tasks: {"data": [{"taskUUID": tasks[0]["taskUUID"], "status": "success",
                                                     "videoURL": "https://vm.runware.ai/v.mp4"}]}
    url = check(env, item).json()["image"]["url"]
    r = env["client"].get(url, headers={"Range": "bytes=4-9"})
    assert r.status_code == 206 and r.content == b"bytes " and r.headers["content-range"] == "bytes 4-9/20"
    assert env["client"].get(url, headers={"Range": "bytes=-4"}).content == b"6789"
    assert env["client"].get(url, headers={"Range": "bytes=50-"}).status_code == 416


# ---------------------------------------------------------------- the real HTTP calls
def _mock(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(svc.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


async def test_fal_is_asked_to_keep_nothing_and_its_errors_read_plainly(monkeypatch):
    sent = {}

    def handler(request):
        sent["headers"] = request.headers
        sent["url"] = str(request.url)
        return httpx.Response(403, text='{"detail":"User is locked. Reason: TOP_UP."}')
    _mock(monkeypatch, handler)
    monkeypatch.setattr(svc, "_key", lambda service: "k")
    with pytest.raises(svc.AccountError) as e:
        await svc.fal_run("fal-ai/flux/schnell", {"prompt": "x"})
    assert e.value.status == 402 and "out of credit" in e.value.message and e.value.down
    assert sent["url"] == "https://fal.run/fal-ai/flux/schnell"
    assert sent["headers"]["authorization"] == "Key k" and sent["headers"]["x-fal-store-io"] == "0"
    assert json.loads(sent["headers"]["x-fal-object-lifecycle-preference"]) == {
        "expiration_duration_seconds": svc.FAL_KEEP_SECONDS}


async def test_fal_video_jobs_keep_nothing_long_and_stay_on_fals_queue(monkeypatch):
    sent = {}

    def handler(request):
        sent["headers"] = request.headers
        return httpx.Response(202, json={"status": "IN_PROGRESS", "request_id": "r"})
    _mock(monkeypatch, handler)
    monkeypatch.setattr(svc, "_key", lambda service: "k")
    code, body = await svc.fal_queue("GET", f"{svc.FAL_QUEUE}/kling/v4/requests/r/status")
    assert code == 202 and body["status"] == "IN_PROGRESS"
    assert json.loads(sent["headers"]["x-fal-object-lifecycle-preference"]) == {
        "expiration_duration_seconds": svc.FAL_VIDEO_KEEP_SECONDS}
    with pytest.raises(svc.StudioError):
        await svc.fal_queue("GET", "https://elsewhere.test/requests/r/status")


@pytest.mark.parametrize("call, response, status", [
    ("runware", httpx.Response(402, json={"errors": [{"code": "insufficientCredits"}]}), 402),
    ("wavespeed", httpx.Response(200, json={"code": 402, "message": "Insufficient balance", "data": None}), 402),
    ("replicate", httpx.Response(401, json={"detail": "Unauthenticated"}), 502),
    ("wavespeed", httpx.Response(429, json={"code": 429, "message": "Too many requests"}), 503),
])
async def test_each_service_reads_account_trouble_as_a_reason_to_try_the_next(monkeypatch, call, response, status):
    sent = []

    def handler(request):
        sent.append(request)
        return response
    _mock(monkeypatch, handler)
    monkeypatch.setattr(svc, "_key", lambda service: "k")
    runs = {"runware": lambda: svc.runware_call([{"taskType": "getResponse", "taskUUID": "t"}]),
            "wavespeed": lambda: svc.wavespeed_call("GET", "/predictions/x/result"),
            "replicate": lambda: svc.replicate_call("GET", f"{svc.REPLICATE_API}/predictions/x")}
    with pytest.raises(svc.AccountError) as e:
        await runs[call]()
    assert e.value.status == status and e.value.down == (status != 503)   # busy is not down
    assert sent[0].headers["authorization"] == "Bearer k"


# ---------------------------------------------------------------- the maker's own GPU (ComfyUI on Baseten)
def png_data_url(w, h):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (90, 60, 30)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_your_gpu_runs_h3_only_when_picked(env):
    env["keys"] = {"fal", "runware", "baseten"}
    q = quote(env, mode="video", model="h3", shape="wide", seconds=5)
    gpu = next(s for s in q["services"] if s["service"] == "baseten")
    assert gpu["usable"] and gpu["auto"] is False and gpu["usd"] < q["choice"]["usd"]
    assert q["choice"]["service"] == "fal"
    assert make(env, mode="video", model="h3", shape="wide", seconds=5).json()["image"]["service"] == "fal"
    assert env["comfy"] == []


def test_your_gpu_wakes_then_takes_the_job_and_the_video_comes_home(env):
    env["keys"] = {"fal", "baseten"}
    item = make(env, mode="video", model="h3", service="baseten", seconds=10,
                source={"data_url": png_data_url(640, 960)}).json()["image"]
    assert item["status"] == "pending" and item["service"] == "baseten"
    assert [c[0] for c in env["comfy"]] == ["wake"]

    assert check(env, item).json()["image"]["status"] == "pending"   # still waking: nothing sent
    assert [c[0] for c in env["comfy"]] == ["wake"]

    env["comfy_ready"] = True
    assert check(env, item).json()["image"]["status"] == "pending"
    assert [c[0] for c in env["comfy"]] == ["wake", "upload", "queue"]
    gen = env["comfy"][2][1]["7"]["inputs"]
    assert (gen["width"], gen["height"], gen["length"]) == comfy.h3_size(640, 960) + (243,)
    assert gen["prompt"] == "an apple on a table" and gen["first_frame"] == ["1", 0]

    check(env, item)   # the saved job is not sent twice
    assert [c[0] for c in env["comfy"]].count("queue") == 1

    env["comfy_state"] = ("done", [{"filename": "h3_00001_.mp4", "subfolder": "studio", "type": "output"}], "", [])
    done = check(env, item).json()["image"]
    assert done["status"] == "ready" and done["est_usd"] == 0.3
    assert env["downloads"][-1] == ("https://model-x.api.baseten.co/sync/view/h3_00001_.mp4",
                                    {"Authorization": "Bearer test-key"})
    assert env["comfy"][-1] == ("forget", "prompt-1")


def test_15_seconds_runs_on_your_gpu_only_and_from_words_alone_takes_the_shape(env):
    env["keys"] = {"fal", "runware", "baseten"}
    r = make(env, mode="video", model="h3", shape="tall", seconds=15)
    assert r.status_code == 400 and "runs only when picked" in r.json()["error"]
    item = make(env, mode="video", model="h3", shape="tall", seconds=15, service="baseten").json()["image"]
    env["comfy_ready"] = True
    check(env, item)
    wf = env["comfy"][-1][1]
    gen = wf["7"]["inputs"]
    assert (gen["width"], gen["height"], gen["length"]) == (768, 1344, 362)
    assert "first_frame" not in gen and "1" not in wf


def test_a_still_on_your_gpu_waits_like_a_video_and_comes_home_as_a_png(env):
    env["keys"] = {"fal", "baseten"}
    item = make(env, mode="create", model="h3-still", shape="landscape", steps=40).json()["image"]
    assert (item["status"], item["service"], item["kind"]) == ("pending", "baseten", "image")
    assert (item["width"], item["height"], item["steps"]) == (1152, 864, 40)
    env["comfy_ready"] = True
    check(env, item)
    wf = env["comfy"][-1][1]
    assert wf["16"]["class_type"] == "SaveImage" and wf["11"]["inputs"]["steps"] == 40
    env["comfy_state"] = ("done", [{"filename": "h3_still_00001_.png", "subfolder": "studio", "type": "output"}], "", [])
    done = check(env, item).json()["image"]
    assert done["status"] == "ready" and done["ext"] == "png"
    assert env["store"][f"studio/{ADMIN['id']}/{item['id']}.png"][1] == "image/png"
    assert env["rows"][-1]["route"] == "studio" and env["rows"][-1]["outcome"] == "complete"


def test_a_run_on_your_gpu_is_rewritten_there_and_claude_is_not_asked(env):
    env["keys"] = {"fal", "baseten"}
    item = make(env, mode="video", model="h3-ref", seconds=5, prompt="picture 1 naps", rewrite=True,
                refs=[{"data_url": png_data_url(64, 64)}]).json()["image"]
    assert env["rewrites"] == [] and item["rewrite_on_gpu"] is True and item["prompt_used"] == "<Picture 1> naps"
    env["comfy_ready"] = True
    check(env, item)
    node = env["comfy"][-1][1]["20"]["inputs"]
    assert node["prompt"] == "<Picture 1> naps" and node["picture_tags"] is True
    assert node["system"].startswith(studio.REWRITE["reference"]) and "adults only" in node["system"]

    env["comfy_state"] = ("done", [{"filename": "h3_00001_.mp4", "subfolder": "studio", "type": "output"}], "",
                          ["<Picture 1> curls up asleep on a sunlit rug, the camera drifting closer."])
    done = check(env, item).json()["image"]
    assert done["prompt_used"].startswith("<Picture 1> curls up") and done["rewritten"] is True
    # no Claude call; the rewrite's GPU seconds are counted with the clip
    assert env["rewrites"] == [] and done["est_usd"] == item["est_usd"] == round(0.35 + 6.5 / 3600 * 20, 4)

    other = make(env, mode="video", model="h3", seconds=5, rewrite=True).json()["image"]   # fal: Claude rewrites
    assert other["service"] == "fal" and env["rewrites"] and other["rewrite_on_gpu"] is False


def test_p_h3_image_draws_and_edits_on_your_gpu(env):
    env["keys"] = {"fal", "runware", "baseten"}
    item = make(env, mode="create", model="p-h3-image", shape="wide").json()["image"]
    assert item["service"] == "baseten" and (item["width"], item["height"]) == (3872, 2176)
    env["comfy_ready"] = True
    check(env, item)
    gen = env["comfy"][-1][1]["7"]["inputs"]
    assert (gen["width"], gen["height"]) == (3872, 2176)

    edit = make(env, mode="edit", model="p-h3-image", prompt="put the hat from picture 2 on him",
                source={"data_url": png_data_url(1000, 750)}, refs=[{"data_url": png_data_url(64, 64)}]).json()["image"]
    assert edit["prompt_used"] == "put the hat from <Picture 2> on him" and edit["width"] is None
    check(env, edit)
    uploads = [c for c in env["comfy"] if c[0] == "upload"]
    assert Image.open(io.BytesIO(uploads[-2][1])).size == (2304, 1728)   # the image to edit, at about 4 MP
    assert uploads[-1][2] == f"{edit['id']}-ref1.png"
    gen = env["comfy"][-1][1]["7"]["inputs"]
    assert (gen["width"], gen["height"]) == (0, 0) and gen["images.image_2"] == ["102", 0]

    r = make(env, mode="edit", model="flux-kontext", source={"data_url": png_data_url(64, 64)},
             refs=[{"data_url": png_data_url(64, 64)}])
    assert r.status_code == 400 and "takes no reference pictures" in r.json()["error"]


def h3_clip(env, seconds=5):
    """A finished MiniMax H3 clip in the studio, made on the GPU."""
    item = make(env, mode="video", model="h3", seconds=seconds, shape="wide", service="baseten").json()["image"]
    env["comfy_ready"] = True
    check(env, item)
    env["comfy_state"] = ("done", [{"filename": "h3_00001_.mp4", "subfolder": "studio", "type": "output"}], "", [])
    done = check(env, item).json()["image"]
    env["comfy_state"] = ("running", [], "", [])
    return done


def test_an_h3_clip_is_extended_on_your_gpu_into_one_longer_clip(env):
    env["keys"] = {"fal", "runware", "baseten"}
    clip = h3_clip(env)
    q = quote(env, mode="video", model="h3", seconds=5, extending=True)
    reasons = {s["service"]: s["reason"] for s in q["services"]}
    assert reasons["fal"] == reasons["runware"] == "cannot extend a clip"

    item = make(env, mode="video", model="h3", seconds=5, service="baseten", prompt="it runs on",
                extend={"id": clip["id"]}).json()["image"]
    assert item["extends_id"] == clip["id"] and item["seconds"] == round(5 + 5 - 22 / 24, 1)
    assert (item["width"], item["height"]) == (clip["width"], clip["height"])
    check(env, item)
    upload = [c for c in env["comfy"] if c[0] == "upload"][-1]
    assert upload[1] == b"mp4 bytes 0123456789" and upload[2] == f"{clip['id']}.mp4"   # the old clip itself
    wf = env["comfy"][-1][1]
    assert wf["29"]["inputs"]["file"] == upload[2] and wf["7"]["inputs"]["length"] == 124


@pytest.mark.parametrize("why", ["not h3", "too long", "with a frame"])
def test_only_an_h3_clip_with_room_left_can_be_extended(env, why):
    env["keys"] = {"fal", "baseten"}
    clip = h3_clip(env, seconds=15)
    body = {"mode": "video", "model": "h3", "seconds": 15, "service": "baseten", "extend": {"id": clip["id"]}}
    if why == "not h3":
        body["model"] = "h3-ref"
    if why == "too long":
        studio_index = env["store"][f"studio/{ADMIN['id']}/index.json"][0]
        items = json.loads(studio_index)
        items[0]["seconds"] = 50
        env["store"][f"studio/{ADMIN['id']}/index.json"] = (json.dumps(items).encode(), "application/json")
    if why == "with a frame":
        body["source"] = {"data_url": png_data_url(64, 64)}
    r = make(env, **body)
    said = {"not h3": "cannot extend a clip", "too long": "can reach 60 seconds", "with a frame": "Remove the other"}
    assert r.status_code in (400, 404) and said[why] in r.json()["error"]


def test_a_last_frame_runs_on_your_gpu_only(env):
    env["keys"] = {"fal", "runware", "baseten"}
    q = quote(env, mode="video", model="h3", seconds=5, ending=True)
    reasons = {s["service"]: s["reason"] for s in q["services"]}
    assert reasons["fal"] == reasons["runware"] == "takes no last frame" and q["choice"] is None
    r = make(env, mode="video", model="wan-3", end={"data_url": png_data_url(64, 64)})
    assert r.status_code == 400 and "takes no last frame" in r.json()["error"]

    item = make(env, mode="video", model="h3", seconds=5, service="baseten",
                source={"data_url": png_data_url(960, 640)}, end={"data_url": png_data_url(960, 640)}).json()["image"]
    env["comfy_ready"] = True
    check(env, item)
    names = [c[2] for c in env["comfy"] if c[0] == "upload"]
    assert names == [f"{item['id']}-source.png", f"{item['id']}-last.png"]   # each picture its own name
    gen = env["comfy"][-1][1]["7"]["inputs"]
    assert gen["first_frame"] == ["1", 0] and gen["last_frame"] == ["17", 0]


def test_pictures_become_references_and_pinned_frames_and_go_when_the_video_goes(env):
    env["keys"] = {"fal", "baseten"}
    pic = {"data_url": png_data_url(800, 600)}
    item = make(env, mode="video", model="h3-ref", seconds=5, shape="wide", prompt="picture 1 waves at Picture 2",
                source=pic, end=pic, refs=[pic, pic], pins=[{"source": pic, "at": 2.5}]).json()["image"]
    assert item["service"] == "baseten" and (item["width"], item["height"]) == (1344, 768)   # no pick needed
    folder = f"studio/{ADMIN['id']}/{item['id']}"
    assert {k for k in env["store"] if k.startswith(folder)} == {
        f"{folder}-{s}.png" for s in ("source", "last", "ref1", "ref2", "at1")}

    env["comfy_ready"] = True
    check(env, item)
    wf = env["comfy"][-1][1]
    gen = wf["7"]["inputs"]
    assert gen["prompt"] == "<Picture 1> waves at <Picture 2>"
    assert gen["ref_images.ref_image_1"] == ["102", 0] and wf["102"]["inputs"]["image"] == f"{item['id']}-ref2.png"
    assert [wf[n]["inputs"]["frame_idx"] for n in ("301", "302", "303")] == [0, 60, -1]   # first, 2.5 s, last

    assert env["client"].delete(f"/api/studio/image/{item['id']}").status_code == 200
    assert not [k for k in env["store"] if k.startswith(folder)]


@pytest.mark.parametrize("extra, said", [
    ({"pins": [{"source": {"data_url": "x"}, "at": 5}]}, "between 0 and 5"),
    ({"refs": [{"data_url": "x"}] * 10}, "up to 9 pictures"),
    ({"pins": [{"source": {"data_url": "x"}, "at": 1}] * 4}, "up to 3 pictures at set seconds"),
])
def test_pictures_beyond_what_the_model_takes_are_turned_back_before_anything_runs(env, extra, said):
    env["keys"] = {"baseten"}
    r = make(env, mode="video", model="h3-ref", seconds=5, **extra)
    assert r.status_code == 400 and said in r.json()["error"] and env["comfy"] == []


# ---------------------------------------------------------------- folders, password locks, many at once
def folder(env, name="Trip", password=None):
    body = {"name": name} | ({"password": password} if password else {})
    r = env["client"].post("/api/studio/folders", json=body)
    assert r.status_code == 200, r.text
    return r.json()["created"]


def listed(env):
    return env["client"].get("/api/studio/images").json()


def test_new_work_lands_in_the_folder_asked_for_and_moves_and_goes_many_at_once(env):
    trip = folder(env)
    a = make(env, folder=trip).json()["image"]
    b = make(env).json()["image"]
    c = make(env).json()["image"]
    assert a["folder_id"] == trip and b["folder_id"] is None
    shown = listed(env)
    assert [{k: f[k] for k in ("id", "name", "protected", "open", "count")} for f in shown["folders"]] == [
        {"id": trip, "name": "Trip", "protected": False, "open": True, "count": 1}]

    c_ = env["client"]
    assert c_.post("/api/studio/items/move", json={"ids": [b["id"], c["id"]], "folder": trip}).json() == {"moved": 2}
    assert {i["id"]: i["folder_id"] for i in listed(env)["images"]} == {a["id"]: trip, b["id"]: trip, c["id"]: trip}
    assert c_.post("/api/studio/items/move", json={"ids": [c["id"]], "folder": None}).json() == {"moved": 1}

    files = {k for k in env["store"] if k.endswith(".jpg")}
    assert c_.post("/api/studio/items/delete", json={"ids": [a["id"], b["id"]]}).json() == {"deleted": 2}
    assert [i["id"] for i in listed(env)["images"]] == [c["id"]]
    assert {k for k in env["store"] if k.endswith(".jpg")} == files - {f"studio/{ADMIN['id']}/{a['id']}.jpg",
                                                                      f"studio/{ADMIN['id']}/{b['id']}.jpg"}

    assert c_.delete(f"/api/studio/folders/{trip}").status_code == 200   # its items stay, outside any folder
    assert listed(env)["folders"] == []
    assert c_.post("/api/studio/items/move", json={"ids": [c["id"]], "folder": trip}).status_code == 404


def test_a_protected_folder_hides_everything_in_it_until_opened_with_its_password(env):
    c = env["client"]
    vault = folder(env, "Vault", password="correct horse")
    inside = make(env, folder=vault).json()["image"]
    outside = make(env).json()["image"]
    raw = env["store"][f"studio/{ADMIN['id']}/folders.json"][0].decode()
    assert "correct horse" not in raw and '"hash"' in raw and '"salt"' in raw   # only a salted hash is kept

    assert c.post(f"/api/studio/folders/{vault}/lock").status_code == 200
    shown = listed(env)
    assert [i["id"] for i in shown["images"]] == [outside["id"]]
    assert {k: shown["folders"][0][k] for k in ("id", "name", "protected", "open", "count")} == {
        "id": vault, "name": "Vault", "protected": True, "open": False, "count": None}
    # closed: no file, no check, no use as a picture, nothing moved in or out, nothing deleted, no new work
    assert c.get(f"/api/studio/image/{inside['id']}").status_code == 404
    assert c.get(f"/api/studio/image/{inside['id']}/check").status_code == 404
    assert make(env, mode="edit", model="flux-kontext", source={"id": inside["id"]}).status_code == 404
    assert c.post("/api/studio/items/move", json={"ids": [outside["id"]], "folder": vault}).status_code == 403
    assert c.post("/api/studio/items/move", json={"ids": [inside["id"]], "folder": None}).json() == {"moved": 0}
    assert c.post("/api/studio/items/delete", json={"ids": [inside["id"]]}).json() == {"deleted": 0}
    assert make(env, folder=vault).status_code == 403
    assert c.patch(f"/api/studio/folders/{vault}", json={"remove_password": True}).status_code == 403
    assert c.delete(f"/api/studio/folders/{vault}").status_code == 403

    assert c.post(f"/api/studio/folders/{vault}/unlock", json={"password": "wrong"}).status_code == 403
    assert c.post(f"/api/studio/folders/{vault}/unlock", json={"password": "correct horse"}).status_code == 200
    assert {i["id"] for i in listed(env)["images"]} == {inside["id"], outside["id"]}
    assert c.get(f"/api/studio/image/{inside['id']}").status_code == 200

    # another browser session starts with every protected folder closed
    other = TestClient(c.app)
    assert [i["id"] for i in other.get("/api/studio/images").json()["images"]] == [outside["id"]]


def test_wrong_passwords_are_slowed_after_five(env, monkeypatch):
    monkeypatch.setattr(studio, "_misses", {})
    c = env["client"]
    vault = folder(env, "Vault", password="right one")
    c.post(f"/api/studio/folders/{vault}/lock")
    for _ in range(studio.TRIES):
        assert c.post(f"/api/studio/folders/{vault}/unlock", json={"password": "nope"}).status_code == 403
    r = c.post(f"/api/studio/folders/{vault}/unlock", json={"password": "right one"})
    assert r.status_code == 429 and "Too many" in r.json()["error"]


def test_a_folders_cover_shows_its_name_and_its_lock_as_this_session_has_it(env, monkeypatch):
    from webapp import house_cover
    drawn = []
    monkeypatch.setattr(house_cover, "folder_cover_sync",
                        lambda fid, name, mode, state, theme=None: drawn.append((name, mode, state, theme)) or b"RIFF webp")
    c = env["client"]
    rome = folder(env, "Rome")
    vault = folder(env, "Vault", password="correct horse")   # made open in this session
    for fid in (rome, vault):
        r = c.get(f"/api/studio/folders/{fid}/cover?mode=dark")
        assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    c.post(f"/api/studio/folders/{vault}/lock")
    c.get(f"/api/studio/folders/{vault}/cover")
    assert [d[:3] for d in drawn] == [("Rome", "dark", "plain"), ("Vault", "dark", "open"), ("Vault", "light", "locked")]
    assert c.get(f"/api/studio/folders/{'f' * 32}/cover").status_code == 404
    assert house_cover.folder_theme("a" * 32, "light") == house_cover.folder_theme("a" * 32, "light")   # the same every time
    assert len({house_cover.folder_theme(f"{n:032x}", "light") for n in range(12)}) > 4   # and neighbors differ


def test_a_folders_cover_color_is_chosen_from_the_house_cloths_for_each_page_mode(env, monkeypatch):
    from webapp import house_cover
    drawn = []
    monkeypatch.setattr(house_cover, "folder_cover_sync",
                        lambda fid, name, mode, state, theme=None: drawn.append((mode, theme)) or b"RIFF webp")
    c = env["client"]
    rome = folder(env, "Rome")
    light, dark = house_cover.folder_themes("light")[3], house_cover.folder_themes("dark")[5]
    r = c.patch(f"/api/studio/folders/{rome}", json={"themes": {"light": light, "dark": dark}})
    assert r.status_code == 200
    f = r.json()["folders"][0]
    assert f["themes"] == {"light": light, "dark": dark} and f["themes_chosen"] == {"light": True, "dark": True}
    c.get(f"/api/studio/folders/{rome}/cover?mode=dark")                    # drawn in the chosen cloth
    c.get(f"/api/studio/folders/{rome}/cover?mode=light&theme=auto")        # the picker's preview of the folder's own pick
    assert drawn == [("dark", dark), ("light", None)]
    # back to the folder's own pick for light pages; a dark cloth is refused for light pages
    f = c.patch(f"/api/studio/folders/{rome}", json={"themes": {"light": None}}).json()["folders"][0]
    assert f["themes"]["light"] == house_cover.folder_theme(rome, "light") and f["themes_chosen"]["light"] is False
    assert c.patch(f"/api/studio/folders/{rome}", json={"themes": {"light": dark}}).status_code == 400


def test_a_folder_cover_is_the_house_cover_laid_landscape_and_books_stay_as_they_were(monkeypatch, tmp_path):
    from PIL import Image

    from webapp import house_cover
    monkeypatch.setenv("COVER_CACHE", str(tmp_path))
    folders, books = house_cover._folder_renderer(), house_cover._renderer()
    assert folders.W > folders.H and books.H > books.W
    assert folders.AUTHOR_BAND == 0 and books.AUTHOR_BAND > 0   # a folder carries its name and no other words
    for state in ("plain", "locked", "open"):
        im = Image.open(io.BytesIO(house_cover.folder_cover_sync("a" * 32, "Studies in light", "dark", state)))
        assert im.format == "WEBP" and im.width > im.height


def test_a_folder_needs_a_name_and_a_real_password(env):
    c = env["client"]
    assert c.post("/api/studio/folders", json={"name": "  "}).status_code == 400
    assert c.post("/api/studio/folders", json={"name": "x", "password": "abc"}).status_code == 400
    plain = folder(env, "Plain")
    r = c.patch(f"/api/studio/folders/{plain}", json={"name": "Renamed", "password": "four"})
    assert r.status_code == 200 and r.json()["folders"][0]["protected"] is True and r.json()["folders"][0]["name"] == "Renamed"


def test_a_workflow_comfyui_refuses_ends_the_job_instead_of_asking_again(env):
    env["keys"] = {"baseten"}
    item = make(env, mode="video", model="h3", seconds=5, service="baseten").json()["image"]
    env["comfy_ready"] = True
    env["comfy_raise"] = svc.StudioError("ComfyUI refused the workflow: Value not in list.", 422)
    out = check(env, item).json()["image"]
    assert out["status"] == "failed" and "Value not in list" in out["error"]
