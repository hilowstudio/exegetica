"""
Public pages for Hi Low Studio's two statements, its position on AI (/position) and its Quiet
Standards Framework (/quiet-standards), Exegetica's privacy page (/privacy), and the list of formats
the Prep Room drafts (/prep-room/formats). The statements are different messages, so each has its own
page, rendered from its one file in docs/. No model is involved.

The privacy page fills its retention lines from webapp/retention.py, so it states only the purges
that are running.
"""
from __future__ import annotations

import html
from pathlib import Path

from starlette.responses import HTMLResponse

from webapp import course, generator, retention

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

_TOKENS_DARK = ("--paper:#14151a;--ink:#e9e7e0;--ink-soft:#a9aeb9;--rule:#2c2f37;--iron:#7fb0c2")
_CSS = (
    ":root{--paper:#f0e8dc;--ink:#1e2026;--ink-soft:#54596a;--rule:#ddd3c1;--iron:#3d6980}"
    "@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]){" + _TOKENS_DARK + "}}"
    ":root[data-theme=\"dark\"]{" + _TOKENS_DARK + "}"
    "*{box-sizing:border-box}"
    "body{margin:0;background:var(--paper);color:var(--ink);font-family:\"Source Serif 4\",Georgia,serif;"
    "font-size:18px;line-height:1.65;-webkit-font-smoothing:antialiased}"
    "main{max-width:68ch;margin:0 auto;padding:12px 20px 72px}"
    "nav{font-family:Inter,system-ui,sans-serif;font-size:14px}"
    "nav a{display:inline-flex;align-items:center;min-height:44px}"
    "h1,h2{font-family:Fraunces,Georgia,serif;font-weight:600;line-height:1.2;text-wrap:balance}"
    "h1{font-size:2rem;margin:.6em 0 .3em}h2{font-size:1.4rem;margin:1.8em 0 .4em}"
    "h3{font-family:Inter,system-ui,sans-serif;font-size:1rem;font-weight:600;margin:1.5em 0 .3em}"
    "em{color:var(--ink-soft)}a{color:var(--iron)}"
    "a:focus-visible{outline:2px solid var(--iron);outline-offset:2px}"
)


def _page(title: str, doc: str, fill: dict[str, str] | None = None) -> HTMLResponse:
    body = course.render_html(DOCS_DIR / doc)
    for marker, text in (fill or {}).items():
        body = body.replace(marker, text)
    return _shell(title, body)


def _shell(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{title} | Exegetica</title>"
        "<link rel=\"stylesheet\" href=\"/static/fonts.css\">"
        f"<style>{_CSS}</style>"
        "<script>try{var t=localStorage.getItem(\"studybible.theme\");"
        "if(t===\"light\"||t===\"dark\")document.documentElement.dataset.theme=t;}catch(e){}</script>"
        "</head><body><main><nav><a href=\"/\">Back to chat</a></nav>"
        f"{body}</main></body></html>"
    )


async def position_page(request):
    return _page("Position on AI", "position-statement-christian-school-theologian.md")


async def quiet_standards_page(request):
    return _page("Quiet Standards", "quiet-standards-statement.md")


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
    css = ("<style>details{border-top:1px solid var(--rule)}details:last-of-type{border-bottom:1px solid var(--rule)}"
           "summary{display:flex;align-items:baseline;gap:12px;cursor:pointer;padding:14px 0;list-style:none}"
           "summary::-webkit-details-marker{display:none}"
           "summary::before{content:'\\25B8';color:var(--ink-soft);font-size:.9rem;transition:transform .15s}"
           "details[open]>summary::before{transform:rotate(90deg)}"
           "summary h2{margin:0;font-size:1.25rem;flex:1}"
           "summary span{font-family:Inter,system-ui,sans-serif;font-size:14px;color:var(--ink-soft)}"
           "summary:focus-visible{outline:2px solid var(--iron);outline-offset:2px}"
           "details ul{padding-left:1.2em}details li{margin:.35em 0}</style>")
    body = (f"{css}<h1>What the Prep Room can make</h1><p>The Prep Room drafts {len(generator.FORMATS)} kinds "
            "of documents for teachers, grouped here by subject. Open a subject to see its formats. A format "
            "that serves several subjects appears under each, and the formats under Universal work for any "
            "subject. Every draft is the teacher's to check and change before students see it.</p>"
            + "".join(sections))
    return _shell("Prep Room formats", body)


def _grades(grades: list[int]) -> str:
    if not grades:
        return ""
    lo, hi = min(grades), max(grades)
    k = lambda g: "K" if g == 0 else str(g)  # noqa: E731
    return f"grade {k(lo)}" if lo == hi else f"grades {k(lo)} to {k(hi)}"


