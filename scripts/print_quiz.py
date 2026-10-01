#!/usr/bin/env python3
"""
Print version of a chapter quiz: a student PDF and a one-page teacher answer key.

For students without a device. Reads the same quiz Markdown the Google Form is
built from (via build_forms_quiz.parse_quiz), so paper and online can't drift.
Renders with the course PDF pipeline's embedded fonts and headless Edge, like
course_pdf.py.

  <quiz>_print.pdf        student copy: name line, lettered choices to circle,
                          ruled lines for the written answers, no key or feedback
  <quiz>_TEACHER-KEY.pdf  the letters for the PRINTED order (the online form
                          shuffles choices), plus the written rubrics and models

Run:
    python scripts/print_quiz.py docs/john-quizzes/ch01-quiz.md
"""
from __future__ import annotations

import asyncio
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from build_forms_quiz import MC_POINTS, WRITTEN_POINTS, parse_quiz  # noqa: E402
from course_pdf import _FONT_CSS  # noqa: E402  (self-hosted fonts, base64-embedded)

LETTERS = "ABCD"
WRITE_LINES = {"ch01-quiz": {22: 9, 23: 7},     # ruled lines per written question, by quiz;
               "ch02-quiz": {22: 10, 23: 12}}   # default below
DEFAULT_LINES = 8


def smart(s: str) -> str:
    """Straight quotes to typographic ones, HTML-escape, and keep each verse
    reference ("1:43-51", "1:31, 33") on one line so it never breaks mid-range."""
    s = re.sub(r'(^|[\s(\[{])"', "\\1\u201c", s)
    s = s.replace('"', "\u201d")
    s = re.sub(r"(^|[\s(\[{\u201c])'", "\\1\u2018", s)
    s = s.replace("'", "\u2019")
    s = html.escape(s, quote=False)
    return re.sub(r"(\d+:\d+(?:-\d+)?(?:, ?\d+)*)", r'<span class="nb">\1</span>', s)


def _field(md: str, name: str) -> str:
    m = re.search(rf"\*\*{name}:\*\*\s*(.+?)\s*$", md, re.M)
    return m.group(1).strip() if m else ""


BASE_CSS = """
@page { size: letter; margin: 0.55in 0.65in 0.7in; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; color: #000; font: 10.6pt/1.32 "Source Serif 4", Georgia, serif; }
.nb { white-space: nowrap; }
h2.part.newpage { break-before: page; margin-top: 0; }   /* written section starts its own page */
.course { font: 600 7.5pt "Inter", sans-serif; letter-spacing: .12em; text-transform: uppercase; color: #000; }
h1 { font: 600 17pt/1.15 "Fraunces", Georgia, serif; margin: 3pt 0 9pt; }
.fields { display: flex; flex-wrap: wrap; gap: 6pt 16pt; font: 9.5pt "Inter", sans-serif; margin: 0 0 9pt; }
.fields span { white-space: nowrap; }
.line { display: inline-block; border-bottom: .75pt solid #000; height: 1em; vertical-align: -1pt; margin-left: 4pt; }
.w-name { width: 2.5in; } .w-short { width: .55in; } .w-date { width: 1.05in; }
.instr { font-size: 9.8pt; margin: 0 0 4pt; padding: 5pt 0; border-top: .75pt solid #000; border-bottom: .75pt solid #000; }
h2.part { font: 700 8.3pt "Inter", sans-serif; letter-spacing: .1em; text-transform: uppercase;
  margin: 13pt 0 7pt; padding-bottom: 3pt; border-bottom: .5pt solid #000; break-after: avoid; }
.q { break-inside: avoid; margin: 0 0 9pt; }
.stem { margin: 0 0 3pt; }
.num { font: 700 9.5pt "Inter", sans-serif; margin-right: 3pt; }
.pts { font: 8.5pt "Inter", sans-serif; color: #000; white-space: nowrap; }
.opts { list-style: none; margin: 0; padding: 0 0 0 14pt; }
.opts li { display: grid; grid-template-columns: 15pt 1fr; column-gap: 5pt; margin: 2pt 0; }
.bub { width: 12.5pt; height: 12.5pt; border: .75pt solid #000; border-radius: 50%;
  font: 600 7.8pt/12.5pt "Inter", sans-serif; text-align: center; margin-top: .5pt; }
.lines div { height: .34in; border-bottom: .6pt solid #000; }
.lines { margin-top: 2pt; }
/* teacher key */
.note { font-size: 9.6pt; margin: 0 0 10pt; }
.keygrid { display: grid; grid-template-columns: 1fr 1fr; column-gap: 18pt; margin-bottom: 8pt; }
.krow { display: grid; grid-template-columns: 16pt 16pt 1fr; column-gap: 5pt; align-items: baseline;
  padding: 2.2pt 0; border-bottom: .4pt solid #000; font-size: 9pt; }
.krow .n { font: 700 8.5pt "Inter", sans-serif; text-align: right; }
.krow .l { font: 700 9.5pt "Inter", sans-serif; }
.krow .t { color: #000; min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.wkey { break-inside: avoid; margin: 0 0 10pt; font-size: 9.4pt; }
.wkey p { margin: 2pt 0 4pt; }
.wkey ul { margin: 0 0 4pt; padding-left: 14pt; }
.wkey li { margin: 1pt 0; }
"""


