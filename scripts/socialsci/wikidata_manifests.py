"""One-time: record which ids each existing Wikidata cache file covers, so a widened harvest can fetch only the
ids not yet fetched (harvest_wikidata.py reads these manifests). Run with the harvest code that produced the
caches, before the scope changes. Each manifest is checked against its files' contents.

    .venv/Scripts/python.exe scripts/socialsci/wikidata_manifests.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harvest_wikidata as H  # noqa: E402


def chunks(ids: list[str]) -> list[list[str]]:
    return [ids[i:i + H.BATCH] for i in range(0, len(ids), H.BATCH)]


def write(kind: str, prefixes: list[str], ids: list[str], exact: bool) -> None:
    man = {}
    for n, chunk in enumerate(chunks(ids)):
        for p in prefixes:
            f = H.OUT / kind / f"{p}_{n:03d}.tsv"
            if not f.exists():
                raise SystemExit(f"missing {f}")
            man[f.name] = chunk
            got = {H.qid(r[0]) for r in H.read(f) if r}
            want = set(chunk)
            if (exact and p == "core" and got != want) or not got <= want:
                raise SystemExit(f"{f.name}: {len(got - want)} ids outside the chunk, {len(want - got)} missing")
    extra = [f.name for f in (H.OUT / kind).glob("*.tsv") if f.name not in man and f.name.split("_")[0] in prefixes]
    if extra:
        raise SystemExit(f"{kind}: files not covered by the reconstruction: {extra}")
    (H.OUT / kind / "_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    print(f"  {kind}: {len(man)} files, {len(ids):,} ids")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cand = sorted(H.candidates())
    write("candidates", ["dates"], cand, exact=False)
    final = sorted(H.final_people())
    write("people", ["core", "aliases", "claims", "positions", "works"], final, exact=True)
    events = sorted(H.ids_of("events"))
    write("events", ["core", "aliases", "claims", "dates"], events, exact=True)
    places = sorted(H.referenced(("people",), {"P19", "P20"}) | H.referenced(("events",), {"P276", "P17"}))
    write("places", ["core", "aliases", "claims"], places, exact=True)
    have: set[str] = set()
    for kind in ("people", "events", "places"):
        for f in (H.OUT / kind).glob("core_*.tsv"):
            have |= {H.qid(r[0]) for r in H.read(f) if r}
    other: set[str] = set()
    for kind in ("people", "events", "places"):
        for f in (H.OUT / kind).glob("claims_*.tsv"):
            other |= {H.qid(r[2]) for r in H.read(f) if len(r) >= 3 and r[2].startswith("<http://www.wikidata.org/entity/Q")}
    for f in (H.OUT / "people").glob("positions_*.tsv"):
        other |= {H.qid(r[1]) for r in H.read(f) if len(r) >= 2 and r[1]}
    for f in (H.OUT / "people").glob("works_*.tsv"):
        other |= {H.qid(r[1]) for r in H.read(f) if len(r) >= 2 and r[1]}
    write("labels", ["core"], sorted(other - have), exact=True)


if __name__ == "__main__":
    main()
