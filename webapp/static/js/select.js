/* Select, then Save to or Remove (decision 0031): on the Living Library's front page a teacher picks any mix of things
   on their own shelves and their class shelves. One Save to sends them all to a class shelf or a unit, and the items
   stay where they were (a copy goes). One Remove takes them all off the shelves they stand on. The pattern people know
   from Google Photos and Finder (rule F6): a Select button, a check circle on every item, a bar that counts them, one
   menu, and one message with Undo for the whole batch.
   Tiles say what they can do with data-sel (shelves.js and library.js set it):
     {k: the tile where it stands, same: the thing itself (one book can sit on a class shelf and on your own), label,
      unit: {kind, ref} for a unit, place: {kind, ref} for a class shelf, copy: a resource id,
      rm: {url, from: a class's name, back: the teacher it goes back to, del: "upload" or "link" for one deleted}} */
(function(){
"use strict";
var main = document.querySelector(".lib-main");
if(!main || !main.hasAttribute("data-teacher")) return;
var e = function(s){ return String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); };
var CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 12.5l4 4 8-9"/></svg>';
var BIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 7h15M9.5 7V4.8h5V7M6.8 7l.9 12.2h8.6l.9-12.2M10.3 10.6v5.5M13.7 10.6v5.5"/></svg>';
var on = false, picked = {};              // key -> descriptor
var ASK = "Choose items to save or remove";
var btn = document.getElementById("select-open");
var bar = document.createElement("div");
bar.className = "sel-bar"; bar.hidden = true; bar.setAttribute("data-toast-above", "");
bar.setAttribute("role", "region"); bar.setAttribute("aria-label", "Selected items");
bar.innerHTML = '<span class="sel-n" role="status" aria-live="polite">' + ASK + '</span>' +
  '<span class="sel-sp"></span><button type="button" class="sel-clear">Clear</button>' +
  '<button type="button" class="sel-rm" disabled>' + BIN + '<span class="sel-w">Remove</span></button>' +
  '<button type="button" class="sel-save" aria-haspopup="true" aria-expanded="false" disabled>' + Passage.icons.save + 'Save to…</button>' +
  '<button type="button" class="sel-done">Done</button>';
document.body.appendChild(bar);
var nEl = bar.querySelector(".sel-n"), save = bar.querySelector(".sel-save"), rm = bar.querySelector(".sel-rm");

function api(method, url, body){
  return fetch(url, {method: method, credentials: "same-origin", headers: body ? {"Content-Type": "application/json"} : {},
    body: body ? JSON.stringify(body) : undefined})
    .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){
      if(!r.ok) throw new Error(d.error || "That didn't work."); return d; }); });
}
function desc(el){ try { return JSON.parse(el.getAttribute("data-sel")); } catch(x){ return null; } }
function count(){ return Object.keys(picked).length; }
function paint(){
  var n = count();
  nEl.textContent = n ? n + " selected" : ASK;
  save.disabled = rm.disabled = !n;
}

