"""The course page and its routes (decision 0032). For now one course, the maker's Gospel of John, at /john.

Containers are rows of `prep_units` (kind course | unit | lesson), so each keeps the Prep Room's sources,
resources and versions. The placing, pace and source rules are in `courses.py`; this module reads and writes
the rows and answers the page.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date

from starlette.responses import HTMLResponse, JSONResponse

from webapp import auth, courses, db, prep, shell

logger = logging.getLogger(__name__)

COURSE_KEY = "bible-2"
CALENDAR = "yorkville-2026-27"
TITLE = "Gospel of John"
AUTO_DRAFT_MAX = 10           # shelf items a draft takes by passage, narrowest passages first
AUTO_DRAFT_WORDS = 30_000     # and at most this many words of them
_FIELDS = {"title": 200, "passage": 80, "notes": 4000}


def _guard(request):
    """(account id, None) for the maker with the database up, else (None, response). Others get "not found"."""
    user = auth.current_user(request)
    if not auth.is_admin(user):
        return None, JSONResponse({"error": "not found"}, status_code=404)
    if not db.ready():
        return None, JSONResponse({"error": prep.UNAVAILABLE}, status_code=503)
    uid = prep._uuid(user.get("id"))
    if not uid:
        return None, JSONResponse({"error": "Sign in again to save your work."}, status_code=401)
    return uid, None


async def page(request):
    if not auth.is_admin(auth.current_user(request)):
        return HTMLResponse("Not found", status_code=404)
    return shell.page(request, "course.html", title=TITLE)


# ------------------------------------------------------------------ rows
_COLS = ("id, parent_id, kind, title, position, passage, calendar, meetings, day_type, plan, taught_on, hidden, "
         "notes, objectives, course_key, updated_at")


def _row(r) -> dict:
    return prep._plain(r)          # ids as text, dates as ISO days


async def ensure_course(uid: uuid.UUID) -> dict:
    row = await db.fetchrow(f"select {_COLS} from prep_units where user_id = $1 and kind = 'course' and course_key = $2",
                            uid, COURSE_KEY)
    if not row:
        row = await db.fetchrow(
            f"""insert into prep_units (user_id, title, course_key, grade_band, kind, calendar)
                values ($1, $2, $3, 'secondary', 'course', $4) returning {_COLS}""", uid, TITLE, COURSE_KEY, CALENDAR)
    return _row(row)


async def _descendants(uid: uuid.UUID, root: uuid.UUID) -> list[dict]:
    rows = await db.fetch(
        f"""with recursive t as (
                select {_COLS}, 0 as depth from prep_units where id = $1 and user_id = $2
                union all
                select {', '.join('u.' + c.strip() for c in _COLS.split(','))}, t.depth + 1
                  from prep_units u join t on u.parent_id = t.id where u.user_id = $2)
            select * from t order by depth, position, title""", root, uid)
    return [_row(r) for r in rows]


def _nest(rows: list[dict]) -> tuple[dict, list[dict]]:
    """(course, units) with each unit's lessons, in order. Groups are units for now."""
    course = rows[0]
    kids: dict[str, list] = {}
    for r in rows[1:]:
        kids.setdefault(r["parent_id"], []).append(r)
    units = [dict(u, lessons=kids.get(u["id"], [])) for u in kids.get(course["id"], []) if u["kind"] != "lesson"]
    return course, units


async def _chain(uid: uuid.UUID, node_id: uuid.UUID) -> list[dict]:
    """The node and its ancestors, root first."""
    rows = await db.fetch(
        f"""with recursive t as (
                select {_COLS}, 0 as up from prep_units where id = $1 and user_id = $2
                union all
                select {', '.join('u.' + c.strip() for c in _COLS.split(','))}, t.up + 1
                  from prep_units u join t on u.id = t.parent_id where u.user_id = $2)
            select * from t order by up desc""", node_id, uid)
    return [_row(r) for r in rows]


async def _pinned(chain: list[dict]) -> dict:
    ids = [uuid.UUID(n["id"]) for n in chain]
    rows = await db.fetch("""select id, unit_id, kind, ref, label, words from prep_sources
                              where unit_id = any($1::uuid[]) order by position, added_at""", ids)
    out: dict[str, list] = {}
    for r in rows:
        d = prep._plain(r)
        out.setdefault(d["unit_id"], []).append(d)
    return out


