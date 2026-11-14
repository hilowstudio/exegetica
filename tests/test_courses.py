"""The course logic of decision 0032 (webapp/courses.py): no database, no network."""
from webapp import courses as c

CAL = "yorkville-2026-27"


def test_calendar_meetings_match_the_school_counts():
    ms = c.meetings(CAL)
    firm = [m for m in ms if not m.tentative]
    assert len(firm) == 152
    assert sum(m.tentative for m in ms) == 1
    by = {k: sum(1 for m in firm if m.schedule == k) for k in c.MINUTES}
    assert by == {"regular": 116, "thursday": 32, "half_day": 4}
    assert ms[0].date == "2026-09-08" and ms[0].minutes == 50
    assert [m.date for m in ms] == sorted(m.date for m in ms)
    assert all(m.minutes == c.MINUTES[m.schedule] for m in ms)


def test_off_days_include_finals_and_holidays():
    kinds = {d.kind for d in c.off_days(CAL)}
    assert kinds == {"no_school", "no_class", "finals"}
    assert sum(1 for d in c.off_days(CAL) if d.kind == "finals") == 8


def _units():
    return [
        {"id": "u1", "meetings": 3, "lessons": [{"id": "a"}, {"id": "b"}]},
        {"id": "u2", "meetings": 2, "lessons": [{"id": "c"}, {"id": "d"}, {"id": "e"}]},
    ]


def test_units_hold_their_meetings_in_order():
    ms = c.meetings(CAL)
    laid = c.lay(_units(), ms)
    u1, u2 = laid["units"]["u1"], laid["units"]["u2"]
    assert [m.date for m in u1["meetings"]] == [m.date for m in ms[:3]]
    assert u1["lessons"]["a"] == ms[0] and u1["lessons"]["b"] == ms[1]
    assert u1["open"] == [ms[2]]                       # a meeting with no lesson yet
    assert u2["first"] == ms[3].date and u2["last"] == ms[4].date
    assert u2["over"] == ["e"]                         # more lessons than the unit's meetings
    assert len(laid["unplanned"]) == len(ms) - 5 and laid["short"] == 0


def test_a_course_longer_than_the_calendar_is_reported_short():
    laid = c.lay([{"id": "u", "meetings": 400, "lessons": []}], c.meetings(CAL))
    assert laid["short"] == 400 - len(c.meetings(CAL))


def test_pace_counts_lessons_left_against_the_units_meetings_left():
    ms = c.meetings(CAL)
    unit = {"id": "u", "meetings": 4, "lessons": [{"id": i} for i in "abcd"]}
    laid = c.lay([unit], ms)["units"]["u"]
    day3 = ms[2].date
    # Taught only the first lesson by the third meeting: three left, two meetings left (day 3 and day 4).
    unit["lessons"][0]["taught_on"] = ms[0].date
    p = c.pace(unit, laid, day3)
    assert (p["taught"], p["left"], p["meetings_left"], p["behind"]) == (1, 3, 2, 1)
    # Teaching one today keeps today out of the meetings left.
    unit["lessons"][1]["taught_on"] = day3
    p = c.pace(unit, laid, day3)
    assert (p["left"], p["meetings_left"], p["behind"]) == (2, 1, 1)


def test_next_lesson_is_the_first_not_taught():
    units = [{"id": "u1", "lessons": [{"id": "a", "taught_on": "2026-09-08"}, {"id": "b"}]}]
    u, ls = c.next_lesson(units)
    assert (u["id"], ls["id"]) == ("u1", "b")
    units[0]["lessons"][1]["taught_on"] = "2026-09-09"
    assert c.next_lesson(units) is None


def test_passages_parse_every_shape_the_shelf_uses():
    P = c.parse_passage
    assert str(P("John 6:22–59 · The Bread of Life")) == "John 6:22-59"
    assert str(P("Pictures of Jesus: The Temple of God (John 2:13–25)")) == "John 2:13-25"
    assert str(P("Nine Promises About Eternal Life: John 3:16, Part 4")) == "John 3:16"
    assert str(P("John 9")) == "John 9" and str(P("John 9-10")) == "John 9-10"
    x = P("John 7:53-8:11")
    assert x.start == (7, 53) and x.end == (8, 11)
    assert P("1 John 1:1-4").book == "1 John"
    assert P("Psalm 23").book == "Psalms"
    assert P("Why Did Jesus Let Lazarus Die? Part 2") is None
    assert P("") is None and P(None) is None


