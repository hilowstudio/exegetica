/* The Living Library's front room for everyone signed in (templates/library.html, decision 0029): a shelf for each
   class the person takes or teaches, then the Reading Room books they shelved. Covers come from static/js/covers.js,
   the same house covers the Reading Room draws. A teacher's videos, podcasts and copies are static/js/library.js. */
(function(){
"use strict";
var main = document.querySelector(".lib-main");
if(!main || main.hasAttribute("data-signed-out")) return;
var teacher = main.hasAttribute("data-teacher");
var $ = function(id){ return document.getElementById(id); };
var e = function(s){ return String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); };
var H = {courses: [], mine: [], classes: [], books: [], progress: {}};
var READ_MIN = 7;   // as the Reading Room: a book counts as begun after this many pages
// a class text with no book to open is bound in its subject's cloth
var SUBJECT = {"Bible": "Christianity", "English": "Literary & Classics", "Social Studies": "History",
  "Science": "Science & Nature", "Mathematics": "Reference & Knowledge", "World Languages": "Language & Reference",
  "Health": "Health & Medicine", "Agriculture": "Science & Nature"};

function api(method, url, body){
  return fetch(url, {method: method, credentials: "same-origin", headers: body ? {"Content-Type": "application/json"} : {},
    body: body ? JSON.stringify(body) : undefined})
    .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){
      if(!r.ok) throw new Error(d.error || "That didn't work. Try again in a minute."); return d; }); });
}
function started(slug){ var p = H.progress[slug]; return !!(p && p.pages >= READ_MIN); }
function chapterCap(b){
  var p = H.progress[b.slug];
  if(!p || p.pages < READ_MIN) return "";
  return (b.chapters > 1 && p.section) ? "Chapter " + p.section + " of " + b.chapters : "In progress";
}

// What Select can do with a tile (static/js/select.js, decision 0031): a unit's source, a class shelf's item, or a
// resource to copy for Save to, and how Remove takes it off the shelf it stands on. k names the tile where it stands,
// same the thing itself, so a book picked on a class shelf and on your own goes once. A teacher's tiles only: students
// don't send things anywhere.
function sel(el, d){ if(teacher && d) el.setAttribute("data-sel", JSON.stringify(d)); return el; }
function bookSel(slug, title, k, rm){ return {k: k || "book:" + slug, same: "book:" + slug, label: title,
  unit: {kind: "book", ref: {slug: slug, coverage: {}}}, place: {kind: "book", ref: {slug: slug}}, rm: rm || null}; }
// a class shelf's item comes off that shelf; another teacher's book or upload goes back to their own (take_off)
function offClass(a, c){ return {url: "/api/shelf/items/" + a.id, from: c.name,
  back: !a.yours && a.added_name && a.kind !== "resource" ? shortName(a.added_name) : ""}; }

// Remove takes tiles off at once and the server hears after the Undo has had its moment (select.js); until then the
// tiles it named stay hidden through any redraw, and once the server has them they leave the shelves' data
var gone = {}, loaded = false;
function shown(k){ return !gone[k]; }
document.addEventListener("shelf:gone", function(ev){
  var d = ev.detail || {};
  (d.keys || []).forEach(function(k){
    if(d.on) gone[k] = 1; else delete gone[k];
    if(d.dropped){
      H.books = H.books.filter(function(b){ return "book:" + b.slug !== k; });
      H.docs = (H.docs || []).filter(function(x){ return "doc:" + x.id !== k; });
      H.prep = (H.prep || []).filter(function(r){ return "res:" + r.id !== k; });
      H.classes.forEach(function(c){ c.added = (c.added || []).filter(function(a){ return "cls:" + a.id !== k; }); });
    }
  });
  if(loaded){ drawClasses(); drawMine(); if(teacher){ drawDocs(); drawPrep(); } }
});

