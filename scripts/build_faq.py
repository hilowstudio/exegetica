#!/usr/bin/env python3
"""Build the chat page's FAQ (the About Exegetica window in webapp/static/index.html) from docs/faq.md.

docs/faq.md holds the answers written with the maker. Each "## " heading is an audience (Students,
Teachers, Parents), each line that is a bold question opens a question, and the Markdown under it is
the answer. Everything after the end marker (the follow-ups list) stays out. The page gets one
collapsible entry per question, between the FAQ markers, so the rest of the page is untouched.

    .venv/Scripts/python.exe scripts/build_faq.py           # rebuild the FAQ in index.html
    .venv/Scripts/python.exe scripts/build_faq.py --check   # exit 1 if index.html is out of date
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "faq.md"
PAGE = ROOT / "webapp" / "static" / "index.html"
END = "<!-- end of the published FAQ -->"
START_MARK, END_MARK = "<!-- FAQ:start (built by scripts/build_faq.py from docs/faq.md) -->", "<!-- FAQ:end -->"
_QUESTION = re.compile(r"^\*\*(.+\?)\*\*\s*$")
_md = MarkdownIt("commonmark", {"html": False})


def sections(text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """[(audience, [(question, answer markdown), ...]), ...] from the published part of docs/faq.md."""
    body = text.split(END, 1)[0]
    out: list[tuple[str, list[tuple[str, str]]]] = []
    question, lines = None, []

    def close():
        if question is not None:
            out[-1][1].append((question, "\n".join(lines).strip()))

    for line in body.splitlines():
        if line.startswith("## "):
            close()
            question, lines = None, []
            out.append((line[3:].strip(), []))
        elif out and (m := _QUESTION.match(line)):
            close()
            question, lines = m.group(1), []
        elif question is not None:
            lines.append(line)
    close()
    return out


def render(text: str) -> str:
    parts = [START_MARK]
    for audience, questions in sections(text):
        parts.append(f'<div class="faq-h">{html.escape(audience)}</div>')
        for question, answer in questions:
            parts.append(f'<details class="faq"><summary>{html.escape(question)}</summary>'
                         f'{_md.render(answer).strip()}</details>')
    parts.append(END_MARK)
    return "\n".join(parts)


def built(page: str, block: str) -> str:
    start, end = page.index(START_MARK), page.index(END_MARK) + len(END_MARK)
    return page[:start] + block + page[end:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if index.html is out of date")
    args = ap.parse_args()
    page = PAGE.read_text(encoding="utf-8")
    new = built(page, render(SOURCE.read_text(encoding="utf-8")))
    if args.check:
        if new != page:
            print("index.html's FAQ is out of date: run scripts/build_faq.py")
            return 1
        print("index.html's FAQ matches docs/faq.md")
        return 0
    PAGE.write_text(new, encoding="utf-8")
    count = sum(len(q) for _a, q in sections(SOURCE.read_text(encoding="utf-8")))
    print(f"built {count} questions into {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