def test_overlap():
    P = c.parse_passage
    assert P("John 6:25-29").overlaps(P("John 6:22-59"))
    assert not P("John 6:1-15").overlaps(P("John 6:16-24"))
    assert P("John 7:53-8:11").overlaps(P("John 8:1"))
    assert P("John 9").overlaps(P("John 9:38"))
    assert not P("John 3:16").overlaps(P("1 John 3:16"))


def test_piper_items_use_their_exact_range():
    item = {"label": "John 11:17–44 · Jesus Is the Resurrection and the Life",
            "ref": {"dg": {"from": [11, 17, 11, 44]}}}
    assert str(c.item_passage(item)) == "John 11:17-44"


def test_feeding_takes_pinned_from_above_but_passage_items_only_here():
    course = {"id": "C", "kind": "course", "title": "John"}
    unit = {"id": "U", "kind": "unit", "title": "Bread of Life", "passage": "John 6"}
    lesson = {"id": "L", "kind": "lesson", "title": "6:25-29", "passage": "John 6:25-29", "hidden": ["s3"]}
    pinned = {"C": [{"id": "carson"}], "U": [{"id": "unit-note"}], "L": [{"id": "own"}]}
    shelf = [
        {"id": "s1", "label": "John 6:22–59 · The Bread of Life (sermon 08)"},
        {"id": "s2", "label": "John 6:1–15 · Feeding the five thousand"},
        {"id": "s3", "label": "John 6:25–29 · removed by the teacher"},
        {"id": "s4", "label": "ThirdMill: Gospel of John"},
    ]
    f = c.feeding([course, unit, lesson], pinned, shelf)
    assert [s["id"] for s in f["own"]] == ["own"]
    assert [(s["id"], s["via"]) for s in f["above"]] == [("carson", "John"), ("unit-note", "Bread of Life")]
    assert [s["id"] for s in f["passage"]] == ["s1"]       # not s2 (another lesson's), not s3 (removed)
    # The unit draws on its own pinned, the course's, and everything on its chapter; never its lessons'.
    fu = c.feeding([course, unit], pinned, shelf)
    assert "own" not in [s["id"] for s in fu["own"] + fu["above"]]
    assert {s["id"] for s in fu["passage"]} == {"s1", "s2", "s3"}
    # The course takes pinned sources only.
    assert c.feeding([course], pinned, shelf)["passage"] == []


def test_course_fields_are_cleaned_before_they_are_stored():
    from webapp import course_routes as cr
    assert cr._clean_fields({"title": "  "}) == "A title is needed."
    assert cr._clean_fields({"passage": "the bread chapter"}).startswith("Write the passage")
    assert cr._clean_fields({"meetings": 500}).startswith("Meetings")
    assert cr._clean_fields({"day_type": "friday"}).startswith("A day type")
    f = cr._clean_fields({"title": "Bread", "passage": "John 6", "meetings": "7", "day_type": "thursday"})
    assert f == {"title": "Bread", "passage": "John 6", "meetings": 7, "day_type": "thursday"}
    plan = cr._clean_plan({"objective": "o", "moves": [{"minutes": "500", "title": "Work"}, "junk"],
                           "questions": [{"q": "Why?", "listen": "6:26"}, {"listen": "no question"}]})
    assert plan["moves"] == [{"minutes": 90, "title": "Work", "text": ""}]
    assert plan["questions"] == [{"q": "Why?", "listen": "6:26"}]


def test_a_list_of_passages_matches_on_every_range():
    ps = c.parse_passages("John 14:16-17, 14:26, 15:26-27, 16:7-11, 16:12-15")
    assert [str(p) for p in ps] == ["John 14:16-17", "John 14:26", "John 15:26-27", "John 16:7-11", "John 16:12-15"]
    assert [str(p) for p in c.parse_passages("John 1:14; 19:35; 21:24")] == ["John 1:14", "John 19:35", "John 21:24"]
    assert [str(p) for p in c.parse_passages("John 13-17; 19")] == ["John 13-17", "John 19"]
    assert [str(p) for p in c.parse_passages("Nine Promises: John 3:16, Part 4")] == ["John 3:16"]
    lesson = {"id": "L", "kind": "lesson", "passage": "John 14:16-17, 15:26-27"}
    shelf = [{"id": "a", "label": "John 15:26–27 · Hated but Helped"}, {"id": "b", "label": "John 15:1–11 · The True Vine"}]
    assert [s["id"] for s in c.feeding([{"id": "C", "kind": "course"}, lesson], {}, shelf)["passage"]] == ["a"]