async def shelf(course_key: str = COURSE_KEY) -> list[dict]:
    rows = await db.fetch("""select id, kind, ref, label, audience from shelf_items where course_key = $1""", course_key)
    return [prep._plain(r) for r in rows]


# ------------------------------------------------------------------ the page's data
def _lesson_out(ls: dict, meeting, made: list, sermons: dict) -> dict:
    return {"id": ls["id"], "title": ls["title"], "passage": ls.get("passage"), "day_type": ls.get("day_type"),
            "materials": made, "makes": plan_makes(ls.get("plan") or {}, sermons),
            "plan": ls.get("plan") or {}, "taught_on": ls.get("taught_on"), "notes": ls.get("notes") or "",
            "date": meeting.date if meeting else None, "schedule": meeting.schedule if meeting else None,
            "minutes": meeting.minutes if meeting else None,
            "fits": (not meeting or not ls.get("day_type") or ls["day_type"] == meeting.schedule)}


async def _materials(uid: uuid.UUID, ids: list[str]) -> dict:
    """{container id: [{id, title, format, kind}]}: what the Prep Room has made for each container."""
    from webapp import generator
    rows = await db.fetch("""select id, unit_id, format_id, title from prep_resources
                              where user_id = $1 and unit_id = any($2::uuid[]) order by created_at""",
                          uid, [uuid.UUID(i) for i in ids])
    out: dict[str, list] = {}
    for r in rows:
        fmt = generator.FORMATS.get(r["format_id"]) or {}
        out.setdefault(str(r["unit_id"]), []).append(
            {"id": str(r["id"]), "title": r["title"], "format": r["format_id"], "kind": fmt.get("name") or r["format_id"]})
    return out


