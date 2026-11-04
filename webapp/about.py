"""
Public pages for Hi Low Studio's two statements, its position on AI (/position) and its Quiet
Standards Framework (/quiet-standards), and Exegetica's privacy page (/privacy). They are different
messages, so each has its own page, rendered from its one file in docs/. No model is involved.

The privacy page fills its retention lines from webapp/retention.py, so it states only the purges
that are running.
"""
from __future__ import annotations

from pathlib import Path

from starlette.responses import HTMLResponse

from webapp import course, retention

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


async def privacy_page(request):
    return _page("Privacy", "privacy.md", {
        "<p>{{retention}}</p>": _retention_text(),
        "{{metrics_days}}": str(retention.METRICS_DAYS),
        "{{cap_days}}": str(retention.CAP_DAYS),
    })