def test_the_scope_and_sequence_fields_are_kept_and_a_save_touches_only_what_it_sends():
    from webapp import course_routes as cr
    plan = cr._clean_plan({
        "topic": "Why John wrote: that you may believe (20:30–31)",
        "aim": ["Students will state why John wrote (20:31).", "", "Students will find John in their Bibles."],
        "application": "Reading to meet a person\nNaming where you stand",
        "strategy": "Inductive study, then think-pair-share.",
        "materials": [{"label": "Gospel of John Summary, Part 1", "use": "show", "shelf_id": "9b2f3c1e-0000-4000-8000-000000000001"},
                      "A one-page map of John", {"label": ""}],
        "assignment": ["Reading Journal: what would you need to see to believe?"],
        "memory": {"ref": "John 20:31", "mode": "plant"},
    })
    assert plan["topic"].startswith("Why John wrote")
    assert plan["aim"] == ["Students will state why John wrote (20:31).", "Students will find John in their Bibles."]
    assert plan["application"] == ["Reading to meet a person", "Naming where you stand"]
    assert [m["label"] for m in plan["materials"]] == ["Gospel of John Summary, Part 1", "A one-page map of John"]
    assert plan["materials"][0]["shelf_id"].startswith("9b2f3c1e")
    assert plan["memory"] == {"ref": "John 20:31", "mode": "plant", "note": ""}
    assert "moves" not in plan and "questions" not in plan     # not sent, so a merge keeps what is stored
    assert set(cr._clean_plan({"moves": []})) == {"moves"}


def test_half_verses_parse_and_assessments_are_kept():
    from webapp import course_routes as cr
    assert str(c.parse_passage("John 18:38b-40")) == "John 18:38-40"
    assert str(c.parse_passage("John 18:28-38a")) == "John 18:28-38"
    plan = cr._clean_plan({"assessments": [{"kind": "quiz", "label": "John 1 chapter quiz", "points": 50},
                                           {"kind": "nonsense", "label": "Recite John 20:31"}, {"label": ""}]})
    assert plan["assessments"] == [{"kind": "quiz", "label": "John 1 chapter quiz", "points": 50},
                                   {"kind": "quiz", "label": "Recite John 20:31", "points": None}]


def test_give_back_days_carry_their_name():
    labels = {d.date: d.label for d in c.off_days(CAL)}
    assert labels["2026-10-14"].startswith("All-School Give Back Day")
    assert labels["2027-03-24"].startswith("All-School Give Back Day")


# ------------------------------------------------------------------ drafting from a course
SERMON = {"id": "11111111-1111-1111-1111-111111111111", "kind": "upload", "label": "John 4:43–54 · The Savior Heals",
          "audience": "students", "ref": {"batch": "vega-john-sermons-2026-11", "sermon": 5, "title": "The Savior Heals",
                                          "passage": "John 4:43–54", "origin": "22222222-2222-2222-2222-222222222222"}}


def test_sermon_and_teaching_transcripts_are_the_teachers_sources():
    """Adam, 2026-11-12: the transcripts are source material; students never see them named."""
    piper = lambda kind: {"kind": "link", "audience": "students", "ref": {"dg": {"kind": kind, "from": [6, 1, 6, 15]}}}
    assert c.teacher_source(SERMON)
    assert c.teacher_source(piper("Sermon")) and c.teacher_source(piper("Conference message"))
    assert not c.teacher_source(piper("Article")) and not c.teacher_source(piper("Solid Joys devotional"))
    assert c.teacher_source({"kind": "upload", "ref": {"site": "Ligonier Ministries", "series": "Knowing Christ", "lesson": 1}})
    assert c.teacher_source({"kind": "link", "audience": "teachers", "ref": {"url": "https://example.org"}})
    assert not c.teacher_source({"kind": "link", "audience": "students", "ref": {"url": "https://thirdmill.org/x.pdf"}})