// each tile gets a check circle beside it, a real button a keyboard reaches; the tile itself goes quiet
function decorate(){
  if(!on) return;
  main.querySelectorAll("[data-sel]").forEach(function(el){
    var d = desc(el); if(!d) return;
    var host = el.parentElement;
    if(el._box && el._box.isConnected) return;
    host.classList.add("sel-host");
    if(!el.hasAttribute("data-sel-tab")){ el.setAttribute("data-sel-tab", el.getAttribute("tabindex") || ""); el.setAttribute("tabindex", "-1"); }
    var b = document.createElement("button");
    b.type = "button"; b.className = "sel-box"; b.setAttribute("role", "checkbox"); b.setAttribute("data-k", d.k);
    b.setAttribute("aria-label", "Select " + d.label); b.innerHTML = CHECK;
    b._tile = el; el._box = b;
    host.insertBefore(b, el.nextSibling);   // read right after its tile; drawn over the tile's corner (place)
    mark(el, d.k);
  });
  place();
}
// a box sits on its tile's top left corner, wherever the tile's grid or strip has put it
function place(){
  main.querySelectorAll(".sel-box").forEach(function(b){
    var el = b._tile; if(!el || !el.isConnected) return;
    b.style.left = (el.offsetLeft + 6) + "px"; b.style.top = (el.offsetTop + 6) + "px";
  });
}
window.addEventListener("resize", function(){ if(on){ clearTimeout(place.t); place.t = setTimeout(place, 80); } });
function mark(el, k){
  var b = el._box, is = !!picked[k];
  if(b) b.setAttribute("aria-checked", String(is));
  el.classList.toggle("sel-on", is);
}
function undecorate(){
  main.querySelectorAll(".sel-box").forEach(function(b){ b.remove(); });
  main.querySelectorAll(".sel-host").forEach(function(h){ h.classList.remove("sel-host"); });
  main.querySelectorAll(".sel-on").forEach(function(x){ x.classList.remove("sel-on"); });
  main.querySelectorAll("[data-sel-tab]").forEach(function(el){
    var t = el.getAttribute("data-sel-tab"); if(t) el.setAttribute("tabindex", t); else el.removeAttribute("tabindex");
    el.removeAttribute("data-sel-tab");
  });
}
function toggle(el){
  var d = desc(el); if(!d) return;
  if(picked[d.k]) delete picked[d.k]; else picked[d.k] = d;
  main.querySelectorAll("[data-sel]").forEach(function(x){ var dx = desc(x); if(dx && dx.k === d.k) mark(x, d.k); });
  paint();
}
function start(){
  on = true; picked = {}; main.classList.add("selecting"); bar.hidden = false; btn.setAttribute("aria-pressed", "true");
  decorate(); paint();
  var first = main.querySelector(".sel-box"); if(first) first.focus();
}
function stop(){
  on = false; picked = {}; main.classList.remove("selecting"); bar.hidden = true; btn.setAttribute("aria-pressed", "false");
  undecorate(); btn.focus();
}
btn.addEventListener("click", function(){ on ? stop() : start(); });
bar.querySelector(".sel-done").onclick = stop;
bar.querySelector(".sel-clear").onclick = function(){ picked = {}; main.querySelectorAll("[data-sel]").forEach(function(x){ var d = desc(x); if(d) mark(x, d.k); }); paint(); };
document.addEventListener("keydown", function(ev){ if(on && ev.key === "Escape" && !document.querySelector(".shell-menu") && !document.querySelector("dialog[open]")) stop(); });
// while selecting, a press on a tile or its box picks it, and nothing opens
main.addEventListener("click", function(ev){
  if(!on) return;
  var b = ev.target.closest(".sel-box");
  var el = b ? b._tile : ev.target.closest("[data-sel]");
  if(!el){ if(ev.target.closest(".placed a, .placed button, .fr-cell a, .fr-cell button")){ ev.preventDefault(); ev.stopPropagation(); } return; }
  ev.preventDefault(); ev.stopPropagation(); toggle(el);
}, true);
// shelves redraw (a load, an Undo): new tiles get their boxes, and what's picked stays picked
new MutationObserver(function(){ if(on){ clearTimeout(decorate.t); decorate.t = setTimeout(decorate, 30); } })
  .observe(main, {childList: true, subtree: true});