// ---- the class shelves ----
function classCell(w, course){
  if(w.book) return {el: sel(Covers.cover(w.book, {wrap: Covers.wrap(), started: started(w.book.slug)}),
    bookSel(w.book.slug, w.book.title, "work:" + course.key + ":" + w.book.slug)), cap: chapterCap(w.book)};
  var bound = {title: w.title, author: w.author, sections: [SUBJECT[course.subject] || ""]};
  if(w.state === "outline"){
    var b = Covers.cover(bound, {button: true, sec: "Outline"});
    b.setAttribute("aria-label", w.title + ", its outline");
    b.addEventListener("click", function(){ openOutline(w, b); });
    sel(b, {k: "work:" + course.key + ":outline:" + w.outline, same: "outline:" + w.outline, label: w.title,
      unit: {kind: "outline", ref: {key: w.outline, parts: []}}});
    return {el: b, cap: "Outline", phone: true};
  }
  var still = Covers.cover(bound, {href: false, sec: "In print"});
  still.setAttribute("role", "img");
  still.setAttribute("aria-label", w.title + (w.author ? ", by " + w.author : "") + ". The class reads it in print.");
  return {el: still, cap: "In print", phone: true};
}
// ---- what teachers placed on a class shelf (decision 0029, phase 2) ----
// A teacher sees who added each item, and which are for teachers alone; a student sees only what is theirs, and no
// names. In a class's Edit mode a teacher can change who sees an item, or take it off.
var MORE = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="6" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="18" cy="12" r="1.6"/></svg>';
var PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 7l9 5-9 5z"/></svg>';
function shortName(n){ var p = String(n || "").trim().split(/\s+/); return p.length > 1 ? p[0].charAt(0) + ". " + p[p.length - 1] : (p[0] || ""); }
function addedCap(a){
  if(!teacher) return "";
  var who = a.yours ? "you" : (a.added_name ? shortName(a.added_name) : "");
  return [a.audience === "teachers" ? "For teachers" : "", who ? "Added by " + who : ""].filter(Boolean).join("\n");
}
function stamp(t){ t = Math.max(0, Math.floor(t || 0)); var m = Math.floor(t / 60), s = t % 60; return m + ":" + (s < 10 ? "0" : "") + s; }
function moreChip(a, c, host){
  if(!teacher) return;
  var b = document.createElement("button");
  b.type = "button"; b.className = "cv-more"; b.innerHTML = MORE;
  b.setAttribute("aria-haspopup", "true"); b.setAttribute("aria-expanded", "false");
  b.setAttribute("aria-label", "Options for " + a.label + " on the " + c.name + " shelf");
  b.onclick = function(ev){
    ev.preventDefault(); ev.stopPropagation();
    var url = a.book ? location.origin + "/read/" + encodeURIComponent(a.book.slug) : a.video ? a.video.url :
      a.podcast ? location.origin + a.podcast.url : location.origin + "/read/doc/" + a.id;
    Passage.menu(b, "Options for " + a.label, [
      {label: "Share to Classroom…", act: function(){ Passage.classroom(url, a.label); }},
      {label: "Students see it", checked: a.audience === "students", act: function(){ setAudience(a, c, a.audience === "students" ? "teachers" : "students"); }},
      {label: "Take off the shelf", danger: true, act: function(){ takeOff(a, c); }}
    ]);
  };
  host.appendChild(b);
}
function addedDoc(a, c){
  var cell = document.createElement("div"); cell.className = "placed";
  var r = a.ref || {}, d = a.doc.type === "resource"
    ? (a.yours && r.resource_id ? {k: "cls:" + a.id, same: "res:" + r.resource_id, label: a.label, place: {kind: "resource", ref: {resource_id: r.resource_id}}, copy: r.resource_id}
                                : {k: "cls:" + a.id, label: a.label})          // another teacher's resource stays in their Prep Room
    : {k: "cls:" + a.id, label: a.label, unit: {kind: "shelf", ref: {item_id: a.id}}, place: {kind: a.kind, ref: {item_id: a.id}}};
  d.rm = offClass(a, c);
  cell.appendChild(sel(docTile(a.doc, "/read/doc/" + a.id), d));
  moreChip(a, c, cell);
  return {el: cell, cap: addedCap(a)};
}
function addedBook(a, c){
  var cell = document.createElement("div"); cell.className = "placed";
  cell.appendChild(sel(Covers.cover(a.book, {wrap: Covers.wrap(), started: started(a.book.slug)}),
    bookSel(a.book.slug, a.book.title, "cls:" + a.id, offClass(a, c))));
  moreChip(a, c, cell);
  return {el: cell, cap: addedCap(a) || chapterCap(a.book)};
}
function videoTile(a, c){
  var v = a.video, cell = document.createElement("div"); cell.className = "placed vcell";
  var from = v.start != null ? "From " + stamp(v.start) : "";
  var t = document.createElement("a");
  t.className = "vtile"; t.href = v.url || "#";   // the watch page, inside Exegetica (decision 0034)
  t.setAttribute("aria-label", v.title + (from ? ", " + from.toLowerCase() : "") + ". Opens the video.");
  t.innerHTML = '<span class="vt-shot">' + (v.thumbnail ? '<img src="' + e(v.thumbnail) + '" alt="" loading="lazy">' : "") +
    '<span class="vt-play">' + PLAY + '</span>' + (from ? '<span class="vt-from">' + e(from) + '</span>' : "") + '</span>' +
    '<span class="vt-t">' + e(v.title) + '</span><span class="vt-s">' + e(v.note || v.sub || "") + '</span>';
  var r = a.ref || {};
  cell.appendChild(sel(t, {k: "cls:" + a.id, label: a.label, unit: {kind: "library", ref: {item_id: r.item_id}},
    place: {kind: "video", ref: {item_id: r.item_id, start: r.start, end: r.end, quote: r.quote, note: r.note}}, rm: offClass(a, c)}));
  moreChip(a, c, cell);
  return {el: cell, cap: addedCap(a)};
}
// a podcast episode, or a moment in one (decision 0031): its show's art, opening Exegetica's own player
function podTile(a, c){
  var p = a.podcast, cell = document.createElement("div"); cell.className = "placed vcell";
  var from = p.start != null ? "From " + stamp(p.start) : "";
  var t = document.createElement("a");
  t.className = "vtile ptile"; t.href = p.url;
  t.setAttribute("aria-label", p.title + (from ? ", " + from.toLowerCase() : "") + ". Opens the player.");
  t.innerHTML = '<span class="vt-shot sq">' + (p.artwork ? '<img src="' + e(p.artwork) + '" alt="" loading="lazy">' : "") +
    '<span class="vt-play">' + PLAY + '</span>' + (from ? '<span class="vt-from">' + e(from) + '</span>' : (p.length ? '<span class="vt-from">' + e(p.length) + '</span>' : "")) + '</span>' +
    '<span class="vt-t">' + e(p.title) + '</span><span class="vt-s">' + e(p.note || p.show || "") + '</span>';
  var r = a.ref || {};
  cell.appendChild(sel(t, {k: "cls:" + a.id, label: a.label, unit: {kind: "library", ref: {item_id: r.item_id}},
    place: {kind: "podcast", ref: {item_id: r.item_id, guid: r.guid, start: r.start, end: r.end, quote: r.quote, note: r.note}}, rm: offClass(a, c)}));
  moreChip(a, c, cell);
  return {el: cell, cap: addedCap(a)};
}
function videoStrip(cells, c, word, sq){
  word = word || "Videos";
  var box = document.createElement("div"); box.className = "cls-sub";
  box.innerHTML = '<h3 class="cls-sub-h">' + e(word) + '</h3>';
  var strip = document.createElement("div"); strip.className = "fr-books " + (sq ? "sq" : "wide"); strip.setAttribute("role", "list");
  strip.setAttribute("aria-label", word + " for " + c.name);
  cells.forEach(function(x){
    var cell = document.createElement("div"); cell.className = "fr-cell"; cell.setAttribute("role", "listitem");
    cell.appendChild(x.el);
    if(x.cap){ var p = document.createElement("div"); p.className = "fr-cap" + (x.cap.indexOf("\n") >= 0 ? " fr-cap-2" : ""); p.textContent = x.cap; cell.appendChild(p); }
    strip.appendChild(cell);
  });
  box.appendChild(strip);
  return box;
}
function setAudience(a, c, to){
  api("PATCH", "/api/shelf/items/" + a.id, {audience: to}).then(function(){
    load();
    Shell.toast((to === "students" ? "Students see " : "Only teachers see ") + a.label + " now", {undo: function(){
      api("PATCH", "/api/shelf/items/" + a.id, {audience: a.audience}).then(load).catch(function(err){ Shell.toast(err.message); });
    }});
  }).catch(function(err){ Shell.toast(err.message); });
}
// Off the shelf at once; the server hears once the Undo has had its moment (rule F3), so an Undo never has to
// rebuild a class copy. Another teacher's book or upload goes back to their shelf; a resource stays in their Prep Room.
var pendingOff = {}, EDITING = {};
function takeOff(a, c){
  var i = (c.added || []).indexOf(a); if(i < 0) return;
  c.added.splice(i, 1); drawClasses();
  var back = !a.yours && a.added_name && a.kind !== "resource";
  pendingOff[a.id] = setTimeout(function(){
    delete pendingOff[a.id];
    api("DELETE", "/api/shelf/items/" + a.id).then(load).catch(function(err){ Shell.toast(err.message); load(); });
  }, 6500);
  Shell.toast("Took " + a.label + " off the " + c.name + " shelf" + (back ? ". It goes back to " + shortName(a.added_name) + "'s shelf" : ""), {undo: function(){
    clearTimeout(pendingOff[a.id]); delete pendingOff[a.id]; c.added.splice(i, 0, a); drawClasses();
  }});
}
window.addEventListener("pagehide", function(){
  Object.keys(pendingOff).forEach(function(id){ clearTimeout(pendingOff[id]);
    fetch("/api/shelf/items/" + id, {method: "DELETE", credentials: "same-origin", keepalive: true}); });
});

