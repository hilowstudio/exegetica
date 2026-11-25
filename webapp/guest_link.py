"""Sign-in links for guests (decision 0005, amended 2026-11-25).

A guest from outside the school can’t use Google sign-in: the school's Google app admits only accounts in its own
organization. So the maker makes a sign-in link for a guest on /ops and sends it to them himself. Opening the link
shows one button, and pressing it signs the guest in. A press is needed because link previews in messages and email
open links by themselves, and a link that signed in on opening would be spent before the guest saw it.

A link:
- names one address on the guest list (GUEST_EMAILS) and works only while the address is still there
- works once: it is refused once its account has signed in since the link was made
- lasts LINK_DAYS days
- is signed with the session secret, so nothing about it is stored

The guest then stays signed in on that device the way everyone does. On another device they need a new link.
"""
from __future__ import annotations

import datetime as dt
import html
import logging
import os

from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.responses import PlainTextResponse, RedirectResponse

from webapp import about, auth, db, shell

logger = logging.getLogger("study-bible-web.guest-link")

LINK_DAYS = 7
_SALT = "exegetica-guest-sign-in"
SPENT = "This sign-in link has been used or has expired. Ask the person who sent it for a new one."
NOT_SET_UP = "Sign-in links aren’t set up on this server."


def _serializer() -> URLSafeTimedSerializer | None:
    secret = os.environ.get("SESSION_SECRET")
    return URLSafeTimedSerializer(secret, salt=_SALT) if secret else None


def make_token(email: str) -> str | None:
    s = _serializer()
    return s.dumps({"e": (email or "").lower()}) if s else None


def read_token(token: str | None) -> dict | None:
    """{"email", "issued"} for a well-signed, unexpired link to an address still on the guest list, else None."""
    s = _serializer()
    if not s or not token:
        return None
    try:
        data, issued = s.loads(token, max_age=LINK_DAYS * 86400, return_timestamp=True)
    except BadSignature:            # SignatureExpired is a BadSignature
        return None
    email = str((data or {}).get("e") or "").lower() if isinstance(data, dict) else ""
    if not auth.is_guest_email(email):
        return None
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=dt.timezone.utc)
    return {"email": email, "issued": issued}


def spent(last_login_at, issued) -> bool:
    """A link is spent once its account has signed in since the link was made."""
    if not last_login_at:
        return False
    if last_login_at.tzinfo is None:
        last_login_at = last_login_at.replace(tzinfo=dt.timezone.utc)
    return last_login_at >= issued


def _base(request) -> str:
    """The site's own address, https behind Fly's proxy (as auth._redirect_uri does)."""
    url = request.base_url
    if url.hostname not in ("localhost", "127.0.0.1"):
        url = url.replace(scheme="https")
    return str(url).rstrip("/")


def _page(request, title: str, body: str, status: int = 200, scripts: tuple[str, ...] = ()):
    return shell.render(request, about.prose(title, body, css=("/static/css/ops.css",), scripts=scripts, noindex=True),
                        status_code=status, cache="no-store")


def _spent_page(request):
    return _page(request, "Sign-in link", f"<h1>Sign-in link</h1><p>{SPENT}</p>", status=410)


async def page(request):
    """GET /auth/link?t=...: what the link signs in, and one button. Opening it signs no one in."""
    token = request.query_params.get("t", "")
    got = read_token(token)
    if not got:
        return _spent_page(request)
    if (auth.current_user(request) or {}).get("email", "").lower() == got["email"]:
        return RedirectResponse("/", status_code=303)
    email = html.escape(got["email"])
    body = ("<h1>Sign in to Exegetica</h1>"
            f"<p>This link signs you in as <strong>{email}</strong>. It works once, and keeps you signed in on this "
            "device.</p>"
            f'<form method="post" action="/auth/link"><input type="hidden" name="t" value="{html.escape(token)}">'
            '<button type="submit" class="join-btn">Sign in</button></form>'
            "<p>If that isn’t your address, close this page.</p>")
    return _page(request, "Sign in", body)


