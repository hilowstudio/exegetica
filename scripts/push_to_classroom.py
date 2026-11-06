#!/usr/bin/env python3
"""
Push the finished, student-facing Gospel of John course into Google Classroom.

This is a standalone, run-on-demand tool (like course_pdf.py and
build_course_calendar.py), NOT part of the webapp. It authenticates as you with a
local token file, uploads the student PDFs to a Drive folder, and creates Topics,
Materials, and graded Coursework (with due dates from the course calendar) in a
class you already teach. Then it exits. Nothing about it lives in the app, and it
stores no one else's data.

What it pushes: student-facing docs only. Teacher lesson guides and answer keys
are never uploaded (the two TEACHER final copies are hard-excluded by name, since
the manifest mislabels their audience).

Safety: everything is created as DRAFT by default, so nothing reaches students
until you review it in Classroom and publish. Pass --publish to create live.
Re-running is idempotent: a local state file remembers what was created and
updates it in place instead of making duplicates.

One-time setup (Google Cloud project, OAuth client, school-admin caveat) is in
docs/john/John_Google_Classroom.md. Read that first.

Run:
    # 1. find the class to push into
    python scripts/push_to_classroom.py --list-courses
    # 2. see exactly what would happen, no writes
    python scripts/push_to_classroom.py --course-id 123456789 --dry-run
    # 3. push as drafts
    python scripts/push_to_classroom.py --course-id 123456789
    # 4. push one unit / one doc while iterating
    python scripts/push_to_classroom.py --course-id 123456789 --only U5
    python scripts/push_to_classroom.py --course-id 123456789 --only syllabus
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# Best-effort: load a local .env so GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET etc.
# set there are available, matching how the webapp loads config. No-op if absent.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env")
except Exception:
    pass

from webapp import course  # noqa: E402
import course_pdf  # noqa: E402  (reuse the exact PDF-naming logic)

# ------------------------------------------------------------------ paths / config
PDF_DIR = ROOT / "docs" / "john" / "john-pdf" / "student"
SECRETS_DIR = ROOT / ".secrets"
CLIENT_SECRET = SECRETS_DIR / "client_secret.json"   # optional: the downloaded OAuth JSON
TOKEN = SECRETS_DIR / "classroom-token.json"          # created on first auth
STATE = SECRETS_DIR / "classroom-push-state.json"     # idempotency map, per course

# Redirect URI used when the OAuth client comes from env vars rather than a JSON file.
_OAUTH_REDIRECT = "http://localhost"

DRIVE_FOLDER_NAME = "Gospel of John — course materials"

# The scopes we ask for. Teacher-side coursework + materials + topics, course
# listing, and per-file Drive upload (drive.file only sees files this tool makes).
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.topics",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials",
    "https://www.googleapis.com/auth/drive.file",
]

# Never upload these, whatever the manifest says (the manifest tags the TEACHER
# answer-key finals as audience=student).
NEVER_UPLOAD = re.compile(r"TEACHER", re.I)

# Topics, in the order we want them created.
T_RESOURCES = "Course resources"
T_PROJECTS = "Projects"
T_EXAMS = "Exams and review"

# Graded coursework due dates, taken from docs/john/john-course-calendar.json
# (project intro/due markers) and its finals-exam events. (year, month, day).
PROJECT_DUE = {
    "GEN_project-1-signs-guide.md": (2026, 11, 5),      # Q1 due (CHK-2)
    "GEN_project-2-character-study-guide.md": None,     # not dated in the calendar
    "GEN_project-3-farewell-teaching-guide.md": (2027, 3, 18),   # Q3 due (CHK-3)
    "GEN_project-4-passion-response-guide.md": (2027, 5, 19),    # Q4 due
}
FINAL_DUE = {
    "GEN_final-1-book-of-signs-STUDENT.md": (2027, 1, 11),  # Sem 1 exam window opens
    "GEN_final-2-book-of-glory-STUDENT.md": (2027, 5, 25),  # Sem 2 exam window opens
}

T_JOURNALS = "Journals"
T_CHECKPOINTS = "Checkpoints"

# Fill-in items delivered as native Google Docs, not PDFs, so students type into
# them inside Classroom. Each: (source .md, topic_key, delivery).
#   doc_copy  -> an (ungraded) assignment with a per-student editable copy
#               (shareMode STUDENT_COPY); the teacher sees each student's copy.
#   doc_view  -> a view-only material; students make their OWN copy into their own
#               Drive, so it stays private and uncollected.
MD_DIR = ROOT / "docs" / "john" / "john-materials"


def _daily_page_fillins() -> list[tuple[str, str, str]]:
    """Every per-lesson daily page on disk, each a per-student Doc copy. Unit pages
    (GEN_U<n>-L<m>_daily-page.md) go under their unit's topic; the four checkpoint
    pages (GEN_CHK-<n>-L<m>_daily-page.md) go under a shared "Checkpoints" topic.
    Discovered by glob so new pages are picked up without editing this file."""
    units = []
    for p in MD_DIR.glob("GEN_U*-L*_daily-page.md"):
        m = re.match(r"GEN_U(\d+)-L(\d+)_daily-page\.md$", p.name)
        if m:
            units.append((int(m.group(1)), int(m.group(2)), p.name))
    units.sort()
    out = [(name, f"Unit {u}", "doc_copy") for u, _l, name in units]

    chks = []
    for p in MD_DIR.glob("GEN_CHK-*-L*_daily-page.md"):
        m = re.match(r"GEN_CHK-(\d+)-L(\d+)_daily-page\.md$", p.name)
        if m:
            chks.append((int(m.group(1)), int(m.group(2)), p.name))
    chks.sort()
    out += [(name, T_CHECKPOINTS, "doc_copy") for _c, _l, name in chks]
    return out


# Fill-in items delivered as native Google Docs, not PDFs, so students type into
# them inside Classroom. Each: (source .md, topic_key, delivery).
#   doc_copy  -> an (ungraded) assignment with a per-student editable copy
#               (shareMode STUDENT_COPY); the teacher sees each student's copy.
#   doc_view  -> a view-only material; students make their OWN copy into their own
#               Drive, so it stays private and uncollected.
FILLIN = _daily_page_fillins() + [
    ("GEN_reading-journal.md", T_JOURNALS, "doc_copy"),
    ("GEN_quiet-time-journal.md", T_JOURNALS, "doc_view"),
]
# Files handled as Docs above must NOT also be pushed as PDFs from the manifest.
DOC_FILES = {f for f, _, _ in FILLIN}


# ------------------------------------------------------------------ unit dates
CALENDAR = ROOT / "docs" / "john" / "john-course-calendar.json"


def _unit_num(fname: str) -> int | None:
    m = re.match(r"GEN_U(\d+)[_-]", fname)
    return int(m.group(1)) if m else None


def _fmt_range(d1: str, d2: str) -> str:
    """'2026-09-28','2026-10-01' -> 'Sep 28–Oct 1'; same month -> 'Sep 10–15';
    one day -> 'Sep 8'. En dash to match the syllabus's date style."""
    from datetime import date
    a, b = date.fromisoformat(d1), date.fromisoformat(d2)
    mon = a.strftime("%b")
    if a == b:
        return f"{mon} {a.day}"
    if a.month == b.month:
        return f"{mon} {a.day}–{b.day}"
    return f"{mon} {a.day}–{b.strftime('%b')} {b.day}"


