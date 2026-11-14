/* The course page (decision 0032): Today, Plan and Year over /api/john.
   Today is the lesson the class does next; Plan is the outline and each container's page; Year lays the units
   over the school's class meetings. Units hold their dates; lessons are marked taught. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var DAY = { regular: "Regular", thursday: "Thursday", half_day: "Half day" };
  var MIN = { regular: 50, thursday: 36, half_day: 26 };
  var VIEWS = ["today", "plan", "year"];
  var D = null, view = VIEWS.indexOf(location.hash.slice(1)) >= 0 ? location.hash.slice(1) : "today", sel = null;

  function api(method, url, body) {
    return fetch(url, { method: method, headers: body ? { "Content-Type": "application/json" } : {},
                        body: body ? JSON.stringify(body) : undefined })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (!r.ok) throw new Error(d.error || "That didn't work. Try again.");
          return d;
        });
      });
  }
  function say(t) { $("#cx-msg").textContent = t || ""; }
  function toast(t, undo) { if (window.Shell && Shell.toast) Shell.toast(t, undo ? { undo: undo } : {}); else say(t); }
  function load() {
    return api("GET", "/api/john").then(function (d) { D = d; render(); })
      .catch(function (e) { say(e.message); });
  }
  function day(iso, long) {
    var d = new Date(iso + "T12:00:00");
    return d.toLocaleDateString(undefined, long ? { weekday: "long", month: "long", day: "numeric" }
                                                : { weekday: "short", month: "short", day: "numeric" });
  }
  function lessons() {
    var out = [];
    D.units.forEach(function (u, ui) { u.lessons.forEach(function (l, li) { out.push({ u: u, ui: ui, l: l, li: li }); }); });
    return out;
  }
  function find(id) {
    for (var i = 0; i < D.units.length; i++) {
      var u = D.units[i];
      if (u.id === id) return { u: u, ui: i };
      for (var j = 0; j < u.lessons.length; j++) if (u.lessons[j].id === id) return { u: u, ui: i, l: u.lessons[j], li: j };
    }
    return null;
  }
  function offOn(iso) {
    var o = D.calendar.off.find(function (x) { return x.date === iso; });
    return o ? (o.label || { finals: "finals", no_class: "no class", no_school: "no school" }[o.kind]) : "";
  }
  function ref(p) {
    return p ? '<button type="button" class="cx-ref" data-ref="' + esc(p) + '">' + esc(p) + "</button>" : "";
  }
  function empty(title, line, action) {
    return '<div class="cx-empty"><h2>' + esc(title) + "</h2><p>" + esc(line) + "</p>" + (action || "") + "</div>";
  }

  // ------------------------------------------------------------------ views
  function show(v, focus) {
    view = v;
    VIEWS.forEach(function (k) {
      var on = k === v, t = $("#tab-" + k);
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      $("#v-" + k).hidden = !on;
      if (on && focus) t.focus();
    });
    if (location.hash !== "#" + v) history.pushState(null, "", "#" + v);
    render();
  }
  function render() {
    if (!D) return;
    say("");
    if (view === "today") renderToday(); else if (view === "plan") renderPlan(); else renderYear();
  }

  // ------------------------------------------------------------------ Today
  function count(n, one, many) { return n + " " + (n === 1 ? one : (many || one + "s")); }
  function paceLine(u) {
    var p = u.pace;
    if (!p) return "";
    var parts = [esc(u.title), "lesson " + Math.min(p.taught + 1, u.lessons.length) + " of " + u.lessons.length];
    if (p.behind) {
      parts.push(p.meetings_left ? count(p.left, "lesson") + " left, " + count(p.meetings_left, "class day") + " left in this unit"
                                 : "this unit's class days have passed");
    }
    parts.push(D.behind ? count(D.behind, "lesson") + " behind the calendar" : "on pace");
    return '<p class="cx-pace' + (D.behind || p.behind ? " is-behind" : "") + '">' + parts.join(" · ") + "</p>";
  }
  function movesHtml(plan, minutes) {
    var moves = (plan && plan.moves) || [];
    if (!moves.length) return "";
    var t = 0, total = moves.reduce(function (a, m) { return a + (m.minutes || 0); }, 0);
    var rows = moves.map(function (m) {
      var from = t; t += m.minutes || 0;
      return "<li><span class=\"cx-t\">" + from + "–" + t + "</span><div><strong>" + esc(m.title) + "</strong>" +
             (m.text ? "<p>" + esc(m.text) + "</p>" : "") + "</div></li>";
    }).join("");
    var over = minutes && total > minutes ? '<p class="cx-warn">The plan runs ' + total + " minutes; today has " + minutes + ".</p>" : "";
    return '<section class="cx-block"><h3>The period</h3>' + over + '<ol class="cx-moves">' + rows + "</ol></section>";
  }
  function questionsHtml(plan) {
    var qs = (plan && plan.questions) || [];
    if (!qs.length) return "";
    return '<section class="cx-block"><h3>Questions</h3><ol class="cx-qs">' + qs.map(function (q) {
      return "<li><p>" + esc(q.q) + "</p>" + (q.listen ? '<p class="cx-listen">Listen for: ' + esc(q.listen) + "</p>" : "") + "</li>";
    }).join("") + "</ol></section>";
  }
  function materialsHtml(list, owner) {
    if (!list || !list.length) return "";
    return '<section class="cx-block"><h3>Materials</h3><ul class="cx-mats">' + list.map(function (m) {
      return '<li><span class="cx-kind">' + esc(m.kind) + '</span> <a href="/generate/unit/' + esc(owner) + "/r/" + esc(m.id) + '">' +
             esc(m.title) + "</a></li>";
    }).join("") + "</ul></section>";
  }
  // What the lesson plan says to make. Each opens the Prep Room for this lesson with its kind picked and its
  // line as the instructions, to read and change there before anything is made.
  function makesHtml(l) {
    var list = l.makes || [];
    if (!list.length) return "";
    return '<section class="cx-block"><h3>To make</h3><ul class="cx-mats cx-makes">' + list.map(function (m) {
      var href = "/generate/unit/" + l.id + "?" + (m.format_id ? "make=" + encodeURIComponent(m.format_id) + "&" : "") +
                 "brief=" + encodeURIComponent(m.brief);
      return "<li>" + (m.format ? '<span class="cx-kind">' + esc(m.format) + "</span>" : "") + "<span>" + esc(m.label) + "</span>" +
             '<a class="cx-link" href="' + esc(href) + '">Make<span class="cx-sr"> ' + esc(m.label) + "</span></a></li>";
    }).join("") + "</ul></section>";
  }
  function renderToday() {
    var el = $("#v-today");
    if (!D.units.length || !lessons().length) {
      el.innerHTML = empty("No lessons yet", "Lay out the year's units and lessons in Plan, and the lesson for each class day shows here.",
                           '<button type="button" class="cx-btn" data-go="plan">Open Plan</button>');
      return;
    }
    var meet = D.meeting_today, head;
    if (meet) {
      head = '<p class="cx-day">' + day(D.today, true) + " · " + DAY[meet.schedule] + " · " + meet.minutes + " minutes</p>";
    } else {
      var nm = D.calendar.meetings.find(function (m) { return m.date > D.today; });
      var off = offOn(D.today);
      head = '<p class="cx-day">No class today' + (off ? " (" + esc(off) + ")" : "") + "." +
             (nm ? " Next class " + day(nm.date) + "." : "") + "</p>";
    }
    var nx = D.next && find(D.next.lesson);
    if (!nx) {
      el.innerHTML = head + empty("Every lesson is taught", "The course is finished for this year.");
      return;
    }
    var l = nx.l, u = nx.u, notes = [];
    if (meet && l.day_type && l.day_type !== meet.schedule) {
      notes.push("Planned for a " + DAY[l.day_type].toLowerCase() + " period (" + MIN[l.day_type] + " minutes); today is " + meet.minutes + ".");
    }
    if (l.date && l.date !== D.today) notes.push("On the plan for " + day(l.date) + ".");
    // a title that opens with its own passage ("John 6:25-29 | Chasing the Baker") shows that passage once, as the link
    var lead = l.passage && l.title.indexOf(l.passage + " | ") === 0;
    var h2 = l.passage && l.passage === l.title ? ref(l.passage)
      : lead ? ref(l.passage) + " | " + esc(l.title.slice(l.passage.length + 3)) : esc(l.title);
    el.innerHTML = head + paceLine(u) +
      '<article class="cx-lesson">' +
        "<header><p class=\"cx-eyebrow\">Lesson " + (nx.li + 1) + " of " + u.lessons.length + "</p><h2>" + h2 + "</h2>" +
        (l.passage && l.passage !== l.title && !lead ? '<p class="cx-passage">' + ref(l.passage) + "</p>" : "") +
        notes.map(function (n) { return '<p class="cx-note">' + esc(n) + "</p>"; }).join("") + "</header>" +
        (l.plan && l.plan.objective ? '<p class="cx-obj">' + esc(l.plan.objective) + "</p>" : "") +
        movesHtml(l.plan, meet && meet.minutes) + questionsHtml(l.plan) + materialsHtml(l.materials, l.id) +
        (!(l.plan && (l.plan.moves || []).length) && !(l.materials || []).length
          ? '<p class="cx-thin">This lesson has no plan yet. <button type="button" class="cx-link" data-edit="' + esc(l.id) + '">Plan it</button></p>' : "") +
        '<footer class="cx-actions"><button type="button" class="cx-btn is-primary" data-taught="' + esc(l.id) + '">Mark taught</button>' +
        '<button type="button" class="cx-btn" data-edit="' + esc(l.id) + '">Edit lesson</button></footer>' +
      "</article>";
  }

  // ------------------------------------------------------------------ Year
  function renderYear() {
    var el = $("#v-year"), at = {};
    D.units.forEach(function (u, ui) {
      u.lessons.forEach(function (l) { if (l.date) at[l.date] = { ui: ui, u: u, l: l }; });
      (u.open || []).forEach(function (d) { at[d] = { ui: ui, u: u }; });
    });
    var days = D.calendar.meetings.map(function (m) { return { date: m.date, m: m }; })
      .concat(D.calendar.off.map(function (o) { return { date: o.date, off: o }; }))
      .sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    var months = [], cur = null;
    days.forEach(function (x) {
      var key = x.date.slice(0, 7);
      if (!cur || cur.key !== key) { cur = { key: key, days: [] }; months.push(cur); }
      cur.days.push(x);
    });
    var counts = { regular: 0, thursday: 0, half_day: 0 };
    D.calendar.meetings.forEach(function (m) { if (!m.tentative) counts[m.schedule]++; });
    var firm = counts.regular + counts.thursday + counts.half_day;
    var head = '<p class="cx-sum">' + firm + " class meetings: " + counts.regular + " regular (50 min), " + counts.thursday +
      " Thursdays (36), " + counts.half_day + " half days (26)" +
      (D.calendar.unplanned ? " · " + D.calendar.unplanned + " not yet in a unit" : "") +
      (D.calendar.short ? ' · <strong class="cx-warn">the units ask for ' + D.calendar.short + " more days than the year has</strong>" : "") + "</p>";
    var grid = months.map(function (mo) {
      var name = new Date(mo.key + "-15T12:00:00").toLocaleDateString(undefined, { month: "long" });
      var cells = mo.days.map(function (x) {
        var d = +x.date.slice(8), label;
        if (x.off) {
          label = day(x.date) + ", " + (x.off.label || x.off.kind.replace("_", " "));
          return '<li class="cx-d is-off" title="' + esc(label) + '"><span class="cx-sr">' + esc(label) + "</span></li>";
        }
        var a = at[x.date], cls = "cx-d s-" + x.m.schedule + (x.date === D.today ? " is-today" : "") + (x.m.tentative ? " is-tent" : "");
        label = day(x.date) + ", " + DAY[x.m.schedule];
        if (a) {
          cls += " u" + (a.ui % 5) + (a.l && a.l.taught_on ? " is-taught" : "") + (a.l ? "" : " is-open");
          label += ", " + a.u.title + (a.l ? ": " + a.l.title + (a.l.taught_on ? ", taught" : "") : ", no lesson yet");
        } else {
          cls += " is-free";
          label += ", not in a unit";
        }
        // A day opens its lesson by pointer; the unit cards and Plan's outline reach the same lessons by keyboard,
        // so the 150-odd days are not each a tab stop.
        if (!a) return '<li><span class="' + cls + '" title="' + esc(label) + '"><span aria-hidden="true">' + d +
                       '</span><span class="cx-sr">' + esc(label) + "</span></span></li>";
        return '<li><button type="button" tabindex="-1" class="' + cls + '" data-open="' + esc(a.l ? a.l.id : a.u.id) +
               '" aria-label="' + esc(label) + '" title="' + esc(label) + '">' + d + "</button></li>";
      }).join("");
      return '<section class="cx-month"><h3>' + esc(name) + '</h3><ol class="cx-days">' + cells + "</ol></section>";
    }).join("");
    var units = D.units.length ? '<h2 class="cx-h2">Units</h2><div class="tablewrap" tabindex="0" role="region" aria-label="Units">' +
      '<table class="cx-utable"><thead><tr><th scope="col">Unit</th><th scope="col">Passage</th><th scope="col">Class days</th>' +
      '<th scope="col">Taught</th></tr></thead><tbody>' + D.units.map(function (u, ui) {
        var taught = u.lessons.filter(function (l) { return l.taught_on; }).length;
        var when = u.first ? (u.first === u.last ? day(u.first) : day(u.first) + " – " + day(u.last)) : "none left";
        return '<tr class="u' + (ui % 5) + '"><th scope="row"><button type="button" class="cx-link cx-ulink" data-open="' + esc(u.id) + '">' +
               '<span class="cx-sw"></span>' + esc(u.title) + "</button></th><td>" + esc(u.passage || "") + "</td><td>" + when + "</td>" +
               "<td>" + taught + " of " + u.lessons.length + (u.pace && u.pace.behind ? ' <span class="cx-warn">· ' + u.pace.behind + " behind</span>" : "") +
               "</td></tr>";
      }).join("") + "</tbody></table></div>" : "";
    el.innerHTML = head + '<div class="cx-year">' + grid + "</div>" +
      '<p class="cx-key"><span class="cx-d s-regular is-free"></span> regular <span class="cx-d s-thursday is-free"></span> Thursday ' +
      '<span class="cx-d s-half_day is-free"></span> half day <span class="cx-d is-off"></span> no class · filled days are taught</p>' + units;
  }

  // ------------------------------------------------------------------ Plan
  function outline() {
    var c = D.course;
    var items = D.units.map(function (u, ui) {
      var ls = u.lessons.map(function (l, li) {
        return '<li><button type="button" class="cx-o' + (sel === l.id ? " is-sel" : "") + (l.taught_on ? " is-taught" : "") +
               '" data-sel="' + esc(l.id) + '" aria-current="' + (sel === l.id) + '"><span class="cx-o-n">' + (li + 1) + "</span>" +
               '<span class="cx-o-t">' + esc(l.title) + "</span>" + (l.date ? '<span class="cx-o-d">' + day(l.date) + "</span>" : "") +
               "</button></li>";
      }).join("");
      return '<li class="cx-ou"><button type="button" class="cx-o is-unit u' + (ui % 5) + (sel === u.id ? " is-sel" : "") +
             '" data-sel="' + esc(u.id) + '" aria-current="' + (sel === u.id) + '"><span class="cx-sw"></span><span class="cx-o-t">' + esc(u.title) +
             "</span><span class=\"cx-o-d\">" + u.lessons.length + "/" + u.meetings + "</span></button>" +
             (ls ? "<ol>" + ls + "</ol>" : "") + "</li>";
    }).join("");
    return '<nav class="cx-outline" aria-label="Course outline"><button type="button" class="cx-o is-course' + (sel === c.id ? " is-sel" : "") +
           '" data-sel="' + esc(c.id) + '">' + esc(c.title) + "</button><ol>" + items + "</ol>" +
           '<button type="button" class="cx-btn cx-add" data-add="unit">Add a unit</button></nav>';
  }
  function field(id, label, value, opts) {
    opts = opts || {};
    var input = opts.area
      ? '<textarea id="' + id + '" rows="' + (opts.rows || 3) + '">' + esc(value) + "</textarea>"
      : '<input id="' + id + '" type="' + (opts.type || "text") + '" value="' + esc(value) + '"' + (opts.min != null ? ' min="' + opts.min + '"' : "") + ">";
    return '<label class="cx-f" for="' + id + '"><span>' + esc(label) + "</span>" + input +
           (opts.hint ? '<small>' + esc(opts.hint) + "</small>" : "") + "</label>";
  }
  function movesEditor(plan) {
    var moves = (plan && plan.moves) || [];
    var rows = moves.map(function (m, i) { return moveRow(m, i); }).join("");
    return '<fieldset class="cx-fs"><legend>The period</legend><ol class="cx-medit" id="f-moves">' + rows + "</ol>" +
           '<button type="button" class="cx-link" data-addmove>Add a move</button></fieldset>';
  }
  function moveRow(m, i) {
    return '<li><input aria-label="Minutes" class="cx-min" type="number" min="0" max="90" value="' + esc(m.minutes || 0) + '">' +
           '<input aria-label="Move" class="cx-mt" value="' + esc(m.title) + '" placeholder="Hear, Work, Land…">' +
           '<textarea aria-label="What happens" class="cx-mx" rows="2">' + esc(m.text) + "</textarea>" +
           '<button type="button" class="cx-x" data-delmove aria-label="Remove this move">×</button></li>';
  }
  function questionsEditor(plan) {
    var qs = (plan && plan.questions) || [];
    return '<fieldset class="cx-fs"><legend>Questions</legend><ol class="cx-qedit" id="f-qs">' + qs.map(qRow).join("") + "</ol>" +
           '<button type="button" class="cx-link" data-addq>Add a question</button></fieldset>';
  }
  function qRow(q) {
    return '<li><textarea aria-label="Question" class="cx-qq" rows="2">' + esc(q.q) + '</textarea>' +
           '<textarea aria-label="Listen for" class="cx-ql" rows="2" placeholder="Listen for…">' + esc(q.listen) + "</textarea>" +
           '<button type="button" class="cx-x" data-delq aria-label="Remove this question">×</button></li>';
  }
  function detail() {
    var c = D.course, f = sel && sel !== c.id ? find(sel) : null;
    if (!f) {
      return '<div class="cx-page"><p class="cx-eyebrow">Course</p><h2>' + esc(c.title) + "</h2>" +
        '<p class="cx-thin">Sources pinned to the course feed every unit and lesson. Pin a commentary on each unit instead, with that unit\'s chapters, so a draft reads the part it needs.</p>' +
        field("f-notes", "What every draft should know", c.notes, { area: true, rows: 4 }) +
        '<div class="cx-actions"><button type="button" class="cx-btn is-primary" data-save="' + esc(c.id) + '">Save</button>' +
        '<a class="cx-btn" href="/generate/unit/' + esc(c.id) + '">Make for the course</a></div>' +
        '<div id="cx-sources" data-for="' + esc(c.id) + '"></div></div>';
    }
    if (!f.l) {
      var u = f.u;
      return '<div class="cx-page"><p class="cx-eyebrow">Unit ' + (f.ui + 1) + (u.first ? " · " + day(u.first) + " – " + day(u.last) : "") + "</p>" +
        field("f-title", "Title", u.title) +
        '<div class="cx-row">' + field("f-passage", "Passage", u.passage, { hint: "Like John 6 or John 6:1-71" }) +
        field("f-meetings", "Class days", u.meetings, { type: "number", min: 0, hint: u.lessons.length + " lessons planned" }) + "</div>" +
        field("f-notes", "What every draft for this unit should know", u.notes, { area: true }) +
        '<div class="cx-actions"><button type="button" class="cx-btn is-primary" data-save="' + esc(u.id) + '">Save</button>' +
        '<button type="button" class="cx-btn" data-add="lesson" data-parent="' + esc(u.id) + '">Add a lesson</button>' +
        '<a class="cx-btn" href="/generate/unit/' + esc(u.id) + '">Make for this unit</a>' +
        '<button type="button" class="cx-btn" data-up="' + esc(u.id) + '" aria-label="Move this unit earlier">Earlier</button>' +
        '<button type="button" class="cx-btn" data-down="' + esc(u.id) + '" aria-label="Move this unit later">Later</button>' +
        '<button type="button" class="cx-btn is-quiet" data-del="' + esc(u.id) + '">Delete unit</button></div>' +
        mixHtml(u) + materialsHtml(u.materials, u.id) + '<div id="cx-sources" data-for="' + esc(u.id) + '"></div></div>';
    }
    var l = f.l;
    var types = '<label class="cx-f" for="f-day"><span>Planned for</span><select id="f-day"><option value="">Any period</option>' +
      Object.keys(DAY).map(function (k) { return '<option value="' + k + '"' + (l.day_type === k ? " selected" : "") + ">" + DAY[k] + " (" + MIN[k] + " min)</option>"; }).join("") +
      "</select></label>";
    return '<div class="cx-page"><p class="cx-eyebrow">' + esc(f.u.title) + " · lesson " + (f.li + 1) +
      (l.date ? " · " + day(l.date) + " · " + DAY[l.schedule] + " (" + l.minutes + " min)" : " · no class day left in the unit") +
      (l.taught_on ? " · taught " + day(l.taught_on) : "") + "</p>" +
      field("f-title", "Title", l.title) +
      '<div class="cx-row">' + field("f-passage", "Passage", l.passage, { hint: "Like John 6:25-29" }) + types + "</div>" +
      field("f-obj", "What students should leave with", (l.plan || {}).objective, { area: true, rows: 2 }) +
      movesEditor(l.plan) + questionsEditor(l.plan) +
      field("f-notes", "What every draft for this lesson should know", l.notes, { area: true }) +
      '<div class="cx-actions"><button type="button" class="cx-btn is-primary" data-save="' + esc(l.id) + '">Save</button>' +
      '<a class="cx-btn" href="/generate/unit/' + esc(l.id) + '">Make for this lesson</a>' +
      (l.taught_on ? '<button type="button" class="cx-btn" data-untaught="' + esc(l.id) + '">Mark not taught</button>'
                   : '<button type="button" class="cx-btn" data-taught="' + esc(l.id) + '">Mark taught</button>') +
      '<button type="button" class="cx-btn" data-up="' + esc(l.id) + '" aria-label="Move this lesson earlier">Earlier</button>' +
      '<button type="button" class="cx-btn" data-down="' + esc(l.id) + '" aria-label="Move this lesson later">Later</button>' +
      '<button type="button" class="cx-btn is-quiet" data-del="' + esc(l.id) + '">Delete lesson</button></div>' +
      makesHtml(l) + materialsHtml(l.materials, l.id) + '<div id="cx-sources" data-for="' + esc(l.id) + '"></div></div>';
  }
  // The kinds of material made across a unit, so a run of the same handout shows before class grows dull.
  function mixHtml(u) {
    var n = {}, total = 0;
    (u.materials || []).concat.apply(u.materials || [], u.lessons.map(function (l) { return l.materials || []; }))
      .forEach(function (m) { n[m.kind] = (n[m.kind] || 0) + 1; total++; });
    if (!total) return "";
    var kinds = Object.keys(n).sort(function (a, b) { return n[b] - n[a]; });
    var bare = u.lessons.filter(function (l) { return !(l.materials || []).length; }).length;
    return '<section class="cx-block"><h3>The mix in this unit</h3><p class="cx-mix">' + kinds.map(function (k) {
      return '<span class="cx-kind">' + esc(k) + (n[k] > 1 ? " × " + n[k] : "") + "</span>";
    }).join(" ") + "</p>" + (bare ? '<p class="cx-thin">' + bare + (bare === 1 ? " lesson has" : " lessons have") + " nothing made yet.</p>" : "") +
      "</section>";
  }
  function renderPlan() {
    if (!sel) sel = D.next ? D.next.lesson : D.course.id;
    if (sel !== D.course.id && !find(sel)) sel = D.course.id;
    $("#v-plan").innerHTML = '<div class="cx-plan">' + outline() + detail() + "</div>";
    loadSources();
  }
  function loadSources() {
    var box = $("#cx-sources");
    if (!box) return;
    var id = box.getAttribute("data-for");
    box.innerHTML = '<p class="cx-thin">Finding what feeds this…</p>';
    api("GET", "/api/john/nodes/" + id + "/sources").then(function (s) {
      if ($("#cx-sources") !== box) return;
      var list = function (title, items, hint, removable) {
        if (!items.length) return "";
        return '<section class="cx-block"><h3>' + esc(title) + '</h3>' + (hint ? '<p class="cx-thin">' + esc(hint) + "</p>" : "") +
          '<ul class="cx-src">' + items.map(function (x) {
            return "<li><span>" + esc(x.label) + "</span>" + (x.via ? ' <small>from ' + esc(x.via) + "</small>" : "") +
              (removable ? ' <button type="button" class="cx-link" data-hide="' + esc(x.id) + '">Remove here</button>' : "") + "</li>";
          }).join("") + "</ul></section>";
      };
      var hidden = (s.hidden || []).length
        ? '<p class="cx-thin">' + s.hidden.length + ' removed here. <button type="button" class="cx-link" data-unhide-all>Bring them back</button></p>' : "";
      var none = !s.own.length && !s.above.length && !s.passage.length;
      box.innerHTML = '<h2 class="cx-h2">What feeds this</h2>' +
        (none ? '<p class="cx-thin">Nothing yet. Pin sources from the Prep Room or the Living Library, or give this a passage.</p>' : "") +
        list("Pinned here", s.own, "", false) +
        list("From above", s.above, "Pinned on the course or the unit, so every draft here uses them.", false) +
        list("On this passage", s.passage, "Class-shelf items whose passage overlaps this one.", true) + hidden;
      box.dataset.hidden = JSON.stringify(s.hidden || []);
    }).catch(function (e) { box.innerHTML = '<p class="cx-warn">' + esc(e.message) + "</p>"; });
  }
  function collect(id) {
    var f = find(id), body = {};
    var v = function (s) { var el = $(s); return el ? el.value : undefined; };
    if (v("#f-title") !== undefined) body.title = v("#f-title");
    if (v("#f-passage") !== undefined) body.passage = v("#f-passage");
    if (v("#f-notes") !== undefined) body.notes = v("#f-notes");
    if (v("#f-meetings") !== undefined) body.meetings = +v("#f-meetings") || 0;
    if (f && f.l) {
      body.day_type = v("#f-day") || null;
      body.plan = {
        objective: v("#f-obj") || "",
        moves: Array.prototype.map.call(document.querySelectorAll("#f-moves li"), function (li) {
          return { minutes: +$(".cx-min", li).value || 0, title: $(".cx-mt", li).value, text: $(".cx-mx", li).value };
        }).filter(function (m) { return m.title || m.text; }),
        questions: Array.prototype.map.call(document.querySelectorAll("#f-qs li"), function (li) {
          return { q: $(".cx-qq", li).value, listen: $(".cx-ql", li).value };
        }).filter(function (q) { return q.q; }),
      };
    }
    return body;
  }
  function siblings(id) {
    var f = find(id);
    return f.l ? f.u.lessons : D.units;
  }

  // ------------------------------------------------------------------ actions
  document.addEventListener("click", function (ev) {
    var t = ev.target.closest("button, a");
    if (!t || !$("#cx").contains(t)) return;
    var a = function (n) { return t.getAttribute(n); };
    if (t.getAttribute("role") === "tab") { show(t.id.slice(4)); return; }
    if (a("data-go")) { show(a("data-go")); return; }
    if (a("data-ref") && window.Passage) { Passage.open(a("data-ref"), t); return; }
    if (a("data-open")) { sel = a("data-open"); show("plan"); return; }
    if (a("data-sel")) { sel = a("data-sel"); renderPlan(); var d = $(".cx-page h2, .cx-page input"); if (d) d.focus(); return; }
    if (a("data-edit")) { sel = a("data-edit"); show("plan"); return; }
    if (a("data-taught") || a("data-untaught")) {
      var id = a("data-taught") || a("data-untaught"), on = a("data-taught") ? D.today : null;
      api("POST", "/api/john/nodes/" + id + "/taught", { on: on }).then(function () {
        return load().then(function () {
          if (on) toast("Marked taught.", function () {
            api("POST", "/api/john/nodes/" + id + "/taught", { on: null }).then(load);
          });
        });
      }).catch(function (e) { say(e.message); });
      return;
    }
    if (a("data-save")) {
      var sid = a("data-save");
      t.disabled = true;
      api("PATCH", "/api/john/nodes/" + sid, collect(sid)).then(function () { return load(); })
        .then(function () { toast("Saved."); }).catch(function (e) { say(e.message); }).then(function () { t.disabled = false; });
      return;
    }
    if (a("data-add")) {
      var kind = a("data-add"), parent = a("data-parent") || D.course.id;
      var title = kind === "unit" ? "New unit" : "New lesson";
      api("POST", "/api/john/nodes", { kind: kind, parent_id: parent, title: title, meetings: kind === "unit" ? 5 : undefined })
        .then(function (d) { sel = d.node.id; return load(); })
        .then(function () { var i = $("#f-title"); if (i) { i.focus(); i.select(); } })
        .catch(function (e) { say(e.message); });
      return;
    }
    if (a("data-up") || a("data-down")) {
      var mid = a("data-up") || a("data-down"), sib = siblings(mid);
      var at = sib.findIndex(function (x) { return x.id === mid; }) + (a("data-up") ? -1 : 1);
      if (at < 0 || at >= sib.length) return;
      api("POST", "/api/john/nodes/" + mid + "/move", { position: at }).then(load).catch(function (e) { say(e.message); });
      return;
    }
    if (a("data-del")) {
      var did = a("data-del"), what = find(did);
      var lesson = what && what.l;
      Shell.ask({ title: lesson ? "Delete this lesson?" : "Delete this unit?",
                  body: lesson ? "What the Prep Room made for it goes too." : "Its lessons and what the Prep Room made for them go too.",
                  ok: "Delete", danger: true })
        .then(function (yes) {
          if (!yes) return;
          return api("DELETE", "/api/john/nodes/" + did).then(function () { sel = null; return load(); });
        }).catch(function (e) { say(e.message); });
      return;
    }
    if (a("data-hide") !== null && t.hasAttribute("data-hide")) {
      var box = $("#cx-sources");
      api("POST", "/api/john/nodes/" + box.getAttribute("data-for") + "/hide", { item_id: a("data-hide"), hidden: true })
        .then(loadSources).catch(function (e) { say(e.message); });
      return;
    }
    if (t.hasAttribute("data-unhide-all")) {
      var b2 = $("#cx-sources"), nid = b2.getAttribute("data-for"), ids = JSON.parse(b2.dataset.hidden || "[]");
      Promise.all(ids.map(function (i) { return api("POST", "/api/john/nodes/" + nid + "/hide", { item_id: i, hidden: false }); }))
        .then(loadSources).catch(function (e) { say(e.message); });
      return;
    }
    if (t.hasAttribute("data-addmove")) { $("#f-moves").insertAdjacentHTML("beforeend", moveRow({ minutes: 5 })); $("#f-moves li:last-child .cx-mt").focus(); return; }
    if (t.hasAttribute("data-delmove") || t.hasAttribute("data-delq")) { t.closest("li").remove(); return; }
    if (t.hasAttribute("data-addq")) { $("#f-qs").insertAdjacentHTML("beforeend", qRow({})); $("#f-qs li:last-child .cx-qq").focus(); }
  });

  // Arrow keys move between the three views, as a tab list does.
  $(".cx-views").addEventListener("keydown", function (ev) {
    var i = VIEWS.indexOf(view);
    if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
      ev.preventDefault();
      show(VIEWS[(i + (ev.key === "ArrowRight" ? 1 : VIEWS.length - 1)) % VIEWS.length], true);
    }
  });

  // The address names the view, so back, forward and a pasted link land on it.
  window.addEventListener("hashchange", function () {
    var h = location.hash.slice(1);
    if (VIEWS.indexOf(h) >= 0 && h !== view) show(h);
  });

  VIEWS.forEach(function (k) {
    var on = k === view;
    $("#tab-" + k).setAttribute("aria-selected", on ? "true" : "false");
    $("#tab-" + k).tabIndex = on ? 0 : -1;
    $("#v-" + k).hidden = !on;
  });
  load();
})();
