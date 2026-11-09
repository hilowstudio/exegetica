"""Every text colour in webapp/static/css/tokens.css stays readable on every background it can sit on, in
both themes: the paper, the surfaces, the sunk panels, and the garden behind every page (shell.css) at its
darkest point for the light theme and its lightest for the dark (WCAG 2.2 AA, 1.4.3 and 1.4.11). Rule D2
of the exegetica-design skill. No network."""
import re
from pathlib import Path

import pytest
from PIL import Image

STATIC = Path(__file__).resolve().parent.parent / "webapp" / "static"
TOKENS = (STATIC / "css" / "tokens.css").read_text(encoding="utf-8")
SHELL = (STATIC / "css" / "shell.css").read_text(encoding="utf-8")

TEXT = ("ink", "ink-soft", "ink-faint", "accent", "accent-soft", "iron", "iron-soft", "ok", "warn", "err")
GROUNDS = ("paper", "surface", "surface-2", "sunk")


def _block(css: str) -> dict:
    out = {}
    for name, h in re.findall(r"--([\w-]+):\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css):
        out[name] = "#" + (h if len(h) == 6 else "".join(ch * 2 for ch in h))   # #fff is #ffffff
    return out


def _themes() -> dict:
    light = _block(re.search(r":root\s*\{(.*?)\}", TOKENS, re.S).group(1))
    system_dark = _block(re.search(r"prefers-color-scheme:\s*dark\)\{:root:not\(\[data-theme=\"light\"\]\)\{(.*?)\}", TOKENS, re.S).group(1))
    chosen_dark = _block(re.search(r':root\[data-theme="dark"\]\{(.*?)\}', TOKENS, re.S).group(1))
    assert system_dark == chosen_dark, "the system-dark and chosen-dark token sets differ"
    return {"light": light, "dark": chosen_dark}


def _rgb(h: str) -> tuple:
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _lum(c) -> float:
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _garden(theme: str) -> str:
    # each theme names its own garden image in tokens.css (--garden), and the page draws var(--garden)
    assert "var(--garden)" in re.search(r"^body\{[^}]*\}", SHELL, re.M).group(0)
    light, *dark = re.findall(r'--garden:url\("/static/([\w.-]+)"\)', TOKENS)
    return light if theme == "light" else dark[-1]


def _garden_extremes(theme: str):
    img = Image.open(STATIC / _garden(theme)).convert("RGB")
    img.thumbnail((300, 300))
    px = sorted(img.getdata(), key=_lum)
    return px[int(len(px) * 0.005)], px[int(len(px) * 0.995)]


def _overlay() -> float:
    body = re.search(r"^body\{[^}]*\}", SHELL, re.M).group(0)
    return int(re.search(r"var\(--paper\)\s+(\d+)%", body).group(1)) / 100


def _grounds(theme: str, tokens: dict) -> dict:
    darkest, lightest = _garden_extremes(theme)
    a, paper = _overlay(), _rgb(tokens["paper"])
    worst = darkest if theme == "light" else lightest
    grounds = {name: _rgb(tokens[name]) for name in GROUNDS}
    grounds["garden"] = tuple(round(a * paper[i] + (1 - a) * worst[i]) for i in range(3))
    return grounds


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_text_colour_is_readable_on_every_background(theme):
    tokens = _themes()[theme]
    failures = []
    for ground, bg in _grounds(theme, tokens).items():
        for name in TEXT:
            r = _ratio(_rgb(tokens[name]), bg)
            if r < 4.5:
                failures.append(f"--{name} on {ground}: {r:.2f}")
        r = _ratio(_rgb(tokens["brass"]), bg)   # brass draws icons, rings and borders: the 3:1 rule
        if r < 3:
            failures.append(f"--brass on {ground}: {r:.2f}")
    assert not failures, f"{theme}: " + "; ".join(failures)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_on_the_accent_is_readable(theme):
    tokens = _themes()[theme]
    assert _ratio(_rgb(tokens["on-accent"]), _rgb(tokens["accent"])) >= 4.5


def test_the_course_pages_text_is_readable_on_their_backgrounds():
    # course.css keeps the school's own palette and is always light: cream over the light garden
    course = (STATIC / "course.css").read_text(encoding="utf-8")
    pal = _block(re.search(r":root\s*\{(.*?)\}", course, re.S).group(1))
    veil = int(re.search(r"var\(--bg\)\s+(\d+)%", course).group(1)) / 100
    darkest, _ = _garden_extremes("light")
    cream = _rgb(pal["cream-50"])
    grounds = {"white": _rgb(pal["c-paper"]), "cream": cream, "cream-100": _rgb(pal["cream-100"]),
               "chip": _rgb("#fff8e6"), "garden": tuple(round(veil * cream[i] + (1 - veil) * darkest[i]) for i in range(3))}
    assert "url(\"/static/garden-light.webp\")" in course
    failures = [f"--{name} on {g}: {_ratio(_rgb(pal[name]), bg):.2f}"
                for name in ("c-ink", "steel-500", "gold-600", "navy-900", "navy-800", "navy-700")
                for g, bg in grounds.items() if _ratio(_rgb(pal[name]), bg) < 4.5]
    assert not failures, "; ".join(failures)


def test_the_page_has_a_paper_colour_under_the_garden():
    # if the image fails to load, and for tools that cannot see images, the page is still paper
    assert "fixed var(--paper)" in re.search(r"^body\{[^}]*\}", SHELL, re.M).group(0)
