#!/usr/bin/env python3
"""John course: per-lesson sub-passage planner.

The calendar map gives each unit a verse range and a lesson count, but only
Units 0-1 have per-lesson passages. This proposes a per-lesson split for every
other multi-lesson unit, snapping boundaries to the seams the instructor cut
when preaching (parsed from the sermon filenames) and otherwise splitting the
range evenly. Output feeds the generation adapter so a lesson generates its own
sub-passage without a manual override. Splits are PROPOSED, for review.

    python -m scripts.plan_passages            # write docs/john-lesson-passages.json
    python -m scripts.plan_passages --show U2  # preview a unit's split
"""
import argparse
import json
import re
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = json.loads((ROOT / "docs" / "john-calendar-map.json").read_text(encoding="utf-8"))
SERMONS = ROOT / "docs" / "john-sermons"


def _range(pas):
    m = re.match(r"\s*(\d+):(\d+)(?:[-–](\d+))?", pas or "")
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
    return (None, None, None)


def _sermon_seams(chapter, a, b):
    """Sermon start-verses that fall inside (a, b] of the given chapter."""
    seams = set()
    for p in SERMONS.glob("*.md"):
        m = re.search(r"\(John ([\d\-]+)\)", p.name)
        if not m:
            continue
        parts = [int(x) for x in m.group(1).split("-") if x]
        if not parts or parts[0] != chapter or len(parts) < 3:
            continue
        s = parts[1]
        if a < s <= b:
            seams.add(s)
    return sorted(seams)


def split_range(chapter, a, b, n, seams):
    total = b - a + 1
    if n <= 1 or total <= 1:
        return [(a, b)]
    cuts = []
    for k in range(1, n):
        v = a + round(k * total / n)
        near = [s for s in seams if abs(s - v) <= 3]
        if near:
            v = min(near, key=lambda s: abs(s - v))
        cuts.append(min(max(v, a + 1), b))
    cuts = sorted(set(cuts))
    if len(cuts) != n - 1:  # snapping collapsed cuts; fall back to plain even split
        cuts = sorted({a + round(k * total / n) for k in range(1, n)})
        cuts = [min(max(c, a + 1), b) for c in cuts]
        cuts = sorted(set(cuts))
    bounds = [a] + cuts + [b + 1]
    segs = []
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1] - 1
        segs.append((s, max(s, e)))
    return segs


def _fmt(chapter, s, e):
    return f"{chapter}:{s}" if s == e else f"{chapter}:{s}-{e}"


def plan():
    out = {}
    preview = {}
    rows = MAP["lessons"]
    # group consecutive rows by unit
    for unit, grp in groupby(rows, key=lambda r: r["unit"]):
        grp = list(grp)
        n = len(grp)
        # if the unit's lessons already carry distinct passages (U0/U1), keep them
        passages = [r.get("passage", "") for r in grp]
        distinct_verse = len({p for p in passages if ":" in p}) > 1
        rng = _range(grp[0].get("passage", ""))
        if distinct_verse or rng[0] is None or n == 1:
            for r in grp:
                out[str(r["i"])] = r.get("passage", "")
            preview[unit] = [(r["i"], r.get("passage", "")) for r in grp]
            continue
        chapter, a, b = rng
        seams = _sermon_seams(chapter, a, b)
        segs = split_range(chapter, a, b, n, seams)
        preview[unit] = []
        for r, (s, e) in zip(grp, segs):
            out[str(r["i"])] = _fmt(chapter, s, e)
            preview[unit].append((r["i"], _fmt(chapter, s, e)))
    return out, preview


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", help="preview one unit key, e.g. U2 (does not write)")
    a = ap.parse_args()
    out, preview = plan()
    if a.show:
        for unit, items in preview.items():
            if unit.split()[0] == a.show:
                print(f"{unit}:")
                for i, p in items:
                    print(f"  lesson {i}: John {p}")
        return
    (ROOT / "docs" / "john-lesson-passages.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote docs/john-lesson-passages.json ({len(out)} lessons)")
    # show the exposition units for a quick eyeball
    for unit, items in preview.items():
        if len(items) > 1 and ":" in (items[0][1] or ""):
            print(f"  {unit}: " + " | ".join(p for _, p in items))


if __name__ == "__main__":
    main()
