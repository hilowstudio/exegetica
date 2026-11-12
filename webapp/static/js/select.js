/* Select, then Save to (decision 0031): on the Living Library's front page a teacher picks any mix of things on their
   own shelves and their class shelves, and one Save to sends them all to a class shelf or a unit. The pattern people
   know from Google Photos and Finder (rule F6): a Select button, a check circle on every item, a bar that counts them,
   one menu, and one message with Undo for the whole batch. The items stay where they were; a copy goes.
   Tiles say what they can do with data-sel (shelves.js and library.js set it):
     {k: a unique key, label, unit: {kind, ref} for a unit, place: {kind, ref} for a class shelf, copy: a resource id} */
(function(){
"use strict";
var main = document.querySelector(".lib-main");
if(!main || !main.hasAttribute("data-teacher")) return;
var e = function(s){ return String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); };
var CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 12.5l4 4 8-9"/></svg>';
var on = false, picked = {};              // key -> descriptor
var btn = document.getElementById("select-open");
var bar = document.createElement("div");
bar.className = "sel-bar"; bar.hidden = true; bar.setAttribute("data-toast-above", "");
bar.setAttribute("role", "region"); bar.setAttribute("aria-label", "Selected items");
bar.innerHTML = '<span class="sel-n" role="status" aria-live="polite">Choose the items to save</span>' +
  '<span class="sel-sp"></span><button type="button" class="sel-clear">Clear</button>' +
  '<button type="button" class="sel-save" aria-haspopup="true" aria-expanded="false" disabled>' + Passage.icons.save + 'Save to…</button>' +
  '<button type="button" class="sel-done">Done</button>';
document.body.appendChild(bar);
var nEl = bar.querySelector(".sel-n"), save = bar.querySelector(".sel-save");

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
  nEl.textContent = n ? n + " selected" : "Choose the items to save";
  save.disabled = !n;
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
  var items = Object.keys(picked).map(function(k){ return picked[k]; });
  save.disabled = true; nEl.textContent = "Saving " + items.length + "…";
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
})();