// ---- Save to: one destination for the whole batch ----
save.addEventListener("click", function(){
  if(!count()) return;
  Promise.all([api("GET", "/api/prep/units").catch(function(){ return {units: []}; }),
               api("GET", "/api/shelf/held?kind=book&key=").catch(function(){ return {classes: []}; })]).then(function(res){
    var units = (res[0].units || []).slice(0, 12), classes = res[1].classes || [];
    var entries = [{heading: "Class shelves"}];
    if(classes.length) classes.forEach(function(c){ entries.push({label: c.name, act: function(){ run({cls: c}); }}); });
    else entries.push({note: "Choose the classes you teach, and their shelves show here."});
    entries.push({sep: true}, {heading: "Your units"});
    units.forEach(function(u){ entries.push({label: u.title, act: function(){ run({unit: u}); }}); });
    entries.push({label: "New unit…", plus: true, act: newUnit});
    Passage.menu(save, "Save " + count() + " to", entries);
  });
});
async function newUnit(){
  var name = await Shell.ask({title: "New unit", body: "Name it the way you plan. The " + count() + " items you chose go in it first.",
    ok: "Create unit", input: {label: "Unit name", value: "", max: 160}, validate: function(t){ return t ? "" : "Give the unit a name."; }});
  if(!name){ save.focus(); return; }
  api("POST", "/api/prep/units", {title: name, grade_band: "secondary"}).then(function(d){ run({unit: d.unit, made: true}); })
    .catch(function(err){ Shell.toast(err.message); });
}
// a few at a time, so a long batch doesn't wait on each in turn
function each(list, fn, width){
  var i = 0, out = new Array(list.length);
  function next(){ if(i >= list.length) return Promise.resolve(); var k = i++;
    return fn(list[k]).then(function(r){ out[k] = r; }, function(err){ out[k] = {error: err.message}; }).then(next); }
  var lanes = []; for(var w = 0; w < Math.min(width, list.length); w++) lanes.push(next());
  return Promise.all(lanes).then(function(){ return out; });
}
function names(list){ return list.length <= 2 ? list.join(" and ") : list.slice(0, 2).join(", ") + " and " + (list.length - 2) + " more"; }
function run(to){
  var seen = {}, items = Object.keys(picked).map(function(k){ return picked[k]; })
    .filter(function(d){ var s = d.same || d.k; if(seen[s]) return false; seen[s] = 1; return true; });
  save.disabled = rm.disabled = true; nEl.textContent = "Saving " + items.length + "…";
  each(items, function(d){
    if(to.cls){
      if(!d.place) return Promise.resolve({error: "can't go on a class shelf", label: d.label});
      return api("POST", "/api/shelf/class/" + encodeURIComponent(to.cls.key) + "/items",
        {kind: d.place.kind, ref: d.place.ref, label: d.label, audience: "students"}).then(function(r){ return {undo: ["DELETE", "/api/shelf/items/" + r.item.id], teachers: r.item.audience === "teachers"}; });
    }
    if(d.copy) return api("POST", "/api/prep/resources/" + encodeURIComponent(d.copy) + "/copy", {unit: to.unit.id})
      .then(function(r){ return {undo: ["DELETE", "/api/prep/resources/" + r.resource.id]}; });
    if(!d.unit) return Promise.resolve({error: "can't go in a unit", label: d.label});
    return api("POST", "/api/prep/units/" + encodeURIComponent(to.unit.id) + "/sources", {kind: d.unit.kind, ref: d.unit.ref, label: d.label})
      .then(function(r){ return {undo: r.source.merged ? ["PATCH", "/api/prep/sources/" + r.source.id, {kind: r.source.kind, ref: r.source.before}]
                                                         : ["DELETE", "/api/prep/sources/" + r.source.id]}; });
  }, 3).then(function(out){
    var done = out.filter(function(r){ return r && r.undo; }), missed = [];
    out.forEach(function(r, i){ if(r && r.error) missed.push("“" + items[i].label + "” (" + plain(r.error) + ")"); });
    var where = to.cls ? "the " + to.cls.name + " shelf" : "“" + to.unit.title + "”";
    var say = done.length ? (to.cls ? "Saved " : "Added ") + done.length + (done.length === 1 ? " item" : " items") + " to " + where : "Nothing went to " + where;
    if(done.some(function(r){ return r.teachers; })) say += ", answer keys and teacher editions for its teachers";
    if(missed.length) say += ". Not saved: " + names(missed);
    stop();
    document.dispatchEvent(new CustomEvent("shelf:changed", {detail: {}}));
    document.dispatchEvent(new CustomEvent("prep:sources-changed", {detail: {unit: to.unit && to.unit.id}}));
    Shell.toast(say, done.length ? {undo: function(){
      each(done, function(r){ return api(r.undo[0], r.undo[1], r.undo[2]); }, 3).then(function(){
        document.dispatchEvent(new CustomEvent("shelf:changed", {detail: {}}));
        if(to.made) api("DELETE", "/api/prep/units/" + encodeURIComponent(to.unit.id)).catch(function(){});
      });
    }} : null);
  });
}
// why a thing didn't go, in the server's own words, set inside a sentence
function plain(m){ m = String(m || "").split(". ")[0].replace(/\.$/, ""); return m.charAt(0).toLowerCase() + m.slice(1); }