_STANDARDS_CSS = (
    "<style>"
    ".std-search{position:relative;margin:1.2em 0 1.6em}"
    ".std-search label{display:block;font-family:Inter,system-ui,sans-serif;font-size:14px;font-weight:600;margin-bottom:6px}"
    ".std-search input{width:100%;font:inherit;font-size:16px;padding:10px 12px;border:1px solid var(--rule);"
    "border-radius:10px;background:transparent;color:var(--ink)}"
    ".std-search input:focus-visible{outline:2px solid var(--iron);outline-offset:1px}"
    "#hits{margin-top:6px;font-family:Inter,system-ui,sans-serif;font-size:14px}"
    "#hits button{display:block;width:100%;text-align:left;font:inherit;color:var(--ink);background:none;border:0;"
    "border-bottom:1px solid var(--rule);padding:9px 4px;cursor:pointer}"
    "#hits button:hover,#hits button:focus-visible{background:color-mix(in srgb,var(--iron) 10%,transparent);outline:none}"
    "#hits .path{display:block;color:var(--ink-soft);font-size:12.5px;margin-top:2px}"
    "details{border-top:1px solid var(--rule)}"
    "summary{display:flex;align-items:baseline;gap:10px;cursor:pointer;padding:12px 0;list-style:none}"
    "summary::-webkit-details-marker{display:none}"
    "summary::before{content:'\\25B8';color:var(--ink-soft);font-size:.85rem;transition:transform .15s}"
    "details[open]>summary::before{transform:rotate(90deg)}"
    "summary:focus-visible{outline:2px solid var(--iron);outline-offset:2px}"
    "summary .n{font-family:Inter,system-ui,sans-serif;font-size:13px;color:var(--ink-soft);white-space:nowrap}"
    "summary h2,summary h3{margin:0;flex:1}summary h2{font-size:1.25rem}summary h3{font-size:1.05rem}"
    ".strand{margin-left:1.1em}.topic{margin:0 0 0 2.2em}"
    ".topic h4{font-family:Inter,system-ui,sans-serif;font-size:13px;letter-spacing:.06em;text-transform:uppercase;"
    "color:var(--ink-soft);margin:1.2em 0 .2em}"
    ".st summary{font-size:16px;padding:9px 0}.st summary .name{flex:1}"
    ".st ol{margin:.2em 0 .8em;padding-left:1.4em;font-size:16px}.st li{margin:.45em 0}"
    ".st li.hit{background:color-mix(in srgb,var(--iron) 14%,transparent);border-radius:4px}"
    ".gr{font-family:Inter,system-ui,sans-serif;font-size:12px;color:var(--ink-soft);margin-right:6px}"
    ".anc{display:block;font-family:Inter,system-ui,sans-serif;font-size:12.5px;color:var(--ink-soft)}"
    ".draft{display:inline-block;font-family:Inter,system-ui,sans-serif;font-size:14px;margin:0 0 .9em}"
    "@media (max-width:600px){.strand{margin-left:.35em}.topic{margin-left:.7em}}"
    "</style>"
)

_STANDARDS_JS = """<script>
(function(){
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function grade(g){return g===0?"K":String(g);}
  function load(d){
    if(d.dataset.loaded)return Promise.resolve();
    d.dataset.loaded="1";
    var box=d.querySelector(".objs");box.textContent="Loading objectives…";
    return fetch("/api/standards/objectives?sub_topic="+encodeURIComponent(d.dataset.st)).then(function(r){return r.json();}).then(function(j){
      var objs=(j.objectives||[]).slice().sort(function(a,b){return a.c-b.c;});
      box.innerHTML="<ol>"+objs.map(function(o){
        var a=o.a||{},anc=[].concat(a.scripture||[],a.confessions||[],a.standards||[]);
        return '<li id="o-'+esc(o.id)+'"><span class="gr">Grade '+grade(o.g)+'</span>'+esc(o.t)+
          (anc.length?'<span class="anc">'+esc(anc.join(" · "))+'</span>':"")+"</li>";}).join("")+"</ol>";
    }).catch(function(){d.dataset.loaded="";box.textContent="The objectives could not be loaded. Close and open this again.";});
  }
  document.querySelectorAll("details.st").forEach(function(d){d.addEventListener("toggle",function(){if(d.open)load(d);});});
  function reveal(ids){
    ["subject","sub_subject","sub_topic"].forEach(function(k){var e=ids[k]&&document.getElementById("S-"+ids[k]);if(e)e.open=true;});
    var st=ids.sub_topic&&document.getElementById("S-"+ids.sub_topic);
    var target=st||document.getElementById("S-"+(ids.sub_subject||ids.subject));
    if(!target)return;
    (st?load(st):Promise.resolve()).then(function(){
      var o=ids.objective&&document.getElementById("o-"+ids.objective);
      document.querySelectorAll("li.hit").forEach(function(x){x.classList.remove("hit");});
      if(o)o.classList.add("hit");
      (o||target).scrollIntoView({block:"center"});
      target.querySelector("summary").focus({preventScroll:true});
    });
  }
  var q=document.getElementById("q"),hits=document.getElementById("hits"),timer=null;
  q.addEventListener("input",function(){
    clearTimeout(timer);var v=q.value.trim();
    if(v.length<2){hits.innerHTML="";return;}
    timer=setTimeout(function(){
      fetch("/api/standards/search?q="+encodeURIComponent(v)).then(function(r){return r.json();}).then(function(j){
        var rs=(j.results||[]).slice(0,10);
        if(!rs.length){hits.innerHTML='<p class="path">No matches. Try fewer or simpler words.</p>';return;}
        hits.innerHTML="";
        rs.forEach(function(h){
          var b=document.createElement("button");b.type="button";
          b.innerHTML=esc(h.label)+'<span class="path">'+esc(h.path.join(" › "))+(h.grade!=null?" · grade "+grade(h.grade):"")+"</span>";
          b.addEventListener("click",function(){reveal(h.ids);});
          hits.appendChild(b);
        });
      }).catch(function(){hits.innerHTML='<p class="path">Search is not available right now.</p>';});
    },200);
  });
})();
</script>"""


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
    return _shell("Academic standards", _STANDARDS_CSS + intro + "".join(out) + _STANDARDS_JS)


async def privacy_page(request):
    return _page("Privacy", "privacy.md", {
        "<p>{{retention}}</p>": _retention_text(),
        "{{metrics_days}}": str(retention.METRICS_DAYS),
        "{{cap_days}}": str(retention.CAP_DAYS),
    })
