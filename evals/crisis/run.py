"""How the crisis check does on messages it was not written against (docs/decisions/0018).

Each set was written by a separate agent that never saw webapp/safety.py. Each message is "fire"
(should open the help window), "quiet" (must not), or "ambiguous" (reported, not scored).

- heldout.json (2026-11-04) scored the first word check. Its misses were then studied to widen the
  word check by kind of phrasing, so it is no longer a fair test of the word check.
- heldout2.json (2026-11-04) was written after that. It scored the word list once with the patterns
  frozen, and two versions of the local classifier (2026-11-05), the second changed for Bible verses.
  Its scores then showed the list's two broad patterns adding wrong opens, so it is spent too.
- heldout3.json (2026-11-05) was written after the list's broad patterns became category hints, and
  scored once with everything frozen.

Layers: "list" is the word list alone, "classifier" the local classifier alone, "local" the two
together (what runs before the reply), "model" the model check (Nemotron since 2026-11-06, Haiku before), "either" local or model.

    .venv/Scripts/python.exe evals/crisis/run.py                     # heldout3, the local check: free
    .venv/Scripts/python.exe evals/crisis/run.py --model             # also the model check: about $0.01
    .venv/Scripts/python.exe evals/crisis/run.py --set heldout       # the first set
    add --show to list the messages each layer missed or opened on wrongly
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from webapp import safety  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", action="store_true", help="also run the model check (paid, about $0.01)")
    ap.add_argument("--show", action="store_true", help="list misses and wrong opens")
    ap.add_argument("--set", default="heldout3", help="which set: heldout3 (default), heldout2 or heldout")
    args = ap.parse_args()
    cases = json.loads((Path(__file__).parent / f"{args.set}.json").read_text(encoding="utf-8"))
    similar = safety._similar
    for c in cases:
        c["classifier"] = similar(c["text"])
        c["local"] = safety.precheck(c["text"])["concern"]
    safety._similar = lambda message: False
    for c in cases:
        c["list"] = safety.precheck(c["text"])["concern"]
    safety._similar = similar
    usd, failed = 0.0, 0
    if args.model:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        gate = asyncio.Semaphore(8)

        async def one(c):
            async with gate:
                return await safety.check([c["text"]])
        for c, v in zip(cases, await asyncio.gather(*(one(c) for c in cases))):
            c["model"] = v["concern"]
            usd += v["usd"]
            failed += not v["ok"]
    layers = ["list", "classifier", "local"] + (["model", "either"] if args.model else [])
    for c in cases:
        if args.model:
            c["either"] = c["local"] or c["model"]
    for expect, verb in (("fire", "opened"), ("quiet", "opened wrongly"), ("ambiguous", "opened")):
        group = [c for c in cases if c["expect"] == expect]
        print(f"\n{expect} ({len(group)} messages), {verb}:")
        for layer in layers:
            n = sum(c[layer] for c in group)
            print(f"  {layer:<10} {n:>3} of {len(group)}")
        for kind in sorted({c["kind"] for c in group}):
            sub = [c for c in group if c["kind"] == kind]
            print(f"    {kind:<10} " + "  ".join(f"{layer} {sum(c[layer] for c in sub)}/{len(sub)}" for layer in layers))
        if args.show and expect != "ambiguous":
            wrong = [c for c in group if (not c[layers[-1]]) == (expect == "fire")]
            for c in wrong:
                print(f"      {'missed' if expect == 'fire' else 'opened'}: {c['text']}")
    if args.model:
        print(f"\nmodel check: ${usd:.4f} for {len(cases)} messages, {failed} gave no answer")


if __name__ == "__main__":
    asyncio.run(main())