function drawClasses(){
  var box = $("class-shelves"); box.innerHTML = "";
  $("classes-edit").hidden = !H.mine.length;
  if(H.guest){              // an account from outside the school takes no classes (decision 0005)
    box.innerHTML = '<div class="class-invite"><p>Class shelves are for Yorkville Christian School accounts. ' +
      'Books you keep from the Reading Room go on your own shelf.</p></div>';
    return;
  }
  if(!H.mine.length){
    box.innerHTML = '<div class="class-invite"><p>' + (teacher
      ? "Choose the classes you teach, and the school's books for them come to the top of your shelves."
      : "Choose the classes you take, and the school's books for them come to the top of your shelves.") + '</p>' +
      '<button type="button" class="add-btn" id="classes-first">Choose your classes</button></div>';
    $("classes-first").onclick = openPicker;
    return;
  }
  H.classes.forEach(function(c, i){
    var note = [c.subject, c.grades ? (c.grades.indexOf("-") > 0 ? "grades " : "grade ") + c.grades : ""].filter(Boolean).join(" · ");
    var added = (c.added || []).filter(function(a){ return shown("cls:" + a.id); });
    var books = c.works.map(function(w){ return classCell(w, c); })
      .concat(added.filter(function(a){ return a.book; }).map(function(a){ return addedBook(a, c); }))
      .concat(added.filter(function(a){ return a.doc; }).map(function(a){ return addedDoc(a, c); }));
    var vids = added.filter(function(a){ return a.video; }).map(function(a){ return videoTile(a, c); });
    var pods = added.filter(function(a){ return a.podcast; }).map(function(a){ return podTile(a, c); });
    var block = document.createElement("div"); block.className = "cls"; block.id = "cls-block-" + i;
    if(books.length){
      block.appendChild(Covers.row("cls-" + i, c.name, note, books));
    } else {
      var head = document.createElement("section"); head.className = "fr-row";
      head.innerHTML = '<div class="fr-h"><h2 id="cls-' + i + '">' + e(c.name) + '</h2><span>' + e(note) + '</span></div>' +
        (vids.length || pods.length ? "" : '<p class="sg-note">' + (teacher
          ? "The school's book list names no texts for this class. Save a book, a video or a podcast episode to it, and the class sees it here."
          : "Nothing is on this shelf yet.") + '</p>');
      block.appendChild(head);
    }
    if(vids.length) block.appendChild(videoStrip(vids, c));
    if(pods.length) block.appendChild(videoStrip(pods, c, "Podcasts", true));
    if(teacher && added.length){            // a class's own Edit, beside its name
      var ed = document.createElement("button");
      ed.type = "button"; ed.className = "sg-act cls-edit"; ed.textContent = "Edit"; ed.setAttribute("aria-pressed", "false");
      ed.setAttribute("aria-label", "Edit the " + c.name + " shelf");
      // Edit mode outlasts a redraw (a take-off, its Undo, a reload), so a teacher can clear several items in one go
      var set = function(on){ EDITING[c.key] = on; block.classList.toggle("editing", on);
        ed.textContent = on ? "Done" : "Edit"; ed.setAttribute("aria-pressed", String(on)); };
      ed.onclick = function(){ set(!block.classList.contains("editing")); };
      set(!!EDITING[c.key]);
      var fh = block.querySelector(".fr-h"), nav = fh.querySelector(".fr-nav");
      fh.insertBefore(ed, nav || null);
    }
    box.appendChild(block);
  });
}

