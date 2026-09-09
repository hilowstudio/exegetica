"""Grep user-facing text for AI-ism tics that the voice rules forbid.

A heuristic backstop for docs/voice-and-copy.md: prompts and rules leak under
context drift, so this catches the tics deterministically in review. It scans
the given files (default: the two static pages) for stock salience metaphors,
flattery openers, honesty framings, em dashes, and contrastive negation, and
exits non-zero if any are found.

    .venv/Scripts/python.exe scripts/lint_voice.py [files...]

Wire it into a pre-commit hook over staged files, or CI over the copy. The
phrase list is examples, not a spec: the target is the move (a vivid stand-in
for a concrete claim), so treat a clean run as necessary, not sufficient.
"""

import re
import sys
from pathlib import Path

# Files that quote the tics on purpose, so they are never linted.
SKIP = {"voice.md", "voice-and-copy.md", "lint_voice.py", "avoid-ai-isms.md"}

# (label, pattern). Multi-word where possible, to avoid firing on domain terms.
PATTERNS = [
    ("structural metaphor", re.compile(
        r"\b(load[- ]bearing|heavy lifting|blast radius|smoking gun|footgun|"
        r"belt[- ]and[- ]suspenders|ground truth)\b", re.I)),
    ("salience stamp", re.compile(
        r"(that'?s not nothing|\bnot nothing\b|sit with (that|this)|"
        r"here'?s why it matters|worth sitting with|resolves (it|the whole thing) cleanly|"
        r"reframes the whole thing)", re.I)),
    ("flattery opener", re.compile(
        r"(you'?re absolutely right|you are absolutely right|"
        r"\b(good|sharp|nice) catch\b|great question)", re.I)),
    ("honesty framing", re.compile(
        r"(let me be honest|honest take|the honest truth|to be blunt|\bhonestly\?)", re.I)),
    ("cliffhanger / pushback", re.compile(
        r"(would you like me to continue|just say the word|"
        r"(i'?ll|let me) (gently )?push back)", re.I)),
    ("em dash", re.compile("—")),
    ("contrastive negation", re.compile(
        r"\b(not|isn'?t|aren'?t|wasn'?t)\b[^.,;:!?]{1,48}[,;]?\s+(but|it'?s|they'?re)\b", re.I)),
]


def lint_file(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for n, line in enumerate(text.splitlines(), 1):
        for label, pat in PATTERNS:
            m = pat.search(line)
            if m:
                hits.append((n, label, m.group(0).strip()))
    return hits


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    if argv:
        files = [Path(a) for a in argv]
    else:
        files = [root / "webapp" / "static" / "index.html",
                 root / "webapp" / "static" / "generate.html"]
    total = 0
    for f in files:
        if f.name in SKIP or not f.is_file():
            continue
        hits = lint_file(f)
        for n, label, snippet in hits:
            rel = f.relative_to(root) if root in f.parents else f
            print(f"{rel}:{n}: {label}: {snippet!r}")
        total += len(hits)
    if total:
        print(f"\n{total} AI-ism tic(s) found. Rewrite the move, do not swap in a synonym.")
        return 1
    print("Clean: no AI-ism tics found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
