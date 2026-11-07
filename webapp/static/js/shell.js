/* The shared shell every page gets from templates/base.html: the rail's collapse handle, the
   light/dark theme button, the Need help now? window, the tool chips, and a reply's status line. A
   page script reaches them through window.Shell: Shell.esc(text), Shell.openHelp(resources, lead),
   Shell.closeHelp(), Shell.chips(box), and Shell.status(container). */
(function () {
  "use strict";
  var root = document.documentElement, RKEY = "exeg-rail", TKEY = "studybible.theme";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function $(id) { return document.getElementById(id); }

  // ---- the rail: collapse to the handle at the left edge, and back (remembered in this browser).
  // A page that measures its own layout (the Reading Room's pages) hears a resize once the rail has moved. ----
  var collapse = $("rail-collapse"), handle = $("rail-handle");
  function setRail(closed, focus) {
    if (closed) root.setAttribute("data-rail", "closed"); else root.removeAttribute("data-rail");
    try { localStorage.setItem(RKEY, closed ? "closed" : "open"); } catch (e) {}
    if (handle) handle.setAttribute("aria-expanded", String(!closed));
    if (collapse) collapse.setAttribute("aria-expanded", String(!closed));
    if (focus) {
      var to = closed ? handle : collapse; if (to) to.focus();
      setTimeout(function () { window.dispatchEvent(new Event("resize")); }, 220);
    }
  }
  if (collapse) collapse.onclick = function () { setRail(true, true); };
  if (handle) handle.onclick = function () { setRail(false, true); };
  setRail(root.getAttribute("data-rail") === "closed", false);

  // ---- the theme button: switches light and dark, starting from the system's choice, and tells the
  // page with a "shell:theme" event on document (detail: "light" or "dark") ----
  var SUN = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2.8v2.2M12 19v2.2' +
            'M2.8 12h2.2M19 12h2.2M5.5 5.5l1.6 1.6M16.9 16.9l1.6 1.6M5.5 18.5l1.6-1.6M16.9 7.1l1.6-1.6"/></svg>';
  var MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.5 14.6A8 8 0 0 1 9.4 4.5a8 8 0 1 0 10.1 10.1z"/></svg>';
  var dark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  var themeBtn = $("theme-toggle");
  function shownTheme() { return root.getAttribute("data-theme") || (dark && dark.matches ? "dark" : "light"); }
  function syncTheme() {
    if (!themeBtn) return;
    var to = shownTheme() === "dark" ? "light" : "dark";
    themeBtn.innerHTML = to === "dark" ? MOON : SUN;
    themeBtn.title = to === "dark" ? "Dark theme" : "Light theme";
    themeBtn.setAttribute("aria-label", "Switch to the " + to + " theme");
  }
  if (themeBtn) themeBtn.onclick = function () {
    var to = shownTheme() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", to);
    try { localStorage.setItem(TKEY, to); } catch (e) {}
    syncTheme();
    document.dispatchEvent(new CustomEvent("shell:theme", { detail: to }));
  };
  if (dark && dark.addEventListener) dark.addEventListener("change", syncTheme);
  syncTheme();

  // ---- the Need help now? window: verified resources the server put in the page ----
  var helpBg = $("help-bg"), helpList = $("help-list"), helpLead = $("help-lead"), opener = null;
  var RESOURCES = [];
  try { RESOURCES = JSON.parse($("help-data").textContent) || []; } catch (e) {}
  var LEAD = "If you're going through something hard, you're not alone. These people can help — any time, free and " +
             "private. You can also tell a parent, pastor, teacher, or friend you trust.";
  function render(list) {
    helpList.innerHTML = (list || []).map(function (r) {
      var u = r.url ? ' &middot; <a href="' + esc(r.url) + '" target="_blank" rel="noopener">' +
                      esc(r.url.replace(/^https?:\/\//, "")) + "</a>" : "";
      var note = r.note ? '<div class="hnote">' + esc(r.note) + "</div>" : "";
      return '<div class="help-item"><div class="hn">' + esc(r.name) + '</div><div class="hc">' + esc(r.contact) + u +
             "</div>" + note + "</div>";
    }).join("");
  }
  function openHelp(list, lead) {
    if (!helpBg) return;
    helpLead.textContent = lead || LEAD;
    render(list && list.length ? list : RESOURCES);
    opener = document.activeElement;
    helpBg.classList.add("open");
    $("help-close").focus();
  }
  function closeHelp() {
    if (!helpBg || !helpBg.classList.contains("open")) return;
    helpBg.classList.remove("open");
    if (opener && opener.focus) opener.focus();
    opener = null;
  }
  if (helpBg) {
    $("help-close").onclick = closeHelp;
    helpBg.addEventListener("click", function (e) { if (e.target === helpBg) closeHelp(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeHelp(); });
  }
  var helpBtn = $("help-link");
  if (helpBtn) helpBtn.onclick = function (e) { e.preventDefault(); openHelp(); };

  // ---- tool chips: one chip per tool in a box, with a count when the tool ran more than once ----
  // Shell.chips(box) gives start(name) and finish(name, error). A chip pulses while any call of its tool
  // is running, then shows how the last call to finish went.
  function chips(box) {
    var byName = {};
    function chip(name) {
      if (!byName[name]) {
        var el = document.createElement("div");
        el.className = "tool-chip running";
        el.innerHTML = "<span class='ic'></span><span class='nm'></span><span class='n' hidden></span>";
        el.querySelector(".nm").textContent = name;
        box.appendChild(el);
        byName[name] = { el: el, calls: 0, open: 0 };
      }
      return byName[name];
    }
    return {
      start: function (name) {
        var c = chip(name), n = c.el.querySelector(".n");
        c.calls++; c.open++;
        c.el.className = "tool-chip running";
        n.hidden = c.calls < 2; n.textContent = c.calls; n.title = "Ran " + c.calls + " times";
      },
      finish: function (name, error) {
        var c = byName[name];
        if (!c) return;
        c.open = Math.max(0, c.open - 1);
        if (!c.open) c.el.className = "tool-chip " + (error ? "error" : "done");
      }
    };
  }

  // ---- the status line: what a reply is doing while nothing shows yet ----
  // Shell.status(container) adds the line and gives set(stage, words) and done(reveal). The server names
  // the stage (webapp/providers.py), so the line changes only when the work does. done() takes the line
  // away, and fades `reveal` in if the line was showing, so an answer held until it was finished arrives
  // smoothly. Only the stage is announced to a screen reader, never each new word count.
  var STAGES = {
    studying: "Studying the question",
    reading: "Reading what the library returned",
    looking: "Looking it up in the library",
    writing: "Writing the answer",
    checking: "Checking the answer against the library"
  };
  function status(container) {
    var el = document.createElement("div");
    el.className = "shell-status";
    el.hidden = true;
    el.innerHTML = "<span><span class='st' role='status'></span><span class='ct' aria-hidden='true'></span></span>";
    container.appendChild(el);
    var st = el.querySelector(".st"), ct = el.querySelector(".ct");
    return {
      set: function (stage, words) {
        if (!STAGES[stage]) return;
        if (st.textContent !== STAGES[stage]) st.textContent = STAGES[stage];
        ct.textContent = words ? ", " + words + " words so far" : "";
        el.hidden = false;
      },
      done: function (reveal) {
        if (el.hidden) return;
        el.hidden = true;
        if (reveal) {
          reveal.classList.remove("shell-reveal");
          void reveal.offsetWidth;   // restart the fade if it ran before
          reveal.classList.add("shell-reveal");
        }
      }
    };
  }

  window.Shell = { esc: esc, openHelp: openHelp, closeHelp: closeHelp, chips: chips, status: status };
})();