// ---- a teacher's uploads and links (decision 0029, phase 3) ----
// A book is bound in cloth; an article, a handout or a document is a sheet. Both open in the reading view.
var KIND_WORD = {book: "Book", article: "Article", handout: "Handout", document: "Document", sermon: "Sermon Transcript"};
var KIND_SHORT = {sermon: "Sermon"};
function docTile(d, href){
  if(d.type === "book") return Covers.cover({title: d.title, author: d.author, sections: ["Literary & Classics"]}, {href: href, sec: "Your copy"});
  var a = document.createElement("a"); a.className = "leaf"; a.href = href;
  var word = d.type === "resource" ? (d.kind_word || "Resource") : (KIND_WORD[d.type] || "Document");   // a resource: Quiz, Study Guide…
  var short = d.type !== "resource" && KIND_SHORT[d.type];   // a phone's narrow tile can't hold "Sermon Transcript" on one line
  a.innerHTML = '<span class="pp-title">' + e(d.title) + '</span>' +
    ((d.author || d.site) ? '<span class="pp-by">' + e(d.author || d.site) + '</span>' : "") +
    '<span class="pp-lines" aria-hidden="true"></span><span class="pp-kind">' +
    (short ? '<span class="pp-k-long">' + e(word) + '</span><span class="pp-k-short">' + e(short) + '</span>' : e(word)) + '</span>';
  return a;
}
var pendingDel = {};
window.addEventListener("pagehide", function(){
  Object.keys(pendingDel).forEach(function(id){ clearTimeout(pendingDel[id]);
    fetch("/api/shelf/docs/" + id, {method: "DELETE", credentials: "same-origin", keepalive: true}); });
});
function drawDocs(){
  var sec = $("docs"); if(!sec) return;
  var list = (H.docs || []).filter(function(d){ return shown("doc:" + d.id); }); sec.hidden = false;
  $("docs-edit").hidden = !list.length;
  var box = $("my-docs");
  if(!list.length){
    sec.classList.remove("editing"); $("docs-edit").textContent = "Edit"; $("docs-edit").setAttribute("aria-pressed", "false");
    box.innerHTML = '<p class="sg-note">Upload a book, an article, a handout or notes, or save a web page, with <b>Add</b>. Each is filed as the kind of thing it is, and stays yours until you share it with a class.</p>';
    return;
  }
  var grid = document.createElement("div"); grid.className = "shelf-grid";
  list.forEach(function(d){
    var cell = document.createElement("div"); cell.className = "placed doc-cell";
    cell.appendChild(sel(docTile(d, "/read/doc/" + d.id), {k: "doc:" + d.id, label: d.title,
      unit: {kind: "shelf", ref: {item_id: d.id}}, place: {kind: d.kind, ref: {item_id: d.id}},
      rm: {url: "/api/shelf/docs/" + d.id, del: d.kind === "link" ? "link" : "upload"}}));   // an upload lives only here: Remove deletes it
    var more = document.createElement("button");
    more.type = "button"; more.className = "cv-more"; more.innerHTML = MORE;
    more.setAttribute("aria-haspopup", "true"); more.setAttribute("aria-expanded", "false");
    more.setAttribute("aria-label", "Options for " + d.title);
    more.onclick = function(ev){ ev.preventDefault(); ev.stopPropagation(); docMenu(d, more); };
    cell.appendChild(more);
    if(d.suggested){
      var cap = document.createElement("div"); cap.className = "fr-cap fr-cap-2";   // a short sentence, free to wrap
      cap.textContent = {pending: "Suggested for the Reading Room", approved: "Approved for the Reading Room", declined: "Not added to the Reading Room"}[d.suggested] || "";
      cell.appendChild(cap);
    }
    grid.appendChild(cell);
  });
  box.innerHTML = ""; box.appendChild(grid);
}
function saveDoc(d, anchor){
  Passage.addToUnit({kind: "shelf", ref: {item_id: d.id}, label: d.title}, anchor, null, {
    place: {kind: d.kind, ref: {item_id: d.id}, label: d.title},
    hold: d.kind === "link" ? {kind: "link", key: d.url} : {kind: "upload", key: d.id},
    share: {shelf: true, title: d.title}});
}
function docMenu(d, anchor){
  Passage.menu(anchor, "Options for " + d.title, [
    {label: "Open", act: function(){ location.href = "/read/doc/" + d.id; }},
    {label: "Save to…", act: function(){ saveDoc(d, anchor); }},
    {label: "Rename", act: function(){ renameDoc(d); }},
    {label: "File as…", act: function(){
      Passage.menu(anchor, "File " + d.title + " as", ["book", "article", "handout", "document", "sermon"].map(function(k){
        return {label: KIND_WORD[k], checked: d.type === k, act: function(){ patchDoc(d, {type: k}, "Filed “" + d.title + "” as " + (k === "article" ? "an " : "a ") + KIND_WORD[k].toLowerCase()); }};
      }));
    }},
    d.type === "book" && d.kind === "upload" && !d.suggested ? {label: "Suggest for the Reading Room", act: function(){ suggestDoc(d); }} : null,
    {label: "Delete", danger: true, act: function(){ deleteDoc(d); }}
  ].filter(Boolean));
}
function patchDoc(d, body, said){
  api("PATCH", "/api/shelf/docs/" + d.id, body).then(function(){ if(said) Shell.toast(said); load(); })
    .catch(function(err){ Shell.toast(err.message); });
}
async function renameDoc(d){
  var t = await Shell.ask({title: "Rename", ok: "Rename", input: {label: "Title", value: d.title, max: 200},
    validate: function(x){ return x ? "" : "Give it a title."; }});
  if(t && t !== d.title) patchDoc(d, {title: t});
}
async function suggestDoc(d){
  var why = await Shell.ask({title: "Suggest for the Reading Room",
    body: "If everyone may read “" + d.title + "”, the maker can add it to the Reading Room. Say why: the year it was published, or its open license.",
    ok: "Suggest", input: {label: "Why everyone may read it", value: "", max: 500},
    validate: function(x){ return x.length >= 6 ? "" : "Say why everyone may read it."; }});
  if(!why) return;
  api("POST", "/api/shelf/docs/" + d.id + "/suggest", {basis: why}).then(function(){ Shell.toast("Suggested. The maker will decide."); load(); })
    .catch(function(err){ Shell.toast(err.message); });
}
function deleteDoc(d){
  var i = H.docs.indexOf(d); if(i < 0) return;
  H.docs.splice(i, 1); drawDocs();
  pendingDel[d.id] = setTimeout(function(){
    delete pendingDel[d.id];
    api("DELETE", "/api/shelf/docs/" + d.id).catch(function(err){ H.docs.splice(i, 0, d); drawDocs(); Shell.toast(err.message); });
  }, 6500);
  Shell.toast("Deleted “" + d.title + "”", {undo: function(){ clearTimeout(pendingDel[d.id]); delete pendingDel[d.id]; H.docs.splice(i, 0, d); drawDocs(); }});
}
// ---- what a teacher put on their own shelf from the Prep Room (decision 0029, phase 4) ----
// Each opens where it lives, in its unit; taking it off the shelf leaves it there.
function drawPrep(){
  var sec = $("prep"); if(!sec) return;
  var list = (H.prep || []).filter(function(r){ return shown("res:" + r.id); }); sec.hidden = !list.length;
  if(!list.length){ sec.classList.remove("editing"); return; }
  var grid = document.createElement("div"); grid.className = "shelf-grid";
  list.forEach(function(r){
    var cell = document.createElement("div"); cell.className = "placed";
    cell.appendChild(sel(docTile({type: "resource", kind_word: r.kind_word, title: r.title}, r.href),
      {k: "res:" + r.id, same: "res:" + r.id, label: r.title, place: {kind: "resource", ref: {resource_id: r.id}}, copy: r.id,
       rm: {url: "/api/shelf/resources/" + r.id}}));
    var more = document.createElement("button");
    more.type = "button"; more.className = "cv-more"; more.innerHTML = MORE;
    more.setAttribute("aria-haspopup", "true"); more.setAttribute("aria-expanded", "false");
    more.setAttribute("aria-label", "Options for " + r.title);
    more.onclick = function(ev){ ev.preventDefault(); ev.stopPropagation();
      Passage.menu(more, "Options for " + r.title, [
        {label: "Open in the Prep Room", act: function(){ location.href = r.href; }},
        {label: "Take off your shelf", act: function(){
          var i = H.prep.indexOf(r); if(i >= 0) H.prep.splice(i, 1); drawPrep();
          api("DELETE", "/api/shelf/resources/" + r.id).then(function(){
            Shell.toast("Took “" + r.title + "” off your shelf. It's still in its unit.", {undo: function(){
              api("PUT", "/api/shelf/resources/" + r.id).then(load).catch(function(err){ Shell.toast(err.message); }); }});
          }).catch(function(err){ Shell.toast(err.message); load(); });
        }}]); };
    cell.appendChild(more);
    grid.appendChild(cell);
  });
  var box = $("my-prep"); box.innerHTML = ""; box.appendChild(grid);
}
var prepEdit = $("prep-edit");
if(prepEdit) prepEdit.onclick = function(){
  var on = !$("prep").classList.contains("editing"); $("prep").classList.toggle("editing", on);
  prepEdit.textContent = on ? "Done" : "Edit"; prepEdit.setAttribute("aria-pressed", String(on));
};
var docsEdit = $("docs-edit");
if(docsEdit) docsEdit.onclick = function(){
  var on = !$("docs").classList.contains("editing"); $("docs").classList.toggle("editing", on);
  docsEdit.textContent = on ? "Done" : "Edit"; docsEdit.setAttribute("aria-pressed", String(on));
};