// ---- Remove: off the shelves at once, one Undo for the batch (rule F3) ----
// The tiles go at once; the server hears once the Undo has had its moment, as a single take-off does (shelves.js), so
// an Undo never has to rebuild a class copy or an upload. Until then shelves.js and library.js keep the tiles hidden
// through any redraw ("shelf:gone"). Leaving the page sends what's waiting.
var waiting = [];
function hide(keys, on, dropped){ document.dispatchEvent(new CustomEvent("shelf:gone", {detail: {keys: keys, on: on, dropped: !!dropped}})); }
function forget(b){ var i = waiting.indexOf(b); if(i >= 0) waiting.splice(i, 1); }
// one line (rule F4): a lone item by its title, a batch by its counts
function n(c, one, many){ return c + " " + (c === 1 ? one : many); }
function removedSay(go){
  var lone = go.length === 1, places = [], seen = {}, off = [], del = [], links = 0, back = 0, who = {};
  go.forEach(function(d){
    if(d.rm.del){ del.push(d); if(d.rm.del === "link") links++; return; }
    var w = d.rm.from ? "the " + d.rm.from + " shelf" : "your shelves";
    if(!seen[w]){ seen[w] = 1; places.push(w); }
    off.push(d); if(d.rm.back){ back++; who[d.rm.back] = 1; }
  });
  var say = off.length ? "Took " + (lone ? "“" + off[0].label + "”" : n(off.length, "item", "items")) + " off " +
    (places.length === 1 ? places[0] : places.length + " shelves") : "";
  if(del.length) say += (say ? " and deleted " : "Deleted ") + (lone ? "“" + del[0].label + "”"
    : !links ? n(del.length, "upload", "uploads") : links === del.length ? n(del.length, "link", "links") : del.length + " uploads and links");
  if(back){ var t = Object.keys(who);   // another teacher's book or upload goes back to their own shelf (shelves.take_off)
    say += ". " + (lone ? "It goes" : n(back, "goes", "go")) + " back to " + (t.length === 1 ? t[0] + "'s shelf" : "the teachers who added them"); }
  return say;
}
// a tile with no rm is a book on the school's list for the class, which no teacher takes off
function stayed(stay, alone){
  if(!alone) return stay.length === 1 ? "1 book on the school's list stays" : stay.length + " books on the school's list stay";
  return "The school's book list keeps " + (stay.length === 1 ? "“" + stay[0].label + "” on its shelf" : "these " + stay.length + " books on their shelves");
}
rm.addEventListener("click", function(){
  var items = Object.keys(picked).map(function(k){ return picked[k]; });
  if(!items.length) return;
  var go = items.filter(function(d){ return d.rm; }), stay = items.filter(function(d){ return !d.rm; });
  stop();
  if(!go.length){ Shell.toast("Nothing was removed. " + stayed(stay, true)); return; }
  var batch = {items: go, keys: go.map(function(d){ return d.k; })};
  hide(batch.keys, true);
  batch.t = setTimeout(function(){ send(batch); }, 6500);
  waiting.push(batch);
  Shell.toast(removedSay(go) + (stay.length ? ". " + stayed(stay) : ""), {undo: function(){
    clearTimeout(batch.t); forget(batch); hide(batch.keys, false);
  }});
});
function send(batch){
  forget(batch);
  each(batch.items, function(d){ return api("DELETE", d.rm.url); }, 3).then(function(out){
    var ok = [], bad = [], why = [];
    out.forEach(function(r, i){ var d = batch.items[i];
      if(r && r.error){ bad.push(d.k); why.push("“" + d.label + "” (" + plain(r.error) + ")"); } else ok.push(d.k); });
    if(ok.length) hide(ok, false, true);
    if(bad.length){ hide(bad, false); Shell.toast("Couldn't remove " + names(why)); }
    document.dispatchEvent(new CustomEvent("shelf:changed", {detail: {}}));
  });
}
window.addEventListener("pagehide", function(){
  waiting.forEach(function(b){ clearTimeout(b.t);
    b.items.forEach(function(d){ fetch(d.rm.url, {method: "DELETE", credentials: "same-origin", keepalive: true}); }); });
  waiting = [];
});
})();
