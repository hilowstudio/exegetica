"""Media Studio's daily price book (webapp/studio_prices.py): one reader per service, each fed the
shape that service publishes; a price that cannot be read or lands far from the listed one keeps
the last good price; the book lives in R2 and goes stale after a day; Inngest runs it each
morning. Every page, API, and R2 are stand-ins; no network, no cost."""
import asyncio
import html
import json

import pytest

from webapp import inngest_app, r2, studio, studio_prices as prices
from webapp import studio_services as svc


@pytest.fixture
def pages(monkeypatch):
    seen = {"json": {}, "text": {}, "store": {}, "keys": {"fal", "wavespeed"}, "wavespeed": []}
    monkeypatch.setattr(svc, "_key", lambda service: "k" if service in seen["keys"] else None)
    monkeypatch.setattr(prices, "_pages", {})
    monkeypatch.setattr(prices, "_cache", {"book": None, "at": 0.0})

    async def fetch_json(url, headers=None):
        for prefix, body in seen["json"].items():
            if url.startswith(prefix):
                if isinstance(body, Exception):
                    raise body
                return body
        raise RuntimeError("no page " + url)

    async def fetch_text(url):
        return seen["text"][url]

    async def wavespeed_call(method, path, body=None):
        seen["wavespeed"].append((method, path, body))
        return seen.get("wavespeed_reply") or {"model_id": body["model_id"], "price": 0.1, "discounted_price": 0.1}
    monkeypatch.setattr(prices, "fetch_json", fetch_json)
    monkeypatch.setattr(prices, "fetch_text", fetch_text)
    monkeypatch.setattr(svc, "wavespeed_call", wavespeed_call)

    store = seen["store"]
    monkeypatch.setattr(r2, "configured", lambda: True)

    async def get_bytes(key):
        return store.get(key)

    async def put_bytes(key, data, content_type):
        store[key] = data
    monkeypatch.setattr(r2, "get_bytes_async", get_bytes)
    monkeypatch.setattr(r2, "put_bytes_async", put_bytes)
    return seen


def route(model_id, service):
    return studio.MODELS[model_id]["routes"][service]


def read(service, model_id):
    r = route(model_id, service)
    return asyncio.run(prices.READERS[service](r["source"], r))


# ---------------------------------------------------------------- one reader per service
def test_fal_scales_its_base_rate_to_the_resolution_the_studio_uses(pages):
    pages["json"][svc.FAL_API] = {"prices": [{"endpoint_id": "alibaba/wan-3.0/text-to-video", "unit_price": 0.05,
                                              "unit": "seconds", "currency": "USD"}]}
    assert read("fal", "wan-3") == {"usd": 0.1}   # 480p base, 720p used


def test_fal_refuses_a_price_in_a_unit_the_route_does_not_use(pages):
    pages["json"][svc.FAL_API] = {"prices": [{"endpoint_id": "fal-ai/flux/dev", "unit_price": 0.025, "unit": "seconds"}]}
    with pytest.raises(ValueError):
        read("fal", "flux-dev")


def test_runware_reads_a_measured_run_or_a_labeled_rate(pages):
    pages["json"]["https://runware.ai/docs/models/bfl-flux-1-dev/"] = {"info": {"x-pricing": {"measured": [
        {"configuration": "512x512 · 28 steps", "price": 0.0019},
        {"configuration": "1024x1024 · 28 steps", "price": 0.0038}]}}}
    pages["json"]["https://runware.ai/docs/models/google-veo-3-1-fast/"] = {"info": {"x-pricing": {"rates": [
        {"amount": 0.1, "label": "720p / 1080p"}, {"amount": 0.15, "label": "720p / 1080p · with audio"},
        {"amount": 0.3, "label": "4K"}]}}}
    assert read("runware", "flux-dev") == {"usd": 0.0038}
    assert read("runware", "veo-fast") == {"usd": 0.1, "usd_audio": 0.15}


def test_wavespeed_is_asked_about_the_exact_request_and_priced_per_second(pages):
    assert read("wavespeed", "hunyuan-video") == {"usd": 0.02}   # $0.10 for 5 seconds
    method, path, body = pages["wavespeed"][0]
    assert (method, path) == ("POST", "/model/price")
    assert body["model_id"] == "wavespeed-ai/hunyuan-video-1.5/text-to-video" and body["inputs"]["size"] == "832*480"
    pages["wavespeed_reply"] = {"price": 100000, "discounted_price": 0}   # millionths of a dollar
    assert read("wavespeed", "hunyuan-video") == {"usd": 0.02}


