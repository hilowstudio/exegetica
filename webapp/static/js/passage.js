/* The passage panel, shared by every page (templates/partials/passage.html, rule B1 and the cohesion work of
   2026-11-09). Any Scripture reference opens its chapter beside the page with the verses marked. From there the
   reader can see the verse in Greek or Hebrew, keep it in Scripture Memory, ask about it in a study, and, for a
   teacher, add it to a Prep Room unit. Nothing here calls a model.

   Passage.open(ref, opener)   open the panel at a reference
   Passage.linkRefs(node)      make every reference under a node open the panel (text only, never inside a link,
                               code, a control, or set maths)
   Passage.linkHtml(html)      the same for an HTML string a page is about to show
   Passage.ask(ref)            what "Ask about it" does: chat sets its own; elsewhere it opens a study on the passage
   Passage.addToUnit(source, anchor)   a teacher's "Add to a unit", shared with the Living Library
   Passage.keep(ref)           add a verse to the reader's own Scripture Memory */
(function () {
  "use strict";
  var panel = document.getElementById("passage");
  if (!panel) return;

  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

  // ---- references --------------------------------------------------------------------------------------------
  var BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke",
    "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter",
    "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"];
  var OT = BOOKS.indexOf("Matthew");
  // chapters in each book, in the ESV's numbering, so "Numbers c. 1" is never a link and the arrows stop at the end
  var CHAPTERS = [50, 40, 27, 36, 34, 24, 21, 4, 31, 24, 22, 25, 29, 36, 10, 13, 10, 42, 150, 31, 12, 8, 66, 52, 5, 48, 12, 14, 3, 9,
    1, 4, 7, 3, 3, 3, 2, 14, 4, 28, 16, 24, 21, 28, 16, 16, 13, 6, 6, 4, 4, 5, 3, 6, 4, 3, 1, 13, 5, 5, 3, 5, 1, 1, 1, 22];
  function lastChapter(book) { return CHAPTERS[BOOKS.indexOf(book)] || 0; }
  // Other names and the abbreviations older books and commentaries use ("Rom. 8:28", "1 Cor. 13:4", "Ps. 23:1").
  // Ambiguous short forms ("Ex", "Is", "Am") are left out: a wrong link is worse than a missing one.
  var ALIAS = {"Psalm": "Psalms", "Song of Songs": "Song of Solomon", "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus",
    "Num": "Numbers", "Deut": "Deuteronomy", "Josh": "Joshua", "Judg": "Judges", "1 Sam": "1 Samuel", "2 Sam": "2 Samuel",
    "1 Kgs": "1 Kings", "2 Kgs": "2 Kings", "1 Chron": "1 Chronicles", "2 Chron": "2 Chronicles", "1 Chr": "1 Chronicles",
    "2 Chr": "2 Chronicles", "Neh": "Nehemiah", "Esth": "Esther", "Ps": "Psalms", "Psa": "Psalms", "Prov": "Proverbs",
    "Eccl": "Ecclesiastes", "Eccles": "Ecclesiastes", "Isa": "Isaiah", "Jer": "Jeremiah", "Lam": "Lamentations",
    "Ezek": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea", "Obad": "Obadiah", "Mic": "Micah", "Nah": "Nahum", "Hab": "Habakkuk",
    "Zeph": "Zephaniah", "Hag": "Haggai", "Zech": "Zechariah", "Mal": "Malachi", "Matt": "Matthew", "Mt": "Matthew",
    "Mk": "Mark", "Lk": "Luke", "Jn": "John", "Rom": "Romans", "1 Cor": "1 Corinthians", "2 Cor": "2 Corinthians",
    "Gal": "Galatians", "Eph": "Ephesians", "Phil": "Philippians", "Col": "Colossians", "1 Thess": "1 Thessalonians",
    "2 Thess": "2 Thessalonians", "1 Tim": "1 Timothy", "2 Tim": "2 Timothy", "Tit": "Titus", "Philem": "Philemon",
    "Phlm": "Philemon", "Heb": "Hebrews", "Jas": "James", "1 Pet": "1 Peter", "2 Pet": "2 Peter", "Rev": "Revelation"};
  // Older books number the first book of a pair in Roman numerals too ("I Cor.", "II Kings").
  var ROMAN_BOOK = {"1": "I", "2": "II", "3": "III"};
  var NAMES = BOOKS.concat(Object.keys(ALIAS)).reduce(function (all, n) {
    all.push(n);
    if (ROMAN_BOOK[n.charAt(0)] && n.charAt(1) === " ") all.push(ROMAN_BOOK[n.charAt(0)] + n.slice(1));
    return all;
  }, []).sort(function (a, b) { return b.length - a.length; }).map(function (n) { return n.replace(/ /g, "\\s"); }).join("|");
  // A reference is a book, then chapter:verse with an optional range ("7:37-39", "7:53-8:11"), or, as most of the
  // Reading Room's older books write it, a Roman chapter and the verse after a point ("Rom. viii. 28", "Ps. li. 10-12").
  // Never a time or a ratio after a word.
  var CORE = "(" + NAMES + ")\\.?\\s(?:(\\d{1,3}):\\s?(\\d{1,3})(?:[-\\u2013](\\d{1,3})(?::(\\d{1,3}))?)?" +
    "|([ivxlc]{1,8}|[IVXLC]{1,8})\\.\\s?(\\d{1,3})(?:[-\\u2013](\\d{1,3}))?)";
  var REF = new RegExp("(^|[^\\w])(" + CORE + ")(?![\\d:])", "g");
  var ONE = new RegExp("^" + CORE + "$");

  // one psalm is "Psalm 23:1", as the ESV and Scripture Memory write it; the book is still Psalms
  function display(book) { return book === "Psalms" ? "Psalm" : book; }
  function canonical(book) {
    var b = String(book || "").replace(/\s+/g, " ").replace(/\.$/, "").replace(/^(I{1,3}) /, function (m, r) { return r.length + " "; });
    return ALIAS[b] || (BOOKS.indexOf(b) >= 0 ? b : null);
  }
  function roman(s) {
    var v = {i: 1, v: 5, x: 10, l: 50, c: 100}, t = String(s).toLowerCase(), n = 0, i;
    for (i = 0; i < t.length; i++) { var a = v[t[i]], b = v[t[i + 1]] || 0; n += a < b ? -a : a; }
    var back = "", left = n;
    [[100, "c"], [90, "xc"], [50, "l"], [40, "xl"], [10, "x"], [9, "ix"], [5, "v"], [4, "iv"], [1, "i"]].forEach(function (p) {
      while (left >= p[0]) { back += p[1]; left -= p[0]; } });
    return back === t ? n : 0;        // "ic" and "iiii" aren't chapter numbers
  }
  // the groups after the book: chapter, verse, range verse, range chapter, Roman chapter, its verse, its range verse
  function fromGroups(g) {
    var book = canonical(g[0]); if (!book) return null;
    var ch = g[1] ? +g[1] : roman(g[5]), v1 = +(g[1] ? g[2] : g[6]);
    if (!ch || ch > lastChapter(book) || !v1 || v1 > 176) return null;
    var tail = g[1] ? (g[3] ? "-" + g[3] + (g[4] ? ":" + g[4] : "") : "") : (g[7] ? "-" + g[7] : "");
    return display(book) + " " + ch + ":" + v1 + tail;
  }
  // "Rom. 8:28" and "Rom. viii. 28" -> "Romans 8:28"; null for anything that isn't a reference
  function normalize(ref) {
    var m = ONE.exec(String(ref || "").trim().replace(/\s+/g, " "));
    return m ? fromGroups(m.slice(1)) : null;
  }
  // a whole chapter, as a teacher types a passage source ("John 7", "Ps. 23"): "John 7", or null
  function chapter(ref) {
    var m = /^(.+?)\.?\s(\d{1,3})$/.exec(String(ref || "").trim().replace(/\s+/g, " ")), book = m && canonical(m[1]);
    return book && +m[2] >= 1 && +m[2] <= lastChapter(book) ? display(book) + " " + +m[2] : null;
  }
  function parse(ref) {
    var whole = chapter(ref);
    if (whole) { var w = /^(.+) (\d+)$/.exec(whole); return {ref: whole, book: canonical(w[1]), ch: +w[2], v1: 0, v2: 0}; }
    var n = normalize(ref); if (!n) return null;
    var m = /^(.+?) (\d{1,3}):(\d{1,3})(?:-(\d{1,3})(?::(\d{1,3}))?)?$/.exec(n);
    // a range into the next chapter ("John 7:53-8:11") marks to the end of the first
    return {ref: n, book: canonical(m[1]), ch: +m[2], v1: +m[3], v2: m[5] ? 999 : +(m[4] || m[3])};
  }
  function chapterName(book, ch) { return display(book) + " " + ch; }
  function link(text, ref) { return '<a class="ref" href="/?passage=' + encodeURIComponent(ref) + '" data-ref="' + esc(ref) + '">' + text + "</a>"; }

  function linkHtml(html) {
    var depth = 0;
    return String(html).split(/(<[^>]+>)/).map(function (part) {
      if (part.charAt(0) === "<") {
        if (/^<(code|a|pre)[\s>]/.test(part)) depth++;
        else if (/^<\/(code|a|pre)>/.test(part)) depth = Math.max(0, depth - 1);
        return part;
      }
      if (depth) return part;
      return part.replace(REF, function (m, pre, whole) {
        var n = fromGroups([].slice.call(arguments, 3, 11)); return n ? pre + link(whole, n) : m;
      });
    }).join("");
  }

  // a page's own title stays a title: the same reference is linked where the text cites it (rule B10)
  var SKIP = "a,button,code,pre,script,style,textarea,input,select,label,h1,[contenteditable],.katex,.passage,[data-no-refs],svg";
  function linkRefs(root) {
    if (!root || !document.createTreeWalker) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (t) {
        if (!t.nodeValue || !/\d:\s?\d|[ivxlcIVXLC]\.\s?\d/.test(t.nodeValue)) return NodeFilter.FILTER_REJECT;
        var el = t.parentElement;
        return el && !el.closest(SKIP) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var hits = [], t;
    while ((t = walker.nextNode())) hits.push(t);
    hits.forEach(function (node) {
      var text = node.nodeValue, out = "", last = 0, any = false, m;
      REF.lastIndex = 0;
      while ((m = REF.exec(text))) {
        var n = fromGroups(m.slice(3, 11)); if (!n) continue;
        var start = m.index + m[1].length;
        out += esc(text.slice(last, start)) + link(esc(m[2]), n);
        last = start + m[2].length; any = true;
      }
      if (!any) return;
      out += esc(text.slice(last));
      var span = document.createElement("span");
      span.innerHTML = out;
      var frag = document.createDocumentFragment();
      while (span.firstChild) frag.appendChild(span.firstChild);
      node.parentNode.replaceChild(frag, node);
    });
  }

  // ---- who is reading ----------------------------------------------------------------------------------------
  var teacher = panel.hasAttribute("data-teacher");
  var mePromise = null;
  function me() {
    if (!mePromise) mePromise = fetch("/api/me", {credentials: "same-origin"}).then(function (r) { return r.json(); })
      .then(function (d) { return (d && d.user) || null; }).catch(function () { return null; });
    return mePromise;
  }

  // ---- the panel ---------------------------------------------------------------------------------------------
  var body = document.getElementById("pg-body"), title = document.getElementById("pg-title"),
      foot = document.getElementById("pg-foot"), orig = document.getElementById("pg-orig");
  var ESV_NOTICE = "Scripture quotations are from the ESV® Bible (The Holy Bible, English Standard Version®), © 2001 by " +
    "Crossway, a publishing ministry of Good News Publishers. Used by permission. All rights reserved.";
  var pg = {ref: null, book: null, ch: 0, v1: 0, v2: 0, opener: null};
  var narrowQ = window.matchMedia ? matchMedia("(max-width:640px)") : null;
  function narrow() { return !!(narrowQ && narrowQ.matches); }
  var inerted = [];
  function setOpen(o) {
    panel.classList.toggle("open", o);
    document.body.classList.toggle("passage-open", o);
    inerted.forEach(function (el) { el.inert = false; });
    inerted = [];
    if (o && narrow()) {          // on a phone the panel covers the page: the rest waits, so focus can't wander behind it
      Array.prototype.forEach.call(document.body.children, function (el) {
        if (el === panel || el.matches("nav.rail,.shell-toast,.shell-sr,dialog,script,.help-bg,[data-keep-live]")) return;
        if (!el.inert) { el.inert = true; inerted.push(el); }
      });
    }
  }
  function open(ref, opener, mark) {
    var p = parse(ref); if (!p) return;
    pg = {ref: p.ref, book: p.book, ch: p.ch, v1: mark === false ? 0 : p.v1, v2: mark === false ? 0 : p.v2,
          opener: opener || pg.opener || document.activeElement};
    title.textContent = chapterName(p.book, p.ch); orig.hidden = true; orig.innerHTML = "";
    document.getElementById("pg-prev").disabled = p.ch <= 1;
    document.getElementById("pg-next").disabled = p.ch >= lastChapter(p.book);
    body.innerHTML = "<p class='pg-note'>Fetching " + esc(chapterName(p.book, p.ch)) + "…</p>"; foot.innerHTML = "";
    setOpen(true); title.focus({preventScroll: true});
    fetch("/api/memory/chapter?ref=" + encodeURIComponent(p.book + " " + p.ch + ":1"), {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); }).then(function (d) {
        if (pg.book !== p.book || pg.ch !== p.ch) return;
        if (!d.verses || !d.verses.length) { body.innerHTML = "<p class='pg-note'>There's no " + esc(chapterName(p.book, p.ch)) + ".</p>"; return; }
        body.innerHTML = d.verses.map(function (v) {
          var t = "<sup>" + v.n + "</sup>" + esc(v.text.replace(/\s+/g, " ")) + " ";
          return (v.n >= pg.v1 && v.n <= pg.v2) ? "<mark>" + t + "</mark>" : t;
        }).join("") + "<p class='pg-credit'>" + esc(ESV_NOTICE) + "</p>";
        if (window.Shell && Shell.tagLanguages) Shell.tagLanguages(body);
        var hit = body.querySelector("mark"); body.scrollTop = hit ? Math.max(0, hit.offsetTop - body.offsetTop - 80) : 0;
        drawFoot();
      }).catch(function () {
        body.innerHTML = "<p class='pg-note' role='status'>The passage couldn't be loaded just now.</p>" +
          "<button type='button' class='pg-act' id='pg-retry'>Try again</button>";
        document.getElementById("pg-retry").onclick = function () { open(ref, null, mark); };
      });
  }
  function selection() { return display(pg.book) + " " + pg.ch + ":" + pg.v1 + (pg.v2 > pg.v1 && pg.v2 < 999 ? "-" + pg.v2 : ""); }
  // The foot keeps looking apart from doing. The verse's line holds how to see it (the original language, opening
  // just beneath). The tools under it take the verse elsewhere, each drawn with the icon of the place it goes.
  function icon(d) { return "<svg viewBox='0 0 24 24' aria-hidden='true'>" + d + "</svg>"; }
  var TO_MEMORY = icon("<rect x='3.5' y='6.5' width='12' height='12' rx='2'/><path d='M8 4.5h10a2 2 0 0 1 2 2v10'/><path d='M6.5 11h6M6.5 14h4'/>");
  var TO_CHAT = icon("<path d='M4 5.5h16v11H9l-4 3.2V16.5H4z'/>");
  var TO_PREP = icon("<path d='M6.5 3.5h8l4 4v13h-12z'/><path d='M14 3.5v4.2h4.2'/><path d='M9 12.5h6M9 15.5h6'/>");
  var SAVE = icon("<path d='M7 3.5h10v17l-5-4-5 4z'/><path d='M12 7.5v5M9.5 10h5'/>");   // "Save to": a unit or a class shelf
  var CHEVRON = icon("<path d='M6 9l6 6 6-6'/>");
  function drawFoot() {
    if (!pg.v1) { foot.innerHTML = ""; return; }
    var r = selection(), lang = BOOKS.indexOf(pg.book) < OT ? "Hebrew" : "Greek";
    foot.innerHTML = "<div class='pg-selrow'><p class='pg-sel'>" + esc(r) + "</p>" +
      "<button type='button' class='pg-lang' id='pg-orig-b' aria-expanded='false' aria-controls='pg-orig'>In " + lang + CHEVRON + "</button></div>" +
      "<span id='pg-orig-slot'></span>" +
      "<div class='pg-tools'>" +
      "<button type='button' class='pg-tool' id='pg-mem'>" + TO_MEMORY + "Memorize</button>" +
      "<button type='button' class='pg-tool' id='pg-ask'>" + TO_CHAT + "Ask about it</button>" +
      (teacher ? "<button type='button' class='pg-tool' id='pg-unit' aria-haspopup='true' aria-expanded='false'>" + TO_PREP + "Add to a unit</button>" : "") +
      "</div>";
    document.getElementById("pg-orig-slot").replaceWith(orig);     // the original opens under its own line
    document.getElementById("pg-orig-b").onclick = function (e) { toggleOriginal(r, lang, e.currentTarget); };
    document.getElementById("pg-mem").onclick = function () { keep(r); };
    document.getElementById("pg-ask").onclick = function () { Passage.ask(r); };
    var u = document.getElementById("pg-unit");
    if (u) u.onclick = function () { addToUnit({kind: "passage", ref: {ref: r, translation: "ESV"}, label: r + " (ESV)"}, u, null,
      {share: {url: location.origin + "/?passage=" + encodeURIComponent(r), title: r}}); };
  }
  function toggleOriginal(r, lang, btn) {
    var on = orig.hidden; orig.hidden = !on; btn.setAttribute("aria-expanded", String(on));
    if (!on) return;
    orig.innerHTML = "<p class='pg-note'>Loading the library's " + lang + "…</p>";
    fetch("/api/memory/original?ref=" + encodeURIComponent(r), {credentials: "same-origin"}).then(function (res) {
      if (res.status === 404) return false;
      return res.ok ? res.json() : Promise.reject(res.status);
    }).then(function (d) {
      if (d === false) { orig.innerHTML = "<p class='pg-note'>The library has no " + lang + " text for " + esc(r) + ".</p>"; return; }
      var bare = function (x) { return String(x || "").replace(/[.,;:?!·;׃]+$/, ""); };
      orig.innerHTML = "<div class='pg-words' dir='" + d.dir + "'>" + d.words.map(function (w, i) {
        return "<button type='button' data-ow='" + i + "' aria-pressed='false'>" + esc(w.word) + "</button>"; }).join("") +
        "</div><div class='pg-gloss' aria-live='polite'><p class='pg-note'>Choose a word to see what it means.</p></div>";
      orig.querySelectorAll("[data-ow]").forEach(function (b) {
        b.onclick = function () {
          orig.querySelectorAll("[data-ow]").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
          b.setAttribute("aria-pressed", "true");
          var w = d.words[+b.dataset.ow];
          orig.querySelector(".pg-gloss").innerHTML = "<span class='gw'>" + esc(bare(w.word)) + "</span> <span class='gt'>" +
            esc(bare(w.translit)) + "</span> <span class='gg'>" + esc(bare(w.gloss)) + "</span><span class='gd'>" + esc(w.definition || "") + "</span>";
        };
      });
    }).catch(function () {
      orig.innerHTML = ""; orig.hidden = true; btn.setAttribute("aria-expanded", "false");
      if (window.Shell) Shell.toast("The " + lang + " couldn't be loaded just now.");
    });
  }
  function close() {
    closeMenu();
    setOpen(false);
    var o = pg.opener; pg.opener = null;
    if (o && o.isConnected) o.focus({preventScroll: true});
  }
  document.getElementById("pg-close").onclick = close;
  document.getElementById("pg-prev").onclick = function () { if (pg.ch > 1) open(pg.book + " " + (pg.ch - 1) + ":1", null, false); };
  document.getElementById("pg-next").onclick = function () { if (pg.ch < lastChapter(pg.book)) open(pg.book + " " + (pg.ch + 1) + ":1", null, false); };
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest(".ref[data-ref]");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault(); open(a.getAttribute("data-ref"), a);
  });
  // Escape closes the panel first; pages that also use Escape check defaultPrevented
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (menu) { var o = menuOpener; closeMenu(); if (o) o.focus(); e.preventDefault(); e.stopPropagation(); return; }
    if (!panel.classList.contains("open") || document.querySelector("dialog[open]")) return;
    e.preventDefault(); close();
  }, true);
  if (narrowQ && narrowQ.addEventListener) narrowQ.addEventListener("change", function () { if (panel.classList.contains("open")) setOpen(true); });

  // ---- Ask: a study on the passage. Chat replaces this with its own composer. ----------------------------------
  function ask(r) { location.href = "/?ask=" + encodeURIComponent(r); }

  // ---- Keep: the reader's own Scripture Memory, the same store that page keeps ---------------------------------
  // A first verse in an empty account brings the course's verses with it, as a first visit there would.
  var MEM_SEED = ["John 20:31", "John 1:14", "John 1:12", "John 3:16", "John 4:24", "John 6:35", "John 8:12", "John 10:11", "John 11:25",
    "John 13:34-35", "John 14:6", "John 15:5", "John 16:33", "John 17:3", "John 19:30", "John 21:17"];
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function memVerse(ref) { return {id: "v" + uid(), reference: ref, text: null, currentStep: 0, masteredAt: null, lastPracticedAt: null,
    lastRefreshedAt: null, folderId: null, createdAt: new Date().toISOString()}; }
  function memStore(signed, db) {
    if (!signed) { try { localStorage.setItem("studybible.memory.v1", JSON.stringify(db)); return Promise.resolve(true); } catch (e) { return Promise.resolve(false); } }
    return fetch("/api/memory", {method: "PUT", credentials: "same-origin", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({verses: db.verses, folders: db.folders})}).then(function (r) { return r.ok; }).catch(function () { return false; });
  }
  async function keep(ref) {
    var user = await me(), signed = !!user, db = null;
    if (signed) {
      try { var r = await fetch("/api/memory", {credentials: "same-origin"}); if (r.ok) db = await r.json(); } catch (e) {}
      if (!db) { Shell.toast("Scripture Memory couldn't be reached. Try again in a minute."); return; }   // a failed read never overwrites the account
    } else { try { db = JSON.parse(localStorage.getItem("studybible.memory.v1")); } catch (e) {} }
    db = {verses: (db && db.verses) || [], folders: (db && db.folders) || []};
    var norm = function (x) { return normalize(x) || String(x || "").toLowerCase().replace(/\u2013/g, "-").replace(/\s+/g, " ").trim(); };
    if (db.verses.some(function (v) { return norm(v.reference) === norm(ref); })) { Shell.toast(ref + " is already in Scripture Memory."); return; }
    if (!db.verses.length && !db.folders.length) db.verses = MEM_SEED.filter(function (s) { return norm(s) !== norm(ref); }).map(memVerse);
    var v = memVerse(ref); db.verses.push(v);
    if (!(await memStore(signed, db))) { Shell.toast("It couldn't be saved just now. Try again in a minute."); return; }
    Shell.toast("Added " + ref + " to Scripture Memory", {undo: function () {
      db.verses = db.verses.filter(function (x) { return x.id !== v.id; }); memStore(signed, db); }});
  }

  // ---- the shell's floating menu: the house menu card (shell.css .shell-menu), anchored to its button ----
  // One opener for every menu here: "Save to", and the small menus on a class shelf (Passage.menu).
  var menu = null, menuOpener = null, place = null;
  var BOX = "<span class='sm-box' aria-hidden='true'><svg viewBox='0 0 24 24'><path d='M20 6L9 17l-5-5'/></svg></span>";
  var PLUS = "<span class='sm-plus' aria-hidden='true'><svg viewBox='0 0 24 24'><path d='M12 5v14M5 12h14'/></svg></span>";
  var OUT = "<span class='sm-plus' aria-hidden='true'><svg viewBox='0 0 24 24'><path d='M14 4h6v6M20 4l-9 9'/><path d='M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5'/></svg></span>";
  // Google Classroom by share link (decision 0030): Classroom's own posting window, given only the link and a title.
  // No Google script loads on Exegetica's pages; the window opens inside the click, so a pop-up blocker lets it through.
  function classroom(url, title, win) {
    var to = "https://classroom.google.com/share?url=" + encodeURIComponent(url) + (title ? "&title=" + encodeURIComponent(title) : "");
    var w = win || window.open("", "exegetica-classroom", "popup,width=720,height=720");
    if (!w) { location.href = to; return; }             // no pop-ups: go there in this tab
    try { w.opener = null; } catch (e) {}
    w.location.href = to;
  }
  function closeMenu() {
    if (!menu) return;
    menu.remove(); menu = null;
    window.removeEventListener("scroll", place, true); window.removeEventListener("resize", closeMenu);
    if (menuOpener) menuOpener.setAttribute("aria-expanded", "false");
  }
  // the menu for this button, or null when it was already open (a second press closes it)
  function openMenu(anchor, label) {
    var was = menu && menuOpener === anchor; closeMenu(); if (was) return null;
    menuOpener = anchor;
    menu = document.createElement("div");
    menu.className = "shell-menu"; menu.setAttribute("role", "menu"); menu.setAttribute("aria-label", label);
    menu.setAttribute("data-keep-live", "");
    // inside an open modal dialog, the menu must live in it: the rest of the page sits under the dialog, inert
    (anchor.closest("dialog[open]") || document.body).appendChild(menu);
    anchor.setAttribute("aria-expanded", "true");
    place = function () {               // under the button, or over it when the screen runs out below
      if (!menu) return;
      var r = anchor.getBoundingClientRect(), w = menu.offsetWidth, h = menu.offsetHeight, gap = 6;
      var below = innerHeight - r.bottom - gap - 8, above = r.top - gap - 8;
      var up = h > below && above > below;
      menu.style.maxHeight = Math.max(160, Math.min(380, up ? above : below)) + "px";
      // its left edge on the button's, or its right edge on the button's when there's no room to the right
      menu.style.left = Math.max(8, r.left + w <= innerWidth - 8 ? r.left : Math.min(r.right, innerWidth - 8) - w) + "px";
      menu.style.top = (up ? Math.max(8, r.top - gap - menu.offsetHeight) : r.bottom + gap) + "px";
    };
    window.addEventListener("scroll", place, true); window.addEventListener("resize", closeMenu);
    menu.addEventListener("keydown", function (e) {
      var bs = Array.prototype.slice.call(menu.querySelectorAll("button")), i = bs.indexOf(document.activeElement);
      if (!bs.length) return;
      if (e.key === "ArrowDown") { e.preventDefault(); bs[(i + 1) % bs.length].focus(); }
      if (e.key === "ArrowUp") { e.preventDefault(); bs[(i - 1 + bs.length) % bs.length].focus(); }
      if (e.key === "Home") { e.preventDefault(); bs[0].focus(); }
      if (e.key === "End") { e.preventDefault(); bs[bs.length - 1].focus(); }
      if (e.key === "Tab") closeMenu();
    });
    return menu;
  }
  function settle(anchor) { setTimeout(function () { if (menu) { closeMenu(); anchor.focus(); } }, 260); }   // the check is seen, then the menu goes
  document.addEventListener("click", function (e) {
    // a click on an item of a menu that has just made way for another (File as…, Save to…) isn't a click outside
    if (menu && e.target.isConnected && !menu.contains(e.target) && e.target !== menuOpener && !(menuOpener && menuOpener.contains(e.target))) closeMenu();
  });
  // A small menu of actions: entries [{label, checked (true or false makes it a checkbox), danger, act}].
  function smallMenu(anchor, label, entries) {
    var m = openMenu(anchor, label); if (!m) return;
    m.innerHTML = entries.map(function (x, i) {
      var box = typeof x.checked === "boolean";
      return "<button type='button' role='" + (box ? "menuitemcheckbox" : "menuitem") + "' data-i='" + i + "'" +
        (box ? " aria-checked='" + x.checked + "'" : "") + (x.danger ? " class='danger'" : "") + ">" +
        (box ? BOX : "") + "<span class='sm-t'>" + esc(x.label) + "</span></button>"; }).join("");
    place();
    m.querySelectorAll("[data-i]").forEach(function (b) {
      b.onclick = function () { var x = entries[+b.dataset.i]; closeMenu(); anchor.focus(); x.act(); };
    });
    var first = m.querySelector("button"); if (first) first.focus();
  }

  function capital(t) { return t.charAt(0).toUpperCase() + t.slice(1); }
  function api(method, url, body) {
    return fetch(url, {method: method, credentials: "same-origin", headers: body ? {"Content-Type": "application/json"} : {},
      body: body ? JSON.stringify(body) : undefined})
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error(d.error || "That didn't work. Try again in a minute."); return d; }); });
  }

  // ---- Save to: a teacher's sources travel into the Prep Room, and books and videos onto class shelves ----------
  // The pattern people know from "Save to" lists (a video to playlists, a file to folders): the teacher's units, then
  // (for a book or a video) the classes they teach, each checked where the item already is. Choosing an unchecked
  // one adds it, a checked one takes it out, and both can be undone (decisions 0026 and 0029).
  function changed(unit) { document.dispatchEvent(new CustomEvent("prep:sources-changed", {detail: {unit: unit}})); }
  function shelfChanged() { document.dispatchEvent(new CustomEvent("shelf:changed", {detail: {}})); }
  var KEY = {book: "slug", outline: "key", passage: "ref", library: "item_id", link: "url"};
  // where this item stands in a unit: "in", "whole" (a moment whose whole video is already there), or "out"
  function standing(unit, source) {
    var h = unit.holds; if (!h) return "out";
    var mine = source.kind === "library" && source.ref.excerpts ? source.ref.excerpts[0] : null;
    if (!mine) return "in";
    if (!(h.ref && h.ref.excerpts)) return "whole";
    return h.ref.excerpts.indexOf(mine) >= 0 ? "in" : "out";
  }
  function add(unit, source, say) {
    return api("POST", "/api/prep/units/" + unit.id + "/sources", source).then(function (d) {
      unit.holds = {source: d.source.id, ref: d.source.ref}; changed(unit.id);
      Shell.toast("Added " + (say || source.label) + " to “" + unit.title + "”", {undo: function () {
        // a moment joined to an item already in the unit goes back to the item as it was; anything else is removed
        (d.source.merged ? api("PATCH", "/api/prep/sources/" + d.source.id, {kind: d.source.kind, ref: d.source.before})
                         : api("DELETE", "/api/prep/sources/" + d.source.id))
          .then(function () { changed(unit.id); }).catch(function (err) { Shell.toast(err.message); });
      }});
    });
  }
  function take(unit, source, say) {
    var h = unit.holds, mine = source.kind === "library" && source.ref.excerpts ? source.ref.excerpts[0] : null;
    var rest = mine ? h.ref.excerpts.filter(function (x) { return x !== mine; }) : [];
    var go = rest.length ? api("PATCH", "/api/prep/sources/" + h.source, {kind: "library", ref: {item_id: h.ref.item_id, excerpts: rest}})
                         : api("DELETE", "/api/prep/sources/" + h.source);
    return go.then(function () {
      var was = h; unit.holds = rest.length ? {source: h.source, ref: {item_id: h.ref.item_id, excerpts: rest}} : null; changed(unit.id);
      Shell.toast("Removed " + (say || source.label) + " from “" + unit.title + "”", {undo: function () {
        (rest.length ? api("PATCH", "/api/prep/sources/" + was.source, {kind: "library", ref: was.ref})
                     : api("POST", "/api/prep/units/" + unit.id + "/sources", source))
          .then(function () { changed(unit.id); }).catch(function (err) { Shell.toast(err.message); });
      }});
    });
  }
  // a class shelf: put the book or video on it for the class's students, or take it off
  function shelve(cls, pl, say) {
    return api("POST", "/api/shelf/class/" + encodeURIComponent(cls.key) + "/items", {kind: pl.kind, ref: pl.ref, label: pl.label, audience: "students"})
      .then(function (d) {
        cls.holds = d.item; shelfChanged();
        Shell.toast("Put " + (say || pl.label) + " on the " + cls.name + " shelf" + (d.item.audience === "teachers" ? ", for its teachers" : ""), {undo: function () {
          api("DELETE", "/api/shelf/items/" + d.item.id).then(shelfChanged).catch(function (err) { Shell.toast(err.message); });
        }});
      });
  }
  function unshelve(cls, pl, say) {
    var was = cls.holds;
    return api("DELETE", "/api/shelf/items/" + was.id).then(function (d) {
      cls.holds = null; shelfChanged();
      Shell.toast("Took " + (say || pl.label) + " off the " + cls.name + " shelf" + (d.returned ? ". It's back on the shelf of the teacher who added it" : ""), {undo: function () {
        // put back from what the menu was given (a class copy's own ref no longer names the teacher's copy)
        api("POST", "/api/shelf/class/" + encodeURIComponent(cls.key) + "/items", {kind: pl.kind, ref: pl.ref, label: was.label, audience: was.audience})
          .then(shelfChanged).catch(function (err) { Shell.toast(err.message); });
      }});
    });
  }
  function row(u, source, here) {
    var st = standing(u, source);
    return "<button type='button' role='menuitemcheckbox' data-u='" + esc(u.id) + "' aria-checked='" + (st !== "out") + "'" +
      (st === "whole" ? " aria-disabled='true'" : "") + ">" + BOX + "<span class='sm-t'>" + esc(u.title) + "</span>" +
      (st === "whole" ? "<span class='sm-note'>all of it</span>" : here && u.id === here.id ? "<span class='sm-note'>open</span>" : "") +
      "</button>";
  }
  function classRow(c) {
    return "<button type='button' role='menuitemcheckbox' data-c='" + esc(c.key) + "' aria-checked='" + !!c.holds + "'>" + BOX +
      "<span class='sm-t'>" + esc(c.name) + "</span>" + (c.holds && c.holds.audience === "teachers" ? "<span class='sm-note'>teachers</span>" : "") + "</button>";
  }
  // say: what the toasts call it, when that isn't the source's label ("the moment at 2:14–3:05").
  // opts.place: {kind: "book" or "video", ref, label}, the same item as a class shelf holds it. With it, the menu
  // also lists the classes the teacher teaches. opts.mine: {label, checked, act(on)}, the person's own shelf, listed
  // first, so one "Save to" says everywhere a book lives for a teacher. opts.share: Google Classroom (decision 0030),
  // {url, title} to share a link as it is, or {shelf: true, title} to share the class shelf's copy, putting it on the
  // class's shelf first when it isn't there, so the Classroom post and the shelf are one thing.
  // the menu's last band: a share as it is, or one share per class shelf (the post links that class's copy)
  function shareGroup(share, classes) {
    if (!share) return "";
    var head = "<div class='shell-menu-sep'></div><div class='shell-menu-lab'>Google Classroom</div>";
    if (!share.shelf) return head + "<button type='button' role='menuitem' data-share>" + OUT + "<span class='sm-t'>Share to Classroom…</span></button>";
    if (!classes.length) return head + "<p class='shell-menu-note'>Choose the classes you teach, then share from a class shelf.</p>";
    // the band's heading says the action; each row is the class whose shelf copy the post links
    return "<div class='shell-menu-sep'></div><div class='shell-menu-lab'>Share to Google Classroom</div>" + classes.map(function (c) {
      return "<button type='button' role='menuitem' data-share='" + esc(c.key) + "' aria-label='Share to Google Classroom from the " +
        esc(c.name) + " shelf'>" + OUT + "<span class='sm-t'>" + esc(c.name) + "</span></button>";
    }).join("");
  }
  function addToUnit(source, anchor, say, opts) {
    var pl = opts && opts.place, mine = opts && opts.mine, share = opts && opts.share;
    var units = !(opts && opts.units === false);   // false: a Prep Room resource already lives in a unit
    var m = openMenu(anchor, pl ? "Save to" : "Add to a unit"); if (!m) return;
    m.innerHTML = "<div class='shell-menu-lab'>" + (units ? "Your units" : "Your shelves") + "</div><p class='shell-menu-note' role='status'>Loading…</p>";
    place();
    var here = Passage.currentUnit;     // the Prep Room says which unit is open
    var hk = (opts && opts.hold) || {kind: source.kind, key: source.ref && source.ref[KEY[source.kind]]};   // opts.hold: how a unit holds it
    var key = hk.key;
    var heldUrl = pl ? "/api/shelf/held?kind=" + pl.kind + "&key=" + encodeURIComponent(pl.kind === "book" ? pl.ref.slug : (pl.ref.origin || pl.ref.item_id || pl.ref.resource_id)) +
      (pl.ref.start != null ? "&start=" + pl.ref.start : "") : null;
    Promise.all([units ? api("GET", "/api/prep/units" + (key ? "?kind=" + encodeURIComponent(hk.kind) + "&key=" + encodeURIComponent(key) : "")) : Promise.resolve({units: []}),
                 heldUrl ? api("GET", heldUrl).catch(function () { return {classes: []}; }) : Promise.resolve({classes: []})])
      .then(function (res) {
        if (!menu) return;
        var d = res[0], classes = res[1].classes || [];
        var list = (d.units || []).slice(0, 8);
        var open = here && (d.units || []).filter(function (u) { return u.id === here.id; })[0];
        if (open) list = [open].concat(list.filter(function (u) { return u.id !== open.id; }));
        // your shelf, your units (with a new one), then the classes you teach: each group in its own band
        menu.innerHTML = (mine ? "<div class='shell-menu-lab'>Your shelf</div><button type='button' role='menuitemcheckbox' data-m aria-checked='" +
            !!mine.checked + "'>" + BOX + "<span class='sm-t'>" + esc(mine.label) + "</span></button><div class='shell-menu-sep'></div>" : "") +
          (units ? "<div class='shell-menu-lab'>Your units</div>" +
            (list.length ? list.map(function (u) { return row(u, source, here); }).join("") : "") +
            "<button type='button' role='menuitem' data-new>" + PLUS + "<span class='sm-t'>New unit…</span></button>" : "") +
          (classes.length ? (units || mine ? "<div class='shell-menu-sep'></div>" : "") + "<div class='shell-menu-lab'>Class shelves</div>" + classes.map(classRow).join("") :
            units ? "" : "<p class='shell-menu-note'>Choose the classes you teach in the Living Library, and their shelves show here.</p>") +
          shareGroup(share, classes);
        place();
        menu.querySelectorAll("[data-u]").forEach(function (b) {
          b.onclick = function () {
            var u = list.filter(function (x) { return x.id === b.dataset.u; })[0], on = b.getAttribute("aria-checked") === "true";
            if (b.getAttribute("aria-disabled") === "true") { Shell.toast("“" + u.title + "” already holds all of it."); return; }
            b.setAttribute("aria-checked", String(!on));          // the check moves at once; the menu closes once it's seen
            (on ? take(u, source, say) : add(u, source, say)).then(function () { settle(anchor); })
              .catch(function (err) { b.setAttribute("aria-checked", String(on)); Shell.toast(err.message); });
          };
        });
        var mb = menu.querySelector("[data-m]");
        if (mb) mb.onclick = function () {
          var on = mb.getAttribute("aria-checked") === "true";
          mb.setAttribute("aria-checked", String(!on)); mine.checked = !on;
          Promise.resolve(mine.act(!on)).then(function () { settle(anchor); });
        };
        menu.querySelectorAll("[data-c]").forEach(function (b) {
          b.onclick = function () {
            var c = classes.filter(function (x) { return x.key === b.dataset.c; })[0], on = b.getAttribute("aria-checked") === "true";
            b.setAttribute("aria-checked", String(!on));
            (on ? unshelve(c, pl, say) : shelve(c, pl, say)).then(function () { settle(anchor); })
              .catch(function (err) { b.setAttribute("aria-checked", String(on)); Shell.toast(err.message); });
          };
        });
        menu.querySelectorAll("[data-share]").forEach(function (b) {
          b.onclick = function () {
            if (!share.shelf) { closeMenu(); anchor.focus(); classroom(share.url, share.title || say || source.label); return; }
            var c = classes.filter(function (x) { return x.key === b.dataset.share; })[0];
            var w = window.open("", "exegetica-classroom", "popup,width=720,height=720");   // inside the click
            var go = function () { classroom(location.origin + "/read/doc/" + c.holds.id, share.title || pl.label, w); };
            closeMenu(); anchor.focus();
            if (c.holds) { go(); return; }
            shelve(c, pl, say).then(go).catch(function (err) { if (w) w.close(); Shell.toast(err.message); });
          };
        });
        if (units) menu.querySelector("[data-new]").onclick = async function () {
          closeMenu();
          var name = await Shell.ask({title: "New unit", body: "Name it the way you plan. " + capital(say || source.label) + " goes in it first.",
            ok: "Create unit", input: {label: "Unit name", value: "", max: 160}, validate: function (t) { return t ? "" : "Give the unit a name."; }});
          if (!name) { anchor.focus(); return; }
          api("POST", "/api/prep/units", {title: name, grade_band: "secondary"})
            .then(function (d2) { return add(d2.unit, source, say); }).catch(function (err) { Shell.toast(err.message); });
        };
        var first = menu.querySelector("button:not([aria-disabled='true'])"); if (first) first.focus();
      }).catch(function (err) { if (menu) { menu.querySelector(".shell-menu-note").textContent = err.message; place(); } });
  }

  window.Passage = {open: open, close: close, linkRefs: linkRefs, linkHtml: linkHtml, normalize: normalize, parse: parse, chapter: chapter,
    ask: ask, keep: keep, addToUnit: addToUnit, menu: smallMenu, teacher: teacher, currentUnit: null, classroom: classroom,
    icons: {memory: TO_MEMORY, chat: TO_CHAT, prep: TO_PREP, save: SAVE}};     // the rail's drawings, for the same actions elsewhere

  // Pages built on the server mark what holds Scripture with data-scripture; it's linked as the page loads.
  Array.prototype.forEach.call(document.querySelectorAll("[data-scripture]"), linkRefs);
})();