def test_a_planned_material_opens_the_prep_room_with_its_kind_and_its_line():
    from webapp import course_routes as cr
    sermons = cr._sermon_titles([SERMON])
    plan = {"materials": [
        {"label": "Honor or dishonor? Seminar questions on John 4:43-48 (to make, from your sermon 05 and Piper’s ‘Moses Wrote of Me’)",
         "use": "make", "format": "Discussion Question Set"},
        {"label": "The faith ladder (to make)", "use": "make", "format": "No Such Kind"},
        {"label": "Chapter 1 page (mine September's daily page and your sermon 05; to make)", "use": "make"},
        {"label": "Carson Center segment", "use": "show"}]}
    makes = cr.plan_makes(plan, sermons)
    assert [m["format_id"] for m in makes] == ["discussion_questions", None, None]
    assert makes[0]["brief"] == ("Honor or dishonor? Seminar questions on John 4:43-48. Draw mainly on the transcript "
                                 "“The Savior Heals” (John 4:43–54) and Piper’s ‘Moses Wrote of Me’.")
    assert makes[1]["brief"] == "The faith ladder."
    assert makes[2]["brief"] == "Chapter 1 page. Draw mainly on the transcript “The Savior Heals” (John 4:43–54)."


def test_a_course_draft_knows_its_lesson_and_never_names_a_transcript_to_students():
    from webapp import generator, prep_catalog
    ctx = {"chain": [{"kind": "course", "title": "Gospel of John", "passage": None, "notes": "Sophomores, ESV."},
                     {"kind": "unit", "title": "Sign 2", "passage": "John 4:43-54", "notes": ""},
                     {"kind": "lesson", "title": "John 4:43-48", "passage": "John 4:43-48", "notes": "Seminar day."}],
           "plan": {"topic": "The welcome that wanted a show", "aim": ["Students will explain 4:48."],
                    "strategy": "Socratic seminar on one question."}}
    unit = {"title": "John 4:43-48", "course_name": "Bible II", "notes": "Seminar day.", "course_context": ctx}
    mats = [{"type": "document", "label": "John 4:43–54 · The Savior Heals", "text": "Sermon text.", "teacher_only": True},
            {"type": "document", "label": "TGC: Signs in John", "text": "Article text."}]
    task = generator.build_unit_task("discussion_questions", settings={}, unit=unit, materials=mats)
    for want in ('for the lesson "John 4:43-48"', "WHERE THIS SITS", "Course: Gospel of John", "The teacher's note: Sophomores, ESV.",
                 "Unit: Sign 2 (John 4:43-54)", "Lesson: John 4:43-48", "The teacher's note: Seminar day.",
                 "Topic: The welcome that wanted a show", "  - Students will explain 4:48.",
                 "Socratic seminar on one question.", "naming no TEACHER'S SOURCE there", "## Sources (Teacher)",
                 "=== TEACHER'S SOURCE (never named to students): John 4:43–54 · The Savior Heals ===",
                 "=== DOCUMENT the teacher provided: TGC: Signs in John ==="):
        assert want in task, want
    assert "DOCUMENT the teacher provided: John 4:43–54" not in task
    doc = "# Seminar\n\n1. Who is the “you”?\n\n## Sources (Teacher)\n\n- The Savior Heals\n"
    assert "Savior Heals" not in prep_catalog.student_copy(doc)
    plain = generator.build_unit_task("quiz", settings={}, unit={"title": "U", "notes": "N"}, materials=mats[1:])
    assert "The teacher's note for this unit: N" in plain and "TEACHER'S SOURCE" not in plain