// ---- the books this person shelved ----
var OFF = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
function drawMine(){
  var box = $("my-books"); $("mine").hidden = false;
  var books = H.books.filter(function(b){ return shown("book:" + b.slug); });
  $("mine-edit").hidden = !books.length;
  if(!books.length){ editing(false);
    box.innerHTML = '<p class="sg-note">Books you shelve in the Reading Room wait here. Open any book there and choose <b>Shelve</b>.</p>';
    return;
  }
  var grid = document.createElement("div"); grid.className = "shelf-grid";
  books.forEach(function(b){
    var cell = document.createElement("div"); cell.className = "mine-cell";
    cell.appendChild(sel(Covers.cover(b, {wrap: Covers.wrap(), started: started(b.slug)}),
      bookSel(b.slug, b.title, null, {url: "/api/shelf/books/" + encodeURIComponent(b.slug)})));
    var off = document.createElement("button");
    off.type = "button"; off.className = "cv-off"; off.innerHTML = OFF;
    off.setAttribute("aria-label", "Take " + b.title + " off your shelf"); off.title = "Take off your shelf";
    off.onclick = function(){ unshelve(b); };
    cell.appendChild(off);
    grid.appendChild(cell);
  });
  box.innerHTML = ""; box.appendChild(grid);
}
function editing(on){
  $("mine").classList.toggle("editing", on);
  $("mine-edit").setAttribute("aria-pressed", String(on)); $("mine-edit").textContent = on ? "Done" : "Edit";
}
$("mine-edit").onclick = function(){ editing(!$("mine").classList.contains("editing")); };
function unshelve(b){
  var i = H.books.indexOf(b); if(i < 0) return;
  H.books.splice(i, 1); drawMine();
  api("DELETE", "/api/shelf/books/" + encodeURIComponent(b.slug)).then(function(){
    Shell.toast("Took " + b.title + " off your shelf", {undo: function(){
      api("PUT", "/api/shelf/books/" + encodeURIComponent(b.slug)).then(function(){ H.books.splice(i, 0, b); drawMine(); })
        .catch(function(err){ Shell.toast(err.message); });
    }});
  }).catch(function(err){ H.books.splice(i, 0, b); drawMine(); Shell.toast(err.message); });
}

