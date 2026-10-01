#!/usr/bin/env python3
"""
Build a Google Forms quiz from a chapter-quiz Markdown file (docs/john-quizzes/).

Run-on-demand, like push_to_classroom.py. It reads the quiz Markdown (the single
source of truth Adam reviews), creates a Forms quiz in your Drive with points,
an answer key, per-question feedback, shuffled options, and verified school
emails, then publishes it. You attach the Form to a Classroom assignment
yourself: the Classroom API can't create Forms attachments, and attaching it
in Classroom is what turns on grade importing.

What it reads from the Markdown:
  - "# Title"                        -> the form title
  - "## Instructions ..." paragraph  -> the form description
  - "## Part ..." headings           -> section header items
  - "**N. question**" + "- A. option" lines, the correct one ending in " ✓"
                                     -> auto-graded multiple choice (2 points)
  - "**N. question**" with no options -> paragraph answer graded by hand (4 points)
  - "*Feedback: ...*" under a question -> the feedback students see after release
Rubrics, model answers, and everything under "## Teacher notes" stay off the form.

Auth: its own token (.secrets/forms-token.json, Forms scope only), so the
Classroom push token is never touched. Same OAuth client as push_to_classroom
(GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET, or .secrets/client_secret.json).
The Forms API must be enabled in that Cloud project. First run opens a browser
for consent.

Idempotent: the form id is remembered in .secrets/forms-state.json, keyed by
quiz file. A second run refuses to duplicate; pass --rebuild to replace the
questions of the existing form in place (do that before anyone responds).

Run:
    python scripts/build_forms_quiz.py docs/john-quizzes/ch01-quiz.md --dry-run
    python scripts/build_forms_quiz.py docs/john-quizzes/ch01-quiz.md
    python scripts/build_forms_quiz.py docs/john-quizzes/ch01-quiz.md --rebuild
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env")
except Exception:
    pass
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

SECRETS_DIR = ROOT / ".secrets"
CLIENT_SECRET = SECRETS_DIR / "client_secret.json"
TOKEN = SECRETS_DIR / "forms-token.json"
STATE = SECRETS_DIR / "forms-state.json"
SCOPES = ["https://www.googleapis.com/auth/forms.body"]

MC_POINTS = 2
WRITTEN_POINTS = 4


# ------------------------------------------------------------------ parse
def _plain(s: str) -> str:
    """Strip Markdown emphasis; Forms titles and options are plain text."""
    return re.sub(r"\*\*|\*", "", s).strip()


def parse_quiz(path: Path) -> dict:
    """Quiz Markdown -> {title, description, items[], total}. Each item is
    {kind: header|mc|written, title, options?, correct?, feedback?}."""
    lines = path.read_text(encoding="utf-8").split("\n")
    title, description, items = "", "", []
    section = None            # which ## section we're in
    cur = None                # the question being built

    def flush():
        nonlocal cur
        if cur:
            cur["kind"] = "mc" if cur["options"] else "written"
            items.append(cur)
            cur = None

    for raw in lines:
        s = raw.strip()
        if s.startswith("# ") and not title:
            title = s[2:].strip()
            continue
        if s.startswith("## "):
            flush()
            head = s[3:].strip()
            if head.lower().startswith("teacher notes"):
                break                                   # nothing below this goes on the form
            section = head
            if head.lower().startswith("part "):
                items.append({"kind": "header", "title": head})
            continue
        if section and section.lower().startswith("instructions"):
            if s:
                description = (description + " " + s).strip()
            continue
        if not (section and section.lower().startswith("part ")):
            continue
        m = re.match(r"^\*\*(\d+)\.\s+(.*)\*\*$", s)
        if m:
            flush()
            cur = {"num": int(m.group(1)), "title": f"{m.group(1)}. {_plain(m.group(2))}",
                   "options": [], "correct": None, "feedback": "", "notes": []}
            continue
        if cur is None:
            continue
        m = re.match(r"^-\s+[A-D]\.\s+(.*)$", s)
        if m:
            opt = m.group(1).strip()
            if opt.endswith("✓"):
                opt = opt[:-1].strip()
                cur["correct"] = _plain(opt)
            cur["options"].append(_plain(opt))
            continue
        m = re.match(r"^\*Feedback:\s*(.*)\*$", s)
        if m:
            cur["feedback"] = m.group(1).strip()
            continue
        if s:                       # rubric / model answers: teacher key only, never the form
            cur["notes"].append(s)
    flush()

    total = sum(MC_POINTS if it["kind"] == "mc" else WRITTEN_POINTS
                for it in items if it["kind"] != "header")
    return {"title": title, "description": description, "items": items, "total": total}


def validate(q: dict) -> list[str]:
    problems = []
    if not q["title"]:
        problems.append("no '# Title' line")
    if not q["description"]:
        problems.append("no instructions paragraph")
    nums = [it["num"] for it in q["items"] if it["kind"] != "header"]
    if nums != list(range(1, len(nums) + 1)):
        problems.append(f"question numbers aren't 1..n in order: {nums}")
    for it in q["items"]:
        if it["kind"] == "mc":
            if len(it["options"]) < 2:
                problems.append(f"Q{it['num']}: fewer than 2 options")
            if not it["correct"]:
                problems.append(f"Q{it['num']}: no option marked ✓")
            if len(set(it["options"])) != len(it["options"]):
                problems.append(f"Q{it['num']}: duplicate option text")
        if it["kind"] in ("mc", "written") and not it["feedback"]:
            problems.append(f"Q{it['num']}: no *Feedback:* line")
    return problems


# ------------------------------------------------------------------ build
def form_requests(q: dict) -> list[dict]:
    """batchUpdate requests: description, quiz + verified-email settings, items."""
    reqs = [
        {"updateFormInfo": {"info": {"description": q["description"]},
                            "updateMask": "description"}},
        {"updateSettings": {"settings": {"quizSettings": {"isQuiz": True},
                                         "emailCollectionType": "VERIFIED"},
                            "updateMask": "quizSettings.isQuiz,emailCollectionType"}},
    ]
    for i, it in enumerate(q["items"]):
        if it["kind"] == "header":
            item = {"title": it["title"], "textItem": {}}
        elif it["kind"] == "mc":
            fb = {"text": it["feedback"]}
            item = {"title": it["title"], "questionItem": {"question": {
                "required": True,
                "grading": {"pointValue": MC_POINTS,
                            "correctAnswers": {"answers": [{"value": it["correct"]}]},
                            "whenRight": fb, "whenWrong": fb},
                "choiceQuestion": {"type": "RADIO", "shuffle": True,
                                   "options": [{"value": o} for o in it["options"]]},
            }}}
        else:
            item = {"title": it["title"], "questionItem": {"question": {
                "required": True,
                "grading": {"pointValue": WRITTEN_POINTS,
                            "generalFeedback": {"text": it["feedback"]}},
                "textQuestion": {"paragraph": True},
            }}}
        reqs.append({"createItem": {"item": item, "location": {"index": i}}})
    return reqs


def _env_client_config() -> dict | None:
    cid = os.environ.get("GOOGLE_CLIENT_ID")
    secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not (cid and secret):
        return None
    return {"installed": {
        "client_id": cid, "client_secret": secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }}


def get_forms():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit("Google client libraries are not installed. Run:\n"
                         "  .venv/Scripts/python.exe -m pip install -e '.[classroom]'")
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cfg = _env_client_config()
            if cfg:
                flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
            elif CLIENT_SECRET.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            else:
                raise SystemExit("No OAuth credentials found. Set GOOGLE_CLIENT_ID and "
                                 "GOOGLE_CLIENT_SECRET, or save the client JSON at "
                                 f"{CLIENT_SECRET}. See docs/John_Google_Classroom.md.")
            print("Opening a browser for Google consent (Forms access)...", flush=True)
            creds = flow.run_local_server(port=0)
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("forms", "v1", credentials=creds, cache_discovery=False)


def _load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def _save_state(state: dict) -> None:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def build_form(q: dict, key: str, rebuild: bool, accepting: bool) -> None:
    forms = get_forms()
    state = _load_state()
    form_id = state.get(key)

    if form_id and not rebuild:
        raise SystemExit(f"Already built: https://docs.google.com/forms/d/{form_id}/edit\n"
                         "Pass --rebuild to replace its questions in place "
                         "(only before anyone has responded).")
    if form_id:
        existing = forms.forms().get(formId=form_id).execute()
        n = len(existing.get("items", []))
        if n:   # delete from the end so indices stay valid
            forms.forms().batchUpdate(formId=form_id, body={"requests": [
                {"deleteItem": {"location": {"index": i}}} for i in range(n - 1, -1, -1)
            ]}).execute()
        forms.forms().batchUpdate(formId=form_id, body={"requests": [
            {"updateFormInfo": {"info": {"title": q["title"]}, "updateMask": "title"}}
        ]}).execute()
        print(f"Rebuilding form {form_id} ({n} old items removed)")
    else:
        created = forms.forms().create(
            body={"info": {"title": q["title"], "documentTitle": q["title"]}}).execute()
        form_id = created["formId"]
        state[key] = form_id
        _save_state(state)          # remember it before anything else can fail
        print(f"Created form {form_id}")

    forms.forms().batchUpdate(formId=form_id,
                              body={"requests": form_requests(q)}).execute()

    # Forms created through the API start unpublished; publish so students can open it.
    forms.forms().setPublishSettings(formId=form_id, body={
        "publishSettings": {"publishState": {"isPublished": True,
                                             "isAcceptingResponses": accepting}},
        "updateMask": "publishState",
    }).execute()

    f = forms.forms().get(formId=form_id).execute()
    qs = [i for i in f.get("items", []) if "questionItem" in i]
    pts = sum(i["questionItem"]["question"].get("grading", {}).get("pointValue", 0) for i in qs)
    print(f"\nDone: {len(qs)} questions, {pts} points, quiz mode on, verified emails, "
          f"published ({'accepting responses' if accepting else 'NOT accepting responses yet'}).")
    print(f"Edit:     https://docs.google.com/forms/d/{form_id}/edit")
    print(f"Students: {f.get('responderUri')}")


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description="Build a Google Forms quiz from a quiz Markdown file.")
    ap.add_argument("quiz", help="path to the quiz Markdown, e.g. docs/john-quizzes/ch01-quiz.md")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and validate only; contact no service")
    ap.add_argument("--rebuild", action="store_true",
                    help="replace the questions of the already-built form in place")
    ap.add_argument("--closed", action="store_true",
                    help="publish but don't accept responses yet (open it in Forms on quiz day)")
    args = ap.parse_args()

    path = Path(args.quiz)
    if not path.is_absolute():
        path = ROOT / path
    q = parse_quiz(path)
    problems = validate(q)

    mc = sum(1 for it in q["items"] if it["kind"] == "mc")
    wr = sum(1 for it in q["items"] if it["kind"] == "written")
    hd = sum(1 for it in q["items"] if it["kind"] == "header")
    print(f"{q['title']}\n  {mc} multiple choice x {MC_POINTS} + {wr} written x {WRITTEN_POINTS}"
          f" = {q['total']} points, {hd} section headers")
    if problems:
        print("Problems:\n  - " + "\n  - ".join(problems))
        raise SystemExit(1)
    if args.dry_run:
        for it in q["items"]:
            if it["kind"] == "header":
                print(f"\n  [{it['title']}]")
            else:
                tag = f"MC ({len(it['options'])} options)" if it["kind"] == "mc" else "written"
                print(f"    {it['title'][:70]:70}  {tag}")
        print("\nValid. Re-run without --dry-run to build the form.")
        return
    build_form(q, path.relative_to(ROOT).as_posix(), args.rebuild, not args.closed)


if __name__ == "__main__":
    main()
