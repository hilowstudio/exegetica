/* The Settings panel, part of the shared layout (templates/base.html): the rail's profile icon
   (id="open-settings") opens it on every page. It holds the Account (who's signed in, from /api/me,
   with Sign in and Sign out) and Your data (download, delete the account, clear this browser).
   The rail's places and the theme button are the server's and shell.js's.

   Bringing your own provider, model or key is off for now (policy.BYOK on the server), so
   AppSettings answers with the server's defaults. The panel injects its own styles and modal. */
(function () {
  "use strict";

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // ---- public API for consumers (the Prep Room): the server's own model, no key ----
  var listeners = [];
  window.AppSettings = {
    provider: function () { return "anthropic"; },
    model: function () { return ""; },
    key: function () { return ""; },
    needsKey: function () { return false; },
    onChange: function (cb) { listeners.push(cb); },
    open: function () { openModal(); },
    close: function () { closeModal(); }
  };

  // ---- styles (self-contained; uses each page's theme tokens) ----
  var css = document.createElement("style");
  css.textContent =
    ".set-bg{position:fixed;inset:0;z-index:300;background:rgba(0,0,0,.42);display:none;align-items:center;justify-content:center;padding:20px}" +
    ".set-bg.open{display:flex}" +
    ".set-card{width:min(560px,96vw);max-height:92vh;overflow:auto;background:var(--surface,#fff);color:var(--ink,#1e2026);" +
      "border:1px solid var(--rule-strong,#c9bda6);border-radius:14px;box-shadow:0 22px 70px rgba(0,0,0,.34);" +
      "font-family:var(--sans,system-ui);padding:20px 22px 22px}" +
    ".set-head{display:flex;align-items:center;gap:10px;margin-bottom:14px}" +
    ".set-head h2{margin:0;font-size:19px;font-family:var(--serif,Georgia,serif);flex:1}" +
    ".set-x{border:none;background:none;color:var(--ink-soft,#54596a);font-size:22px;line-height:1;cursor:pointer;padding:2px 6px;border-radius:8px}" +
    ".set-x:hover{background:var(--surface-2,#eee);color:var(--ink,#1e2026)}" +
    ".set-hint{display:block;font-weight:400;font-size:12px;color:var(--ink-faint,#5f636f);margin-top:5px}" +
    ".set-row{display:flex;align-items:center;gap:10px;margin-top:4px}" +
    ".set-ghost{border:1px solid var(--rule-strong,#c9bda6);background:none;color:var(--ink-soft,#54596a);font:inherit;" +
      "font-size:13px;cursor:pointer;padding:8px 12px;border-radius:9px}" +
    ".set-ghost:hover{color:var(--ink,#1e2026);background:var(--surface-2,#eee)}" +
    ".set-acct{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 14px;border:1px solid var(--rule,#ddd3c1);" +
      "border-radius:10px;background:var(--paper,#fff)}" +
    ".set-acct .acct-who{flex:1;min-width:150px}" +
    ".set-acct .acct-nm{font-weight:600;font-size:14px;line-height:1.3;color:var(--ink,#1e2026)}" +
    ".set-acct .acct-em{font-size:12.5px;color:var(--ink-soft,#54596a);margin-top:2px;word-break:break-word}" +
    ".set-acct .acct-rl{display:inline-block;font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--iron-soft,#5f8698);" +
      "border:1px solid var(--rule,#ddd3c1);border-radius:999px;padding:2px 8px;margin-top:8px}" +
    ".set-acct a{flex-shrink:0;text-decoration:none;padding:9px 14px;border-radius:9px;font-size:13.5px;font-weight:600}" +
    ".set-acct a.act-in{background:var(--accent,#9f4751);color:var(--on-accent,#fff)}" +
    ".set-acct a.act-out{border:1px solid var(--rule-strong,#c9bda6);color:var(--ink-soft,#54596a)}" +
    ".set-data{margin-top:18px;border-top:1px solid var(--rule,#ddd3c1);padding-top:14px}" +
    ".set-data h3{margin:0 0 4px;font-size:14px;color:var(--ink,#1e2026)}" +
    ".set-data p{margin:0 0 10px;font-size:12.5px;line-height:1.5;color:var(--ink-soft,#54596a)}" +
    ".set-data p a{color:var(--iron,#3d6980)}" +
    ".set-data .set-row{flex-wrap:wrap}" +
    ".set-data a.set-ghost{text-decoration:none;display:inline-flex;align-items:center}" +
    ".set-del{margin-top:10px;padding:12px;border:1px solid var(--rule-strong,#c9bda6);border-radius:10px;background:var(--paper,#fff)}" +
    ".set-del input{width:100%;margin:6px 0 8px;padding:8px 10px;font:inherit;color:var(--ink,#1e2026);background:var(--surface,#fff);" +
      "border:1px solid var(--rule-strong,#c9bda6);border-radius:8px}" +
    ".set-danger{border:0;background:var(--err,#a34919);color:var(--on-accent,#fff);font:inherit;font-size:13px;font-weight:600;" +
      "cursor:pointer;padding:8px 14px;border-radius:9px}" +
    ".set-danger:disabled{opacity:.45;cursor:default}" +
    ".set-msg{font-size:12.5px;color:var(--ink-soft,#54596a);margin-top:8px}" +
    ".set-x:focus-visible,.set-ghost:focus-visible,.set-danger:focus-visible," +
      ".set-acct a:focus-visible{outline:2px solid var(--accent,#9f4751);outline-offset:2px}" +
    "@media (pointer:coarse){.set-x{min-width:44px;min-height:44px}.set-ghost,.set-danger,.set-acct a{min-height:44px}}";
  document.head.appendChild(css);

  // ---- modal DOM ----
  var bg = document.createElement("div");
  bg.className = "set-bg";
  bg.innerHTML =
    '<div class="set-card" role="dialog" aria-modal="true" aria-label="Settings">' +
      '<div class="set-head"><h2>Settings</h2><button class="set-x" type="button" aria-label="Close">×</button></div>' +
      '<div class="set-acct" id="set-acct"><div class="acct-em">Loading…</div></div>' +
      '<div class="set-data">' +
        '<h3>Your data</h3>' +
        '<p>What Exegetica keeps, and who can read it, is on the <a href="/privacy">privacy page</a>.</p>' +
        '<div class="set-row" id="set-mine" hidden>' +
          '<a class="set-ghost" href="/api/account/export" download>Download my data</a>' +
          '<button class="set-ghost" id="set-del-open" type="button">Delete my account</button>' +
        '</div>' +
        '<div class="set-del" id="set-del" hidden>' +
          '<p>This deletes your account and everything saved in it: studies, verses, reading places, and any library shelf. It cannot be undone. Type <b>delete</b> to confirm.</p>' +
          '<label for="set-del-in" class="set-hint" style="margin:0">Confirmation</label>' +
          '<input id="set-del-in" type="text" autocomplete="off" spellcheck="false">' +
          '<div class="set-row"><button class="set-danger" id="set-del-go" type="button" disabled>Delete my account</button>' +
          '<button class="set-ghost" id="set-del-cancel" type="button">Cancel</button></div>' +
        '</div>' +
        '<div class="set-row" style="margin-top:10px"><button class="set-ghost" id="set-clear" type="button">Clear this browser</button></div>' +
        '<p class="set-msg" id="set-data-msg" role="status" aria-live="polite"></p>' +
      '</div>' +
    '</div>';
  document.body.appendChild(bg);
  function $(id) { return bg.querySelector(id); }

  // ---- open / close ----
  function openModal() { renderAccount(); bg.classList.add("open"); }
  function closeModal() { bg.classList.remove("open"); }
  $(".set-x").onclick = closeModal;
  bg.addEventListener("click", function (e) { if (e.target === bg) closeModal(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && bg.classList.contains("open")) closeModal(); });

  // ---- Account ----
  function renderAccount() {
    var box = $("#set-acct"), here = location.pathname + location.search;
    fetch("/api/me", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (d) {
      var u = d && d.user;
      if (u) {
        box.innerHTML = '<div class="acct-who"><div class="acct-nm">' + esc(u.name || "Signed in") + "</div>" +
          (u.email ? '<div class="acct-em">' + esc(u.email) + "</div>" : "") +
          '<span class="acct-rl">' + (u.role === "teacher" ? "Teacher" : "Student") + "</span></div>" +
          '<a class="act-out" href="/auth/logout?next=' + encodeURIComponent(here) + '">Sign out</a>';
        $("#set-mine").hidden = false;
      } else {
        $("#set-mine").hidden = true;
        $("#set-del").hidden = true;
        box.innerHTML = '<div class="acct-who"><div class="acct-nm">Not signed in</div>' +
          '<div class="acct-em">Sign in with your school Google account to use chat and keep your studies.</div></div>' +
          '<a class="act-in" href="/auth/login?next=' + encodeURIComponent(here) + '">Sign in with Google</a>';
      }
    }).catch(function () { box.innerHTML = '<div class="acct-em">Account unavailable right now.</div>'; });
  }

  // ---- Your data: Delete my account, Clear this browser ----
  var delBox = $("#set-del"), delIn = $("#set-del-in"), delGo = $("#set-del-go"), dataMsg = $("#set-data-msg");
  $("#set-del-open").onclick = function () { delBox.hidden = false; delIn.value = ""; delGo.disabled = true; delIn.focus(); };
  $("#set-del-cancel").onclick = function () { delBox.hidden = true; };
  delIn.addEventListener("input", function () { delGo.disabled = delIn.value.trim().toLowerCase() !== "delete"; });
  delGo.onclick = function () {
    delGo.disabled = true; dataMsg.textContent = "Deleting…";
    fetch("/api/account/delete", { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirm: "delete" }) })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (x) {
        if (!x.ok) { dataMsg.textContent = (x.d && x.d.error) || "The account could not be deleted."; delGo.disabled = false; return; }
        clearBrowser();
        dataMsg.textContent = "Your account is deleted.";
        setTimeout(function () { location.href = "/"; }, 1200);
      })
      .catch(function () { dataMsg.textContent = "The account could not be deleted. Try again later."; delGo.disabled = false; });
  };
  // Everything Exegetica keeps in this browser uses one of these prefixes.
  function clearBrowser() {
    [localStorage, sessionStorage].forEach(function (store) {
      try {
        Object.keys(store).forEach(function (k) { if (/^(studybible\.|exeg-)/.test(k)) store.removeItem(k); });
      } catch (e) {}
    });
  }
  $("#set-clear").onclick = function () {
    if (!confirm("Remove everything Exegetica keeps in this browser: settings, any API key, and anything saved before sign-in? Your account is not affected.")) return;
    clearBrowser();
    dataMsg.textContent = "This browser is cleared.";
    setTimeout(function () { location.reload(); }, 900);
  };

  // ---- boot ----
  var gear = document.getElementById("open-settings");
  if (gear) gear.onclick = openModal;
  renderAccount();
})();