async def redeem(request):
    """POST /auth/link: sign the guest in, once."""
    form = await request.form()
    got = read_token(form.get("t"))
    if not got:
        return _spent_page(request)
    email = got["email"]
    if (auth.current_user(request) or {}).get("email", "").lower() == email:
        return RedirectResponse("/", status_code=303)     # a second press of the same button
    if not db.ready():
        return _page(request, "Sign in", "<h1>Sign in</h1><p>Exegetica can’t sign anyone in right now. Try the "
                                         "same link again in a few minutes.</p>", status=503)
    row = await db.fetchrow("""select id, name, role, last_login_at from users where lower(email) = $1
                               order by last_login_at desc nulls last limit 1""", email)
    if row and spent(row["last_login_at"], got["issued"]):
        return _spent_page(request)
    if row:
        row = await db.fetchrow("update users set last_login_at = now() where id = $1 returning id, name, role",
                                row["id"])
    else:
        row = await db.fetchrow(
            """insert into users (google_sub, email, name, picture, role, last_login_at)
               values ($1, $2, $3, null, 'student', now()) returning id, name, role""",
            "link:" + email, email, email.split("@")[0])
    request.session["user"] = {"id": str(row["id"]), "email": email, "name": row["name"] or email.split("@")[0],
                               "role": "student"}
    logger.info("A guest signed in with a sign-in link")
    return RedirectResponse("/", status_code=303)


# ------------------------------------------------------------------------------------------ the maker's side (/ops)
def ops_section() -> str:
    """The guest list on /ops, each with a button that makes a sign-in link."""
    guests = sorted(auth.guest_emails())
    rows = "".join(
        f"<tr><td>{html.escape(e)}</td><td class=acts><form method=post action=\"/ops/guest-link\">"
        f"<input type=hidden name=email value=\"{html.escape(e)}\"><button type=submit>Make a sign-in link</button>"
        "</form></td></tr>" for e in guests) or "<tr><td colspan=2>No guests. Add an address to GUEST_EMAILS on the server.</td></tr>"
    return ("<h2 id=guests>Guest sign-in links</h2><p>Guests are accounts from outside the school (decision 0005). "
            "The school's Google sign-in turns them away, so each signs in with a link you send them. A link works "
            f"once, for {LINK_DAYS} days, and only while the address is on the guest list.</p>"
            "<div class=wide tabindex=0 role=region aria-label=\"Guest sign-in links\"><table>"
            "<tr><th>Guest</th><th>Act</th></tr>" + rows + "</table></div>")


async def make(request):
    """POST /ops/guest-link: a fresh sign-in link for one guest, shown once to copy."""
    if not auth.is_admin(auth.current_user(request)):
        return PlainTextResponse("Not Found", status_code=404)
    form = await request.form()
    email = str(form.get("email") or "").lower()
    if not auth.is_guest_email(email):
        return _page(request, "Sign-in link", "<h1>Sign-in link</h1><p>That address isn’t on the guest list.</p>"
                                              '<p><a href="/ops#guests">Back to operations</a></p>', status=400)
    token = make_token(email)
    if not token:
        return _page(request, "Sign-in link", f"<h1>Sign-in link</h1><p>{NOT_SET_UP}</p>", status=503)
    url = f"{_base(request)}/auth/link?t={token}"
    end = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=LINK_DAYS)
    until = f"{end:%B} {end.day}"
    body = ("<h1>Sign-in link</h1>"
            f"<p>For <strong>{html.escape(email)}</strong>. Send it to them yourself. It works once, until {until}, "
            "and only while the address is on the guest list. Making another link doesn’t cancel this one.</p>"
            '<label for="link" class="link-label">The link</label>'
            f'<input id="link" class="link-box" readonly value="{html.escape(url)}">'
            '<button type="button" class="join-btn" id="copy-link">Copy link</button>'
            '<p><a href="/ops#guests">Back to operations</a></p>')
    return _page(request, "Sign-in link", body, scripts=("/static/js/guest-link.js",))
