#!/usr/bin/env python3
"""
Render the generated course Markdown to print-ready PDFs.

Self-contained: inlines the course stylesheet (webapp/static/course.css) and
renders each document with headless Edge/Chromium via Playwright (channel=msedge).
No server and no MCP bridge — it only reads the generated Markdown, so it runs
under the plain interpreter that has playwright + markdown-it-py.

Student-facing docs go to docs/john/john-pdf/student/; --teacher additionally renders
the teacher guides and answer keys to docs/john/john-pdf/teacher/ (kept separate so the
student set can be shared without leaking teacher material).

Run:
    python scripts/course_pdf.py --all
    python scripts/course_pdf.py --file GEN_syllabus.md
    python scripts/course_pdf.py --all --teacher
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from webapp import course  # noqa: E402

CSS = (ROOT / "webapp" / "static" / "course-print.css").read_text(encoding="utf-8")
OUT = ROOT / "docs" / "john" / "john-pdf"
FONTS_DIR = ROOT / "webapp" / "static" / "fonts"


def _embedded_fonts() -> str:
    """Self-hosted fonts as base64 @font-face rules, so the render never touches the
    network — glyphs stay correct offline / in CI. Files from scripts/fetch_fonts.py."""
    manifest = json.loads((FONTS_DIR / "fonts.json").read_text(encoding="utf-8"))
    faces = []
    for e in manifest:
        b64 = base64.b64encode((FONTS_DIR / e["file"]).read_bytes()).decode("ascii")
        faces.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
            "src:url(data:font/woff2;base64,%s) format('woff2');unicode-range:%s;}"
            % (e["family"], e["style"], e["weight"], b64, e["unicode_range"]))
    return "".join(faces)


_FONT_CSS = _embedded_fonts()


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-") or "document"


def _running_head(title: str) -> str:
    """Per-doc running head via the native @page @top-left margin box (Edge/Chrome
    131+). One doc per PDF, so the title is templated straight in — no string-set."""
    t = title if len(title) <= 58 else title[:57].rstrip() + "…"
    t = t.replace("\\", "\\\\").replace('"', '\\"')
    return ('@page{@top-left{content:"' + t + '";'
            'font:8.5pt "Inter",system-ui,sans-serif;color:#7a828f;letter-spacing:.02em}}'
            '@page:first{@top-left{content:""}}')


def _html(art: dict) -> str:
    body = course.render_html(art["path"])
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<style>{_FONT_CSS}</style>"
        f"<style>{CSS}</style><style>{_running_head(art['title'])}</style></head>"
        f"<body><main><article class=\"doc\">{body}</article></main></body></html>"
    )


async def _render(page, art: dict, out_path: Path) -> None:
    await page.set_content(_html(art), wait_until="networkidle")
    await page.evaluate("() => document.fonts.ready")   # embed real glyphs, not fallbacks
    # @page (CSS) owns geometry, margins, and the running head/folio margin boxes.
    await page.pdf(path=str(out_path), prefer_css_page_size=True,
                   print_background=True, tagged=True)


async def _run(jobs: list[tuple[dict, Path]]) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        for art, out_path in jobs:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            await _render(page, art, out_path)
            print(f"[pdf] {out_path.relative_to(ROOT)}")
        await browser.close()


def _pdf_name(art: dict) -> str:
    """Lesson-guide titles can repeat, which would silently overwrite one PDF with
    another, so name teacher lesson guides by their (unique) source file. Course
    docs and reading guides have distinct titles, so keep the friendlier title."""
    if art.get("kind") in ("teacher_guide", "reading_guide"):
        return _slug(re.sub(r"^GEN[_-]", "", Path(art["file"]).stem)) + ".pdf"
    return _slug(art["title"]) + ".pdf"


def _jobs(m: dict, args) -> list[tuple[dict, Path]]:
    if args.file:
        art = next((a for a in m["artifacts"] if a["file"] == args.file), None)
        if not art:
            raise SystemExit(f"no artifact named {args.file}")
        sub = "teacher" if art["audience"] == "teacher" else "student"
        return [(art, OUT / sub / _pdf_name(art))]

    jobs: list[tuple[dict, Path]] = []
    for a in m["artifacts"]:
        if a["audience"] == "student":
            jobs.append((a, OUT / "student" / _pdf_name(a)))
        elif args.teacher:
            jobs.append((a, OUT / "teacher" / _pdf_name(a)))
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser(description="Render course Markdown to print-ready PDFs.")
    ap.add_argument("--all", action="store_true", help="render every generated doc")
    ap.add_argument("--file", help="render a single doc by filename, e.g. GEN_syllabus.md")
    ap.add_argument("--teacher", action="store_true", help="also render teacher guides + keys")
    args = ap.parse_args()
    if not (args.all or args.file):
        ap.error("pass --all or --file <name>")

    m = course.build_manifest()
    jobs = _jobs(m, args)
    if not jobs:
        raise SystemExit("nothing to render")
    print(f"rendering {len(jobs)} PDF(s) -> {OUT.relative_to(ROOT)}/")
    asyncio.run(_run(jobs))


if __name__ == "__main__":
    main()