def unit_ranges() -> dict[int, str]:
    """{unit number: 'Sep 10–15'} from the finished-course calendar (each unit's
    first to last teaching day)."""
    import json
    cal = json.loads(CALENDAR.read_text(encoding="utf-8"))
    dates: dict[int, list[str]] = {}
    for l in cal["lessons"]:
        m = re.search(r"U(\d+)[-_]", l["file"])
        if m:
            dates.setdefault(int(m.group(1)), []).append(l["date"])
    out = {}
    for n, ds in dates.items():
        ds.sort()
        out[n] = _fmt_range(ds[0], ds[-1])
    return out


def topic_display(topic_key: str, ranges: dict[int, str]) -> str:
    """The name shown in Classroom. Unit topics get their date range appended;
    the fixed topics keep their plain names."""
    if topic_key.startswith("Unit "):
        n = int(topic_key.split()[1])
        rng = ranges.get(n)
        return f"{topic_key} · {rng}" if rng else topic_key
    return topic_key


# ------------------------------------------------------------------ classification
def classify(art: dict) -> dict | None:
    """Return {topic_key, kind: 'material'|'coursework', due} for a student
    artifact, or None to skip it. topic_key is the STABLE identity ('Unit 5',
    'Projects'); the displayed name (with dates) is derived later so the date
    range can change without orphaning the Classroom topic."""
    f = art["file"]
    if NEVER_UPLOAD.search(f) or NEVER_UPLOAD.search(art.get("title", "")):
        return None

    if f in PROJECT_DUE:
        return {"topic_key": T_PROJECTS, "kind": "coursework", "due": PROJECT_DUE[f]}
    if f in FINAL_DUE:
        return {"topic_key": T_EXAMS, "kind": "coursework", "due": FINAL_DUE[f]}
    if re.match(r"GEN_review-\d", f):
        return {"topic_key": T_EXAMS, "kind": "material", "due": None}

    n = _unit_num(f)
    if n is not None:
        return {"topic_key": f"Unit {n}", "kind": "material", "due": None}

    # syllabus, how-to-read, journals, memory cards/master — general resources
    return {"topic_key": T_RESOURCES, "kind": "material", "due": None}