// ---- loading, and the states before there's anything to show ----
function load(){
  api("GET", "/api/shelf/home").then(function(d){
    H = d; loaded = true; drawClasses(); drawMine(); if(teacher){ drawDocs(); drawPrep(); }
  }).catch(function(err){
    $("class-shelves").innerHTML = '<div class="class-invite"><p>' + e(err.message) + '</p>' +
      '<button type="button" class="add-btn" id="shelves-retry">Try again</button></div>';
    $("shelves-retry").onclick = function(){ $("class-shelves").innerHTML = '<p class="sg-note" role="status">Opening your shelves…</p>'; load(); };
  });
}
window.addEventListener("pageshow", function(ev){ if(ev.persisted) load(); });   // back from a book: its place may have moved
document.addEventListener("shelf:changed", load);                                  // the Add dialog shelved a book

// ---- one dialog: the classes a person takes or teaches, and a school text's outline ----
var dlg = $("cl-dlg"), opener = null;
function openDlg(title, html){
  $("cl-dlg-title").textContent = title; $("cl-dlg-body").innerHTML = html; opener = document.activeElement;
  if(!dlg.open) dlg.showModal();
  var f = $("cl-dlg-body").querySelector("input,button,a"); if(f) f.focus();
}
dlg.addEventListener("click", function(ev){ if(ev.target === dlg || ev.target.closest("[data-close]")) dlg.close(); });
dlg.addEventListener("close", function(){ if(opener && opener.isConnected) opener.focus(); });

