#!/usr/bin/env python3
"""
The deploy gate (docs/harness-maturity-proposal.md, Layer 5 item 7; docs/decisions/0014-deploy-gate.md).

`fly deploy` ships the working tree, so this refuses unless the tree is clean and every free
check passes, and it deploys only when asked. In order:

  1. the git tree is clean (untracked files count: they would ship too)
  2. pytest
  3. the Bible and History tool checks, and one stdio round trip through the app's own bridge
  4. the voice lint over the pages, and over the assembled student prompts (warnings only: the
     pages hold older copy too)
  5. the student prompt has a recorded probe: the maker probes the bot himself, then records the
     prompt with --record-probe; a changed prompt needs a new record before it ships
  6. with --deploy: `fly deploy`, then the live site is checked: /api/config reports the same tool
     counts as this tree, /api/health answers, and a teacher answer key is refused when signed out

No model is called and nothing is spent. Usage:

    .venv/Scripts/python.exe scripts/predeploy.py                  # every check, no deploy
    .venv/Scripts/python.exe scripts/predeploy.py --deploy         # checks, then deploy and verify
    .venv/Scripts/python.exe scripts/predeploy.py --record-probe "probed greetings, feelings, names"
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
RECORDS = ROOT / "evals" / "probe-records.json"
SITE = os.environ.get("EXEGETICA_URL", "https://exegetica.app")
# A teacher-only file that must never be served to a signed-out visitor.
KEY_PATH = "/course/doc/GEN_final-1-book-of-signs-TEACHER.md"


def say(ok: bool | None, what: str) -> None:
    mark = {True: "PASS", False: "FAIL", None: "WARN"}[ok]
    print(f"[{mark}] {what}", flush=True)


def run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout + p.stderr)


def tail(text: str, n: int = 15) -> str:
    return "\n".join("      " + line for line in text.strip().splitlines()[-n:])


# ---------------------------------------------------------------- the student prompt's identity
def prompt_fingerprint() -> dict:
    """What students are served: both subjects' system prompts and the locked model."""
    sys.path.insert(0, str(ROOT))
    from webapp import app, policy
    parts = {s: app._system_for("professor", s) for s in ("bible", "history")}
    h = hashlib.sha256()
    for s in sorted(parts):
        h.update(parts[s].encode())
    model = policy.STUDENT_MODEL + (f" (fallback {policy.STUDENT_FALLBACK_MODEL})" if policy.STUDENT_FALLBACK_MODEL else "")
    h.update(model.encode())
    return {"prompt_hash": h.hexdigest()[:16], "model": model}


