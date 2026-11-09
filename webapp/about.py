"""
Public pages for Hi Low Studio's two statements, its position on AI (/position) and its Quiet
Standards Framework (/quiet-standards), Exegetica's privacy page (/privacy), and the list of formats
the Prep Room drafts (/prep-room/formats). The statements are different messages, so each has its own
page, rendered from its one file in docs/. No model is involved.

The privacy page fills its retention lines from webapp/retention.py, so it states only the purges
that are running. Each page is a prose column (static/css/prose.css) in the shared layout (shell.py).
"""
from __future__ import annotations

import html
from pathlib import Path

from webapp import course, generator, retention, shell

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


def _doc(title: str, doc: str, fill: dict[str, str] | None = None) -> shell.Built:
    body = course.render_html(DOCS_DIR / doc)
    for marker, text in (fill or {}).items():
        body = body.replace(marker, text)
    return prose(title, body)


def prose(title: str, body: str, css: tuple[str, ...] = (), scripts: tuple[str, ...] = (),
          noindex: bool = False) -> shell.Built:
    """One prose page: a back link, the wordmark, and the body in a reading column."""
    return shell.Built(f"{title} | Exegetica",
                       f'<main class="prose shell-col"><nav class="back"><a href="/">Back to chat</a></nav>'
                       f'{shell.MASTHEAD}{body}</main>',
                       css=("/static/css/prose.css", *css), scripts=scripts, noindex=noindex)


async def position_page(request):
    return shell.render(request, _doc("Position on AI", "position-statement-christian-school-theologian.md"))


async def quiet_standards_page(request):
    return shell.render(request, _doc("Quiet Standards", "quiet-standards-statement.md"))


def _retention_text() -> str:
    if retention.enabled():
        return (f"<p>A student account with no sign-in for {retention.INACTIVE_MONTHS} months is deleted with "
                "everything in it. Until then, everything stays until you delete it.</p>")
    return "<p>Everything stays in your account until you delete it or delete your account.</p>"


def _first_sentence(text: str) -> str:
    text = " ".join((text or "").split())
    end = text.find(". ")
    return text if end < 0 else text[:end + 1]


async def formats_page(request):
    """Every format the Prep Room drafts, by subject, read from its catalog (resource-generators.yaml)
    so the list never drifts from what the Prep Room offers. Withheld formats (decision 0010) are left out."""
    sections = []
    for subject, groups in generator._catalog.get("subjects", {}).items():
        parts, seen = [], set()
        for group, spec in groups.items():
            items = [generator.FORMATS[f] for f in spec.get("formats", []) if f in generator.FORMATS]
            seen.update(f["id"] for f in items)
            if items:
                parts.append(f"<h3>{html.escape(group)}</h3><ul>" + "".join(
                    f"<li><strong>{html.escape(f['name'])}.</strong> {html.escape(_first_sentence(f['definition']))}</li>"
                    for f in items) + "</ul>")
        if parts:
            sections.append(f"<details><summary><h2>{html.escape(subject)}</h2><span>{len(seen)} formats</span>"
                            "</summary>" + "".join(parts) + "</details>")
    body = (f"<h1>What the Prep Room can make</h1><p>The Prep Room drafts {len(generator.FORMATS)} kinds "
            "of documents for teachers, grouped here by subject. Open a subject to see its formats. A format "
            "that serves several subjects appears under each, and the formats under Universal work for any "
            "subject. Every draft is the teacher's to check and change before students see it.</p>"
            + "".join(sections))
    return shell.render(request, prose("Prep Room formats", body, css=("/static/css/formats.css",)))


def _grades(grades: list[int]) -> str:
    if not grades:
        return ""
    lo, hi = min(grades), max(grades)
    k = lambda g: "K" if g == 0 else str(g)  # noqa: E731
    return f"grade {k(lo)}" if lo == hi else f"grades {k(lo)} to {k(hi)}"


async def standards_page(request):
    """The academic spine, for anyone to browse: subjects, strands, topics, and sub-topics from
    webapp/standards/, with each sub-topic's objectives loaded when it is opened, and the same search
    the Prep Room uses. A teacher also gets a link from each sub-topic into the Prep Room."""
    from webapp import auth
    teacher = auth.is_teacher(auth.current_user(request))
    tree = generator.TREE
    count = lambda node: sum(st.get("objective_count", 0) for tp in node["topics"] for st in tp.get("sub_topics", []))  # noqa: E731
    total = sum(count(ss) for s in tree["subjects"] for ss in s["sub_subjects"])
    out = []
    for s in tree["subjects"]:
        n = sum(count(ss) for ss in s["sub_subjects"])
        out.append(f'<details class="subj" id="S-{s["id"]}"><summary><h2>{html.escape(s["name"])}</h2>'
                   f'<span class="n">{n:,} objectives</span></summary>')
        for ss in s["sub_subjects"]:
            out.append(f'<details class="strand" id="S-{ss["id"]}"><summary><h3>{html.escape(ss["name"])}</h3>'
                       f'<span class="n">{count(ss):,} objectives</span></summary>')
            for tp in ss["topics"]:
                out.append(f'<div class="topic"><h4>{html.escape(tp["name"])}</h4>')
                for st in tp.get("sub_topics", []):
                    draft = (f'<a class="draft" href="/generate?standard={st["id"]}">Draft from this in the Prep Room</a>'
                             if teacher else "")
                    out.append(f'<details class="st" id="S-{st["id"]}" data-st="{st["id"]}"><summary>'
                               f'<span class="name">{html.escape(st["name"])}</span><span class="n">'
                               f'{st.get("objective_count", 0)} · {_grades(st.get("grades") or [])}</span></summary>'
                               f'<div class="objs"></div>{draft}</details>')
                out.append("</div>")
            out.append("</details>")
        out.append("</details>")
    intro = (f"<h1>Academic standards</h1><p>The learning objectives the Prep Room drafts toward: {total:,} across "
             f"{len(tree['subjects'])} subjects, from kindergarten to grade 12. Open a subject, then a strand, then a "
             "sub-topic to see its objectives, each with the grade where a student can first do it and the standard, "
             "Scripture, or confession it rests on. Or search for a skill or a doctrine.</p>"
             '<div class="std-search"><label for="q">Search the standards</label>'
             '<input id="q" type="search" autocomplete="off" placeholder="For example: FFA officer roles, or justification by faith">'
             '<div id="hits" aria-live="polite"></div></div>')
    return shell.render(request, prose("Academic standards", intro + "".join(out),
                                       css=("/static/css/standards.css",), scripts=("/static/js/standards.js",)))


def privacy() -> shell.Built:
    return _doc("Privacy", "privacy.md", {
        "<p>{{retention}}</p>": _retention_text(),
        "{{metrics_days}}": str(retention.METRICS_DAYS),
        "{{cap_days}}": str(retention.CAP_DAYS),
    })


async def privacy_page(request):
    return shell.render(request, privacy())
