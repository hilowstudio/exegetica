"""
Google OAuth sign-in. Chat needs a signed-in school account; most of the rest of the app
works signed out. Only accounts in the school's Google Workspace may sign in, plus the
teacher and admin allowlists (docs/decisions/0005-sign-in-required.md).

Identity is Google SSO for everyone (no passwords). On callback we upsert the user
into Neon and keep a small profile in the signed session cookie. Role
(teacher/student) comes from the TEACHER_EMAILS allowlist, re-evaluated on every
login so promoting someone later takes effect on their next sign-in.
"""
from __future__ import annotations

import logging
import os

from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.responses import JSONResponse, RedirectResponse

from webapp import db

logger = logging.getLogger("study-bible-web.auth")

oauth = OAuth()
_registered = False


def ensure_registered() -> bool:
    """Register the Google client from env the first time it's needed. Returns
    False if the web OAuth credentials aren't configured on this server."""
    global _registered
    if _registered:
        return True
    cid = os.environ.get("GOOGLE_CLIENT_ID_WEB")
    csec = os.environ.get("GOOGLE_CLIENT_SECRET_WEB")
    if not (cid and csec):
        return False
    oauth.register(
        name="google",
        client_id=cid,
        client_secret=csec,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    _registered = True
    return True


def configured() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID_WEB") and os.environ.get("GOOGLE_CLIENT_SECRET_WEB"))


def _emails_env(var: str) -> set[str]:
    """Comma-separated email allowlist from an env var, robust to surrounding quotes.
    (python-dotenv strips quotes locally, but Fly/other hosts inject secrets raw, so a value
    set as "a@x.com,b@y.com" would otherwise keep its quotes and never match.)"""
    raw = (os.environ.get(var) or "").strip().strip('"').strip("'")
    return {e.strip().strip('"').strip("'").lower() for e in raw.split(",") if e.strip().strip('"').strip("'")}


def _teacher_emails() -> set[str]:
    return _emails_env("TEACHER_EMAILS")


def _role_for(email: str | None) -> str:
    return "teacher" if (email or "").lower() in _teacher_emails() else "student"


def _admin_emails() -> set[str]:
    return _emails_env("LIBRARY_ADMIN_EMAILS")


def is_admin(user) -> bool:
    """A library admin may edit canonical shared-catalog data (e.g. cover art for everyone)."""
    return bool(user) and (user.get("email") or "").lower() in _admin_emails()


def is_teacher(user) -> bool:
    """Checked live against TEACHER_EMAILS (not the role cached in the session cookie), so
    removing a teacher takes effect on their next request."""
    return bool(user) and (user.get("email") or "").lower() in _teacher_emails()


SCHOOL_DOMAIN = (os.environ.get("SCHOOL_DOMAIN") or "yorkvillechristian.com").strip().lower()


def _may_sign_in(userinfo: dict) -> bool:
    email = (userinfo.get("email") or "").lower()
    if email in _teacher_emails() or email in _admin_emails():
        return True
    return bool(userinfo.get("email_verified")) and email.endswith("@" + SCHOOL_DOMAIN)


def current_user(request):
    """The signed-in user's profile dict, or None."""
    return request.session.get("user")


def _safe_next(request) -> str:
    """Only allow same-site relative redirect targets (no open redirects)."""
    nxt = request.query_params.get("next") or "/"
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else "/"


def _redirect_uri(request) -> str:
    url = request.url_for("auth_callback")
    # Behind Fly's TLS-terminating proxy the request scheme reads as http; the
    # registered Google redirect URI is https for the public host.
    if url.hostname not in ("localhost", "127.0.0.1"):
        url = url.replace(scheme="https")
    return str(url)


async def login(request):
    if not ensure_registered():
        return JSONResponse({"error": "Google sign-in is not configured on this server."}, status_code=503)
    request.session["next"] = _safe_next(request)
    return await oauth.google.authorize_redirect(request, _redirect_uri(request))


async def auth_callback(request):
    if not ensure_registered():
        return RedirectResponse("/")
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:  # user denied, state mismatch, etc.
        logger.warning("OAuth callback error: %s", e)
        return RedirectResponse("/?auth=error")

    userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
    sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name") or (email.split("@")[0] if email else "Friend")
    if not sub:
        return RedirectResponse("/?auth=error")
    if not _may_sign_in(userinfo):
        logger.info("Sign-in refused for an account outside %s", SCHOOL_DOMAIN)
        return RedirectResponse("/?auth=domain")

    if not db.ready():
        # We can authenticate but not persist/scope data without the DB. Fail soft.
        logger.warning("Sign-in attempted but the database is unavailable")
        return RedirectResponse("/?auth=nodb")

    # The Google profile photo is never stored (QSF DAT-07): nothing in the app shows it.
    row = await db.fetchrow(
        """insert into users (google_sub, email, name, picture, role, last_login_at)
           values ($1, $2, $3, null, $4, now())
           on conflict (google_sub) do update
             set email=excluded.email, name=excluded.name, picture=null,
                 role=excluded.role, last_login_at=now()
           returning id, role""",
        sub, email, name, _role_for(email),
    )
    request.session["user"] = {
        "id": str(row["id"]), "email": email, "name": name, "role": row["role"],
    }
    nxt = request.session.pop("next", "/")
    return RedirectResponse(nxt if nxt.startswith("/") else "/")


async def logout(request):
    request.session.pop("user", None)
    return RedirectResponse(_safe_next(request))


async def me(request):
    u = current_user(request)
    return JSONResponse({"user": u, "admin": is_admin(u)})