def pdf_path(art: dict) -> Path:
    return PDF_DIR / course_pdf._pdf_name(art)


def _fillin_items(ranges: dict[int, str]) -> list[dict]:
    """The native-Doc, fill-in items (daily pages + journals)."""
    out = []
    for f, topic_key, delivery in FILLIN:
        src = MD_DIR / f
        title = course._h1(src) or src.stem
        out.append({
            "file": f, "title": title,
            "topic_key": topic_key, "topic": topic_display(topic_key, ranges),
            # doc_copy is an (ungraded) assignment with a per-student copy;
            # doc_view is a view-only material students copy on their own.
            "kind": "coursework" if delivery == "doc_copy" else "material",
            "delivery": delivery,
            "share": "STUDENT_COPY" if delivery == "doc_copy" else "VIEW",
            "points": None, "due": None,
            "pdf": None, "src": src,
        })
    return out


def plan() -> list[dict]:
    """Build the ordered push plan. Units first (1..28), then resources, journals,
    projects, exams. PDFs come from the manifest; the fill-in daily pages and
    journals are native Google Docs. Each item carries a stable topic_key, a dated
    display name in 'topic', and a 'delivery' of pdf | doc_copy | doc_view."""
    m = course.build_manifest()
    ranges = unit_ranges()
    items = []
    for a in m["artifacts"]:
        if a.get("audience") != "student":
            continue
        if a["file"] in DOC_FILES:      # delivered as a Doc below, not a PDF
            continue
        c = classify(a)
        if not c:
            continue
        items.append({
            "file": a["file"], "title": a["title"],
            "topic_key": c["topic_key"], "topic": topic_display(c["topic_key"], ranges),
            "kind": c["kind"], "delivery": "pdf", "share": "VIEW",
            "points": 100 if c["kind"] == "coursework" else None,
            "due": c["due"], "pdf": pdf_path(a), "src": None,
        })
    items += _fillin_items(ranges)

    order = {T_CHECKPOINTS: 1, T_RESOURCES: 2, T_JOURNALS: 3, T_PROJECTS: 4, T_EXAMS: 5}

    def sort_key(it):
        t = it["topic_key"]
        if t.startswith("Unit "):
            return (0, int(t.split()[1]), it["file"])
        return (order.get(t, 9), 0, it["file"])

    items.sort(key=sort_key)
    return items


def filter_plan(items: list[dict], only: str | None) -> list[dict]:
    if not only:
        return items
    key = only.lower()
    out = []
    for it in items:
        f = it["file"].lower()
        title = it["title"].lower()
        topic = it["topic"].lower()
        # "U5" matches Unit 5's topic exactly; otherwise substring on file/title/topic
        if re.fullmatch(r"u\d+", key):
            if it["topic_key"].lower() == f"unit {key[1:]}":
                out.append(it)
        elif key in f or key in title or key in topic:
            out.append(it)
    return out


# ------------------------------------------------------------------ dry run
def _source(it: dict) -> Path:
    return it["pdf"] if it["delivery"] == "pdf" else it["src"]


_DELIVERY_TAG = {
    "pdf": "PDF view   ",
    "doc_copy": "DOC copy   ",   # per-student editable copy (assignment)
    "doc_view": "DOC private",   # view-only; student copies to own Drive
}