def test_a_course_draft_flags_transcripts_and_takes_a_pinned_one_once(monkeypatch):
    import asyncio

    from webapp import course_routes as cr, prep, shelf_docs
    lesson = {"id": "33333333-3333-3333-3333-333333333333", "kind": "lesson", "passage": "John 4:43-48", "hidden": []}
    chain = [{"id": "44444444-4444-4444-4444-444444444444", "kind": "course"}, lesson]
    article = {"id": "55555555-5555-5555-5555-555555555555", "kind": "link", "label": "John 4:46–54 · Faith in the word",
               "audience": "students", "ref": {"url": "https://example.org/a"}}
    piper = {"id": "66666666-6666-6666-6666-666666666666", "kind": "link", "label": "John 4:46–54 · The Official’s Son",
             "audience": "students", "ref": {"url": "https://example.org/p", "dg": {"kind": "Sermon", "from": [4, 46, 4, 54]}}}
    episode = {"id": "77777777-7777-7777-7777-777777777777", "kind": "podcast", "label": "The Official’s Faith (John 4:43–54)",
               "audience": "students", "ref": {"item_id": "88888888-8888-8888-8888-888888888888",
                                               "ep": {"guid": "g1", "feed": "https://feed.test/rss", "show": "A Show"}}}

    async def own(uid, node):
        if str(node) == lesson["id"]:
            return [{"id": "p1", "kind": "upload", "label": "The Savior Heals", "ref": {"shelf": SERMON["ref"]["origin"]}, "text": "Sermon."}]
        return [{"id": "p2", "kind": "book", "label": "Carson (John 4)", "ref": {"slug": "carson", "coverage": {"chapters": [17]}}}]

    async def chain_of(uid, node):
        return chain

    async def shelf_items(course_key=cr.COURSE_KEY):
        return [article, piper, SERMON, episode]

    async def text_of(item_id):
        return "Some words here."
    monkeypatch.setattr(cr, "_chain", chain_of)
    monkeypatch.setattr(cr, "shelf", shelf_items)
    monkeypatch.setattr(prep, "own_sources", own)
    monkeypatch.setattr(shelf_docs, "text_of", text_of)
    out = asyncio.run(cr.draft_sources(None, lesson["id"]))
    # the lesson's own pins, then the course's; the sermon pinned here isn't taken again by passage
    assert [(s["label"], bool(s.get("teacher_only"))) for s in out] == [
        ("The Savior Heals", True), ("Carson (John 4)", False),
        ("John 4:46–54 · Faith in the word", False), ("John 4:46–54 · The Official’s Son (John Piper)", True),
        ("The Official’s Faith (John 4:43–54)", False)]
    assert out[-1]["shelved"] and out[-1]["episode"]["title"] == "The Official’s Faith (John 4:43–54)"
    # unpinned, the teacher's own sermon comes before narrower passages
    monkeypatch.setattr(prep, "own_sources", lambda uid, node: asyncio.sleep(0, []))
    out = asyncio.run(cr.draft_sources(None, lesson["id"]))
    assert out[0]["label"] == "John 4:43–54 · The Savior Heals" and out[0]["teacher_only"]


def test_a_class_shelf_episode_reaches_a_draft_under_its_own_title(monkeypatch):
    import asyncio

    from webapp import db, excerpts, prep_draft

    async def row(sql, *args):
        assert "left join library_items" in sql and args[2] is True
        return {"id": args[1], "kind": "podcast", "title": "A Show", "creator": "Host", "source_url": "https://feed.test/rss",
                "source_meta": {}, "full_text": "The whole show's description.", "notes": None}

    async def ep_t(feed, guid):
        return None

    async def none(*a):
        return []
    monkeypatch.setattr(db, "fetchrow", row)
    monkeypatch.setattr(excerpts, "episode_transcript", ep_t)
    monkeypatch.setattr(excerpts, "for_item", none)
    item = asyncio.run(prep_draft._library_item(None, "88888888-8888-8888-8888-888888888888", None, shelved=True,
                                                episode={"guid": "g1", "feed": "https://feed.test/rss", "show": "A Show",
                                                         "title": "The Official’s Faith"}))
    assert item["title"] == "The Official’s Faith" and item["creator"] == "A Show" and "transcript" not in item


def test_a_course_draft_reads_only_the_chosen_chapters_of_a_large_book(monkeypatch):
    """A commentary pinned with its unit's chapters: no paid whole-book reading is started for a course draft."""
    import asyncio

    from webapp import comprehension, db, prep_draft

    async def missing(book):
        return "missing", None
    monkeypatch.setattr(comprehension, "status", missing)
    monkeypatch.setattr(db, "ready", lambda: True)
    started = []
    import webapp.app as appmod

    async def request(slug):
        started.append(slug)
    monkeypatch.setattr(appmod, "_request_comprehension", request)
    book = {"slug": "carson", "title": "John", "chapters": [{"n": n, "words": 10_000} for n in range(1, 35)]}
    m = {"type": "book", "book": book, "covered": {19}, "cov_desc": "John 6", "positioned": True, "last": 19, "query": "q"}
    out, note = asyncio.run(prep_draft._large_book(dict(m), 30_000, read_whole=False))
    assert [c["n"] for c in out["chapters"]] == [19] and note is None and not started

    async def plain_unit():                          # a plain Prep Room unit still starts the reading
        out, note = await prep_draft._large_book(dict(m), 30_000)
        await asyncio.sleep(0)
        return out, note
    out, note = asyncio.run(plain_unit())
    assert started == ["carson"] and "for the first time" in note
