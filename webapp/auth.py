"""
Google OAuth sign-in. Optional by design — the app works fully signed-out; signing
in just moves a person's data to their Neon account.

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


def _teacher_emails() -> set[str]:
    raw = os.environ.get("TEACHER_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _role_for(email: str | None) -> str:
    return "teacher" if (email or "").lower() in _teacher_emails() else "student"


def _admin_emails() -> set[str]:
    raw = os.environ.get("LIBRARY_ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_admin(user) -> bool:
    """A library admin may edit canonical shared-catalog data (e.g. cover art for everyone)."""
    return bool(user) and (user.get("email") or "").lower() in _admin_emails()


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
    picture = userinfo.get("picture")
    if not sub:
        return RedirectResponse("/?auth=error")

    if not db.ready():
        # We can authenticate but not persist/scope data without the DB. Fail soft.
        logger.warning("Sign-in attempted but the database is unavailable")
        return RedirectResponse("/?auth=nodb")

    row = await db.fetchrow(
        """insert into users (google_sub, email, name, picture, role, last_login_at)
           values ($1, $2, $3, $4, $5, now())
           on conflict (google_sub) do update
             set email=excluded.email, name=excluded.name, picture=excluded.picture,
                 role=excluded.role, last_login_at=now()
           returning id, role""",
        sub, email, name, picture, _role_for(email),
    )
    request.session["user"] = {
        "id": str(row["id"]), "email": email, "name": name,
        "picture": picture, "role": row["role"],
    }
    nxt = request.session.pop("next", "/")
    return RedirectResponse(nxt if nxt.startswith("/") else "/")


async def logout(request):
    request.session.pop("user", None)
    return RedirectResponse(_safe_next(request))


async def me(request):
    u = current_user(request)
    return JSONResponse({"user": u, "admin": is_admin(u)})