def do_dry_run(items: list[dict]) -> int:
    missing = [it for it in items if not _source(it).exists()]
    print(f"Plan: {len(items)} student item(s) would be pushed as DRAFT "
          f"(course not contacted).\n")
    cur = None
    for it in items:
        if it["topic"] != cur:
            cur = it["topic"]
            print(f"\n# Topic: {cur}")
        due = it["due"]
        due_s = f"  due {due[0]}-{due[1]:02d}-{due[2]:02d}" if due else ""
        src = _source(it)
        ok = "" if src.exists() else "  [!! SOURCE MISSING]"
        print(f"  {_DELIVERY_TAG[it['delivery']]}  {it['title']}{due_s}{ok}")
        print(f"                 <- {src.name}")
    if missing:
        print(f"\n{len(missing)} source file(s) missing. Render PDFs first "
              f"(python scripts/course_pdf.py --all); Doc sources live in docs/john/john-materials/:")
        for it in missing:
            print(f"  - {_source(it).name}  (for {it['file']})")
        return 1
    print("\nAll source files exist. Re-run without --dry-run to push.")
    return 0


# ------------------------------------------------------------------ google plumbing
def _load_json(p: Path):
    import json
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_json(p: Path, data):
    import json
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _import_google():
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
    except ImportError:
        raise SystemExit(
            "Google client libraries are not installed. Run:\n"
            "  .venv/Scripts/python.exe -m pip install -e '.[classroom]'\n"
            "(or: pip install google-api-python-client google-auth-oauthlib "
            "google-auth-httplib2)")


def _env_client_config() -> dict | None:
    """Build an installed-app OAuth client config from GOOGLE_CLIENT_ID /
    GOOGLE_CLIENT_SECRET, so no client_secret.json file is needed. Returns None
    if the env vars are absent."""
    cid = os.environ.get("GOOGLE_CLIENT_ID")
    secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not (cid and secret):
        return None
    return {
        "installed": {
            "client_id": cid,
            "client_secret": secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_OAUTH_REDIRECT],
        }
    }


def _service_account_creds(sa_path: str, subject: str):
    """Service-account credentials that impersonate a real teacher (subject email).
    Only works if a Workspace admin has granted this service account domain-wide
    delegation for the SCOPES; a bare service account is not a teacher of any course
    and Classroom will reject it."""
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(
        sa_path, scopes=SCOPES)
    return creds.with_subject(subject)


