/* Global Settings — ONE page-independent Settings panel, loaded on every rail page.

   It owns, identically everywhere:
     • Account      — who's signed in (/api/me), Sign in / Sign out, and revealing the
                      teacher-only rail modules (.teach) — supersedes the old acct.js.
     • Model & Key  — the BYOK provider / model / API key (localStorage 'studybible.byok.v1',
                      already shared by Chat + Generator; other pages just don't read it).
     • Appearance   — theme: System / Light / Dark (localStorage 'studybible.theme').

   The settings are GLOBAL, not per-page: the same store, the same panel, on Chat, Generator,
   Memory, and Library. Host page only needs a rail button id="open-settings"; this injects its
   own styles + modal. Consumers read window.AppSettings and listen for 'appsettings:changed'. */
(function () {
  "use strict";
  var SKEY = "studybible.byok.v1", TKEY = "studybible.theme";

  function load() { try { return JSON.parse(localStorage.getItem(SKEY)) || {}; } catch (e) { return {}; } }
  var S = load();
  S.provider = S.provider || "anthropic";
  S.models = S.models || {};
  S.keys = S.keys || {};
  function save() { try { localStorage.setItem(SKEY, JSON.stringify(S)); } catch (e) {} }

  var CFG = { providers: [], server_anthropic_key: false };
  function pcfg(id) { for (var i = 0; i < (CFG.providers || []).length; i++) if (CFG.providers[i].id === id) return CFG.providers[i]; return {}; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // ---- public API for consumers (Chat / Generator) ----
  var listeners = [];
  function fire() {
    for (var i = 0; i < listeners.length; i++) { try { listeners[i](); } catch (e) {} }
    try { window.dispatchEvent(new CustomEvent("appsettings:changed")); } catch (e) {}
  }
  window.AppSettings = {
    provider: function () { return S.provider; },
    model: function () { return S.models[S.provider] || pcfg(S.provider).default_model || ""; },
    key: function () { return S.keys[S.provider] || ""; },
    needsKey: function () { return !(S.provider === "anthropic" && CFG.server_anthropic_key) && !this.key(); },
    config: function () { return CFG; },
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
    ".set-tabs{display:flex;gap:4px;border-bottom:1px solid var(--rule,#ddd3c1);margin-bottom:16px}" +
    ".set-tab{border:none;background:none;color:var(--ink-soft,#54596a);font:inherit;font-size:13.5px;font-weight:600;" +
      "cursor:pointer;padding:8px 12px;border-bottom:2px solid transparent;margin-bottom:-1px}" +
    ".set-tab:hover{color:var(--ink,#1e2026)}" +
    ".set-tab.on{color:var(--accent,#9f4751);border-bottom-color:var(--accent,#9f4751)}" +
    ".set-pane{display:none}.set-pane.on{display:block}" +
    ".set-fld{display:block;margin-bottom:14px;font-size:13px;font-weight:600;color:var(--ink-soft,#54596a)}" +
    ".set-fld select,.set-fld input{display:block;width:100%;margin-top:6px;padding:9px 11px;font:inherit;font-weight:400;" +
      "color:var(--ink,#1e2026);background:var(--paper,#fff);border:1px solid var(--rule-strong,#c9bda6);border-radius:9px}" +
    ".set-hint{display:block;font-weight:400;font-size:12px;color:var(--ink-faint,#5f636f);margin-top:5px}" +
    ".set-hint a{color:var(--iron,#3d6980)}" +
    ".set-row{display:flex;align-items:center;gap:10px;margin-top:4px}" +
    ".set-ghost{border:1px solid var(--rule-strong,#c9bda6);background:none;color:var(--ink-soft,#54596a);font:inherit;" +
      "font-size:13px;cursor:pointer;padding:8px 12px;border-radius:9px}" +
    ".set-ghost:hover{color:var(--ink,#1e2026);background:var(--surface-2,#eee)}" +
    ".set-saved{font-size:12.5px;color:var(--ok,#3f7a52);opacity:0;transition:opacity .15s ease}" +
    ".set-saved.show{opacity:1}" +
    ".set-seg{display:inline-flex;border:1px solid var(--rule-strong,#c9bda6);border-radius:10px;overflow:hidden;margin-top:8px}" +
    ".set-seg button{border:none;background:var(--paper,#fff);color:var(--ink-soft,#54596a);font:inherit;font-size:13px;" +
      "cursor:pointer;padding:8px 16px;border-right:1px solid var(--rule,#ddd3c1)}" +
    ".set-seg button:last-child{border-right:none}" +
    ".set-seg button.on{background:var(--accent,#9f4751);color:var(--on-accent,#fff)}" +
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
    ".set-x:focus-visible,.set-tab:focus-visible,.set-ghost:focus-visible,.set-danger:focus-visible,.set-seg button:focus-visible," +
      ".set-acct a:focus-visible{outline:2px solid var(--accent,#9f4751);outline-offset:2px}" +
    "@media (pointer:coarse){.set-x{min-width:44px;min-height:44px}.set-tab,.set-ghost,.set-danger,.set-seg button,.set-acct a{min-height:44px}}";
  document.head.appendChild(css);

  // ---- modal DOM ----
  var bg = document.createElement("div");
  bg.className = "set-bg";
  bg.innerHTML =
    '<div class="set-card" role="dialog" aria-modal="true" aria-label="Settings">' +
      '<div class="set-head"><h2>Settings</h2><button class="set-x" type="button" aria-label="Close">×</button></div>' +
      '<div class="set-tabs">' +
        '<button class="set-tab on" type="button" data-p="account">Account</button>' +
        '<button class="set-tab" type="button" data-p="model" id="set-tab-model" style="display:none">Model &amp; Key</button>' +
        '<button class="set-tab" type="button" data-p="appearance">Appearance</button>' +
      '</div>' +
      '<div class="set-pane on" id="setp-account"><div class="set-acct" id="set-acct"><div class="acct-em">Loading…</div></div>' +
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
      '</div>' +
      '<div class="set-pane" id="setp-model">' +
        '<p class="set-hint" style="margin:0 0 14px">Bring your own key. It is stored only in this browser and sent to the app only to make your request — the server never saves it. Chat runs on Exegetica’s own model, so only the Prep Room uses it.</p>' +
        '<label class="set-fld">Provider<select id="set-prov"></select></label>' +
        '<label class="set-fld">Model<input id="set-model" type="text" spellcheck="false" autocomplete="off"><span class="set-hint" id="set-modelhint"></span></label>' +
        '<label class="set-fld">API key<input id="set-key" type="password" spellcheck="false" autocomplete="off" placeholder="Paste your key"><span class="set-hint" id="set-keyhint"></span></label>' +
        '<div class="set-row"><button class="set-ghost" id="set-forget" type="button">Forget key</button><span class="spacer" style="flex:1"></span><span class="set-saved" id="set-saved">Saved ✓</span></div>' +
      '</div>' +
      '<div class="set-pane" id="setp-appearance">' +
        '<label class="set-fld">Theme<span class="set-hint">Applies to this browser.</span>' +
          '<span class="set-seg" id="set-theme"><button type="button" data-t="system">System</button><button type="button" data-t="light">Light</button><button type="button" data-t="dark">Dark</button></span>' +
        '</label>' +
      '</div>' +
    '</div>';
  document.body.appendChild(bg);
  function $(id) { return bg.querySelector(id); }

  // ---- open / close + tabs ----
  function openModal() { syncModel(); syncTheme(); renderAccount(); bg.classList.add("open"); }
  function closeModal() { bg.classList.remove("open"); }
  $(".set-x").onclick = closeModal;
  bg.addEventListener("click", function (e) { if (e.target === bg) closeModal(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && bg.classList.contains("open")) closeModal(); });
  var tabs = bg.querySelectorAll(".set-tab");
  for (var i = 0; i < tabs.length; i++) tabs[i].onclick = function () {
    var p = this.getAttribute("data-p");
    for (var j = 0; j < tabs.length; j++) tabs[j].classList.toggle("on", tabs[j] === this);
    var panes = bg.querySelectorAll(".set-pane");
    for (var k = 0; k < panes.length; k++) panes[k].classList.toggle("on", panes[k].id === "setp-" + p);
  }.bind(tabs[i]);

  // ---- Model & Key ----
  var sel = $("#set-prov"), inModel = $("#set-model"), inKey = $("#set-key"),
      mHint = $("#set-modelhint"), kHint = $("#set-keyhint"), saved = $("#set-saved");
  function populateProviders() {
    sel.innerHTML = "";
    (CFG.providers || []).forEach(function (p) {
      var o = document.createElement("option"); o.value = p.id; o.textContent = p.label; sel.appendChild(o);
    });
    sel.value = S.provider;
  }
  function syncModel() {
    sel.value = S.provider;
    var p = pcfg(S.provider);
    inModel.value = S.models[S.provider] || p.default_model || "";
    inModel.placeholder = p.default_model || "";
    inKey.value = S.keys[S.provider] || "";
    mHint.textContent = "Default: " + (p.default_model || "none") + (p.fallback_model ? " · auto-falls back to " + p.fallback_model + " if unavailable" : "") + " · editable.";
    if (S.provider === "anthropic" && CFG.server_anthropic_key) kHint.textContent = "Optional — leave blank to use the app's key, or paste your own.";
    else kHint.innerHTML = "Required. Get one at <a href='" + (p.key_url || "#") + "' target='_blank' rel='noopener'>" + (p.key_url || "the provider") + "</a>.";
  }
  var savedT;
  function flashSaved() { saved.classList.add("show"); clearTimeout(savedT); savedT = setTimeout(function () { saved.classList.remove("show"); }, 1400); }
  sel.addEventListener("change", function () { S.provider = sel.value; save(); syncModel(); fire(); flashSaved(); });
  inModel.addEventListener("change", function () { S.models[S.provider] = inModel.value.trim(); save(); fire(); flashSaved(); });
  inKey.addEventListener("change", function () { var k = inKey.value.trim(); if (k) S.keys[S.provider] = k; else delete S.keys[S.provider]; save(); fire(); flashSaved(); });
  $("#set-forget").onclick = function () { delete S.keys[S.provider]; inKey.value = ""; save(); fire(); flashSaved(); };

  // ---- Appearance (theme) ----
  function curTheme() { return document.documentElement.getAttribute("data-theme") || "system"; }
  function applyTheme(v) {
    if (v === "system") { document.documentElement.removeAttribute("data-theme"); try { localStorage.removeItem(TKEY); } catch (e) {} }
    else { document.documentElement.setAttribute("data-theme", v); try { localStorage.setItem(TKEY, v); } catch (e) {} }
  }
  function syncTheme() { var t = curTheme(); bg.querySelectorAll("#set-theme button").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-t") === t); }); }
  bg.querySelectorAll("#set-theme button").forEach(function (b) { b.onclick = function () { applyTheme(b.getAttribute("data-t")); syncTheme(); }; });

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
        // Teacher-only: the rail's teacher modules and bringing a model or key (the server
        // ignores both for students).
        if (u.role === "teacher") {
          document.querySelectorAll(".rail .teach").forEach(function (e) { e.style.display = ""; });
          $("#set-tab-model").style.display = "";
        }
        // Admin-only modules (Media Studio). The server checks again on every request.
        if (d.admin) {
          document.querySelectorAll(".rail .admin").forEach(function (e) { e.style.display = ""; });
        }
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
  fetch("/api/config", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (c) {
    CFG = c || CFG; populateProviders(); syncModel(); fire();          // fire so Chat/Generator refresh once config is known
  }).catch(function () {});
  renderAccount();                                                      // reveal .teach on load (was acct.js's job)
})();
