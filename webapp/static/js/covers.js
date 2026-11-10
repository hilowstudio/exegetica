/* The house covers, shared by the Reading Room (static/js/reader.js) and the Living Library's shelves
   (static/js/shelves.js), so a book wears the same cover in both rooms (decision 0029). Moved here from reader.js:
   the reader's cover styles (CS), the cloth colours, and the drawing of one cover. Styles: static/css/covers.css. */
window.Covers = (function(){
  "use strict";
  var root = document.documentElement;
  function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
  document.addEventListener("shell:theme", function(){ if(window.__exegRestyle) window.__exegRestyle(); });   // the page redraws its covers
  // ---- house cloth covers (Book Wrap): each reader's cover style ----
  // A style is {light, dark, font, motif}. It can be set for the whole library, for a shelf (a book's
  // first section) and for one book; for each field the most specific setting wins, then the house
  // default. Signed-in readers keep their settings in Neon; everyone else in this browser.
  function isDark(){
    var t = root.getAttribute("data-theme");
    return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  }
  var CS = (function(){
    var FIELDS = ["light", "dark", "font", "motif"];
    var KEY = "exeg-cover-prefs";
    var HOUSE = {light: "exegetica-rose", dark: "exegetica-rose-dark", font: "house", motif: "universal"};
    var prefs = {library: {}, shelves: {}, books: {}}, server = false, version = "r1", options = null, ready = null;
    function blank(p){ p = p || {}; return {library: p.library || {}, shelves: p.shelves || {}, books: p.books || {}}; }
    function local(){ try{ return JSON.parse(localStorage.getItem(KEY) || "null"); }catch(e){ return null; } }
    function load(){
      if(ready) return ready;
      ready = fetch("/api/cover-prefs").then(function(r){
        if(r.ok){ server = true; return r.json(); }
        return null;
      }).catch(function(){ return null; }).then(function(p){
        var mine = local();
        if(server && p && !Object.keys(p.library || {}).length && !Object.keys(p.shelves || {}).length &&
           !Object.keys(p.books || {}).length && mine){   // first sign-in: bring this browser's style along
          prefs = blank(mine); save(); return prefs;
        }
        prefs = blank(server ? p : mine); return prefs;
      });
      return ready;
    }
    function save(){
      if(server){
        return fetch("/api/cover-prefs", {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(prefs)})
          .catch(function(){});
      }
      try{ localStorage.setItem(KEY, JSON.stringify(prefs)); }catch(e){}
      return Promise.resolve();
    }
    function getOptions(){
      if(!options){
        options = fetch("/api/house-cover/options").then(function(r){ return r.json(); })
          .then(function(o){ version = o.version || version; HOUSE = o.house || HOUSE; return o; });
      }
      return options;
    }
    function shelfOf(b){ return (b.sections && b.sections[0]) || ""; }
    // A book follows the first of its shelves (in its own section order) that sets a field. "Each shelf's
    // own motif" means the shelf that chose it, or the book's first shelf when chosen for the library.
    function resolve(b){
      var out = {}, bk = prefs.books[b.slug] || {}, secs = b.sections || [];
      FIELDS.forEach(function(f){
        if(bk[f]){ out[f] = bk[f]; out[f + "From"] = shelfOf(b); return; }
        for(var i = 0; i < secs.length; i++){
          var sh = prefs.shelves[secs[i]];
          if(sh && sh[f]){ out[f] = sh[f]; out[f + "From"] = secs[i]; return; }
        }
        out[f] = prefs.library[f] || HOUSE[f]; out[f + "From"] = shelfOf(b);
      });
      return out;
    }
    function motifParam(style){ return style.motif === "shelf" ? "shelf:" + (style.motifFrom || "") : style.motif; }
    function textKey(b){                     // a short hash of the title and author, so a retitled book's cover refreshes
      var s = (b.title || "") + "|" + (b.author || ""), h = 0;
      for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
      return (h >>> 0).toString(36);
    }
    function url(slug, style, dark, x){
      return "/api/house-cover/" + encodeURIComponent(slug) + "?t=" + encodeURIComponent(dark ? style.dark : style.light) +
        "&f=" + encodeURIComponent(style.font) + "&m=" + encodeURIComponent(motifParam(style)) + "&v=" + version +
        (x ? "&x=" + x : "");
    }
    function bookURL(b){ return url(b.slug, resolve(b), isDark(), textKey(b)); }
    return {FIELDS: FIELDS, load: load, save: save, getOptions: getOptions, resolve: resolve, url: url, bookURL: bookURL,
            shelfOf: shelfOf, prefs: function(){ return prefs; }, house: function(){ return HOUSE; }};
  })();
  try{ matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function(){ if(window.__exegRestyle) window.__exegRestyle(); }); }catch(e){}

  var CLOTH = {
    "Literary & Classics":"#6d2b30","Fantasy":"#1f5a54","Science Fiction":"#26364f",
    "Mystery & Crime":"#33373d","Horror & Gothic":"#2a2130","Adventure":"#8a4a2b",
    "Romance":"#8d4a5a","Humor & Satire":"#8f7130","Short Stories":"#495560",
    "Children's":"#b0733a","Poetry":"#4a2e54","Plays & Drama":"#5e2a2a",
    "Biography & Memoir":"#34513a","History":"#6a4a24","Travel & Places":"#1f5e6e",
    "Christianity":"#2f3a6b","World Religions & Spirituality":"#7a5326","Philosophy":"#3b3f47",
    "Psychology":"#4a3f6b","Science & Nature":"#2c5140","Health & Medicine":"#7d3f3a",
    "Technology & How-To":"#3d5566","Cooking & Home":"#8a4030","Society, Politics & Economics":"#5a5a2e",
    "Art, Music & Performance":"#1f5a63","Sports & Recreation":"#2f4d33","Language & Reference":"#6a5230",
    "Reference & Knowledge":"#4d4a44","Christmas Reading":"#24503a"
  };
  function cloth(sec){ return CLOTH[sec] || "#4a4038"; }

  // One book's cover. o: wrap (Book Wrap: the house cover faces out), started (the "in progress" ribbon), cog (the
  // cover-style button), admin (the cover-art button), shelf (true or false: the shelve button, for someone signed
  // in), href (false for a cover that opens nothing), button (one that opens a dialog), sec (the line at the foot
  // instead of the book's section).
  var known = {};
  function cover(b, o){
    o = o || {};
    var a = document.createElement(o.button ? "button" : o.href === false ? "div" : "a");   // button: a cover that opens a dialog
    if(o.button) a.type = "button";
    var art = !!b.cover, sec = o.sec != null ? o.sec : ((b.sections || [])[0] || "");
    a.className = "cover" + (art ? " has-img" : "") + (o.wrap ? " wrapped" : "") + (o.href === false ? " cv-still" : "");
    if(o.href !== false && !o.button) a.href = o.href || "/read/" + encodeURIComponent(b.slug);
    if(b.slug){ a.dataset.slug = b.slug; known[b.slug] = b; }
    a.style.setProperty("--cloth", cloth((b.sections || [])[0]));
    a.innerHTML =
      '<span class="cv-title">' + esc(b.title) + '</span><span class="cv-rule"></span>' +
      (b.author ? '<span class="cv-author">' + esc(b.author) + '</span>' : "") +
      '<span class="cv-sec">' + esc(sec) + '</span>' +
      (b.slug ? '<img class="cv-house" alt="" loading="lazy" onload="this.classList.add(\'ld\')" onerror="this.remove()"' +
        ((!art || o.wrap) ? ' src="' + esc(CS.bookURL(b)) + '"' : "") + '>' : "") +
      (art ? '<img class="cv-img" alt="" loading="lazy" src="' + esc(b.cover) + '" onload="this.classList.add(\'ld\')" onerror="var c=this.parentNode;c.classList.remove(\'has-img\');this.remove();if(window.__exegLoadHouse)window.__exegLoadHouse(c)">' : "") +
      (o.cog ? '<button class="cv-cog" type="button" title="Cover style for this book" aria-label="Cover style for this book"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7"/><circle cx="12" cy="12" r="6.6"/></svg></button>' : "") +
      (o.shelf != null ? '<button class="cv-shelf" type="button"></button>' : "") +
      (o.started ? '<span class="cv-flag" title="In progress"></span>' : "") +
      (o.admin ? '<button class="cv-edit" type="button" title="Find cover art" aria-label="Find cover art">✎</button>' : "");
    if(o.shelf != null) chip(a.querySelector(".cv-shelf"), b, !!o.shelf);
    return a;
  }
  // ---- your shelf (decision 0029): which books are on it, and putting one on or taking it off ----
  // Every room that shows a book asks here, and hears "shelf:changed" ({slug, on}) when one moves.
  var mine = null, signed = false, loading = null;
  function shelfLoad(){
    if(!loading) loading = fetch("/api/shelf/books", {credentials: "same-origin"}).then(function(r){ return r.json(); })
      .then(function(d){ signed = !!d.signed; mine = {}; (d.slugs || []).forEach(function(s){ mine[s] = true; }); return mine; })
      .catch(function(){ mine = {}; return mine; });
    return loading;
  }
  function onShelf(slug){ return !!(mine && mine[slug]); }
  function shelve(b, on, quiet){
    return fetch("/api/shelf/books/" + encodeURIComponent(b.slug), {method: on ? "PUT" : "DELETE", credentials: "same-origin"})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(d){
        if(!r.ok) throw new Error(d.error || "That didn't work. Try again in a minute."); }); })
      .then(function(){
        if(!mine) mine = {};
        if(on) mine[b.slug] = true; else delete mine[b.slug];
        document.dispatchEvent(new CustomEvent("shelf:changed", {detail: {slug: b.slug, on: on}}));
        if(!quiet && window.Shell) Shell.toast((on ? "Shelved " : "Took off your shelf: ") + b.title, {undo: function(){ shelve(b, !on, true); }});
      })
      .catch(function(err){ if(window.Shell) Shell.toast(err.message); });
  }
  // the corner button on a cover in the Reading Room: a plus to shelve it, a check once it's yours
  var PLUS = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>';
  var CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>';
  function chip(btn, b, on){
    btn.setAttribute("aria-pressed", String(on));
    btn.setAttribute("aria-label", on ? b.title + " is on your shelf. Take it off" : "Shelve " + b.title);
    btn.title = on ? "On your shelf" : "Shelve";
    btn.innerHTML = on ? CHECK : PLUS;
  }
  document.addEventListener("shelf:changed", function(ev){
    var b = known[ev.detail.slug]; if(!b) return;
    Array.prototype.forEach.call(document.querySelectorAll('.cover[data-slug="' + CSS.escape(ev.detail.slug) + '"] .cv-shelf'),
      function(btn){ chip(btn, b, ev.detail.on); });
  });
  // load (or reload, after a style or theme change) a drawn cover's house image
  function loadHouse(a){
    var img = a && a.querySelector(".cv-house"), b = a && known[a.dataset.slug];
    if(!img || !b) return;
    var u = CS.bookURL(b);
    if(img.getAttribute("src") !== u){ img.classList.remove("ld"); img.setAttribute("src", u); }
  }
  // A titled row of books that scrolls sideways: by trackpad or touch, by the arrows for a mouse, by Tab for a
  // keyboard (the Reading Room's front table, and each shelf in the Living Library). cells: [{el, cap}].
  var ARROW = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>';
  function row(id, title, note, cells){
    var sec = document.createElement("section"); sec.className = "fr-row"; sec.setAttribute("aria-labelledby", id);
    sec.innerHTML = '<div class="fr-h"><h2 id="' + id + '">' + esc(title) + '</h2>' + (note ? '<span>' + esc(note) + '</span>' : "") +
      '<div class="fr-nav" hidden><button type="button" class="fr-prev" aria-label="Earlier books in ' + esc(title) + '">' + ARROW + '</button>' +
      '<button type="button" class="fr-next" aria-label="More books in ' + esc(title) + '"><span style="display:grid;transform:scaleX(-1)">' + ARROW + '</span></button></div></div>';
    var strip = document.createElement("div"); strip.className = "fr-books"; strip.setAttribute("role", "list");
    cells.forEach(function(c){
      var cell = document.createElement("div"); cell.className = "fr-cell"; cell.setAttribute("role", "listitem");
      cell.appendChild(c.el);
      if(c.cap){ var p = document.createElement("div"); p.className = "fr-cap" + (c.phone ? " fr-cap-phone" : "") + (c.cap.indexOf("\n") >= 0 ? " fr-cap-2" : ""); p.textContent = c.cap; cell.appendChild(p); }
      strip.appendChild(cell);
    });
    sec.appendChild(strip);
    var nav = sec.querySelector(".fr-nav"), prev = sec.querySelector(".fr-prev"), next = sec.querySelector(".fr-next");
    function ends(){
      var over = strip.scrollWidth > strip.clientWidth + 4;
      nav.hidden = !over;
      prev.disabled = strip.scrollLeft < 4;
      next.disabled = strip.scrollLeft + strip.clientWidth > strip.scrollWidth - 4;
    }
    function by(dir){ strip.scrollBy({left: dir * Math.max(160, strip.clientWidth - 170)}); }
    prev.addEventListener("click", function(){ by(-1); });
    next.addEventListener("click", function(){ by(1); });
    strip.addEventListener("scroll", ends, {passive: true});
    window.addEventListener("resize", ends);
    requestAnimationFrame(ends);
    return sec;
  }
  if(!window.__exegLoadHouse) window.__exegLoadHouse = loadHouse;
  return {CS: CS, CLOTH: CLOTH, cloth: cloth, cover: cover, row: row, loadHouse: loadHouse, isDark: isDark,
    shelfLoad: shelfLoad, onShelf: onShelf, shelve: shelve, signed: function(){ return signed; }, wrap: function(){
    try{ return localStorage.getItem("exeg-book-wrap") !== "0"; }catch(e){ return true; } }};
})();