def _doc(title: str, foot: str, body: str) -> str:
    """One PDF per doc, so the footer text is templated straight into @page (the
    native margin box, Edge 131+), the same way course_pdf does running heads."""
    foot_css = foot.replace("\\", "\\\\").replace('"', '\\"')
    page_css = ('@page{@bottom-center{content:"' + foot_css + ' · page " counter(page) '
                '" of " counter(pages);font:7.5pt "Inter",system-ui,sans-serif;color:#000}}')
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(title)}</title>"
            f"<style>{_FONT_CSS}</style><style>{BASE_CSS}</style><style>{page_css}</style>"
            f"</head><body>{body}</body></html>")


def student_html(q: dict, course: str, instructions: str, lines: dict[int, int]) -> str:
    out = [f'<div class="course">{smart(course)}</div>',
           f"<h1>{smart(q['title'])}</h1>",
           '<div class="fields">'
           '<span>Name<i class="line w-name"></i></span>'
           '<span>Period<i class="line w-short"></i></span>'
           '<span>Date<i class="line w-date"></i></span>'
           f'<span>Score<i class="line w-short"></i> / {q["total"]}</span></div>',
           f'<p class="instr">{smart(instructions)}</p>']
    items = q["items"]
    for i, it in enumerate(items):
        if it["kind"] == "header":
            nxt = items[i + 1]["kind"] if i + 1 < len(items) else ""
            cls = "part newpage" if nxt == "written" else "part"
            out.append(f'<h2 class="{cls}">{smart(it["title"])}</h2>')
            continue
        num, text = it["title"].split(". ", 1)
        if it["kind"] == "mc":
            opts = "".join(f'<li><span class="bub">{LETTERS[i]}</span><span>{smart(o)}</span></li>'
                           for i, o in enumerate(it["options"]))
            out.append(f'<section class="q"><p class="stem"><span class="num">{num}.</span>'
                       f'{smart(text)}</p><ol class="opts">{opts}</ol></section>')
        else:
            n = lines.get(it["num"], DEFAULT_LINES)
            out.append(f'<section class="q"><p class="stem"><span class="num">{num}.</span>'
                       f'{smart(text)} <span class="pts">({WRITTEN_POINTS} points)</span></p>'
                       f'<div class="lines">{"<div></div>" * n}</div></section>')
    return "".join(out)


def key_html(q: dict, course: str) -> str:
    mcs = [it for it in q["items"] if it["kind"] == "mc"]
    rows = []
    for it in mcs:
        letter = LETTERS[it["options"].index(it["correct"])]
        rows.append(f'<div class="krow"><span class="n">{it["num"]}</span>'   # one line;
                    f'<span class="l">{letter}</span>'                         # CSS clips the text
                    f'<span class="t">{smart(it["correct"])}</span></div>')
    half = (len(rows) + 1) // 2
    grid = (f'<div class="keygrid"><div>{"".join(rows[:half])}</div>'
            f'<div>{"".join(rows[half:])}</div></div>')
    mc_pts = len(mcs) * MC_POINTS
    wr = [it for it in q["items"] if it["kind"] == "written"]
    out = [f'<div class="course">{smart(course)}</div>',
           f"<h1>Answer key: {smart(q['title'].split(':')[0])} (paper copy)</h1>",
           f'<p class="note">These letters match the printed copy. The online form shuffles the '
           f'choices, so use this key for paper only. Multiple choice is {MC_POINTS} points each '
           f'({mc_pts}), the written answers are {WRITTEN_POINTS} each '
           f'({len(wr) * WRITTEN_POINTS}), {q["total"]} total.</p>',
           '<h2 class="part">Multiple choice</h2>', grid,
           '<h2 class="part">Written answers</h2>']
    for it in wr:
        out.append(f'<div class="wkey"><p class="stem"><span class="num">{it["num"]}.</span>'
                   f'{smart(it["title"].split(". ", 1)[1])}</p>{_notes_html(it["notes"])}</div>')
    return "".join(out)


def _notes_html(notes: list[str]) -> str:
    """Rubric and model-answer lines: "Label: text" gets a bold label, and a run
    of "- " lines (an accept list) becomes a bulleted list."""
    out, items = [], []
    for n in notes + [""]:
        if n.startswith("- "):
            items.append(f"<li>{smart(n[2:])}</li>")
            continue
        if items:
            out.append(f'<ul>{"".join(items)}</ul>')
            items = []
        if n:
            label, _, rest = n.partition(": ")
            out.append(f"<p><b>{smart(label)}:</b> {smart(rest)}</p>" if rest
                       else f"<p>{smart(n)}</p>")
    return "".join(out)


async def _render(jobs: list[tuple[str, Path]]) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        for doc, out in jobs:
            await page.set_content(doc, wait_until="networkidle")
            await page.evaluate("() => document.fonts.ready")
            await page.pdf(path=str(out), prefer_css_page_size=True,
                           print_background=True, tagged=True)
            print(f"[pdf] {out.relative_to(ROOT)}")
        await browser.close()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/print_quiz.py docs/john-quizzes/ch01-quiz.md")
    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = ROOT / path
    md = path.read_text(encoding="utf-8")
    q = parse_quiz(path)
    course = _field(md, "Course") or "Sophomore Bible"
    instructions = q["description"] + " Circle the letter of the best answer."
    short = q["title"].split(":")[0]
    student = _doc(q["title"], short,
                   student_html(q, course, instructions, WRITE_LINES.get(path.stem, {})))
    key = _doc(q["title"] + " answer key", f"{short} answer key, teacher copy",
               key_html(q, course))
    asyncio.run(_render([(student, path.with_name(path.stem + "_print.pdf")),
                         (key, path.with_name(path.stem + "_TEACHER-KEY.pdf"))]))


if __name__ == "__main__":
    main()