async def view(uid: uuid.UUID, today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    course = await ensure_course(uid)
    rows = await _descendants(uid, uuid.UUID(course["id"]))
    course, units = _nest(rows)
    meets = courses.meetings(course.get("calendar") or CALENDAR)
    laid = courses.lay(units, meets)
    made = await _materials(uid, [r["id"] for r in rows])
    sermons = _sermon_titles(await shelf())
    out_units = []
    for u in units:
        lu = laid["units"][u["id"]]
        out_units.append({
            "id": u["id"], "title": u["title"], "passage": u.get("passage"), "meetings": u.get("meetings") or 0,
            "notes": u.get("notes") or "", "first": lu["first"], "last": lu["last"],
            "pace": courses.pace(u, lu, today) if lu["meetings"] else None,
            "lessons": [_lesson_out(ls, lu["lessons"].get(ls["id"]), made.get(ls["id"], []), sermons) for ls in u["lessons"]],
            "materials": made.get(u["id"], []),
            "open": [m.date for m in lu["open"]],
        })
    nxt = courses.next_lesson(units)
    # Lessons whose day has passed and that aren't marked taught: how far the class is behind the calendar.
    behind = sum(1 for u in out_units for ls in u["lessons"] if not ls["taught_on"] and ls["date"] and ls["date"] < today)
    term = courses.term(course.get("calendar") or CALENDAR)
    m_today = courses.meeting_on(meets, today)
    return {
        "course": {"id": course["id"], "title": course["title"], "notes": course.get("notes") or "",
                   "calendar": course.get("calendar") or CALENDAR},
        "today": today,
        "meeting_today": m_today and {"date": m_today.date, "schedule": m_today.schedule, "minutes": m_today.minutes},
        "next": nxt and {"unit": nxt[0]["id"], "lesson": nxt[1]["id"]},
        "behind": behind,
        "units": out_units,
        "calendar": {"term": term, "meetings": [{"date": m.date, "schedule": m.schedule, "minutes": m.minutes,
                                                  "tentative": m.tentative} for m in meets],
                     "off": [{"date": d.date, "kind": d.kind, "label": d.label} for d in courses.off_days(CALENDAR)],
                     "unplanned": len(laid["unplanned"]), "short": laid["short"]},
    }


async def sources_view(uid: uuid.UUID, node_id: uuid.UUID) -> dict | None:
    chain = await _chain(uid, node_id)
    if not chain or chain[0]["kind"] != "course":
        return None
    feed = courses.feeding(chain, await _pinned(chain), await shelf())

    def item(s):
        p = courses.item_passage(s) if "audience" in s else None
        return {"id": s["id"], "label": s.get("label"), "kind": s.get("kind"), "via": s.get("via"),
                "passage": str(p) if p else None}
    return {"own": [item(s) for s in feed["own"]], "above": [item(s) for s in feed["above"]],
            "passage": [item(s) for s in feed["passage"]], "hidden": chain[-1].get("hidden") or []}


async def draft_sources(uid: uuid.UUID, node_id: uuid.UUID, labels_only: bool = False) -> list[dict] | None:
    """What a draft for a course container draws on, shaped like prep.sources_for_draft: its own pinned
    sources, its ancestors' pinned sources (nearest first), then shelf items attached by passage (the
    teacher's own sermons, then the narrowest passages; capped). Transcripts are marked teacher_only.
    None when the node isn't in a course, so the Prep Room keeps its own rule for a plain unit.
    `labels_only` skips reading the shelf texts (and so their word cap), for the Prep Room's "Draws on" line."""
    from webapp import shelf_docs
    chain = await _chain(uid, node_id)
    if len(chain) < 1 or chain[0]["kind"] != "course":
        return None
    items = await shelf()
    # A pinned copy of a shelf item names it by the item's origin (or id): the same transcript pinned here
    # is still the teacher's source, and isn't taken a second time by passage.
    by_origin = {str((s.get("ref") or {}).get("origin") or s["id"]): s for s in items}
    by_origin.update({str(s["id"]): s for s in items})
    out, pinned = [], set()
    for n in reversed(chain):                            # own, then above (nearest first): the Prep Room's own decryption
        for src in await prep.own_sources(uid, uuid.UUID(n["id"])):
            item = by_origin.get(str((src.get("ref") or {}).get("shelf") or ""))
            if item:
                pinned.add(str(item["id"]))
                if courses.teacher_source(item):
                    src["teacher_only"] = True
            out.append(src)
    feed = courses.feeding(chain, {}, items)

    def rank(it):
        """The teacher's own sermons first, then the narrowest passages."""
        p = courses.item_passage(it)
        own = 0 if (it.get("ref") or {}).get("sermon") is not None else 1
        return own, (p.end[0] - p.start[0]) * 1000 + (p.end[1] - p.start[1]) if p else 10**6
    words = 0
    for it in sorted((it for it in feed["passage"] if str(it["id"]) not in pinned), key=rank)[:AUTO_DRAFT_MAX]:
        ref = it.get("ref") or {}
        if it["kind"] in ("upload", "link", "resource"):
            text = "" if labels_only else await shelf_docs.text_of(uuid.UUID(it["id"]))
            if not labels_only and (not text or words + len(text.split()) > AUTO_DRAFT_WORDS):
                continue
            words += len(text.split())
            by = ref.get("author") or ("John Piper" if ref.get("dg") else None)   # two talks can share a title
            out.append({"id": it["id"], "kind": "upload", "ref": {"url": ref.get("url")},
                        "label": it["label"] + (f" ({by})" if by and by not in it["label"] else ""), "text": text,
                        **({"teacher_only": True} if courses.teacher_source(it) else {})})
        elif it["kind"] in ("video", "podcast") and ref.get("item_id"):
            ep = ref.get("ep") if isinstance(ref.get("ep"), dict) else None
            out.append({"id": it["id"], "kind": "library", "ref": {"item_id": ref["item_id"]}, "label": it["label"],
                        "shelved": True, **({"episode": {**ep, "title": ep.get("title") or it["label"]}} if ep else {})})
        elif it["kind"] == "book" and ref.get("slug"):
            out.append({"id": it["id"], "kind": "book", "ref": {"slug": ref["slug"]}, "label": it["label"]})
    return out


DRAFT_PLAN_KEYS = ("topic", "aim", "application", "strategy", "assignment")


async def draft_context(uid: uuid.UUID, node_id: uuid.UUID) -> dict | None:
    """What a draft for a course container is told about where it sits (decision 0032: "what the whole course
    rests on, what this unit is for, what this lesson must do"): each container from the course down, with its
    passage and note, and the container's own plan. None when the node isn't in a course."""
    chain = await _chain(uid, node_id)
    if not chain or chain[0]["kind"] != "course":
        return None
    plan = chain[-1].get("plan") or {}
    return {"chain": [{"kind": n["kind"], "title": n["title"], "passage": n.get("passage"), "notes": (n.get("notes") or "").strip()}
                      for n in chain],
            "plan": {k: plan[k] for k in DRAFT_PLAN_KEYS if plan.get(k)}}


def _format_id(name: str | None) -> str | None:
    from webapp import generator
    want = (name or "").casefold()
    return next((k for k, f in generator.FORMATS.items() if f["name"].casefold() == want), None) if want else None


_TO_MAKE = re.compile(r"\s*\((?:(?P<pre>[^()]*?);\s*)?to make(?:, from (?P<src>[^()]*))?\)\s*$")
_SERMON = re.compile(r"your sermon (\d+)")


def _brief(label: str, sermons: dict) -> str:
    """A planned material's line as the Prep Room's instructions: the thing to make, then what to draw on most,
    with "your sermon 05" written as the transcript's own title, the name a draft sees it under."""
    m = _TO_MAKE.search(label)
    if not m:
        return label
    main = label[:m.start()].rstrip(" .")
    src = m.group("src") or re.sub(r"^mine September['’]s daily page(?: and )?", "", m.group("pre") or "")
    src = _SERMON.sub(lambda s: sermons.get(int(s.group(1)), s.group(0)), src).strip()
    return f"{main}." + (f" Draw mainly on {src}." if src else "")


def plan_makes(plan: dict, sermons: dict) -> list[dict]:
    """The materials the lesson's plan says to make, each ready to open in the Prep Room."""
    return [{"label": m["label"], "format": m.get("format"), "format_id": _format_id(m.get("format")),
             "brief": _brief(m["label"], sermons)}
            for m in (plan or {}).get("materials") or [] if m.get("use") == "make" and m.get("label")]


def _sermon_titles(items: list[dict]) -> dict:
    out = {}
    for s in items:
        ref = s.get("ref") or {}
        if isinstance(ref.get("sermon"), int):
            out[ref["sermon"]] = f"the transcript “{ref.get('title') or s['label']}”" + (f" ({ref['passage']})" if ref.get("passage") else "")
    return out


# ------------------------------------------------------------------ writes
def _clean_fields(b: dict) -> dict | str:
    f = {}
    for k, limit in _FIELDS.items():
        if k in b:
            f[k] = prep._clean(b[k], limit)
    if "title" in f and not f["title"]:
        return "A title is needed."
    if f.get("passage") and not courses.parse_passage(f["passage"]):
        return "Write the passage like John 6:25-29."
    if "meetings" in b:
        try:
            n = int(b["meetings"])
        except (TypeError, ValueError):
            return "Meetings is a number of class days."
        if not 0 <= n <= 200:
            return "Meetings is a number of class days."
        f["meetings"] = n
    if "day_type" in b:
        if b["day_type"] not in (None, *courses.MINUTES):
            return "A day type is regular, thursday or half_day."
        f["day_type"] = b["day_type"]
    if "plan" in b:
        if not isinstance(b["plan"], dict):
            return "The plan wasn't readable."
        f["plan"] = _clean_plan(b["plan"])
    return f


def _lines(v, n: int, limit: int) -> list[str]:
    """Up to n non-empty lines from a list of strings (or one string with a line per item)."""
    items = v.splitlines() if isinstance(v, str) else (v if isinstance(v, list) else [])
    return [s for s in (prep._clean(x, limit) for x in items[:n] if isinstance(x, str)) if s]


def _clean_plan(p: dict) -> dict:
    """A lesson's plan, keeping only the keys the request sent, so a save from one part of the page never
    wipes another (node_update merges the result into the stored plan).

    The scope-and-sequence fields (Adam, 2026-11-12): topic, aim ("Students will..." lines), application,
    strategy, materials, assignment and the memory verse. The period's moves and questions sit beside them."""
    out: dict = {}
    if "moves" in p:
        moves = []
        for m in (p.get("moves") or [])[:12]:
            if isinstance(m, dict):
                try:
                    mins = max(0, min(90, int(m.get("minutes") or 0)))
                except (TypeError, ValueError):
                    mins = 0
                moves.append({"minutes": mins, "title": prep._clean(m.get("title"), 120), "text": prep._clean(m.get("text"), 4000)})
        out["moves"] = moves
    if "questions" in p:
        out["questions"] = [{"q": prep._clean(q.get("q"), 600), "listen": prep._clean(q.get("listen"), 1200)}
                            for q in (p.get("questions") or [])[:20] if isinstance(q, dict) and q.get("q")]
    if "objective" in p:
        out["objective"] = prep._clean(p.get("objective"), 600)
    if "topic" in p:
        out["topic"] = prep._clean(p.get("topic"), 200)
    if "strategy" in p:
        out["strategy"] = prep._clean(p.get("strategy"), 2000)
    for key, n, limit in (("aim", 6, 400), ("application", 4, 300), ("assignment", 4, 800)):
        if key in p:
            out[key] = _lines(p.get(key), n, limit)
    if "materials" in p:
        mats = []
        for m in (p.get("materials") or [])[:8]:
            if isinstance(m, str):
                m = {"label": m}
            if not isinstance(m, dict) or not prep._clean(m.get("label"), 300):
                continue
            mat = {"label": prep._clean(m.get("label"), 300), "use": prep._clean(m.get("use"), 40)}   # show | make | read
            if prep._uuid(m.get("shelf_id")):
                mat["shelf_id"] = str(prep._uuid(m["shelf_id"]))
            if prep._uuid(m.get("resource_id")):
                mat["resource_id"] = str(prep._uuid(m["resource_id"]))
            if isinstance(m.get("format"), str):
                mat["format"] = prep._clean(m["format"], 80)
            mats.append(mat)
        out["materials"] = mats
    if "assessments" in p:             # quizzes, recitations, project days on this lesson
        out["assessments"] = [
            {"kind": a.get("kind") if a.get("kind") in ("quiz", "recitation", "project", "makeup") else "quiz",
             "label": prep._clean(a.get("label"), 300), "points": a.get("points") if isinstance(a.get("points"), int) else None}
            for a in (p.get("assessments") or [])[:6] if isinstance(a, dict) and prep._clean(a.get("label"), 300)]
    if "memory" in p:
        mv = p.get("memory") if isinstance(p.get("memory"), dict) else {}
        ref, mode = prep._clean(mv.get("ref"), 80), mv.get("mode")
        out["memory"] = ({"ref": ref, "mode": mode if mode in ("plant", "review", "recite") else "review",
                          "note": prep._clean(mv.get("note"), 300)} if ref else {})
    return out


async def create_node(uid: uuid.UUID, parent: uuid.UUID, kind: str, fields: dict) -> dict | None:
    par = await db.fetchrow("select id, kind from prep_units where id = $1 and user_id = $2", parent, uid)
    if not par or par["kind"] == "lesson" or (kind == "lesson" and par["kind"] == "course"):
        return None
    pos = await db.fetchval("select coalesce(max(position), -1) + 1 from prep_units where parent_id = $1", parent)
    cols = ["user_id", "parent_id", "kind", "position", "course_key", "grade_band", *fields]
    vals = [uid, parent, kind, pos, COURSE_KEY, "secondary", *fields.values()]
    marks = ", ".join(f"${i}" for i in range(1, len(vals) + 1))
    row = await db.fetchrow(f"insert into prep_units ({', '.join(cols)}) values ({marks}) returning {_COLS}", *vals)
    return _row(row)


async def _in_course(uid: uuid.UUID, node: uuid.UUID) -> bool:
    chain = await _chain(uid, node)
    return bool(chain) and chain[0]["kind"] == "course"


async def node_create(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    b = await prep._body(request)
    kind = b.get("kind")
    parent = prep._uuid(b.get("parent_id"))
    if kind not in ("unit", "lesson") or not parent or not await _in_course(uid, parent):
        return JSONResponse({"error": "That can't go there."}, status_code=400)
    f = _clean_fields(b)
    if isinstance(f, str):
        return JSONResponse({"error": f}, status_code=400)
    if not f.get("title"):
        return JSONResponse({"error": "A title is needed."}, status_code=400)
    row = await create_node(uid, parent, kind, f)
    if not row:
        return JSONResponse({"error": "That can't go there."}, status_code=400)
    return JSONResponse({"node": row}, status_code=201)


async def node_update(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    node = prep._uuid(request.path_params["id"])
    if not node or not await _in_course(uid, node):
        return JSONResponse({"error": "That isn't in your course."}, status_code=404)
    f = _clean_fields(await prep._body(request))
    if isinstance(f, str):
        return JSONResponse({"error": f}, status_code=400)
    if "plan" in f:                          # merge, so saving the moves never drops the aim or the materials
        stored = await db.fetchval("select plan from prep_units where id = $1 and user_id = $2", node, uid) or {}
        f["plan"] = {**stored, **f["plan"]}
    ok = await prep.update_unit(uid, node, f)
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


async def node_taught(request):
    """Mark a lesson taught on a day (today when none is given), or clear the mark."""
    uid, denied = _guard(request)
    if denied:
        return denied
    node = prep._uuid(request.path_params["id"])
    b = await prep._body(request)
    on = b.get("on", date.today().isoformat())
    if on is not None:
        try:
            on = date.fromisoformat(str(on))
        except ValueError:
            return JSONResponse({"error": "That isn't a date."}, status_code=400)
    status = await db.execute("""update prep_units set taught_on = $3, updated_at = now()
                                  where id = $1 and user_id = $2 and kind = 'lesson'""", node, uid, on)
    ok = status.endswith(" 1")
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


async def node_move(request):
    """Put a node at `position` among its siblings (and under `parent_id` when given), renumbering the rest."""
    uid, denied = _guard(request)
    if denied:
        return denied
    node = prep._uuid(request.path_params["id"])
    b = await prep._body(request)
    row = await db.fetchrow("select id, parent_id, kind from prep_units where id = $1 and user_id = $2", node, uid)
    if not row or row["kind"] == "course" or not await _in_course(uid, node):
        return JSONResponse({"error": "That isn't in your course."}, status_code=404)
    parent = prep._uuid(b.get("parent_id")) or row["parent_id"]
    if parent != row["parent_id"]:
        par = await db.fetchrow("select kind from prep_units where id = $1 and user_id = $2", parent, uid)
        if not par or (row["kind"] == "lesson") != (par["kind"] == "unit") or not await _in_course(uid, parent):
            return JSONResponse({"error": "That can't go there."}, status_code=400)
    sibs = [r["id"] for r in await db.fetch(
        "select id from prep_units where parent_id = $1 and id <> $2 order by position, title", parent, node)]
    try:
        at = max(0, min(len(sibs), int(b.get("position", len(sibs)))))
    except (TypeError, ValueError):
        at = len(sibs)
    sibs.insert(at, node)
    async with db.pool().acquire() as conn, conn.transaction():
        for i, sid in enumerate(sibs):
            await conn.execute("update prep_units set position = $2, parent_id = $3 where id = $1 and user_id = $4",
                               sid, i, parent, uid)
    return JSONResponse({"ok": True})


async def node_delete(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    node = prep._uuid(request.path_params["id"])
    row = await db.fetchrow("select kind from prep_units where id = $1 and user_id = $2", node, uid)
    if not row or row["kind"] == "course" or not await _in_course(uid, node):
        return JSONResponse({"error": "That isn't in your course."}, status_code=404)
    ok = await prep.delete_unit(uid, node)
    return JSONResponse({"ok": ok})


async def node_hide(request):
    """Remove a shelf item that attached itself here by passage, or bring it back."""
    uid, denied = _guard(request)
    if denied:
        return denied
    node = prep._uuid(request.path_params["id"])
    b = await prep._body(request)
    item = prep._uuid(b.get("item_id"))
    if not node or not item or not await _in_course(uid, node):
        return JSONResponse({"error": "That isn't in your course."}, status_code=404)
    hidden = set(await db.fetchval("select hidden from prep_units where id = $1 and user_id = $2", node, uid) or [])
    (hidden.add if b.get("hidden", True) else hidden.discard)(str(item))
    await prep.update_unit(uid, node, {"hidden": sorted(hidden)})
    return JSONResponse({"ok": True, "hidden": sorted(hidden)})


async def course_get(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    today = request.query_params.get("today")
    return JSONResponse(await view(uid, today if today and len(today) == 10 else None),
                        headers={"Cache-Control": "no-store"})


async def node_sources(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    node = prep._uuid(request.path_params["id"])
    out = await sources_view(uid, node) if node else None
    if out is None:
        return JSONResponse({"error": "That isn't in your course."}, status_code=404)
    return JSONResponse(out, headers={"Cache-Control": "no-store"})
