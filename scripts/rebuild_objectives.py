"""Rebuild one subject's objectives on the academic spine under the maker's count rule.

The spine (webapp/standards/) came from a Quill template that gave every sub-topic exactly 16
objectives, laddered from kindergarten to grade 12. Twelve subjects were rebuilt by hand in September
2026. Bible & Theology was not (220 of 223 sub-topics still hold 16), and Agriculture was added late
as a uniform first pass (6 objectives in every sub-topic, no standards). This script rebuilds a
subject one sub-topic at a time, the same way for each:

- The maker's rule: the count is not a target. A sub-topic gets as many objectives as its distinct
  competencies warrant, from the real sub-skills of its grade span, with no padding and no trimming.
- Each objective is a distinct, student-facing, on-topic competency a teacher can observe, placed
  within the sub-topic's grade span.
- Anchors. Bible objectives cite the Scripture they teach (verified against the bundled Bible) and,
  where a confession or catechism states the doctrine, that article (verified against the library's
  documents). Agriculture objectives cite the AFNR standard they teach (2024 edition, from
  standards/standards-index.json), chosen only from candidates the script supplies, or none.

Each sub-topic's result, with the model, the prompt's inputs, and the token use, is kept in
standards/rebuild/<SUBJECT>/<sub-topic>.json, so the rebuild is on record. A later run skips
sub-topics already done. --merge writes the results into standards-objectives.json and the tree's
counts, after saving the old file beside the results.

    .venv/Scripts/python.exe scripts/rebuild_objectives.py BIB --only BIB.2.4.6      # one sub-topic
    .venv/Scripts/python.exe scripts/rebuild_objectives.py AGR --limit 3              # a pilot
    .venv/Scripts/python.exe scripts/rebuild_objectives.py BIB                        # the rest (paid)
    .venv/Scripts/python.exe scripts/rebuild_objectives.py BIB --merge                # write the spine

Then rebuild the search embeddings: .venv/Scripts/python.exe scripts/build_standards_embeddings.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

STD = ROOT / "webapp" / "standards"
TREE_PATH = STD / "standards-tree.json"
OBJ_PATH = STD / "standards-objectives.json"
OUT = ROOT / "standards" / "rebuild"
INDEX = ROOT / "standards" / "standards-index.json"
MODEL = "claude-opus-5-5"
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0)}
CANDIDATES = 15

RULES = """You rebuild the learning objectives for one sub-topic of a K-12 academic spine used by teachers at a Christian school to plan lessons and draft materials.

The rule for how many: the count is not a target. Give this sub-topic as many objectives as its distinct competencies warrant, drawn from the real sub-skills of its subject across its grade span. Do not pad to reach a number and do not cut to stay under one. Let the count fall out of the content: a narrow sub-topic may need only two or three, a rich one many more.

Each objective must be:
- a distinct competency, not a restatement of another objective at a higher grade
- student-facing, beginning with an observable verb (identify, explain, compare, analyze, evaluate, create, and so on), so a teacher can see and assess it
- on the topic of this sub-topic and no other; leave neighbouring material to the sibling sub-topics named below
- placed at a grade within the sub-topic's grade span, where a student can first reasonably do it

The existing objectives come from an older template that forced a fixed number per sub-topic, so many are filler or drift off the topic as the grades climb. Keep any that name a real competency (you may reword them), drop the rest, and add what is missing.

Write each objective as one plain sentence with no ending period, no em dashes, and no semicolons. Give its Bloom level (1 remember, 2 understand, 3 apply, 4 analyze, 5 evaluate, 6 create)."""

BIBLE_RULES = """This sub-topic is Bible & Theology at a school in the Reformed tradition. Objectives teach what Scripture says, how it is read in context, and how the church has confessed it. State a doctrinal position as the tradition's, and keep belief invitational: a student's inner experience, feelings, or profession of faith is never an objective. A spiritual practice may be taught, so a student can describe it, explain its basis in Scripture, or carry it out in class, but the objective is what they can know and do, not what they feel.

Anchor each objective where it truly rests on a text:
- scripture: the passages it teaches, as Book chapter:verse or Book chapter:verse-verse (for example "Exodus 20:1-17"), never a whole chapter or book without verses
- confessions: the article or question that states the doctrine it teaches, written as the document's name and number (for example "Westminster Shorter Catechism Q41", "Westminster Confession of Faith 1.6", "Heidelberg Catechism Q1"), only when it truly states that doctrine
Leave standards empty."""

AG_RULES = """This sub-topic is Agriculture, Food & Natural Resources at a school where agricultural education and FFA are central. Objectives should serve classroom instruction, supervised agricultural experience, and FFA, in the language of the field.

