/* The shared shell every page gets from templates/base.html: the rail's collapse handle, the
   light/dark theme button, the Need help now? window, the tool chips, a reply's status line, the page's
   question dialog and its toast. A page script reaches them through window.Shell: Shell.esc(text),
   Shell.openHelp(resources, lead), Shell.closeHelp(), Shell.chips(box), Shell.status(container),
   Shell.ask(question), Shell.toast(text, {undo}) and Shell.tagLanguages(node), which marks Greek and Hebrew. */
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

  // ---- a bar that stays put (.shell-stick) frosts over only while the page scrolls under it: stuck, its
  // sticky top (at least 1px above the scroller's edge) clips it, so only part of it shows ----
  if (window.IntersectionObserver) {
    var sticks = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.target.classList.toggle("stuck", e.intersectionRatio > 0 && e.intersectionRatio < 1); });
    }, { threshold: [1] });
    Array.prototype.forEach.call(document.querySelectorAll(".shell-stick"), function (el) { sticks.observe(el); });
  }

  // ---- the Need help now? window: verified resources the server put in the page ----
  var helpBg = $("help-bg"), helpList = $("help-list"), helpLead = $("help-lead"), opener = null;
  var RESOURCES = [];
  try { RESOURCES = JSON.parse($("help-data").textContent) || []; } catch (e) {}
  var LEAD = "If you're going through something hard, you're not alone. These people can help any time. It's free and " +
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

  // ---- a question in the page's own dialog, in place of the browser's confirm() and prompt() ----
  // Shell.ask({title, body, ok, cancel, danger, input, validate}) gives a promise of true or false. With
  // `input` ({label, value, max}) it gives the text typed, trimmed, or null when cancelled, and `validate`
  // (text => error or "") keeps the dialog open until the text is right. A native <dialog>: focus moves
  // in, Escape cancels, and focus goes back to what opened it. A destructive question starts on Cancel.
  var dlg = null, dlgDone = null;
  function ask(o) {
    o = o || {};
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.className = "shell-dlg";
      dlg.setAttribute("aria-labelledby", "shell-dlg-title");
      dlg.innerHTML = '<form method="dialog"><h2 id="shell-dlg-title"></h2><p class="sd-body"></p>' +
        '<label class="sd-field" hidden><span></span><input type="text" autocomplete="off"></label>' +
        '<p class="sd-error" role="alert" hidden></p><div class="sd-actions">' +
        '<button type="button" class="sd-cancel"></button><button type="submit" class="sd-ok" value="ok"></button></div></form>';
      document.body.appendChild(dlg);
      dlg.addEventListener("click", function (e) { if (e.target === dlg) dlg.close("cancel"); });   // the backdrop
      dlg.querySelector(".sd-cancel").onclick = function () { dlg.close("cancel"); };
      dlg.addEventListener("close", function () { if (dlgDone) dlgDone(); });
    }
    if (dlg.open) dlg.close("cancel");   // a new question replaces one still open
    var form = dlg.querySelector("form"), field = dlg.querySelector(".sd-field"), input = field.querySelector("input");
    var body = dlg.querySelector(".sd-body"), err = dlg.querySelector(".sd-error");
    var okBtn = dlg.querySelector(".sd-ok"), cancelBtn = dlg.querySelector(".sd-cancel");
    dlg.querySelector("h2").textContent = o.title || "";
    body.textContent = o.body || ""; body.hidden = !o.body;
    okBtn.textContent = o.ok || "OK"; cancelBtn.textContent = o.cancel || "Cancel";
    okBtn.classList.toggle("danger", !!o.danger);
    field.hidden = !o.input; err.hidden = true; err.textContent = "";
    if (o.input) {
      field.querySelector("span").textContent = o.input.label || "";
      input.value = o.input.value || "";
      if (o.input.max) input.maxLength = o.input.max; else input.removeAttribute("maxlength");
    }
    form.onsubmit = function (e) {
      if (!o.input || !o.validate) return;
      var problem = o.validate(input.value.trim());
      if (problem) { e.preventDefault(); err.textContent = problem; err.hidden = false; input.focus(); }
    };
    var opener = document.activeElement;
    dlg.returnValue = "";
    return new Promise(function (resolve) {
      dlgDone = function () {
        dlgDone = null;
        var yes = dlg.returnValue === "ok";
        resolve(o.input ? (yes ? input.value.trim() : null) : yes);
        if (opener && opener.isConnected && opener.focus) opener.focus();
      };
      dlg.showModal();
      if (o.input) { input.focus(); input.select(); } else (o.danger ? cancelBtn : okBtn).focus();
    });
  }

  // ---- a toast: one line that says what happened, with Undo when the action can be taken back ----
  // Shell.toast(text, {undo, ms}). One at a time. A screen reader hears the words through a live region
  // that is on the page from the start, and the Undo button is a real button. A page marks what the toast
  // must not cover with data-toast-above (chat's composer), and the toast sits just above it.
  var toastEl = document.createElement("div"), toastSay = document.createElement("div"), toastTimer = null;
  toastEl.className = "shell-toast"; toastEl.hidden = true;
  toastSay.className = "shell-sr"; toastSay.setAttribute("role", "status");
  document.body.appendChild(toastSay); document.body.appendChild(toastEl);
  function hideToast() { clearTimeout(toastTimer); toastEl.hidden = true; toastEl.innerHTML = ""; }
  // Shell.say(text): a screen reader hears it through the same live region, with nothing shown. For a note
  // a page shows in a place that may be out of reach for now (Scripture Memory's page behind its verse list).
  function say(text) { toastSay.textContent = ""; setTimeout(function () { toastSay.textContent = text; }, 50); }
  function toast(text, o) {
    o = o || {};
    hideToast();
    var words = document.createElement("span");
    words.textContent = text;
    toastEl.appendChild(words);
    if (o.undo) {
      var b = document.createElement("button");
      b.type = "button"; b.textContent = "Undo";
      b.onclick = function () { hideToast(); o.undo(); };
      toastEl.appendChild(b);
    }
    toastSay.textContent = "";
    setTimeout(function () { toastSay.textContent = text + (o.undo ? ". Undo is available." : ""); }, 50);
    var above = document.querySelector("[data-toast-above]"), r = above && above.getBoundingClientRect();
    toastEl.style.bottom = r && r.height ? Math.round(window.innerHeight - r.top + 12) + "px" : "";   // clear of chat's composer
    toastEl.hidden = false;
    toastTimer = setTimeout(hideToast, o.ms || (o.undo ? 6000 : 3000));
  }

  // ---- Greek and Hebrew: each run is tagged with its language, so it takes the faces in fonts/orig.css and
  // a screen reader can switch voices. Hebrew also runs right to left, isolated inside an English line.
  // Shell.tagLanguages(node) tags what is there now. The page is tagged once, then whatever is added to
  // it (a streaming reply, a book's chapter, a Prep Room document) as it arrives. Code and form fields are
  // left alone, and a run that is already tagged is never tagged again. ----
  var GREEK = "\u0370-\u03FF\u1F00-\u1FFF", HEBREW = "\u0590-\u05FF\uFB1D-\uFB4F";
  var RUN = new RegExp("([" + GREEK + "](?:[" + GREEK + "\u0300-\u036F\u00B7\u2019']|\\s(?=[" + GREEK + "]))*)|" +
                       "([" + HEBREW + "](?:[" + HEBREW + "]|\\s(?=[" + HEBREW + "]))*)", "g");
  var ANY = new RegExp("[" + GREEK + HEBREW + "]");
  var SKIP = "script,style,textarea,input,select,code,pre,svg,math,[contenteditable],.orig";
  function tagLanguages(node) {
    if (!node || !document.createTreeWalker) return;
    var walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
      acceptNode: function (t) {
        if (!ANY.test(t.nodeValue)) return NodeFilter.FILTER_REJECT;
        var p = t.parentElement;
        return p && !p.closest(SKIP) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var texts = [];
    while (walker.nextNode()) texts.push(walker.currentNode);
    texts.forEach(function (t) {
      var s = t.nodeValue, frag = document.createDocumentFragment(), last = 0, m;
      RUN.lastIndex = 0;
      while ((m = RUN.exec(s))) {
        if (m.index > last) frag.appendChild(document.createTextNode(s.slice(last, m.index)));
        var span = document.createElement("span");
        span.className = "orig";
        span.lang = m[1] ? "grc" : "he";
        if (m[2]) span.dir = "rtl";
        span.textContent = m[0];
        frag.appendChild(span);
        last = m.index + m[0].length;
      }
      if (last < s.length) frag.appendChild(document.createTextNode(s.slice(last)));
      t.parentNode.replaceChild(frag, t);
    });
  }
  tagLanguages(document.body);
  if (window.MutationObserver) {
    var pending = [], queued = false;
    var watcher = new MutationObserver(function (records) {
      records.forEach(function (r) {
        if (r.type === "characterData") pending.push(r.target.parentNode);
        else for (var i = 0; i < r.addedNodes.length; i++) pending.push(r.addedNodes[i]);
      });
      if (queued) return;
      queued = true;
      Promise.resolve().then(function () {
        queued = false;
        var batch = pending; pending = [];
        watcher.disconnect();   // tagging changes the page too, so stop listening while it runs
        batch.forEach(function (n) {
          if (n && n.isConnected) { var el = n.nodeType === 3 ? n.parentNode : n; tagLanguages(el); fitTables(el); }
        });
        watcher.observe(document.body, { childList: true, subtree: true, characterData: true });
      });
    });
    watcher.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  // ---- a table from Markdown (rule J2): Shell.table(head, rows, inline) gives the HTML both chat and the Prep
  // Room render.
  //  - A column whose every filled cell is a number, a reference or a range ("12", "1:14", "3:16-18") is
  //    right-aligned in tabular figures.
  //  - A table of five columns or more becomes a list of labelled rows on a phone (.stack, shell.css). It keeps
  //    its table roles, since changing how cells display can hide them from a screen reader.
  //  - Otherwise a wide table scrolls inside its own labelled region the keyboard can reach. A soft shade at
  //    an edge shows there is more to see (fitTables). ----
  var NUMERIC = /^[\s\d.,:;%$+\u2013\u2014\-]+$/;
  var REF = /\d+(?::\d+)?[\u2013\-]\d+(?::\d+)?|\d+:\d+/g;   // 1:14, 1:4-9, 12-15
  function table(head, rows, inline) {
    var num = head.map(function (_, c) {
      var filled = rows.map(function (r) { return (r[c] || "").trim(); }).filter(Boolean);
      return filled.length > 0 && filled.every(function (v) { return NUMERIC.test(v) && /\d/.test(v); });
    });
    var plain = head.map(function (h) { return h.replace(/[*_`]/g, "").trim(); });
    var stack = head.length >= 5;
    var role = function (r) { return stack ? " role='" + r + "'" : ""; };
    var cls = function (c) { return num[c] ? " class='num'" : ""; };
    // a reference or range ("4:46-54", "12-15") never breaks across lines, and a list of them wraps between
  // items. Text only, never inside a tag.
    var cell = function (s) {
      return inline(s).split(/(<[^>]*>)/).map(function (part) {
        return part.charAt(0) === "<" ? part : part.replace(REF, "<span class='nobr'>$&</span>");
      }).join("");
    };
    var t = "<div class='tablebox'><div class='tablewrap' role='region' tabindex='0' aria-label=\"" +
      esc("Table: " + plain.filter(Boolean).join(", ")) + "\"><table" + (stack ? " class='stack' role='table'" : "") + ">" +
      "<thead" + role("rowgroup") + "><tr" + role("row") + ">" +
      head.map(function (h, c) { return "<th scope='col'" + role("columnheader") + cls(c) + ">" + inline(h) + "</th>"; }).join("") +
      "</tr></thead><tbody" + role("rowgroup") + ">";
    rows.forEach(function (r) {
      t += "<tr" + role("row") + ">" + head.map(function (_, c) {
        return "<td" + role("cell") + cls(c) + (stack ? " data-label=\"" + esc(plain[c]) + "\"" : "") + ">" + cell(r[c] || "") + "</td>";
      }).join("") + "</tr>";
    });
    return t + "</tbody></table></div></div>";
  }
  function fit(box) {
    var w = box && box.firstElementChild;
    if (!w) return;
    var hidden = w.scrollWidth - w.clientWidth;
    box.classList.toggle("more-left", w.scrollLeft > 2);
    box.classList.toggle("more-right", w.scrollLeft < hidden - 2);
  }
  // a table's width changes when the window turns, fonts arrive or a hidden panel opens, so watch each one
  var sized = window.ResizeObserver ? new ResizeObserver(function (entries) {
    entries.forEach(function (e) { fit(e.target.closest(".tablebox")); });
  }) : null;
  function fitTables(root) {
    if (!root) return;
    var boxes = root.querySelectorAll ? Array.prototype.slice.call(root.querySelectorAll(".tablebox")) : [];
    if (root.classList && root.classList.contains("tablebox")) boxes.push(root);
    boxes.forEach(function (b) {
      fit(b);
      if (sized && b.firstElementChild) { sized.observe(b.firstElementChild); sized.observe(b.firstElementChild.firstElementChild); }
    });
  }
  document.addEventListener("scroll", function (e) {
    var t = e.target;
    if (t && t.classList && t.classList.contains("tablewrap")) fit(t.parentNode);
  }, true);
  if (!sized) window.addEventListener("resize", function () { fitTables(document); });
  fitTables(document);

  window.Shell = { esc: esc, openHelp: openHelp, closeHelp: closeHelp, chips: chips, status: status, ask: ask, toast: toast,
                   tagLanguages: tagLanguages, table: table, say: say };
})();