def test_a_service_with_no_key_is_not_asked(pages):
    pages["keys"] = set()
    assert read("wavespeed", "hunyuan-video") is None and read("fal", "flux-dev") is None
    assert pages["wavespeed"] == []


def replicate_page(prices_by_tier):
    config = {"current_description": None, "current_tiers": [
        {"criteria": [{"title": "target resolution", "type": "equals", "value": res}],
         "prices": [{"metric": "video_output_duration_seconds", "price": price, "type": "per-unit"}]}
        for res, price in prices_by_tier]}
    return '<script>{"model": {"billingConfig": ' + html.escape(json.dumps(config)) + ', "x": 1}}</script>'


def test_replicate_reads_the_billing_tier_for_the_resolution_used(pages):
    pages["text"]["https://replicate.com/alibaba/wan-3"] = replicate_page(
        (("480p", "$0.035"), ("720p", "$0.07"), ("1080p", "$0.14")))
    assert read("replicate", "wan-3") == {"usd": 0.07}


# ---------------------------------------------------------------- the book
def test_refresh_keeps_the_last_good_price_when_a_reading_fails_or_looks_wrong(pages):
    routes = {"wan-3:fal": ("fal", route("wan-3", "fal")), "wan-3:runware": ("runware", route("wan-3", "runware")),
              "wan-3:replicate": ("replicate", route("wan-3", "replicate")),
              "hunyuan-video:wavespeed": ("wavespeed", route("hunyuan-video", "wavespeed"))}
    pages["store"][prices.BOOK_KEY] = json.dumps({"routes": {
        "wan-3:runware": {"usd": 0.09, "status": "ok", "checked": "yesterday"},
        "wan-3:replicate": {"usd": 0.065, "status": "ok", "checked": "yesterday"}}}).encode()
    pages["json"][svc.FAL_API] = {"prices": [{"endpoint_id": "alibaba/wan-3.0/text-to-video", "unit_price": 0.045,
                                              "unit": "seconds"}]}
    pages["json"]["https://runware.ai/docs/models/alibaba-wan3-0/"] = RuntimeError("page moved")
    pages["text"]["https://replicate.com/alibaba/wan-3"] = replicate_page((("720p", "$7.00"),))   # a misread
    pages["keys"] = {"fal"}
    book = asyncio.run(prices.refresh(routes))
    assert book["routes"]["wan-3:fal"] == {"usd": 0.09, "usd_audio": None, "status": "ok", "checked": book["checked"]}
    assert book["routes"]["wan-3:runware"]["usd"] == 0.09 and "RuntimeError" in book["routes"]["wan-3:runware"]["note"]
    kept = book["routes"]["wan-3:replicate"]
    assert kept["usd"] == 0.065 and kept["status"] == "kept" and "far from the listed" in kept["note"]
    assert book["routes"]["hunyuan-video:wavespeed"]["note"] == "no key to ask with"
    assert json.loads(pages["store"][prices.BOOK_KEY])["checked"] == book["checked"]
    assert not prices.stale(book)


def test_the_book_overrides_the_listed_price_only_where_it_has_one():
    book = {"routes": {"a:x": {"usd": 0.05, "usd_audio": None}, "b:x": {"usd": None}}}
    assert prices.current(book, "a:x", {"unit": "second", "usd": 0.1, "usd_audio": 0.15}) == \
        {"unit": "second", "usd": 0.05, "usd_audio": 0.15}
    assert prices.current(book, "b:x", {"unit": "image", "usd": 0.04}) == {"unit": "image", "usd": 0.04}
    assert prices.stale({}) and prices.stale({"checked_ts": 0})


def test_every_route_in_the_catalog_has_a_reader_and_a_listed_price():
    for route_id, (service, r) in studio.price_routes().items():
        assert service in prices.READERS, route_id
        assert r["price"]["usd"] > 0 and r["price"]["unit"] in ("image", "mp", "1k", "second"), route_id
        assert r.get("source"), route_id


def test_inngest_checks_prices_each_morning_central_time():
    fn = next(f for f in inngest_app.functions if f.id.endswith("studio-prices"))
    triggers = fn.get_config("https://example.test").main.triggers
    assert any(getattr(t, "cron", None) == "TZ=America/Chicago 0 5 * * *" for t in triggers)
