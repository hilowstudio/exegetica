"""Which Yorkville courses a teacher teaches (decision 0026), so their Living Library opens on the books
for their own classes. Rows are keyed by the account's address. 'school' rows come from the school's book
list (scripts/seed_teacher_courses.py); 'teacher' rows are the teacher's own picks; 'removed' keeps a
school row the teacher took off from coming back. No name is stored."""
from __future__ import annotations

from starlette.responses import JSONResponse

from webapp import auth, db, yorkville


def _teacher(request):
    user = auth.current_user(request)
    return user if auth.is_teacher(user) else None


async def mine(email: str) -> list[str]:
    rows = await db.fetch("select course_key from teacher_courses where email = $1 and source <> 'removed' "
                          "order by course_key", (email or "").lower())
    return [r["course_key"] for r in rows]


async def set_course(email: str, course_key: str, on: bool) -> None:
    email = (email or "").lower()
    if on:
        await db.execute(
            """insert into teacher_courses (email, course_key, source) values ($1, $2, 'teacher')
               on conflict (email, course_key) do update set source = case when teacher_courses.source = 'removed'
                    then 'teacher' else teacher_courses.source end""", email, course_key)
    else:
        await db.execute("delete from teacher_courses where email = $1 and course_key = $2 and source = 'teacher'",
                         email, course_key)
        await db.execute("update teacher_courses set source = 'removed' where email = $1 and course_key = $2",
                         email, course_key)


def _works_out(keys: list[str]) -> list[dict]:
    names = {c["key"]: c["name"] for c in yorkville.courses()}
    out = []
    for w in yorkville.works(keys):
        o = yorkville.outline(w["outline"]) if w["state"] == "outline" else None
        out.append({"key": w["key"], "title": (o or {}).get("title") or w.get("title"),
                    "author": w.get("author") or ", ".join((o or {}).get("authors") or []),
                    "state": w["state"], "slug": w.get("slug"), "outline": w.get("outline") if o else None,
                    "note": w.get("note"), "courses": [k for k in w["courses"] if k in keys],
                    "course_names": [names.get(k, k) for k in w["courses"] if k in keys]})
    return out


async def get(request):
    user = _teacher(request)
    if not user:
        return JSONResponse({"error": "The Living Library is for teachers."}, status_code=403)
    keys = await mine(user.get("email")) if db.ready() else []
    return JSONResponse({"courses": yorkville.courses(), "mine": keys, "works": _works_out(keys),
                         "saving": db.ready()})


async def change(request):
    user = _teacher(request)
    if not user:
        return JSONResponse({"error": "The Living Library is for teachers."}, status_code=403)
    if not db.ready():
        return JSONResponse({"error": "Saving is unavailable right now. Try again in a minute."}, status_code=503)
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        b = {}
    keys = b.get("courses") if isinstance(b, dict) else None
    known = {c["key"] for c in yorkville.courses()}
    if not isinstance(keys, list) or not set(keys) <= known:
        return JSONResponse({"error": "Pick courses from the school's list."}, status_code=400)
    now = set(await mine(user.get("email")))
    for k in set(keys) - now:
        await set_course(user.get("email"), k, True)
    for k in now - set(keys):
        await set_course(user.get("email"), k, False)
    keys = await mine(user.get("email"))
    return JSONResponse({"mine": keys, "works": _works_out(keys)})


async def outline(request):
    if not _teacher(request):
        return JSONResponse({"error": "The Living Library is for teachers."}, status_code=403)
    o = yorkville.outline(request.path_params["key"])
    if not o:
        return JSONResponse({"error": "There's no outline for that book yet."}, status_code=404)
    return JSONResponse({"outline": o})