def load_records() -> list[dict]:
    try:
        return json.loads(RECORDS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def record_probe(note: str) -> int:
    fp = prompt_fingerprint()
    records = load_records()
    records.append({**fp, "date": dt.date.today().isoformat(), "note": note})
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    RECORDS.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded a probe of prompt {fp['prompt_hash']} on {fp['model']}. Commit {RECORDS.relative_to(ROOT)}.")
    return 0


# ---------------------------------------------------------------- checks
def stdio_round_trip() -> tuple[bool, str, dict]:
    """Spawn both servers the way the app does, through webapp/bridge.py, and call one tool each."""
    sys.path.insert(0, str(ROOT))
    from webapp.bridge import MCPBridge

    async def one(module: str, with_curriculum: bool, tool: str, args: dict):
        b = MCPBridge(module, with_curriculum=with_curriculum)
        await b.start()
        try:
            text, is_error = await b.call(tool, args)
            return len(b.tools), (not is_error and bool(text.strip()))
        finally:
            await b.stop()

    async def both():
        counts, notes = {}, []
        n, ok = await one("studybible_mcp.server", True, "lookup_verse", {"reference": "John 1:1", "translation": "BSB"})
        counts["bible"] = n
        notes.append(f"Bible: {n} tools, lookup_verse {'answered' if ok else 'FAILED'}")
        good = ok
        if (ROOT / "db" / "social_sciences.db").exists():
            n, ok = await one("socialsci_mcp.server", False, "define_term", {"term": "federalism"})
            counts["history"] = n
            notes.append(f"History: {n} tools, define_term {'answered' if ok else 'FAILED'}")
            good = good and ok
        return good, "; ".join(notes), counts

    try:
        return asyncio.run(asyncio.wait_for(both(), 400))
    except Exception as e:  # noqa: BLE001
        return False, f"stdio round trip failed: {type(e).__name__}: {e}", {}


def history_off() -> bool:
    """fly.toml can withhold History mode (docs/decisions/0023); the live site then lists no History tools."""
    import tomllib
    env = tomllib.loads((ROOT / "fly.toml").read_text(encoding="utf-8")).get("env", {})
    return str(env.get("HISTORY_MODE", "on")).strip().lower() == "off"


def get(url: str, timeout: int = 60) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "exegetica-predeploy"}),
                                    timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def verify_live(counts: dict) -> bool:
    good = True
    status, body = 0, b""
    for _ in range(12):   # a fresh machine may still be fetching its databases
        status, body = get(SITE + "/api/config")
        if status == 200:
            break
        time.sleep(15)
    if status != 200:
        say(False, f"live /api/config answered {status}")
        return False
    cfg = json.loads(body)
    live = {"bible": cfg.get("tools"), "history": len(cfg.get("history_tools") or [])}
    for subject, n in counts.items():
        expect = n
        ok = live.get(subject) == expect
        good &= ok
        say(ok, f"live {subject} tools: {live.get(subject)} (this tree: {expect})")
    status, _ = get(SITE + "/api/health")
    good &= status == 200
    say(status == 200, f"live /api/health answered {status}")
    status, _ = get(SITE + KEY_PATH)
    ok = status in (302, 303, 401, 403, 404)
    good &= ok
    say(ok, f"signed-out request for a teacher answer key answered {status}")
    return good


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deploy", action="store_true", help="deploy with fly after every check passes")
    ap.add_argument("--record-probe", metavar="NOTE", help="record that the current student prompt was probed")
    ap.add_argument("--no-probe-record", action="store_true",
                    help="ship without a probe record for this prompt (printed as a warning)")
    args = ap.parse_args()
    if args.record_probe:
        return record_probe(args.record_probe)

    failed = []

    code, out = run(["git", "status", "--porcelain"])
    clean = code == 0 and not out.strip()
    say(clean, "git tree is clean" if clean else f"git tree has {len(out.strip().splitlines())} changed or untracked paths")
    if not clean:
        failed.append("clean tree")

    code, out = run([PY, "-m", "pytest", "-q", "-p", "no:warnings"])
    say(code == 0, "pytest")
    if code:
        print(tail(out))
        failed.append("pytest")

    for name, script in (("Bible tool check", "scripts/check_bible_tools.py"),
                         ("History tool check", "scripts/socialsci/check_history_tools.py")):
        if not (ROOT / script).exists():
            say(None, f"{name}: {script} not found")
            continue
        code, out = run([PY, script])
        say(code == 0, name)
        if code:
            print(tail(out))
            failed.append(name)

    ok, note, counts = stdio_round_trip()
    say(ok, f"stdio round trip ({note})")
    if not ok:
        failed.append("stdio")
    if history_off():
        counts["history"] = 0
        say(None, "History mode is off in fly.toml; the live site should list no History tools")

    code, out = run([PY, "scripts/lint_voice.py"])
    say(None if code else True, "voice lint" + ("" if code == 0 else " reports tics (not blocking)"))
    code, out = run([PY, "scripts/lint_voice.py", "--prompts"])
    say(None if code else True, "student prompts pass their own voice rules"
        + ("" if code == 0 else ": tics reported (not blocking)"))

    fp = prompt_fingerprint()
    probed = any(r.get("prompt_hash") == fp["prompt_hash"] and r.get("model") == fp["model"] for r in load_records())
    if probed:
        say(True, f"student prompt {fp['prompt_hash']} on {fp['model']} has a probe record")
    elif args.no_probe_record:
        say(None, f"student prompt {fp['prompt_hash']} has NO probe record; shipping anyway (--no-probe-record)")
    else:
        say(False, f"student prompt {fp['prompt_hash']} on {fp['model']} has no probe record. Probe it, then run "
                   "--record-probe \"what you probed\"")
        failed.append("probe record")

    if failed:
        print(f"\nNot deploying. Failed: {', '.join(failed)}.")
        return 1
    if not args.deploy:
        print("\nEvery check passed. Run again with --deploy to ship.")
        return 0

    print("\nDeploying with fly...", flush=True)
    code = subprocess.call(["fly", "deploy"], cwd=ROOT)
    if code:
        say(False, "fly deploy")
        return code
    return 0 if verify_live(counts) else 1


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)   # bridge subprocesses and database threads must not keep this alive