Anchor each objective with standards: the codes, from the candidate AFNR standards listed below, of the standard it teaches. Use a code only when the objective truly teaches that standard, never a code that is not in the list, and leave the list empty when none fits. The AFNR standards are written for grades 9 to 12, so objectives below grade 9 usually have none. Leave scripture and confessions empty."""

SCHEMA = {"type": "json_schema", "schema": {
    "type": "object",
    "properties": {
        "objectives": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "grade": {"type": "integer"},
                "bloom": {"type": "integer"},
                "scripture": {"type": "array", "items": {"type": "string"}},
                "confessions": {"type": "array", "items": {"type": "string"}},
                "standards": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["text", "grade", "bloom", "scripture", "confessions", "standards"],
            "additionalProperties": False}},
        "changes": {"type": "string"},
    },
    "required": ["objectives", "changes"],
    "additionalProperties": False}}


# ------------------------------------------------------------------------------------------- inputs
def sub_topics(tree: dict, subject: str) -> list[dict]:
    """Each sub-topic of a subject with its place in the tree and its siblings."""
    s = next(s for s in tree["subjects"] if s["id"] == subject)
    out = []
    for ss in s["sub_subjects"]:
        for tp in ss["topics"]:
            names = [st["name"] for st in tp.get("sub_topics", [])]
            for st in tp.get("sub_topics", []):
                out.append({"id": st["id"], "name": st["name"], "grades": st.get("grades") or [],
                            "path": [s["name"], ss["name"], tp["name"]],
                            "siblings": [n for n in names if n != st["name"]]})
    return out


class AgStandards:
    """The AFNR standards (2024), with the embeddings the spine search already uses, to offer each
    sub-topic its closest candidates."""

    def __init__(self) -> None:
        import numpy as np
        from webapp import safety
        rows = json.loads(INDEX.read_text(encoding="utf-8")).get("AGR", [])
        self.rows = [r for r in rows if r.get("code") and len(r.get("statement", "")) > 25]
        self.embed = safety._embedder()
        self.np = np
        m = self.embed.encode([f"{r['set']}: {r['statement']}" for r in self.rows]).astype(np.float64)
        self.matrix = m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)

    def near(self, text: str, k: int = CANDIDATES) -> list[dict]:
        q = self.embed.encode([text]).astype(self.np.float64)[0]
        q /= max(self.np.linalg.norm(q), 1e-9)
        best = self.np.argsort(-(self.matrix @ q))[:k]
        return [self.rows[i] for i in best]


def prompt(subject: str, st: dict, old: list[dict], candidates: list[dict]) -> str:
    lo, hi = (min(st["grades"]), max(st["grades"])) if st["grades"] else (0, 12)
    lines = [f"Subject > strand > topic: {' > '.join(st['path'])}",
             f"Sub-topic: {st['name']}",
             f"Grade span: {'K' if lo == 0 else lo} to {hi}",
             "Sibling sub-topics in the same topic: " + ("; ".join(st["siblings"]) or "none"),
             "", "Existing objectives (grade: text):"]
    lines += [f"- {o.get('g')}: {o.get('t') or o.get('text')}" for o in old] or ["- none"]
    if subject == "BIB":
        refs = sorted({r for o in old for r in (o.get("a") or {}).get("scripture", [])})
        confs = sorted({r for o in old for r in (o.get("a") or {}).get("confessions", [])})
        lines += ["", "References the existing objectives cited (use, replace, or drop as fits):",
                  "Scripture: " + ("; ".join(refs) or "none"), "Confessions: " + ("; ".join(confs) or "none")]
    if candidates:
        lines += ["", "Candidate AFNR standards (code: statement, set):"]
        lines += [f"- {c['code']}: {c['statement']} ({c['set']})" for c in candidates]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------- validation
_CONFESSIONS: list[str] | None = None
_ONE_CHAPTER = re.compile(r"^(Obadiah|Philemon|2 John|3 John|Jude) (\d+(?:-\d+)?)$")


def confession_titles() -> list[str]:
    global _CONFESSIONS
    if _CONFESSIONS is None:
        con = sqlite3.connect(f"file:{ROOT / 'db' / 'study_bible.db'}?mode=ro", uri=True)
        _CONFESSIONS = sorted({t for (t,) in con.execute("select distinct doc_title from historical_documents")},
                              key=len, reverse=True)
    return _CONFESSIONS


def check(subject: str, st: dict, objs: list[dict], codes: set[str]) -> list[str]:
    """Problems with a result, or [] when it is sound."""
    from webapp import citations
    problems = []
    lo, hi = (min(st["grades"]), max(st["grades"])) if st["grades"] else (0, 12)
    seen = set()
    if not objs:
        problems.append("no objectives")
    for o in objs:
        t = o["text"].strip()
        if t.lower() in seen:
            problems.append(f"duplicate: {t}")
        seen.add(t.lower())
        if not lo <= o["grade"] <= hi:
            problems.append(f"grade {o['grade']} outside {lo}-{hi}: {t}")
        if not 1 <= o["bloom"] <= 6:
            problems.append(f"bloom {o['bloom']}: {t}")
        if "—" in t or ";" in t:
            problems.append(f"dash or semicolon: {t}")
        for ref in o["scripture"]:
            # One-chapter books are cited by verse alone ("Jude 3"); read them as chapter 1.
            ref = _ONE_CHAPTER.sub(r"\1 1:\2", ref)
            parsed = citations.references(ref)
            b = citations.bible()
            if len(parsed) != 1 or not b or not all(
                    b.verse_exists(parsed[0]["code"], parsed[0]["chapter"], v) for v in (parsed[0]["v1"], parsed[0]["v2"])):
                problems.append(f"scripture not found: {ref}")
        for c in o["confessions"]:
            if not any(c.startswith(title) or c.startswith(title.removeprefix("The "))
                       for title in confession_titles()):
                problems.append(f"confession not in the library: {c}")
        for code in o["standards"]:
            if code not in codes:
                problems.append(f"standard not among the candidates: {code}")
    return problems


# ------------------------------------------------------------------------------------------ calling
async def rebuild_one(client, subject: str, st: dict, old: list[dict], ag: AgStandards | None, model: str) -> dict:
    candidates = ag.near(f"{' '.join(st['path'])} {st['name']} " + " ".join(o.get("t", "") for o in old)) if ag else []
    user = prompt(subject, st, old, candidates)
    system = RULES + "\n\n" + (BIBLE_RULES if subject == "BIB" else AG_RULES)
    codes = {c["code"] for c in candidates}
    usage = {"input": 0, "output": 0}
    note = ""
    for attempt in range(2):
        msg = await client.messages.create(
            model=model, max_tokens=12000, system=system,
            output_config={"effort": "medium", "format": SCHEMA},
            messages=[{"role": "user", "content": user + note}])
        usage["input"] += msg.usage.input_tokens
        usage["output"] += msg.usage.output_tokens
        data = json.loads(next(b.text for b in msg.content if b.type == "text"))
        problems = check(subject, st, data["objectives"], codes)
        if not problems:
            break
        note = ("\n\nYour last answer had these problems. Fix them and answer again in full:\n- "
                + "\n- ".join(problems[:20]))
    return {"sub_topic": st["id"], "name": st["name"], "path": st["path"], "grades": st["grades"],
            "model": model, "objectives": data["objectives"], "changes": data["changes"],
            "problems": problems, "old_count": len(old), "candidates": sorted(codes), "usage": usage}


def cost(model: str, usage: dict) -> float:
    i, o = PRICES.get(model, (0, 0))
    return (usage["input"] * i + usage["output"] * o) / 1e6


async def run(subject: str, only: list[str], limit: int | None, model: str, concurrency: int) -> None:
    from anthropic import AsyncAnthropic
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    tree = json.loads(TREE_PATH.read_text(encoding="utf-8"))
    objectives = json.loads(OBJ_PATH.read_text(encoding="utf-8"))
    todo = [st for st in sub_topics(tree, subject) if (not only or st["id"] in only)]
    out_dir = OUT / subject
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [st for st in todo if not (out_dir / f"{st['id']}.json").exists()]
    if limit:
        todo = todo[:limit]
    print(f"{subject}: {len(todo)} sub-topics to rebuild with {model}")
    ag = AgStandards() if subject == "AGR" else None
    client = AsyncAnthropic(max_retries=4)
    gate = asyncio.Semaphore(concurrency)
    spent = 0.0

    async def one(st):
        nonlocal spent
        async with gate:
            try:
                rec = await rebuild_one(client, subject, st, objectives.get(st["id"], []), ag, model)
            except Exception as e:  # noqa: BLE001
                print(f"  FAILED {st['id']}: {type(e).__name__}: {e}")
                return
            (out_dir / f"{st['id']}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            spent += cost(model, rec["usage"])
            flag = f"  PROBLEMS {len(rec['problems'])}" if rec["problems"] else ""
            print(f"  {st['id']} {st['name'][:50]}: {rec['old_count']} -> {len(rec['objectives'])}"
                  f"  ${cost(model, rec['usage']):.3f}{flag}")

    await asyncio.gather(*(one(st) for st in todo))
    done = list(out_dir.glob("*.json"))
    total = sum(cost(json.loads(p.read_text(encoding="utf-8"))["model"], json.loads(p.read_text(encoding="utf-8"))["usage"]) for p in done)
    print(f"spent ${spent:.2f} this run; {len(done)} sub-topics done in all, ${total:.2f} in all")


# -------------------------------------------------------------------------------------------- merge
def complexity(i: int, n: int) -> int:
    """The spine's complexity field orders a sub-topic's objectives from 3 to 26."""
    return 15 if n == 1 else round(3 + 23 * i / (n - 1))


def recheck(subject: str) -> None:
    """Run the checks again over saved results, with no model call (after a check is corrected)."""
    tree = json.loads(TREE_PATH.read_text(encoding="utf-8"))
    sts = {st["id"]: st for st in sub_topics(tree, subject)}
    for p in sorted((OUT / subject).glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        st = dict(sts[r["sub_topic"]], grades=r["grades"])   # the span the result was written for
        r["problems"] = check(subject, st, r["objectives"], set(r.get("candidates") or []))
        p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        if r["problems"]:
            print(f"  {r['sub_topic']}: {r['problems'][:3]}")


def merge(subject: str) -> None:
    tree = json.loads(TREE_PATH.read_text(encoding="utf-8"))
    objectives = json.loads(OBJ_PATH.read_text(encoding="utf-8"))
    results = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (OUT / subject).glob("*.json")}
    unsound = [k for k, r in results.items() if r["problems"]]
    if unsound:
        raise SystemExit(f"{len(unsound)} sub-topics still have problems, fix or rerun them first: {unsound[:10]}")
    backup = OUT / f"{subject}-objectives-before.json"
    backup.write_text(json.dumps({k: v for k, v in objectives.items() if k.startswith(subject + ".")},
                                 ensure_ascii=False), encoding="utf-8")
    described = {}
    if subject == "AGR":   # an AFNR anchor carries its wording, as the other subjects' anchors do
        described = {r["code"]: f"AFNR {r['code']}: {' '.join(r['statement'].split()).rstrip('.')} ({r['set']})"
                     for r in json.loads(INDEX.read_text(encoding="utf-8")).get("AGR", [])}
    for stid, r in results.items():
        objs = sorted(r["objectives"], key=lambda o: (o["grade"], o["bloom"]))
        for o in objs:
            o["standards"] = [described.get(c, c) for c in o["standards"]]
        new = []
        for i, o in enumerate(objs):
            anchor = {k: o[k] for k in ("scripture", "confessions", "standards") if o[k]}
            rec = {"id": f"{stid}.{i + 1}", "t": o["text"].strip(), "g": o["grade"],
                   "c": complexity(i, len(objs)), "u": str(uuid.uuid4())}
            if anchor:
                rec["a"] = anchor
            new.append(rec)
        objectives[stid] = new
    for s in tree["subjects"]:
        for ss in s["sub_subjects"]:
            for tp in ss["topics"]:
                for st in tp.get("sub_topics", []):
                    if st["id"] in results:
                        st["objective_count"] = len(objectives[st["id"]])
                        st["grades"] = sorted({o["g"] for o in objectives[st["id"]]})
    OBJ_PATH.write_text(json.dumps(objectives, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    TREE_PATH.write_text(json.dumps(tree, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = sum(len(objectives[k]) for k in results)
    print(f"merged {len(results)} {subject} sub-topics, {n} objectives; the old set is in {backup.resolve()}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("subject", choices=["BIB", "AGR"])
    ap.add_argument("--only", nargs="*", default=[], help="sub-topic ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--merge", action="store_true", help="write finished results into the spine")
    ap.add_argument("--recheck", action="store_true", help="rerun the checks over saved results, no model call")
    args = ap.parse_args()
    if args.recheck:
        recheck(args.subject)
    elif args.merge:
        merge(args.subject)
    else:
        asyncio.run(run(args.subject, args.only, args.limit, args.model, args.concurrency))


if __name__ == "__main__":
    main()