def get_services(sa_path: str | None = None, impersonate: str | None = None):
    """Authenticate and return (classroom, drive) API clients.

    Auth precedence:
      1. Service account + impersonation (--service-account / GOOGLE_SERVICE_ACCOUNT_FILE,
         with --impersonate / CLASSROOM_IMPERSONATE) — headless, needs admin delegation.
      2. OAuth user flow — cached token, else GOOGLE_CLIENT_ID/SECRET env vars, else
         .secrets/client_secret.json. Opens a browser for consent on first run.
    """
    _import_google()
    from googleapiclient.discovery import build

    sa_path = sa_path or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    impersonate = impersonate or os.environ.get("CLASSROOM_IMPERSONATE")

    if sa_path:
        if not impersonate:
            raise SystemExit(
                "A service account needs someone to act as. Pass --impersonate "
                "<teacher-email> (or set CLASSROOM_IMPERSONATE). Note: this only "
                "works if your Workspace admin has granted the service account "
                "domain-wide delegation for the Classroom scopes.")
        if not Path(sa_path).exists():
            raise SystemExit(f"Service-account key not found at {sa_path}.")
        creds = _service_account_creds(sa_path, impersonate)
    else:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

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
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CLIENT_SECRET), SCOPES)
                else:
                    raise SystemExit(
                        "No OAuth credentials found. Set GOOGLE_CLIENT_ID and "
                        "GOOGLE_CLIENT_SECRET (env or .env), or save the OAuth client "
                        f"JSON at {CLIENT_SECRET}. See docs/john/John_Google_Classroom.md.")
                creds = flow.run_local_server(port=0)
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            TOKEN.write_text(creds.to_json(), encoding="utf-8")

    classroom = build("classroom", "v1", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    return classroom, drive


def list_courses(classroom) -> None:
    resp = classroom.courses().list(teacherId="me", pageSize=100).execute()
    courses = resp.get("courses", [])
    if not courses:
        print("No courses found where you are a teacher. Create the class in "
              "Google Classroom first, then re-run.")
        return
    print(f"{'COURSE ID':<14}  {'STATE':<10}  NAME")
    for c in courses:
        print(f"{c['id']:<14}  {c.get('courseState',''):<10}  {c.get('name','')}"
              + (f"  ({c['section']})" if c.get("section") else ""))
    print("\nRe-run with:  --course-id <COURSE ID>")


def ensure_drive_folder(drive, state) -> str:
    fid = state.get("drive_folder_id")
    if fid:
        try:
            drive.files().get(fileId=fid, fields="id").execute()
            return fid
        except Exception:
            pass
    meta = {"name": DRIVE_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = drive.files().create(body=meta, fields="id").execute()
    state["drive_folder_id"] = folder["id"]
    return folder["id"]


def upload_pdf(drive, folder_id, pdf: Path, existing_id: str | None) -> str:
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(pdf), mimetype="application/pdf", resumable=False)
    if existing_id:
        drive.files().update(fileId=existing_id, media_body=media).execute()
        return existing_id
    meta = {"name": pdf.name, "parents": [folder_id]}
    f = drive.files().create(body=meta, media_body=media, fields="id").execute()
    return f["id"]


# -------------------------------------------------------- styled Google-Doc render
# Drive's HTML->Doc importer honors inline color, size, bold/italic, table cell
# background, borders, padding and alignment (confirmed empirically). So the fill-in
# pages are laid out as styled tables: colored section bars, tinted Scripture and
# note callouts, and clean write-in boxes, for a document that looks composed rather
# than dumped. Everything is inline-styled because the importer drops <style>/CSS.
_NAVY = "#12305a"
_GOLD = "#a9812c"
_CREAM = "#f5efe0"
_CREAM_BD = "#d9c68d"
_NOTE_BG = "#eef2f7"
_NOTE_BD = "#c3d1de"
_BOX_BG = "#fcfbf7"
_BOX_BD = "#cfcabb"
_INK = "#2b2b2b"
# NOTE: single font names only. Drive's HTML->Doc importer honors a named font
# (incl. Google fonts like Merriweather) only when it is the sole font-family value;
# a comma fallback stack makes it default to Arial. Both are standard Docs fonts.
_SERIF = "Merriweather"
_SANS = "Arial"


def _inl(text: str) -> str:
    """Inline Markdown (bold/italic/links) to HTML, no surrounding <p>."""
    return course._md.renderInline(text)


def _rule(color: str = _GOLD) -> str:
    return (f'<table style="width:100%;border-collapse:collapse"><tr>'
            f'<td style="background-color:{color};font-size:2pt;line-height:2pt;'
            f'padding:0">&nbsp;</td></tr></table>')


def _spacer(pt: int = 6) -> str:
    return f'<p style="margin:0;font-size:{pt}pt;line-height:{pt}pt">&nbsp;</p>'


def _title(h1: str) -> str:
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", h1)
    main, ref = (m.group(1), m.group(2)) if m else (h1, "")
    out = (f'<p style="margin:0;font-family:{_SERIF};font-size:21pt;font-weight:700;'
           f'color:{_NAVY}">{_inl(main)}</p>')
    if ref:
        out += (f'<p style="margin:0;font-family:{_SANS};font-size:10.5pt;'
                f'letter-spacing:1.5px;color:{_GOLD}">{ref.upper()}</p>')
    return out + _spacer(4) + _rule() + _spacer(8)


def _bar(text: str) -> str:
    return (f'<table style="width:100%;border-collapse:collapse"><tr>'
            f'<td style="background-color:{_NAVY};color:#ffffff;font-family:{_SANS};'
            f'font-size:12pt;font-weight:700;padding:6px 11px">{_inl(text)}</td>'
            f'</tr></table>')


def _callout(inner: str, scripture: bool) -> str:
    if scripture:
        st = (f'background-color:{_CREAM};border:1px solid {_CREAM_BD};'
              f'padding:9px 13px;font-family:{_SERIF};font-style:italic;'
              f'color:#4a4022;font-size:12pt')
    else:
        st = (f'background-color:{_NOTE_BG};border:1px solid {_NOTE_BD};'
              f'padding:8px 12px;font-family:{_SANS};color:#3a4653;font-size:10.5pt')
    return (f'<table style="width:100%;border-collapse:collapse"><tr>'
            f'<td style="{st}">{inner}</td></tr></table>')


def _writebox(n_lines: int) -> str:
    """A tinted, bordered box the student clicks into. Height scales with the number
    of write-on lines the source had."""
    rows = "".join('<p style="margin:0;font-size:12pt;line-height:15pt">&nbsp;</p>'
                   for _ in range(max(n_lines, 1)))
    return (f'<table style="width:100%;border-collapse:collapse"><tr>'
            f'<td style="background-color:{_BOX_BG};border:1px solid {_BOX_BD};'
            f'padding:7px 9px">{rows}</td></tr></table>')


def _para(inner: str) -> str:
    return (f'<p style="font-family:{_SERIF};font-size:11.5pt;color:{_INK};'
            f'line-height:1.35">{inner}</p>')


def _listitem(marker: str, rest: str) -> str:
    mk = "&bull;" if marker in ("-", "*") else marker
    return (f'<p style="font-family:{_SERIF};font-size:11.5pt;color:{_INK};'
            f'margin:2px 0 2px 22px">{mk}&nbsp;&nbsp;{_inl(rest)}</p>')


def _footer(lines: list[str]) -> str:
    inner = "<br>".join(_inl(x) for x in lines)
    st = (f'background-color:{_CREAM};border:1px solid {_CREAM_BD};padding:9px 13px;'
          f'font-family:{_SANS};font-size:10.5pt;color:#4a4022')
    return (f'<table style="width:100%;border-collapse:collapse"><tr>'
            f'<td style="{st}">{inner}</td></tr></table>')


def _is_special(s: str) -> bool:
    return bool(s.startswith("#") or s.startswith(">")
                or re.fullmatch(r"[-*_]{3,}", s)
                or re.match(r"^(\d+\.|[-*])\s+", s)
                or s.startswith("**Memory:**") or s.startswith("**At home:**")
                or s.startswith("**At-home"))


def doc_html(md_path: Path) -> str:
    """Render a fill-in Markdown page to a richly styled HTML document for import as
    a Google Doc: title with passage line, navy section bars, Scripture/note
    callouts, write-in boxes, list items, and a footer strip."""
    lines = md_path.read_text(encoding="utf-8").split("\n")
    blocks: list[str] = []
    footer: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
        elif s.startswith("# "):
            blocks.append(_title(s[2:].strip()))
            i += 1
        elif s.startswith("## "):
            blocks += [_spacer(8), _bar(s[3:].strip()), _spacer(3)]
            i += 1
        elif s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            joined = " ".join(x for x in buf if x)
            blocks += [_callout(_inl(joined), bool(re.search(r"\(John\s", joined))),
                       _spacer(3)]
        elif re.fullmatch(r"_{5,}", s):
            cnt = 0
            while i < n and (re.fullmatch(r"_{5,}", lines[i].strip())
                             or (lines[i].strip() == "" and cnt)):
                if lines[i].strip():
                    cnt += 1
                i += 1
            blocks += [_writebox(cnt), _spacer(4)]
        elif re.fullmatch(r"[-*]{3,}", s):
            blocks += [_spacer(6), _rule("#dcdcdc"), _spacer(4)]
            i += 1
        elif s.startswith("**Memory:**") or s.startswith("**At home:**") \
                or s.startswith("**At-home"):
            footer.append(s)
            i += 1
        elif re.match(r"^(\d+\.|[-*])\s+", s):
            m = re.match(r"^(\d+\.|[-*])\s+(.*)$", s)
            blocks.append(_listitem(m.group(1), m.group(2)))
            i += 1
        else:
            buf = []
            while i < n and lines[i].strip() and not _is_special(lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            blocks.append(_para(_inl(" ".join(buf))))
    if footer:
        blocks += [_spacer(2), _footer(footer)]
    return ("<html><head><meta charset='utf-8'></head><body>"
            + "\n".join(blocks) + "</body></html>")


def upload_doc(drive, folder_id, md_path: Path, name: str, existing_id: str | None) -> str:
    """Create (or replace the content of) a native Google Doc from a fill-in page."""
    from googleapiclient.http import MediaInMemoryUpload
    html = doc_html(md_path).encode("utf-8")
    media = MediaInMemoryUpload(html, mimetype="text/html", resumable=False)
    if existing_id:
        drive.files().update(fileId=existing_id, media_body=media).execute()
        return existing_id
    meta = {"name": name, "parents": [folder_id],
            "mimeType": "application/vnd.google-apps.document"}
    f = drive.files().create(body=meta, media_body=media, fields="id").execute()
    return f["id"]


def ensure_topics(classroom, course_id, wanted, state):
    """Reconcile topics from ordered (key, display) pairs. Returns {key: topicId}.

    The key ('Unit 5', 'Projects') is the stable identity kept in state; the
    display name ('Unit 5 · Oct 5–6') is what shows in Classroom. Existing topics
    are found by state, then by live name, and RENAMED in place when their name
    no longer matches the desired display, so changing a date range never orphans
    or duplicates a topic."""
    topic_ids = dict(state.get("topics", {}))   # key -> id (legacy keys == names)
    name_to_id, id_to_name = {}, {}
    tok = None
    while True:
        r = classroom.courses().topics().list(courseId=course_id, pageSize=100,
                                              pageToken=tok).execute()
        for t in r.get("topic", []):
            name_to_id[t["name"]] = t["topicId"]
            id_to_name[t["topicId"]] = t["name"]
        tok = r.get("nextPageToken")
        if not tok:
            break

    for key, display in wanted:
        tid = topic_ids.get(key) or name_to_id.get(display) or name_to_id.get(key)
        if tid:
            topic_ids[key] = tid
            cur = id_to_name.get(tid)
            if cur is not None and cur != display:
                classroom.courses().topics().patch(
                    courseId=course_id, id=tid, updateMask="name",
                    body={"name": display}).execute()
                print(f"  ~ topic: {cur}  ->  {display}")
        else:
            t = classroom.courses().topics().create(
                courseId=course_id, body={"name": display}).execute()
            topic_ids[key] = t["topicId"]
            print(f"  + topic: {display}")
    state["topics"] = topic_ids
    return topic_ids


def _materials(drive_file_id, share="VIEW"):
    return [{"driveFile": {"driveFile": {"id": drive_file_id}, "shareMode": share}}]


def _delete_item(classroom, course_id, prev):
    """Remove a previously created item (used when its delivery type changes,
    e.g. a daily page moving from a PDF material to a Doc assignment)."""
    try:
        if prev["type"] == "coursework":
            classroom.courses().courseWork().delete(
                courseId=course_id, id=prev["id"]).execute()
        else:
            classroom.courses().courseWorkMaterials().delete(
                courseId=course_id, id=prev["id"]).execute()
    except Exception as e:
        print(f"    (could not delete old {prev['type']}: {e})")


def _desc(it: dict) -> str:
    base = f"{it['title']} — Gospel of John (Sophomore Bible)."
    if it["delivery"] == "doc_copy":
        return base + " You get your own copy to write in."
    if it["delivery"] == "doc_view":
        return (base + " This one is private. Open it, then File > Make a copy to keep "
                "your own in your Drive. It is not turned in and no one grades it.")
    return base


def push_item(classroom, course_id, it, topic_id, drive_file_id, state, publish):
    """Create or update one Classroom Material/Coursework. Idempotent via state;
    if an item's delivery type changed since last run, the stale one is deleted."""
    key = it["file"]
    items = state.setdefault("items", {})
    prev = items.get(key)
    want = "coursework" if it["kind"] == "coursework" else "material"
    if prev and prev.get("type") != want:
        _delete_item(classroom, course_id, prev)
        print(f"  - removed old {prev['type']}: {it['title']}")
        prev = None
        items.pop(key, None)

    body_state = "PUBLISHED" if publish else "DRAFT"
    mats = _materials(drive_file_id, it["share"])

    if want == "coursework":
        body = {
            "title": it["title"], "description": _desc(it),
            "workType": "ASSIGNMENT", "state": body_state,
            "topicId": topic_id, "materials": mats,
        }
        if it.get("points"):
            body["maxPoints"] = it["points"]      # omitted -> ungraded
        if it["due"]:
            y, mo, d = it["due"]
            body["dueDate"] = {"year": y, "month": mo, "day": d}
            body["dueTime"] = {"hours": 23, "minutes": 59}
        if prev:
            mask = "title,description,topicId,state"
            if it["due"]:
                mask += ",dueDate,dueTime"
            classroom.courses().courseWork().patch(
                courseId=course_id, id=prev["id"], updateMask=mask,
                body={k: body[k] for k in mask.split(",")}).execute()
            act = "~ assignment"
        else:
            r = classroom.courses().courseWork().create(
                courseId=course_id, body=body).execute()
            items[key] = {"type": "coursework", "id": r["id"]}
            act = "+ assignment"
    else:
        body = {"title": it["title"], "description": _desc(it),
                "state": body_state, "topicId": topic_id, "materials": mats}
        if prev:
            classroom.courses().courseWorkMaterials().patch(
                courseId=course_id, id=prev["id"],
                updateMask="title,description,topicId,state",
                body={"title": body["title"], "description": body["description"],
                      "topicId": topic_id, "state": body_state}).execute()
            act = "~ material"
        else:
            r = classroom.courses().courseWorkMaterials().create(
                courseId=course_id, body=body).execute()
            items[key] = {"type": "material", "id": r["id"]}
            act = "+ material"
    items[key]["drive"] = drive_file_id
    note = "  [per-student copy]" if it["share"] == "STUDENT_COPY" else (
        "  [private, own-copy]" if it["delivery"] == "doc_view" else "")
    print(f"  {act}: {it['title']}{note}")


def do_push(items, course_id, publish, sa_path=None, impersonate=None) -> int:
    missing = [it for it in items if not _source(it).exists()]
    if missing:
        print("Refusing to push: some source files are missing. Render PDFs first "
              "(python scripts/course_pdf.py --all):")
        for it in missing:
            print(f"  - {_source(it).name}")
        return 1

    classroom, drive = get_services(sa_path, impersonate)
    all_state = _load_json(STATE)
    state = all_state.setdefault(str(course_id), {})

    folder_id = ensure_drive_folder(drive, state)
    print(f"Drive folder: {DRIVE_FOLDER_NAME} ({folder_id})")

    wanted_topics = []   # ordered (key, display) pairs, unique by key
    seen = set()
    for it in items:
        if it["topic_key"] not in seen:
            seen.add(it["topic_key"])
            wanted_topics.append((it["topic_key"], it["topic"]))
    topic_ids = ensure_topics(classroom, course_id, wanted_topics, state)

    pdf_ids = state.setdefault("drive_files", {})   # PDF Drive ids, by file key
    doc_ids = state.setdefault("drive_docs", {})    # Google Doc Drive ids, by file key
    print(f"\nPushing {len(items)} item(s) as {'PUBLISHED' if publish else 'DRAFT'}:")
    cur = None
    for it in items:
        if it["topic"] != cur:
            cur = it["topic"]
            print(f"\n# {cur}")
        key = it["file"]
        if it["delivery"] == "pdf":
            drive_file_id = upload_pdf(drive, folder_id, it["pdf"], pdf_ids.get(key))
            pdf_ids[key] = drive_file_id
        else:
            # migrating from a PDF (daily pages)? drop the orphan PDF Drive file.
            if key in pdf_ids:
                try:
                    drive.files().delete(fileId=pdf_ids[key]).execute()
                except Exception:
                    pass
                pdf_ids.pop(key, None)
            drive_file_id = upload_doc(drive, folder_id, it["src"], it["title"],
                                       doc_ids.get(key))
            doc_ids[key] = drive_file_id
        push_item(classroom, course_id, it, topic_ids[it["topic_key"]],
                  drive_file_id, state, publish)
        _save_json(STATE, all_state)  # save after each, so a crash never re-duplicates

    _save_json(STATE, all_state)
    print(f"\nDone. {len(items)} item(s) in Classroom as "
          f"{'PUBLISHED' if publish else 'DRAFT'}.")
    if not publish:
        print("They are drafts: open Classroom, review, and publish when ready "
              "(or re-run with --publish).")
    return 0


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Push the student-facing Gospel of John course into Google Classroom.")
    ap.add_argument("--list-courses", action="store_true",
                    help="list classes you teach (to find the --course-id) and exit")
    ap.add_argument("--course-id", help="target Classroom course id (see --list-courses)")
    ap.add_argument("--only", help="push a subset: a unit like U5, or a substring "
                    "like 'syllabus' / 'project'")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and check PDFs exist; contact no service")
    ap.add_argument("--publish", action="store_true",
                    help="create items live (default is DRAFT, hidden from students)")
    ap.add_argument("--service-account", metavar="KEY.json",
                    help="use a service-account key instead of the OAuth user flow "
                    "(headless; requires admin domain-wide delegation + --impersonate)")
    ap.add_argument("--impersonate", metavar="EMAIL",
                    help="teacher email the service account acts as")
    args = ap.parse_args()

    items = filter_plan(plan(), args.only)
    if args.only and not items:
        raise SystemExit(f"--only {args.only!r} matched no student documents.")

    if args.list_courses:
        classroom, _ = get_services(args.service_account, args.impersonate)
        list_courses(classroom)
        return
    if args.dry_run:
        raise SystemExit(do_dry_run(items))
    if not args.course_id:
        ap.error("pass --course-id <id> (use --list-courses to find it), or --dry-run")
    raise SystemExit(do_push(items, args.course_id, args.publish,
                             args.service_account, args.impersonate))


if __name__ == "__main__":
    main()
