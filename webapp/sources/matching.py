"""Shared fuzzy title/author matching for the source adapters.

Ported verbatim (behavior) from quillnext `src/lib/sources/matching.ts`. A WRONG
full text is worse than none, so matching is deliberately conservative: a candidate
must clear a title-containment bar and, when an author is supplied, expose that
author's surname. All functions are pure and never raise.
"""
from __future__ import annotations

import re

# A real desktop UA — some catalogs/mirrors 403 a default client UA. Shared.
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def normalize(s: str | None) -> str:
    """Lowercase, strip punctuation, collapse whitespace — for fuzzy comparison."""
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def author_last_name(name: str | None) -> str:
    """A comparable surname: before the first comma ("Austen, Jane"), else the last
    whitespace token ("Jane Austen") — the most stable token across orderings."""
    n = (name or "").strip()
    if not n:
        return ""
    if "," in n:
        return normalize(n.split(",")[0])
    parts = normalize(n).split()
    return parts[-1] if parts else ""


def score_title_author(
    candidate_title: str | None,
    candidate_authors: list[str] | None,
    want_title_norm: str,
    want_author_last: str | None,
) -> float | None:
    """Score a candidate against the requested title/author. Higher = better; None
    when it is NOT a genuine match.

    - Title: normalized containment in EITHER direction (catalogs carry subtitles),
      with a 3-char minimum so a 1-2 char overlap can't pass.
    - Author (only when supplied): the requested surname must appear among the
      candidate authors, else reject — this blocks a wrong-author same-title work.
    Score = exact-title(2) + author-match(1) − small length-distance penalty.
    """
    t = normalize(candidate_title)
    if not t or not want_title_norm:
        return None
    title_ok = (want_title_norm in t or t in want_title_norm) and min(len(t), len(want_title_norm)) >= 3
    if not title_ok:
        return None

    author_score = 0
    if want_author_last:
        last_names = [ln for ln in (author_last_name(a) for a in (candidate_authors or [])) if ln]
        author_ok = any(
            ln == want_author_last or want_author_last in ln or ln in want_author_last
            for ln in last_names
        )
        if not author_ok:
            return None
        author_score = 1

    exact = 2 if t == want_title_norm else 0
    return exact + author_score - abs(len(t) - len(want_title_norm)) / 100
