"""The browser check (exegetica-design skill, rule K3): every page, as each role, in both themes, at three sizes.

    .venv/Scripts/python scripts/design_check.py                    # everything, about fifteen minutes
    .venv/Scripts/python scripts/design_check.py --pages /,/memory --roles student --sizes phone
    .venv/Scripts/python scripts/design_check.py --out DIR --port 8101

It starts its own local server with the database, the file store and every model key blanked, so nothing
it does reaches production data or costs money, and it stops that server at the end. Each request is
signed in as the role being checked (student, teacher, admin, or guest for signed out) through a header
that only this server reads. It never uses port 8100.

The checks:
  axe       axe-core's WCAG 2.2 A and AA rules on every page, theme and size (rule D1)
  keyboard  laptop, light: a Tab walk where every stop shows a focus ring and isn't covered, and nothing
            clickable the keyboard can't reach (D3)
  targets   phone, light: every control at least 24px, inline text links exempt (D6)
  reflow    320px wide, light: nothing sticks out past the screen unless it sits in a scroller (D7, J2)
  motion    laptop, light, reduced motion: no animation still running (D9)

A screenshot of every page lands in the output folder for the eye pass (A8), with report.json beside it.
Exits 1 when anything fails. Needs Playwright's Chromium (`playwright install chromium`).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AXE = ROOT / "scripts" / "vendor" / "axe-core" / "axe.min.js"
ROLE_HEADER = "x-design-check-role"
PAGES = ["/", "/memory", "/read", "/library", "/generate", "/prep-room/formats", "/prep-room/standards", "/course",
         "/calendar", "/corpus", "/studio", "/john", "/ops", "/read/admin/covers", "/privacy", "/position", "/quiet-standards"]
ROLES = ["student", "teacher", "admin"]
SIZES = {"phone": (390, 844), "tablet": (820, 1180), "laptop": (1366, 768)}
THEMES = ["light", "dark"]
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
# Blanked before the app reads .env, which never overrides a variable that is already set.
BLANK = ["DATABASE_URL", "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_BUCKET_NAME",
         "ANTHROPIC_API_KEY", "DEEPINFRA_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
         "BIBLE_API_KEY", "GOOGLE_BOOKS_API_KEY", "YOUTUBE_API_KEY", "FAL_KEY", "REPLICATE_API_TOKEN",
         "RUNWARE_API_KEY", "WAVESPEED_API_KEY", "BASETEN_API_KEY"]


# ---------------------------------------------------------------- the server half (run as a child process)

def serve(port: int) -> None:
    for name in BLANK:
        os.environ[name] = ""
    sys.path.insert(0, str(ROOT))
    from webapp import auth

    people = {
        "student": {"email": "student@local.test", "name": "Local Student", "role": "student"},
        "teacher": {"email": "teacher@local.test", "name": "Local Teacher", "role": "teacher"},
        "admin": {"email": "admin@local.test", "name": "Local Admin", "role": "teacher"},
    }
    auth.current_user = lambda request: people.get(request.headers.get(ROLE_HEADER, "guest"))
    auth.is_teacher = lambda user: bool(user) and user.get("role") == "teacher"
    auth.is_admin = lambda user: bool(user) and user.get("email") == "admin@local.test"

    import uvicorn

    from webapp.app import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


# ---------------------------------------------------------------- what runs inside each page

FOCUS = """() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
  let ring = (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || (cs.boxShadow && cs.boxShadow !== 'none');
  if (!ring) {   // a search box often shows focus on the box around it: compare focused and unfocused
    const sig = e => { if (!e) return ''; const c = getComputedStyle(e);
      return [c.outlineStyle, c.outlineWidth, c.outlineColor, c.boxShadow, c.borderColor, c.backgroundColor].join('|'); };
    const on = sig(el) + sig(el.parentElement);
    el.blur(); const off = sig(el) + sig(el.parentElement); el.focus();
    ring = on !== off;
  }
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const hit = (cx >= 0 && cy >= 0 && cx < innerWidth && cy < innerHeight) ? document.elementFromPoint(cx, cy) : null;
  const covered = !!hit && hit !== el && !el.contains(hit) && !hit.contains(el);
  const name = (el.getAttribute('aria-label') || el.innerText || el.value || el.title || '').trim().replace(/\\s+/g, ' ').slice(0, 40);
  const path = el.id ? '#' + el.id : el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
  return {path, name, ring, covered: covered ? (hit.id ? '#' + hit.id : hit.tagName.toLowerCase() + '.' + String(hit.className).split(' ')[0]) : ''};
}"""

UNREACHABLE = """() => {
  const native = new Set(['A','BUTTON','INPUT','SELECT','TEXTAREA','SUMMARY','LABEL','OPTION','VIDEO','AUDIO']);
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (native.has(el.tagName) || el.hasAttribute('tabindex') || el.isContentEditable) continue;
    if (el.closest('a,button,label,summary,[tabindex]')) continue;
    if (el.querySelector('a[href],button,input,select,textarea,summary,[tabindex]:not([tabindex="-1"])')) continue;
    const cs = getComputedStyle(el);
    if (cs.cursor !== 'pointer') continue;
    const up = el.parentElement;
    if (up && getComputedStyle(up).cursor === 'pointer' && !native.has(up.tagName) && !up.hasAttribute('tabindex')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || cs.visibility === 'hidden') continue;
    out.push((el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + String(el.className).trim().split(/\\s+/).slice(0, 2).join('.')) +
             ' "' + (el.innerText || '').trim().slice(0, 30) + '"');
  }
  return out;
}"""

TARGETS = """() => {
  const out = [];
  for (const el of document.querySelectorAll('a,button,input,select,textarea,[role=button],[role=tab],[role=link],[tabindex]:not([tabindex="-1"])')) {
    let r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || cs.display === 'none' || el.type === 'hidden') continue;
    if (el.type === 'checkbox' || el.type === 'radio') {   // its label ticks it too, so the label is the target
      const lab = el.closest('label') || (el.id && document.querySelector(`label[for="${el.id}"]`));
      if (lab) { const l = lab.getBoundingClientRect(); r = {width: Math.max(l.right, r.right) - Math.min(l.left, r.left),
                                                         height: Math.max(l.bottom, r.bottom) - Math.min(l.top, r.top)}; }
    }
    if (el.tagName === 'A' && cs.display === 'inline' && (el.closest('p,li,dd,td,blockquote') ||
        el.parentElement.textContent.trim().length > el.textContent.trim().length + 3)) continue;   // a link in a sentence is exempt
    const native = /^(A|BUTTON|INPUT|SELECT|TEXTAREA|SUMMARY)$/.test(el.tagName) || /^(button|link|tab)$/.test(el.getAttribute('role') || '');
    if (!native && cs.cursor !== 'pointer') continue;   // a focusable scroll region, not a target
    if (el.closest('[aria-hidden="true"],[inert]')) continue;
    if (r.width < 24 || r.height < 24) {
      const name = (el.getAttribute('aria-label') || el.innerText || el.title || '').trim().replace(/\\s+/g, ' ').slice(0, 30);
      out.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''} ${Math.round(r.width)}x${Math.round(r.height)} "${name}"`);
    }
  }
  return out;
}"""

# Anything that sticks out past the screen, reported at its outermost element. What sits inside a scroller
# (overflow auto or scroll) is that scroller's business. A clipper (overflow hidden) gives no pass, since the
# reader can't reach what it hides.
REFLOW = """() => {
  const W = document.documentElement.clientWidth, out = [];
  const label = el => el.id ? '#' + el.id : el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
  (function walk(el) {
    for (const c of el.children) {
      const cs = getComputedStyle(c);
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.position === 'fixed' || c.hidden ||
          c.getAttribute('aria-hidden') === 'true' || c.hasAttribute('inert')) continue;
      const r = c.getBoundingClientRect();
      if (r.width <= 2 || r.height <= 2) continue;   // visually hidden text
      if (r.right > W + 1 || r.left < -1) { out.push(`${label(c)} spans ${Math.round(r.left)} to ${Math.round(r.right)}`); continue; }
      if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') continue;
      walk(c);
    }
  })(document.body);
  if (document.documentElement.scrollWidth > W + 1) out.unshift(`the page is ${document.documentElement.scrollWidth}px wide`);
  return out;
}"""

MOTION = """() => document.getAnimations().filter(a => a.playState === 'running').map(a => {
    const t = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming() : {};
    const el = a.effect && a.effect.target;
    return {name: a.animationName || a.transitionProperty || 'animation', ms: t.duration, loops: t.iterations,
            on: el ? (el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]) : ''};
  }).filter(x => x.loops === Infinity || (typeof x.ms === 'number' && x.ms > 50))"""


# ---------------------------------------------------------------- the checking half

def _free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _wait_for(base: str, proc: subprocess.Popen, seconds: int = 90) -> None:
    end = time.time() + seconds
    while time.time() < end:
        if proc.poll() is not None:
            raise SystemExit(f"The local server stopped before it was ready (exit {proc.returncode}). See server.log.")
        try:
            urllib.request.urlopen(base + "/privacy", timeout=3)
            return
        except urllib.error.HTTPError:
            return   # it answered
        except OSError:
            time.sleep(0.5)
    raise SystemExit("The local server didn't answer within 90 seconds.")


def _slug(path: str) -> str:
    return path.strip("/").replace("/", "-") or "chat"


def check(base: str, out: Path, pages, roles, themes, sizes) -> dict:
    from playwright.sync_api import sync_playwright

    axe = AXE.read_text(encoding="utf-8")
    found = {"axe": {}, "keyboard": {}, "targets": {}, "reflow": {}, "motion": {}, "errors": {}}
    closed: dict[str, list[str]] = {}

    def open_page(page, role, path):
        """Load a page. False when this role may not open it (a redirect or a refusal)."""
        res = page.goto(base + path, wait_until="load", timeout=45000)
        landed = page.url.split("?")[0].split("#")[0].replace(base, "") or "/"
        if (res and res.status >= 400) or landed.rstrip("/") != path.rstrip("/"):
            closed.setdefault(role, [])
            if path not in closed[role]:
                closed[role].append(path)
            return False
        page.wait_for_timeout(900)
        return True

    def note(kind, key, items):
        if items:
            found[kind][key] = items

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def context(role, theme, w, h, phone=False, touch=False, motion="no-preference"):
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=theme, reduced_motion=motion,
                                      is_mobile=phone, has_touch=touch, extra_http_headers={ROLE_HEADER: role})
            ctx.add_init_script(f"try{{localStorage.setItem('studybible.theme','{theme}')}}catch(e){{}}")
            return ctx

        for role in roles:
            for theme in themes:
                for size in sizes:
                    w, h = SIZES[size]
                    ctx = context(role, theme, w, h, phone=size == "phone", touch=size != "laptop")
                    page = ctx.new_page()
                    for path in pages:
                        key = f"{role} {path} {theme} {size}"
                        try:
                            if not open_page(page, role, path):
                                continue
                            page.screenshot(path=str(out / f"{role}-{_slug(path)}-{theme}-{size}.png"))
                            page.add_script_tag(content=axe)
                            res = page.evaluate("t => axe.run(document, {runOnly: {type: 'tag', values: t}, resultTypes: ['violations']})", TAGS)
                            note("axe", key, [f"{v['id']} ({v['impact']}, {len(v['nodes'])}): {v['help']} at " +
                                              "; ".join(", ".join(n["target"]) for n in v["nodes"][:3]) for v in res["violations"]])
                            if size == "laptop" and theme == "light":
                                page.add_style_tag(content="*,*::before,*::after{transition:none!important}")
                                page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); }")
                                stops, bad = [], []
                                for _ in range(80):
                                    page.keyboard.press("Tab")
                                    f = page.evaluate(FOCUS)
                                    if f is None or (stops and f["path"] == stops[0]["path"] and f["name"] == stops[0]["name"]):
                                        break
                                    stops.append(f)
                                    if not f["ring"]:
                                        bad.append(f"no focus ring on {f['path']} \"{f['name']}\"")
                                    if f["covered"]:
                                        bad.append(f"{f['path']} \"{f['name']}\" is covered by {f['covered']} when focused")
                                bad += [f"clickable but not reachable by keyboard: {u}" for u in page.evaluate(UNREACHABLE)]
                                note("keyboard", f"{role} {path}", bad)
                            if size == "phone" and theme == "light":
                                note("targets", f"{role} {path}", page.evaluate(TARGETS))
                        except Exception as e:   # one page failing never stops the check
                            found["errors"][key] = str(e)[:300]
                    ctx.close()
            if "light" in themes:
                for kind, args in (("reflow", dict(w=320, h=720, phone=True, touch=True)),
                                   ("motion", dict(w=1366, h=768, motion="reduce"))):
                    ctx = context(role, "light", args.pop("w"), args.pop("h"), **args)
                    page = ctx.new_page()
                    for path in pages:
                        try:
                            if open_page(page, role, path):
                                note(kind, f"{role} {path}", page.evaluate(REFLOW if kind == "reflow" else MOTION))
                        except Exception as e:
                            found["errors"][f"{role} {path} {kind}"] = str(e)[:300]
                    ctx.close()
            print(f"checked as {role}", flush=True)
        browser.close()
    found["not open to this role"] = closed
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--serve", type=int, help=argparse.SUPPRESS)
    ap.add_argument("--port", type=int, default=8101)
    ap.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "exegetica-design-check")
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--roles", default=",".join(ROLES), help="student, teacher, admin, guest")
    ap.add_argument("--themes", default=",".join(THEMES))
    ap.add_argument("--sizes", default=",".join(SIZES))
    a = ap.parse_args()
    if a.serve:
        serve(a.serve)
        return 0
    if a.port == 8100:
        raise SystemExit("Port 8100 is Adam's own server. Pick another.")
    if not _free(a.port):
        raise SystemExit(f"Something is already listening on port {a.port}. Pick another with --port.")
    a.out.mkdir(parents=True, exist_ok=True)
    pages = a.pages.split(",")
    if any(not pg.startswith("/") for pg in pages):
        raise SystemExit(f"Pages start with /: {pages}. (Git Bash rewrites a bare /, so run this from PowerShell.)")
    base = f"http://localhost:{a.port}"   # the app sends 127.0.0.1 to localhost, for Google sign-in
    log = (a.out / "server.log").open("w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve", str(a.port)], cwd=ROOT,
                            stdout=log, stderr=subprocess.STDOUT)
    try:
        _wait_for(base, proc)
        found = check(base, a.out, pages, a.roles.split(","), a.themes.split(","), a.sizes.split(","))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()
    (a.out / "report.json").write_text(json.dumps(found, indent=1, ensure_ascii=False), encoding="utf-8")
    failures = 0
    for kind in ("axe", "keyboard", "targets", "reflow", "motion", "errors"):
        items = found[kind]
        count = sum(len(v) if isinstance(v, list) else 1 for v in items.values())
        failures += count
        print(f"{kind}: {'pass' if not count else f'{count} found'}")
        for key, v in list(items.items())[:12]:
            for line in (v if isinstance(v, list) else [v])[:4]:
                print(f"   {key}: {line}")
    for role, paths in found["not open to this role"].items():
        print(f"not open to {role}: {', '.join(paths)}")
    print(f"screenshots and report.json in {a.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
