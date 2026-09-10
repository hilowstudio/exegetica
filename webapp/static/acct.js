/* Shared account control for the rail.
   Renders the #acct button from /api/me and, on click, opens a small menu that
   shows who's signed in (name, email, role) with an explicit Sign out / Sign in
   action. Also reveals teacher-only rail modules (.teach) for teacher accounts.
   Self-contained: injects its own styles; the only page requirements are a
   rail button with id="acct" and the theme CSS custom properties. */
(function () {
  var acct = document.getElementById("acct");
  if (!acct) return;
  var here = location.pathname + location.search;

  var css = document.createElement("style");
  css.textContent =
    ".acctmenu{position:fixed;z-index:200;min-width:210px;max-width:min(290px,92vw);" +
    "background:var(--surface,#fff);border:1px solid var(--rule-strong,#c9bda6);border-radius:12px;" +
    "box-shadow:0 12px 44px rgba(0,0,0,.30);padding:13px 14px 14px;font-family:var(--sans,system-ui);" +
    "color:var(--ink,#1e2026);display:none}" +
    ".acctmenu.open{display:block}" +
    ".acctmenu .nm{font-weight:600;font-size:14px;line-height:1.3;word-break:break-word}" +
    ".acctmenu .em{font-size:12.5px;color:var(--ink-soft,#54596a);margin-top:2px;word-break:break-word}" +
    ".acctmenu .rl{display:inline-block;font-size:10px;letter-spacing:.09em;text-transform:uppercase;" +
    "color:var(--iron-soft,#5f8698);border:1px solid var(--rule,#ddd3c1);border-radius:999px;padding:2px 8px;margin-top:9px}" +
    ".acctmenu a.act{display:block;text-align:center;margin-top:13px;padding:9px 12px;border-radius:9px;" +
    "background:var(--accent,#c05a64);color:#fff;text-decoration:none;font-weight:600;font-size:13.5px}" +
    ".acctmenu a.act:hover{background:var(--accent-soft,#a84a55)}" +
    ".rail .acct{overflow:hidden}" +
    ".rail .acct img{width:26px;height:26px;border-radius:50%;object-fit:cover;display:block}" +
    ".rail .acct .ini{width:26px;height:26px;border-radius:50%;background:var(--accent,#c05a64);color:#fff;" +
    "display:grid;place-items:center;font-family:var(--sans,system-ui);font-weight:700;font-size:12px}";
  document.head.appendChild(css);

  var menu = document.createElement("div");
  menu.className = "acctmenu";
  menu.setAttribute("role", "menu");
  document.body.appendChild(menu);

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function render(user) {
    if (user) {
      var initial = ((user.name || user.email || "?").trim()[0] || "?").toUpperCase();
      acct.innerHTML = user.picture
        ? '<img src="' + esc(user.picture) + '" alt="" referrerpolicy="no-referrer">'
        : '<span class="ini">' + esc(initial) + "</span>";
      acct.setAttribute("title", (user.name || user.email || "Account") + " — account menu");
      acct.setAttribute("aria-label", "Account menu");
      var role = user.role === "teacher" ? "Teacher" : "Student";
      menu.innerHTML =
        '<div class="nm">' + esc(user.name || "Signed in") + "</div>" +
        (user.email ? '<div class="em">' + esc(user.email) + "</div>" : "") +
        '<div class="rl">' + role + "</div>" +
        '<a class="act" href="/auth/logout?next=' + encodeURIComponent(here) + '">Sign out</a>';
    } else {
      acct.setAttribute("title", "Sign in");
      acct.setAttribute("aria-label", "Sign in");
      menu.innerHTML =
        '<div class="nm">Not signed in</div>' +
        '<div class="em">Sign in to sync your studies across devices.</div>' +
        '<a class="act" href="/auth/login?next=' + encodeURIComponent(here) + '">Sign in with Google</a>';
    }
  }

  function place() {
    var r = acct.getBoundingClientRect(), vw = innerWidth, vh = innerHeight;
    menu.style.visibility = "hidden";
    menu.classList.add("open");
    var mw = menu.offsetWidth, mh = menu.offsetHeight;
    var left = Math.min(Math.max(8, r.left), vw - mw - 8);
    if (r.right < vw * 0.25) left = Math.min(r.right + 8, vw - mw - 8); // left rail: open to the right
    var top = r.top > vh * 0.5 ? r.top - mh - 8 : r.bottom + 8;
    top = Math.min(Math.max(8, top), vh - mh - 8);
    menu.style.left = left + "px";
    menu.style.top = top + "px";
    menu.style.visibility = "";
  }

  var open = false;
  function setOpen(o) {
    open = o;
    if (o) place();
    else menu.classList.remove("open");
    acct.setAttribute("aria-expanded", String(o));
  }
  acct.addEventListener("click", function (e) { e.preventDefault(); setOpen(!open); });
  document.addEventListener("click", function (e) {
    if (open && !menu.contains(e.target) && !acct.contains(e.target)) setOpen(false);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && open) setOpen(false); });
  addEventListener("resize", function () { if (open) place(); });

  fetch("/api/me", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var user = (d && d.user) || null;
      render(user);
      if (user && user.role === "teacher") {
        document.querySelectorAll(".rail .teach").forEach(function (e) { e.style.display = ""; });
      }
    })
    .catch(function () { render(null); });
})();