function openPicker(){
  var subjects = {}, order = [];
  H.courses.forEach(function(c){ if(!subjects[c.subject]){ subjects[c.subject] = []; order.push(c.subject); } subjects[c.subject].push(c); });
  openDlg(teacher ? "The classes you teach" : "The classes you take",
    '<form id="cl-form"><p class="cl-help">' + (teacher
      ? "Their books open your shelves. Change them whenever you like."
      : "Their books open your shelves. Change them whenever your schedule does.") + '</p>' +
    order.map(function(s){ return '<fieldset><legend>' + e(s) + '</legend>' + subjects[s].map(function(c){
      return '<label><input type="checkbox" value="' + e(c.key) + '"' + (H.mine.indexOf(c.key) >= 0 ? " checked" : "") + '> ' + e(c.name) +
        ' <span class="cl-g">' + (String(c.grades).indexOf("-") > 0 ? "grades " : "grade ") + e(c.grades) + '</span></label>'; }).join("") + '</fieldset>'; }).join("") +
    '<p class="cl-err" role="alert" hidden></p><div class="cl-actions"><button type="button" class="btn-ghost" data-close>Cancel</button>' +
    '<button type="submit" class="cl-save">Save</button></div></form>');
  $("cl-form").onsubmit = function(ev){
    ev.preventDefault();
    var keys = [].slice.call($("cl-form").querySelectorAll("input:checked")).map(function(x){ return x.value; });
    api("POST", "/api/shelf/classes", {courses: keys}).then(function(){
      dlg.close(); Shell.toast("Saved your classes"); load();
    }).catch(function(err){ var p = $("cl-form").querySelector(".cl-err"); p.textContent = err.message; p.hidden = false; });
  };
}
$("classes-edit").onclick = openPicker;

