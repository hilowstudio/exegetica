"""The site's shared layout: one Jinja2 base template (templates/base.html) that every page extends.

It holds what every page has, once: the head (icons, fonts, colour tokens, the theme set before
the first paint), the rail, the Settings panel, and the Need help now? window. A page supplies only
its own content, styles and script. The rail's icons depend on who is signed in, and nothing else:
everyone sees Chat, Scripture Memory and the Reading Room, teachers also the Prep Room and the
Living Library, and admins also Media Studio. The server draws them, so a teacher's rail never
reaches a student's browser.

A page whose content is built in Python (the statements and privacy page in about.py, the course
and calendar views, ops) hands back a Built, and render() puts it in the same layout through
templates/built.html.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from markupsafe import Markup
from starlette.templating import Jinja2Templates

from webapp import auth, safety

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _icon(paths: str) -> Markup:
    return Markup(f'<svg viewBox="0 0 24 24" aria-hidden="true">{paths}</svg>')


# The rail's places, in order: (link, label, who sees it, icon). "teacher" means teachers and admins.
RAIL = (
    ("/", "Chat", "everyone", _icon('<path d="M4 5.5h16v11H9l-4 3.2V16.5H4z"/>')),
    ("/memory", "Scripture Memory", "everyone",
     _icon('<rect x="3.5" y="6.5" width="12" height="12" rx="2"/><path d="M8 4.5h10a2 2 0 0 1 2 2v10"/>'
           '<path d="M6.5 11h6M6.5 14h4"/>')),
    ("/read", "Reading Room", "everyone",
     _icon('<path d="M12 6.6C10.2 5.3 7.3 5 4.8 5.6v12.3c2.5-.6 5.4-.3 7.2 1 1.8-1.3 4.7-1.6 7.2-1V5.6'
           'C16.7 5 13.8 5.3 12 6.6z"/><path d="M12 6.6v11.7"/>')),
    ("/generate", "Prep Room", "teacher",
     _icon('<path d="M6.5 3.5h8l4 4v13h-12z"/><path d="M14 3.5v4.2h4.2"/><path d="M9 12.5h6M9 15.5h6"/>')),
    ("/library", "Living Library", "teacher",
     _icon('<rect x="4.5" y="5" width="4" height="14" rx="1"/><rect x="10" y="5" width="4" height="14" rx="1"/>'
           '<path d="M16 6.3l3.3.9-2.9 12.7-3.3-.9"/>')),
    ("/studio", "Media Studio", "admin",
     _icon('<rect x="3.5" y="5" width="17" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/>'
           '<path d="M4.5 17.5l5-5 3.5 3.5 2.5-2.5 4 4"/>')),
)


def rail_items(path: str, teacher: bool, admin: bool) -> list[dict]:
    """The places one person's rail shows, with the current page marked."""
    def shown(who):
        return who == "everyone" or (who == "teacher" and (teacher or admin)) or (who == "admin" and admin)

    def here(href):
        return path == "/" if href == "/" else path == href or path.startswith(href + "/")

    return [{"href": href, "label": label, "icon": icon, "active": here(href)}
            for href, label, who, icon in RAIL if shown(who)]


def page(request, template: str, status_code: int = 200, cache: str = "private, no-cache", **context):
    """Render one page in the shared layout. It differs by person, so no shared cache keeps it."""
    user = auth.current_user(request)
    teacher, admin = auth.is_teacher(user), auth.is_admin(user)
    context = {"rail": rail_items(request.url.path, teacher, admin), "crisis": safety.get_crisis_resources(),
               "user": user, "teacher": teacher, "admin": admin, **context}
    return TEMPLATES.TemplateResponse(request, template, context, status_code=status_code,
                                      headers={"Cache-Control": cache})


@dataclass(frozen=True)
class Built:
    """A page built in Python: its title, its body HTML (already escaped where it needs to be), and the
    page's own stylesheets and scripts under /static."""
    title: str
    body: str
    css: tuple[str, ...] = ()
    scripts: tuple[str, ...] = ()
    noindex: bool = False


def render(request, built: Built, status_code: int = 200, cache: str = "private, no-cache"):
    return page(request, "built.html", status_code, cache, title=built.title, body=Markup(built.body),
                css=built.css, scripts=built.scripts, noindex=built.noindex)
