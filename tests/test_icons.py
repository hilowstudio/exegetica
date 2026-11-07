"""Browser and home-screen icons (scripts/build_icons.py): every page links the same versioned set and
the manifest, the manifest's icons exist at their sizes, and the site root answers the two paths
browsers and phones ask for when a page names no icon. No network."""
import json
import re

from PIL import Image
from starlette.testclient import TestClient

from webapp import app as appmod

ICONS = appmod.STATIC_DIR / "icons"


def test_every_page_links_the_icons_and_the_manifest():
    for page in sorted(appmod.STATIC_DIR.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        hrefs = re.findall(r'<link rel="(?:icon|apple-touch-icon|manifest)"[^>]*href="([^"]+)"', text)
        assert {h.split("?")[0] for h in hrefs} == {
            "/static/icons/favicon.ico", "/static/icons/favicon-32.png", "/static/icons/favicon-16.png",
            "/static/icons/apple-touch-icon.png", "/static/manifest.json"}, page.name
        versions = {h.split("?v=")[1] for h in hrefs if "?v=" in h}
        assert len(versions) == 1, page.name   # one version, so a new icon reaches every page


def test_the_icons_are_square_at_their_sizes():
    for name, size in {"favicon-16.png": 16, "favicon-32.png": 32, "favicon-48.png": 48,
                       "apple-touch-icon.png": 180, "icon-192.png": 192, "icon-512.png": 512}.items():
        assert Image.open(ICONS / name).size == (size, size), name
    assert Image.open(ICONS / "favicon.ico").info["sizes"] >= {(16, 16), (32, 32), (48, 48)}


def test_the_manifest_names_icons_that_exist():
    manifest = json.loads((appmod.STATIC_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["start_url"] == "/" and manifest["name"] == "Exegetica"
    for icon in manifest["icons"]:
        path = ICONS / icon["src"].split("?")[0].rsplit("/", 1)[1]
        size = int(icon["sizes"].split("x")[0])
        assert Image.open(path).size == (size, size)


def test_the_site_root_answers_for_the_icons():
    client = TestClient(appmod.app)   # no lifespan: these routes need none
    for path, kind in (("/favicon.ico", "image/"), ("/apple-touch-icon.png", "image/png")):
        r = client.get(path)
        assert r.status_code == 200 and r.headers["content-type"].startswith(kind), path