// a teacher's outline of a school text Exegetica has no copy of, and the way to plan from it
function openOutline(w, from){
  opener = from;
  openDlg(w.title, '<p class="cl-help">Loading its contents…</p>');
  api("GET", "/api/library/outline/" + encodeURIComponent(w.outline)).then(function(d){
    var o = d.outline;
    function walk(es){ return '<ul>' + es.map(function(x){ return '<li><span class="cl-ol">' + e([x.label, x.title].filter(Boolean).join(" ")) + '</span>' +
      (x.covers ? '<span class="cl-cov">' + e(x.covers) + (x.basis === "general" ? ' <span class="cl-gen" title="Written from general knowledge of the subject, not from the publisher\'s page">general</span>' : "") + '</span>' : "") +
      (x.children ? walk(x.children) : "") + '</li>'; }).join("") + '</ul>'; }
    $("cl-dlg-body").innerHTML =
      '<p class="cl-help">' + e([(o.authors || []).join(", "), o.publisher, o.edition].filter(Boolean).join(" · ")) + '</p>' +
      '<p class="cl-help">Exegetica doesn\'t have this book\'s text. Drafts get these contents and what each part covers; a description marked “general” was written from knowledge of the subject, the rest from the publisher\'s or a school\'s page.' +
      (o.match && o.match !== "exact edition" ? " These contents come from " + e(o.match) + ", so numbering may differ from the class copies." : "") + '</p>' +
      (window.Passage ? '<div class="cl-tools"><button type="button" class="shell-tool" id="ol-unit" aria-haspopup="true" aria-expanded="false">' + Passage.icons.prep + 'Add to a unit</button></div>' : "") +
      (o.summary ? '<p class="cl-sum">' + e(o.summary) + '</p>' : "") + (o.toc && o.toc.length ? walk(o.toc) : "") +
      ((o.sources || []).length ? '<p class="cl-src">From: ' + o.sources.map(function(s){ return '<a href="' + e(s.url) + '" target="_blank" rel="noopener">' + e(s.what || "source") + '</a>'; }).join(", ") + '</p>' : "");
    var u = $("ol-unit");
    if(u) u.onclick = function(){ Passage.addToUnit({kind: "outline", ref: {key: w.outline, parts: []}, label: w.title}, u); };
  }).catch(function(err){ $("cl-dlg-body").innerHTML = '<p class="cl-help">' + e(err.message) + '</p>'; });
}

Covers.CS.load().then(load);
window.__exegRestyle = function(){ Array.prototype.forEach.call(document.querySelectorAll(".lib-main .cover"), Covers.loadHouse); };
})();
