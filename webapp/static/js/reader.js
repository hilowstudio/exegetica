/* The Reading Room page (templates/reader.html). The rail, theme and Need help now? come from static/js/shell.js. */
(function(){
  "use strict";
  var $ = function(id){ return document.getElementById(id); };
  var root = document.documentElement;
  var relayout = null;  // set by the reader to re-paginate after a text-size change

  // ---- theme + text size (per-viewer, localStorage). The rail's theme button switches the theme
  // and announces it, and covers and the open book redraw for it. ----
  function lsGet(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
  function lsSet(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }
  document.addEventListener("shell:theme", function(){ if(window.__exegRestyle) window.__exegRestyle(); });
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
  var SCALES = [1.0, 1.08, 1.15, 1.24, 1.34, 1.45];
  var scaleIdx = parseInt(lsGet("exeg-read-scale") || "2", 10);
  if(isNaN(scaleIdx) || scaleIdx < 0 || scaleIdx >= SCALES.length){ scaleIdx = 2; }
  function applyScale(){ root.style.setProperty("--read-scale", SCALES[scaleIdx] + "rem"); lsSet("exeg-read-scale", scaleIdx); if(relayout){ relayout(); } }
  $("fMinus").addEventListener("click", function(){ if(scaleIdx>0){ scaleIdx--; applyScale(); } });
  $("fPlus").addEventListener("click", function(){ if(scaleIdx<SCALES.length-1){ scaleIdx++; applyScale(); } });
  applyScale();
  // book face: EB Garamond (house) or Literata (sturdier at small sizes)
  function applyFace(f){ if(f === "literata"){ root.setAttribute("data-face", "literata"); } else { root.removeAttribute("data-face"); }
    lsSet("exeg-face", f); if(relayout){ relayout(); } }
  applyFace(lsGet("exeg-face") || "garamond");
  $("fFace").addEventListener("click", function(){ applyFace(root.getAttribute("data-face") === "literata" ? "garamond" : "literata"); });

  function fmtWords(w){
    if(!w) return "";
    if(w >= 1000) return Math.round(w/1000) + "k words";
    return w + " words";
  }
  function readTime(w){
    var mins = Math.round((w||0)/220);
    if(mins < 60) return mins + " min";
    var h = Math.floor(mins/60), m = mins%60;
    return h + "h" + (m ? " " + m + "m" : "");
  }
  function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

  var m = location.pathname.match(/^\/read\/(.+)$/);
  if(m){ initReader(decodeURIComponent(m[1])); } else { initBrowse(); }

  // =================== BROWSE (search-first, faceted cover grid) ===================
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
  var LENGTHS = [
    {key:"s",label:"Short reads · under 20k",lo:0,hi:20000},
    {key:"m",label:"Medium · 20–80k words",lo:20000,hi:80000},
    {key:"l",label:"Long · 80–200k words",lo:80000,hi:200000},
    {key:"e",label:"Epics · 200k+ words",lo:200000,hi:Infinity}
  ];
  var SORTS = [
    {key:"author",label:"Author (A–Z)"},{key:"title",label:"Title (A–Z)"},
    {key:"long",label:"Longest first"},{key:"short",label:"Shortest first"}
  ];

  function initBrowse(){
    $("browse").hidden = false;
    $("back").href = "/"; $("back").textContent = "‹ Exegetica";
    $("topTitle").textContent = "Reading Room";
    document.title = "The Library · Exegetica";

    var books = [], positions = {}, progress = {}, secList = [];
    var READ_MIN = 7;   // a book joins "Continue Reading" only after this many pages read
    function started(slug){ return (progress[slug] || 0) >= READ_MIN; }
    var state = { q:"", section:null, length:null, sort:"author", reading:false, wrap: lsGet("exeg-book-wrap") !== "0", hoverFlip: lsGet("exeg-hover-flip") !== "0" };   // both on unless turned off
    var filtered = [], shown = 0, BATCH = 48;

    var bySlug = {}, isAdmin = false;
    function cloth(sec){ return CLOTH[sec] || "#4a4038"; }
    function cover(b){
      var a = document.createElement("a");
      var art = !!b.cover;   // in book-wrap mode the art still loads, hidden, and the hover flip reveals it
      a.className = "cover" + (art ? " has-img" : "") + (state.wrap ? " wrapped" : "");
      a.href = "/read/" + encodeURIComponent(b.slug); a.dataset.slug = b.slug;
      a.style.setProperty("--cloth", cloth(b.sections[0]));
      a.innerHTML =
        '<span class="cv-title">' + esc(b.title) + '</span><span class="cv-rule"></span>' +
        (b.author ? '<span class="cv-author">' + esc(b.author) + '</span>' : "") +
        '<span class="cv-sec">' + esc(b.sections[0] || "") + '</span>' +
        '<img class="cv-house" alt="" loading="lazy" onload="this.classList.add(\'ld\')" onerror="this.remove()"' +
          ((!art || state.wrap) ? ' src="' + esc(CS.bookURL(b)) + '"' : "") + '>' +
        (art ? '<img class="cv-img" alt="" loading="lazy" src="' + esc(b.cover) + '" onload="this.classList.add(\'ld\')" onerror="var c=this.parentNode;c.classList.remove(\'has-img\');this.remove();if(window.__exegLoadHouse)window.__exegLoadHouse(c)">' : "") +
        '<button class="cv-cog" type="button" title="Cover style for this book" aria-label="Cover style for this book"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7"/><circle cx="12" cy="12" r="6.6"/></svg></button>' +
        (started(b.slug) ? '<span class="cv-flag" title="In progress"></span>' : "") +
        (isAdmin ? '<button class="cv-edit" type="button" title="Find cover art" aria-label="Find cover art">✎</button>' : "");
      return a;
    }

    // ---- house covers on the shelf ----
    // Every tile carries its house cover under the art. A book with no art shows it as its cover; for the
    // rest it loads on demand, when Book Wrap is on or the tile turns over on hover.
    function houseImg(a){ return a ? a.querySelector(".cv-house") : null; }
    function loadHouse(a){
      var img = houseImg(a), b = a && bySlug[a.dataset.slug];
      if(!img || !b) return;
      var u = CS.bookURL(b);
      if(img.getAttribute("src") !== u){ img.classList.remove("ld"); img.setAttribute("src", u); }
    }
    function restyle(){            // a style or the light/dark mode changed: redraw what's been drawn
      Array.prototype.forEach.call(document.querySelectorAll("#grid .cover"), function(a){
        var img = houseImg(a);
        if(img && (img.getAttribute("src") || state.wrap || !a.classList.contains("has-img"))) loadHouse(a);
      });
    }
    window.__exegRestyle = restyle;

    // ---- the cover-style picker ----
    // One dialog: pick the mode (light/dark), pick what to style (the library, a shelf, or the book whose
    // cog opened it), then 1 colors, 2 font, 3 pattern. Fonts and patterns are drawn in the chosen colors
    // on the chosen board. Edits to several shelves can be made before saving; Save applies them all.
    var sdlg = $("styleDlg"), sd = null;
    function scopeOf(id){
      if(id === "lib") return {level: "library", key: null};
      var i = id.indexOf(":");
      return {level: id.slice(0, i) === "shelf" ? "shelf" : "book", key: id.slice(i + 1)};
    }
    function stored(id){
      var p = CS.prefs(), s = scopeOf(id);
      return s.level === "library" ? p.library : s.level === "shelf" ? (p.shelves[s.key] || {}) : (p.books[s.key] || {});
    }
    function level(id){ return sd.drafts[id] || stored(id); }
    function sampleFor(id){
      var s = scopeOf(id);
      if(s.level === "book") return bySlug[s.key];
      if(s.level === "shelf"){
        for(var i = 0; i < books.length; i++){ if((books[i].sections || [])[0] === s.key) return books[i]; }
      }
      return bySlug["kenneth-grahame_the-wind-in-the-willows"] || books[0];
    }
    function inherited(id){          // what this scope gets from above it, field by field
      var H = CS.house(), s = scopeOf(id), out = {}, lib = level("lib");
      CS.FIELDS.forEach(function(f){
        var v = H[f];
        if(s.level !== "library" && lib[f]) v = lib[f];
        if(s.level === "book"){
          var secs = (sd.book && sd.book.sections) || [];
          for(var i = 0; i < secs.length; i++){ var sh = level("shelf:" + secs[i]); if(sh[f]){ v = sh[f]; break; } }
        }
        out[f] = v;
      });
      return out;
    }
    function effective(id){
      var lv = level(id), par = inherited(id), out = {};
      CS.FIELDS.forEach(function(f){ out[f] = lv[f] || par[f]; });
      var s = scopeOf(id);
      out.motifFrom = s.level === "shelf" ? s.key : CS.shelfOf(sampleFor(id) || {});
      return out;
    }
    function edit(f, v){             // set (v) or clear (null) a field on the current scope
      var d = sd.drafts[sd.scope] || (sd.drafts[sd.scope] = JSON.parse(JSON.stringify(stored(sd.scope))));
      if(v) d[f] = v; else delete d[f];
      paint();
    }
    function theme(key){ return (sd.opts.themes.filter(function(t){ return t.key === key; })[0]) || sd.opts.themes[0]; }
    function nameOf(list, key){ var x = list.filter(function(o){ return o.key === key; })[0]; return x ? x.name : key; }
    function motifName(key){
      if(key === "shelf") return "each shelf's own";
      var m = sd.opts.motifs.filter(function(o){ return o.key === key; })[0];
      return m ? m.subject : key;
    }
    var prevT;
    function paint(){
      var o = sd.opts, id = sd.scope, s = scopeOf(id), mode = sd.mode;
      var lv = level(id), par = inherited(id), eff = effective(id), th = theme(eff[mode]);
      var inhLabel = s.level === "library" ? "" : s.level === "shelf" ? "Use the library's" : "Use the shelf's";
      // header: mode, scope, note
      $("sdModeL").classList.toggle("on", mode === "light"); $("sdModeD").classList.toggle("on", mode === "dark");
      $("sdModeL").setAttribute("aria-selected", mode === "light"); $("sdModeD").setAttribute("aria-selected", mode === "dark");
      $("sdScope").value = id;
      $("sdNote").textContent = s.level === "library" ? "Every book, except shelves and books you style separately."
        : s.level === "shelf" ? "Books on this shelf. Anything you leave on “" + inhLabel + "” follows the library."
        : "Only this book. Anything you leave on “" + inhLabel + "” follows its shelf and the library.";
      // the board the tiles sit on, in the chosen colors
      sdlg.style.setProperty("--board", th.cloth);
      sdlg.style.setProperty("--ink-on-board", th.text);
      sdlg.style.setProperty("--board-faint", mode === "dark" ? "rgba(236,227,211,.6)" : "rgba(46,43,40,.55)");
      // 1. colors for this mode
      var cbox = $("sdColors"); cbox.innerHTML = "";
      if(inhLabel){
        var ci = document.createElement("button"); ci.type = "button"; ci.className = "sd-inh" + (!lv[mode] ? " on" : "");
        ci.textContent = inhLabel + " (" + theme(par[mode]).name + ")";
        ci.addEventListener("click", function(){ edit(mode, null); }); cbox.appendChild(ci);
      }
      var groups = {};
      o.themes.filter(function(t){ return t.mode === mode; }).forEach(function(t){ (groups[t.groupName] = groups[t.groupName] || []).push(t); });
      Object.keys(groups).forEach(function(g){
        var h = document.createElement("div"); h.className = "sd-gh"; h.textContent = g; cbox.appendChild(h);
        var row = document.createElement("div"); row.className = "sd-row";
        groups[g].forEach(function(t){
          var b = document.createElement("button"), on = eff[mode] === t.key && (lv[mode] || s.level === "library");
          b.type = "button"; b.className = "sd-chip" + (on ? " on" : ""); b.title = t.name;
          b.setAttribute("aria-pressed", on ? "true" : "false");
          var sw = document.createElement("span"); sw.className = "sd-sw";
          sw.style.background = t.foil2 ? "linear-gradient(90deg," + t.foil + " 50%," + t.foil2 + " 50%)" : t.foil;
          sw.style.boxShadow = "inset 0 0 0 3px " + t.cloth;
          b.appendChild(sw);
          b.addEventListener("click", function(){ edit(mode, t.key); });
          row.appendChild(b);
        });
        cbox.appendChild(row);
      });
      $("sdCurColor").textContent = th.name + (lv[mode] || s.level === "library" ? "" : " · inherited");
      // 2. fonts, each in itself, in the chosen lettering color
      var fs = $("sdFont"); fs.innerHTML = "";
      if(inhLabel){
        var fi = document.createElement("button"); fi.type = "button"; fi.className = "sd-inh" + (!lv.font ? " on" : "");
        fi.style.gridColumn = "1/-1"; fi.style.justifySelf = "start";
        fi.textContent = inhLabel + " (" + nameOf(o.fonts, par.font).replace(" (house)", "") + ")";
        fi.addEventListener("click", function(){ edit("font", null); }); fs.appendChild(fi);
      }
      o.fonts.forEach(function(f){
        var b = document.createElement("button"), on = eff.font === f.key && (lv.font || s.level === "library");
        b.type = "button"; b.className = "sd-ft" + (on ? " on" : "");
        b.setAttribute("role", "radio"); b.setAttribute("aria-checked", on ? "true" : "false");
        b.title = f.name + (f.genres.length && f.key !== "house" ? ": " + f.genres.join(", ") : "");
        b.innerHTML = '<span class="sd-ft-img" style="--src:url(\'/api/house-cover/font/' + encodeURIComponent(f.key) + '.png?v=' + esc(o.version) + '\')"></span>' +
          '<span class="sd-ft-name">' + esc(f.name.replace(" (house)", "")) + (f.key === "house" ? " · house" : "") + '</span>';
        b.addEventListener("click", function(){ edit("font", f.key); });
        fs.appendChild(b);
      });
      $("sdCurFont").textContent = nameOf(o.fonts, eff.font).replace(" (house)", "") + (lv.font || s.level === "library" ? "" : " · inherited");
      // 3. patterns, in the chosen foil (two-color schemes alternate, as on the cover)
      var mbox = $("sdMotif"); mbox.innerHTML = "";
      var top = document.createElement("div"); top.className = "sd-row";
      if(inhLabel){
        var mi = document.createElement("button"); mi.type = "button"; mi.className = "sd-inh" + (!lv.motif ? " on" : "");
        mi.textContent = inhLabel + " (" + motifName(par.motif) + ")";
        mi.addEventListener("click", function(){ edit("motif", null); }); top.appendChild(mi);
      }
      var ms = document.createElement("button"), mson = eff.motif === "shelf" && (lv.motif || s.level === "library");
      ms.type = "button"; ms.className = "sd-mt txt" + (mson ? " on" : "");
      ms.textContent = "Each shelf’s own pattern"; ms.addEventListener("click", function(){ edit("motif", "shelf"); });
      top.appendChild(ms); mbox.appendChild(top);
      var shelf = s.level === "shelf" ? s.key : (s.level === "book" ? CS.shelfOf(sd.book) : null);
      var byShelf = {};
      o.motifs.forEach(function(m){ (byShelf[m.shelf] = byShelf[m.shelf] || []).push(m); });
      var order = Object.keys(byShelf);
      if(shelf && byShelf[shelf]){ order.splice(order.indexOf(shelf), 1); order.splice(1, 0, shelf); }
      order.forEach(function(sh){
        var h = document.createElement("div"); h.className = "sd-gh"; h.textContent = sh; mbox.appendChild(h);
        var row = document.createElement("div"); row.className = "sd-row";
        byShelf[sh].forEach(function(m, i){
          var parts = m.key === "universal" ? ["library", "universal"] : m.key.split("/");
          var on = eff.motif === m.key && (lv.motif || s.level === "library");
          var b = document.createElement("button");
          b.type = "button"; b.className = "sd-mt" + (on ? " on" : ""); b.title = m.subject;
          b.setAttribute("aria-pressed", on ? "true" : "false");
          b.innerHTML = '<i style="--src:url(\'/api/house-cover/motif/' + parts[0] + '/' + parts[1] + '.png\');--f:' +
            ((th.foil2 && i % 2) ? th.foil2 : th.foil) + '"></i>';
          b.addEventListener("click", function(){ edit("motif", m.key); });
          row.appendChild(b);
        });
        mbox.appendChild(row);
      });
      $("sdCurMotif").textContent = motifName(eff.motif) + (lv.motif || s.level === "library" ? "" : " · inherited");
      // the preview: one book, in the mode being styled
      clearTimeout(prevT);
      prevT = setTimeout(function(){
        if(!sd) return;
        var smp = sampleFor(id) || sd.book;
        $("sdPrev").src = CS.url(smp.slug, effective(id), mode === "dark");
        var e2 = effective(id);
        $("sdPrevCap").innerHTML = '<b>' + esc(smp.title) + '</b><br>' + (mode === "dark" ? "Dark" : "Light") + " mode · " +
          esc(theme(e2[mode]).name) + " · " + esc(nameOf(sd.opts.fonts, e2.font).replace(" (house)", "")) + " · " + esc(motifName(e2.motif));
      }, 120);
      // footer
      $("sdReset").hidden = s.level === "library" || !Object.keys(level(id)).length;
      $("sdReset").textContent = s.level === "book" ? "Clear this book's style" : "Clear this shelf's style";
      var n = changed().length;
      $("sdDirty").hidden = n < 2;
      $("sdDirty").textContent = n + " unsaved changes";
    }
    function buildScopes(){
      var sel = $("sdScope"), p = CS.prefs(), html = '<option value="lib">Entire library (all shelves)</option>';
      if(sd.book) html += '<option value="book:' + esc(sd.book.slug) + '">This book only: ' + esc(sd.book.title) + '</option>';
      html += '<optgroup label="Shelves">' + secList.map(function(x){
        var custom = Object.keys(p.shelves[x.name] || {}).length || sd.drafts["shelf:" + x.name];
        return '<option value="shelf:' + esc(x.name) + '">' + esc(x.name) + (custom ? " · custom" : "") + '</option>';
      }).join("") + '</optgroup>';
      sel.innerHTML = html;
    }
    function openStyle(lvl, key, sample){
      sd = {drafts: {}, mode: isDark() ? "dark" : "light", book: lvl === "book" ? sample : null,
            scope: lvl === "library" ? "lib" : (lvl === "shelf" ? "shelf:" : "book:") + key};
      $("sdAsk").hidden = true; $("sdBtns").hidden = false;
      $("sdColors").innerHTML = $("sdFont").innerHTML = $("sdMotif").innerHTML = "";
      buildScopes();
      sdlg.showModal();
      CS.getOptions().then(function(o){ if(!sd) return; sd.opts = o; paint(); });
    }
    $("sdModeL").addEventListener("click", function(){ if(sd){ sd.mode = "light"; paint(); } });
    $("sdModeD").addEventListener("click", function(){ if(sd){ sd.mode = "dark"; paint(); } });
    $("sdScope").addEventListener("change", function(e){ if(sd){ sd.scope = e.target.value; buildScopes(); paint(); } });
    $("sdClose").addEventListener("click", function(){ sdlg.close(); });
    $("sdCancel").addEventListener("click", function(){ sdlg.close(); });
    sdlg.addEventListener("click", function(e){ if(e.target === sdlg) sdlg.close(); });
    sdlg.addEventListener("close", function(){ sd = null; });
    $("sdReset").addEventListener("click", function(){ if(sd){ sd.drafts[sd.scope] = {}; buildScopes(); paint(); } });

    function changed(){              // [{id, fields}] for every scope edited in this session
      var out = [];
      Object.keys(sd.drafts).forEach(function(id){
        var cur = stored(id), d = sd.drafts[id];
        var fields = CS.FIELDS.filter(function(f){ return (cur[f] || "") !== (d[f] || ""); });
        if(fields.length) out.push({id: id, fields: fields});
      });
      return out;
    }
    function below(ch){              // customized scopes beneath an edit that set any of its fields
      var p = CS.prefs(), s = scopeOf(ch.id), out = [];
      function sets(st){ return st && ch.fields.some(function(f){ return st[f]; }); }
      if(s.level === "library"){
        Object.keys(p.shelves).forEach(function(x){ if(!sd.drafts["shelf:" + x] && sets(p.shelves[x])) out.push("shelf:" + x); });
        Object.keys(p.books).forEach(function(x){ if(!sd.drafts["book:" + x] && sets(p.books[x])) out.push("book:" + x); });
      } else if(s.level === "shelf"){
        Object.keys(p.books).forEach(function(x){
          var b = bySlug[x]; if(b && (b.sections || []).indexOf(s.key) >= 0 && !sd.drafts["book:" + x] && sets(p.books[x])) out.push("book:" + x);
        });
      }
      return out;
    }
    function commit(override, chs){
      var p = CS.prefs();
      chs.forEach(function(ch){
        var s = scopeOf(ch.id), d = {};
        CS.FIELDS.forEach(function(f){ if(sd.drafts[ch.id][f]) d[f] = sd.drafts[ch.id][f]; });
        if(s.level === "library") p.library = d;
        else if(s.level === "shelf"){ if(Object.keys(d).length) p.shelves[s.key] = d; else delete p.shelves[s.key]; }
        else { if(Object.keys(d).length) p.books[s.key] = d; else delete p.books[s.key]; }
      });
      if(override){                  // the new settings win: drop those fields from the customized scopes beneath
        chs.forEach(function(ch){
          below(ch).forEach(function(id){
            var s = scopeOf(id), map = s.level === "shelf" ? p.shelves : p.books;
            if(!map[s.key]) return;
            ch.fields.forEach(function(f){ delete map[s.key][f]; });
            if(!Object.keys(map[s.key]).length) delete map[s.key];
          });
        });
      }
      CS.save(); restyle(); sdlg.close();
    }
    $("sdSave").addEventListener("click", function(){
      if(!sd) return;
      var chs = changed();
      if(!chs.length){ sdlg.close(); return; }
      chs.sort(function(a, b){ return "lsb".indexOf(scopeOf(a.id).level[0]) - "lsb".indexOf(scopeOf(b.id).level[0]); });
      var seen = {}, shelves = 0, bks = 0;
      chs.forEach(function(ch){ below(ch).forEach(function(id){ if(!seen[id]){ seen[id] = 1; if(id.indexOf("shelf:") === 0) shelves++; else bks++; } }); });
      var n = shelves + bks;
      if(!n){ commit(false, chs); return; }
      var parts = [];
      if(shelves) parts.push(shelves + (shelves === 1 ? " shelf" : " shelves"));
      if(bks) parts.push(bks + (bks === 1 ? " book" : " books"));
      $("sdAskText").textContent = parts.join(" and ") + (n === 1 ? " has its own" : " have their own") +
        " settings for this. Apply your change to " + (n === 1 ? "it" : "them") + " as well, or only where there's no custom setting?";
      $("sdBtns").hidden = true; $("sdAsk").hidden = false;
      $("sdOverride").onclick = function(){ commit(true, chs); };
      $("sdKeep").onclick = function(){ commit(false, chs); };
    });
    $("sdBack").addEventListener("click", function(){ $("sdAsk").hidden = true; $("sdBtns").hidden = false; });

    // the cogs open the picker on the library, the selected shelf, or one book
    $("styleLib").addEventListener("click", function(){ openStyle("library", null, null); });
    $("styleShelf").addEventListener("click", function(){ if(state.section) openStyle("shelf", state.section, null); });
    window.__exegLoadHouse = loadHouse;

    // ---- facet rail ----
    function fopt(label, count, active, onClick){
      var b = document.createElement("button"); b.className = "fopt" + (active ? " on" : "");
      b.innerHTML = '<span>' + esc(label) + '</span>' + (count != null ? '<span class="fk">' + count.toLocaleString() + '</span>' : "");
      b.addEventListener("click", onClick); return b;
    }
    function buildFacets(){
      var sortBox = $("sortOpts"); sortBox.innerHTML = "";
      SORTS.forEach(function(s){ sortBox.appendChild(fopt(s.label, null, state.sort === s.key, function(){ state.sort = s.key; compute(); })); });

      var lenBox = $("lenOpts"); lenBox.innerHTML = "";
      lenBox.appendChild(fopt("Any length", null, !state.length, function(){ state.length = null; compute(); }));
      LENGTHS.forEach(function(L){
        var c = books.filter(function(b){ return b.words >= L.lo && b.words < L.hi; }).length;
        lenBox.appendChild(fopt(L.label, c, state.length === L.key, function(){ state.length = (state.length === L.key ? null : L.key); compute(); }));
      });

      $("mSort").innerHTML = SORTS.map(function(o){
        return '<option value="' + o.key + '"' + (state.sort === o.key ? " selected" : "") + '>' + esc(o.label) + '</option>';
      }).join("");
      $("mLen").innerHTML = '<option value="">Any length</option>' + LENGTHS.map(function(L){
        var c = books.filter(function(b){ return b.words >= L.lo && b.words < L.hi; }).length;
        return '<option value="' + L.key + '"' + (state.length === L.key ? " selected" : "") + '>' + esc(L.label) + ' (' + c.toLocaleString() + ')</option>';
      }).join("");

      var secBox = $("secOpts"); secBox.innerHTML = "";
      secBox.appendChild(fopt("All sections", books.length, !state.section, function(){ state.section = null; compute(); }));
      secList.forEach(function(s){
        secBox.appendChild(fopt(s.name, s.count, state.section === s.name, function(){ state.section = (state.section === s.name ? null : s.name); compute(); }));
      });
    }

    function updateCount(){
      var n = filtered.length, act = state.section || state.length || state.reading;
      $("count").innerHTML = '<b>' + n.toLocaleString() + '</b> ' + (n === 1 ? "book" : "books") +
        (state.q ? ' matching “' + esc(state.q) + '”' : "") +
        (state.section ? " in " + esc(state.section) : "");
      $("resetF").hidden = !(act || state.q);
      $("styleShelf").hidden = !state.section;
      if(state.section) $("styleShelfName").textContent = state.section + " style";
      var rb = $("readingOpt"); if(rb){ rb.classList.toggle("on", state.reading); }
    }

    function render(reset){
      var grid = $("grid");
      if(reset){ grid.innerHTML = ""; shown = 0; }
      var frag = document.createDocumentFragment();
      var end = Math.min(shown + BATCH, filtered.length);
      for(var i = shown; i < end; i++){ frag.appendChild(cover(filtered[i])); }
      grid.appendChild(frag); shown = end;
      var left = filtered.length - shown;   // more appear only when the reader asks (no auto-loading on scroll)
      $("loadMore").hidden = left <= 0;
      $("loadMore").textContent = left > BATCH ? "Show " + BATCH + " more · " + left.toLocaleString() + " left"
        : left === 1 ? "Show the last book" : "Show the last " + left;
      $("browseEmpty").hidden = filtered.length !== 0;
      if(!filtered.length){
        $("browseEmpty").innerHTML = state.q ? 'No books match <b>“' + esc(state.q) + '”</b>.' : "No books match these filters.";
      }
    }
    function compute(){
      var q = state.q.toLowerCase();
      var L = state.length ? LENGTHS.filter(function(x){ return x.key === state.length; })[0] : null;
      filtered = books.filter(function(b){
        if(q && b._s.indexOf(q) < 0) return false;
        if(state.section && b.sections.indexOf(state.section) < 0) return false;
        if(state.reading && !started(b.slug)) return false;
        if(L && !(b.words >= L.lo && b.words < L.hi)) return false;
        return true;
      });
      var s = state.sort;
      filtered.sort(function(a,b){
        if(s === "title") return a._t < b._t ? -1 : (a._t > b._t ? 1 : 0);
        if(s === "long") return b.words - a.words;
        if(s === "short") return a.words - b.words;
        return a._a < b._a ? -1 : (a._a > b._a ? 1 : (a._t < b._t ? -1 : 1));
      });
      render(true); updateCount(); buildFacets();
    }

    // ---- wire controls ----
    var t;
    $("q").addEventListener("input", function(e){
      var v = e.target.value; $("qClear").hidden = !v;
      clearTimeout(t); t = setTimeout(function(){ state.q = v.trim(); compute(); }, 160);
    });
    $("qClear").addEventListener("click", function(){ $("q").value = ""; $("qClear").hidden = true; state.q = ""; compute(); $("q").focus(); });
    $("resetF").addEventListener("click", function(){
      state.q = ""; state.section = null; state.length = null; state.reading = false;
      $("q").value = ""; $("qClear").hidden = true; compute(); window.scrollTo({top:0});
    });
    $("wrapTog").classList.toggle("on", state.wrap);
    $("wrapTog").setAttribute("aria-pressed", state.wrap ? "true" : "false");
    $("flipTog").classList.toggle("on", state.hoverFlip);
    $("flipTog").setAttribute("aria-pressed", state.hoverFlip ? "true" : "false");
    $("flipTog").addEventListener("click", function(){
      state.hoverFlip = !state.hoverFlip; lsSet("exeg-hover-flip", state.hoverFlip ? "1" : "0");
      $("flipTog").classList.toggle("on", state.hoverFlip);
      $("flipTog").setAttribute("aria-pressed", state.hoverFlip ? "true" : "false");
      if(!state.hoverFlip) unhover();
    });
    $("wrapTog").addEventListener("click", function(){
      state.wrap = !state.wrap; lsSet("exeg-book-wrap", state.wrap ? "1" : "0");
      $("wrapTog").classList.toggle("on", state.wrap);
      $("wrapTog").setAttribute("aria-pressed", state.wrap ? "true" : "false");
      turnAll();
    });
    // Turn every book on the page over at once (the art or the wrap swaps in at the midpoint).
    // Books outside the viewport just swap, so a long page doesn't animate hundreds of tiles.
    function turnAll(){
      unhover();
      var vh = window.innerHeight, tiles = Array.prototype.slice.call(document.querySelectorAll("#grid .cover"));
      tiles.forEach(function(a){
        if(state.wrap) loadHouse(a);
        a.classList.remove("flip-in", "flip-out", "turn-to-wrap", "turn-to-art");
        a.classList.toggle("wrapped", state.wrap);
      });
      void document.body.offsetWidth;            // one reflow, so a turn restarts if toggled mid-turn
      tiles.forEach(function(a){
        var r = a.getBoundingClientRect();
        if(r.bottom > 0 && r.top < vh) a.classList.add(state.wrap ? "turn-to-wrap" : "turn-to-art");
      });
    }
    $("loadMore").addEventListener("click", function(e){
      var first = shown; render(false);
      if(e.detail === 0){                         // from the keyboard: carry on at the first new book
        var t = $("grid").children[first]; if(t){ t.focus({preventScroll: true}); }
      }
    });
    $("mSort").addEventListener("change", function(){ state.sort = this.value; compute(); });
    $("mLen").addEventListener("change", function(){ state.length = this.value || null; compute(); });
    // admin: one-click cover search (delegated; buttons only render for admins). The modal
    // shows Google Images results; clicking one downloads it server-side as the new cover.
    var dlg = $("coverDlg"), dlgBook = null;
    function jsonRes(r){ return r.json().catch(function(){ return {}; }).then(function(j){ return {ok:r.ok, status:r.status, j:j}; }); }
    function cdStatus(msg, bad){ $("cdStatus").textContent = msg || ""; $("cdStatus").classList.toggle("bad", !!bad); }
    function applyCover(url, meta){                     // meta: {source, page} for attribution
      var b = dlgBook; if(!b) return; meta = meta || {};
      cdStatus(url ? "Downloading that image and saving it as the cover…" : "Restoring the original cover…");
      dlg.classList.add("busy");
      fetch("/api/reading/cover", {method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify({slug: b.slug, cover_url: url, source: meta.source || "", source_page: meta.page || ""})})
        .then(jsonRes)
        .then(function(res){
          dlg.classList.remove("busy");
          if(res.ok){
            b.cover = res.j.cover || null;
            var a = $("grid").querySelector('.cover[data-slug="' + CSS.escape(b.slug) + '"]');
            if(a){ a.replaceWith(cover(b)); }
            dlg.close(); return;
          }
          var err = res.j.error;
          cdStatus(res.status === 403 ? "You're not signed in as a library admin, so you can't change covers."
            : err === "bad-url" ? "That address has to start with http:// or https://."
            : err === "fetch-failed" ? "That site wouldn't let us download the image. Pick another result, or paste a different image address."
            : err === "no-db" ? "Storage is unavailable right now. Try again shortly."
            : "Couldn't update the cover.", true);
        })
        .catch(function(){ dlg.classList.remove("busy"); cdStatus("Couldn't reach the server to update the cover.", true); });
    }
    function resultItem(r){
      var btn = document.createElement("button"), frame = document.createElement("span"),
          img = document.createElement("img"), meta = document.createElement("span"), dims = document.createElement("b");
      btn.type = "button"; btn.className = "cd-item" + (r.w && r.w < 400 ? " lo" : "");
      btn.title = (r.title ? r.title + "\n" : "") + "Use this image as the cover";
      frame.className = "cd-frame";
      img.alt = r.title || ""; img.loading = "lazy"; img.referrerPolicy = "no-referrer"; img.src = r.thumb;
      img.onerror = function(){ btn.remove(); };
      meta.className = "cd-meta";
      if(r.w && r.h){ dims.textContent = r.w + "×" + r.h; meta.appendChild(dims); }
      meta.appendChild(document.createTextNode(r.domain ? (r.w && r.h ? " · " : "") + r.domain : ""));
      frame.appendChild(img); btn.appendChild(frame); btn.appendChild(meta);
      btn.addEventListener("click", function(){
        applyCover(r.image, {source: r.source || ("Image search: " + (r.domain || "")), page: r.page || ""});
      });
      return btn;
    }
    function section(name, note){
      var h = document.createElement("div"), n = document.createElement("span");
      h.className = "cd-sec"; h.textContent = name; n.textContent = note; h.appendChild(n);
      return h;
    }
    function openCoverSearch(b){
      dlgBook = b; dlg.classList.remove("busy");
      $("cdTitle").textContent = b.title; $("cdAuthor").textContent = b.author || "";
      $("cdQuery").textContent = ""; $("cdGoogle").hidden = true; $("cdUrl").value = "";
      $("cdResults").replaceChildren();
      cdStatus("Searching Google Images…");
      dlg.showModal();
      fetch("/api/reading/cover/search?slug=" + encodeURIComponent(b.slug))
        .then(jsonRes)
        .then(function(res){
          if(dlgBook !== b) return;                       // closed or moved on to another book
          if(!res.ok){ cdStatus(res.status === 403 ? "You're not signed in as a library admin." : "Couldn't find that book in the catalog.", true); return; }
          var j = res.j;
          $("cdQuery").textContent = j.query; $("cdGoogle").href = j.google_url; $("cdGoogle").hidden = false;
          var mag = j.magazine, pulp = j.pulpcovers || [], cb = j.coverbrowser || [], g = j.results || [];
          function count(n, one){ return n ? n + " " + (n === 1 ? one : one + "es") : "No match for this book"; }
          var parts = [];
          if(mag && mag.results.length){                 // the story's own magazine issue: shown first, only when known
            parts.push(section("Original magazine issue", mag.issue), mag.results.map(resultItem));
          }
          parts.push(section("PulpCovers", count(pulp.length, "match")), pulp.map(resultItem));
          if(j.error === "no-key"){
            parts.push(section("Google Images", "needs a SERPER_API_KEY on the server; use “Open in Google Images” and paste an address below"));
          } else if(j.error === "no-credits"){
            parts.push(section("Google Images and CoverBrowser", "every search key is out of credits; top up Serper or Tavily, or use “Open in Google Images” and paste an address below"));
          } else if(j.error === "search-failed"){
            parts.push(section("Google Images", "the search didn't respond; try again, or open it in Google Images"));
          } else {
            var web = j.web_source === "tavily" ? "Web images (Tavily)" : "Google Images";
            parts.push(section("CoverBrowser", count(cb.length, "match")), cb.map(resultItem),
                       section(web, g.length + " results" + (j.fallback ? " · backup search key" : "")), g.map(resultItem));
          }
          cdStatus("Click a cover to use it. Sizes in red are under 400px wide and will look soft.");
          $("cdResults").replaceChildren.apply($("cdResults"), [].concat.apply([], parts));
        })
        .catch(function(){ if(dlgBook === b) cdStatus("Couldn't reach the server to search.", true); });
    }
    // hover flip to the cloth wrap (CSS does the motion; these just set which side faces out)
    function flip(a, toWrap){
      if(!a || !a.classList.contains("has-img")) return;
      if(toWrap && !state.hoverFlip) return;
      if(toWrap) loadHouse(a);
      if(toWrap){ a.classList.remove("flip-out"); a.classList.add("flip-in"); }
      else if(a.classList.contains("flip-in")){ a.classList.remove("flip-in"); a.classList.add("flip-out"); }
    }
    function tileOf(e){ return e.target.closest ? e.target.closest(".cover") : null; }
    // Mid-flip the tile narrows to nothing, so the pointer "leaves" it and comes back, which would
    // bounce the flip. So hover is judged against the tile's resting outline, captured on entry.
    var hovered = null, hoverBox = null;
    function unhover(){ if(hovered){ flip(hovered, false); hovered = null; hoverBox = null; } }
    $("grid").addEventListener("mouseover", function(e){
      var a = tileOf(e); if(!a || a === hovered) return;
      unhover();
      hovered = a; hoverBox = a.getBoundingClientRect(); flip(a, true);
    });
    document.addEventListener("mousemove", function(e){
      if(!hoverBox) return;
      var r = hoverBox;   // a few px of slack above for the hover lift
      if(e.clientX < r.left || e.clientX > r.right || e.clientY < r.top - 8 || e.clientY > r.bottom) unhover();
    }, {passive: true});
    window.addEventListener("scroll", unhover, {passive: true});
    document.documentElement.addEventListener("mouseleave", unhover);
    $("grid").addEventListener("focusin", function(e){ var a = tileOf(e); if(a && a.matches(":focus-visible")) flip(a, true); });
    $("grid").addEventListener("focusout", function(e){ var a = tileOf(e); if(a && !a.contains(e.relatedTarget)) flip(a, false); });
    $("grid").addEventListener("animationend", function(e){
      if(e.animationName === "cvFlipOut") e.target.classList.remove("flip-out");
      if(e.animationName === "cvTurn") e.target.classList.remove("turn-to-wrap", "turn-to-art");
    });
    $("grid").addEventListener("click", function(e){
      var cog = e.target.closest ? e.target.closest(".cv-cog") : null;
      if(cog){
        e.preventDefault(); e.stopPropagation();
        var ct = cog.closest(".cover"), cb = ct && bySlug[ct.dataset.slug]; if(cb) openStyle("book", cb.slug, cb);
        return;
      }
      var btn = e.target.closest ? e.target.closest(".cv-edit") : null; if(!btn) return;
      e.preventDefault(); e.stopPropagation();
      var a = btn.closest(".cover"), b = a && bySlug[a.dataset.slug]; if(b) openCoverSearch(b);
    });
    $("cdClose").addEventListener("click", function(){ dlg.close(); });
    dlg.addEventListener("click", function(e){ if(e.target === dlg) dlg.close(); });   // backdrop
    dlg.addEventListener("close", function(){ dlgBook = null; });
    $("cdForm").addEventListener("submit", function(e){
      e.preventDefault(); var url = $("cdUrl").value.trim(); if(url) applyCover(url, {source: "Pasted address"});
    });
    $("cdRevert").addEventListener("click", function(){
      Shell.ask({title: "Remove the custom cover?", body: "The book goes back to its original cover.",
                 ok: "Remove cover", danger: true}).then(function(yes){ if(yes) applyCover(""); });
    });
    // ---- load the whole catalog once, then everything is instant client-side ----
    Promise.all([
      fetch("/api/catalog").then(function(r){ return r.json(); }),
      CS.load(), CS.getOptions().catch(function(){}),
      fetch("/api/reading/position").then(function(r){ return r.ok ? r.json() : {positions:{}}; }).catch(function(){ return {positions:{}}; })
    ]).then(function(res){
      var d = res[0];
      if(!d || d.available === false || !(d.items && d.items.length)){
        $("browseEmpty").hidden = false;
        $("browseEmpty").textContent = "The Reading Room is still being stocked. Check back soon.";
        return;
      }
      res.splice(1, 2);
      positions = (res[1] && res[1].positions) || {};
      progress = (res[1] && res[1].progress) || {};
      isAdmin = !!d.admin;
      if(isAdmin){ $("grid").classList.add("admin"); $("adminCovers").hidden = false; }
      books = d.items;
      books.forEach(function(b){ b._t = (b.title || "").toLowerCase(); b._a = (b.author_sort || "").toLowerCase(); b._s = b._t + " " + (b.author || "").toLowerCase(); bySlug[b.slug] = b; });
      var counts = {};
      books.forEach(function(b){ b.sections.forEach(function(g){ counts[g] = (counts[g] || 0) + 1; }); });
      secList = Object.keys(counts).map(function(k){ return {name:k, count:counts[k]}; }).sort(function(a,b){ return b.count - a.count; });
      // if the reader has books in progress, offer a one-click "Continue" filter
      var inProg = books.filter(function(b){ return started(b.slug); }).length;
      if(inProg){
        var g = document.createElement("div"); g.className = "facet-group";
        g.innerHTML = '<div class="facet-h">Yours</div>';
        var box = document.createElement("div"); g.appendChild(box);
        var rb = fopt("Continue reading", inProg, false, function(){ state.reading = !state.reading; compute(); });
        rb.id = "readingOpt"; box.appendChild(rb);
        $("facets").insertBefore(g, $("facets").firstChild);
      }
      compute();
    }).catch(function(){ $("browseEmpty").hidden = false; $("browseEmpty").textContent = "Could not load the library."; });
  }

  // =================== READER (paginated) ===================
  function initReader(slug){
    $("reader").hidden = false;
    document.body.classList.add("reading");
    $("tocToggle").hidden = false; $("fMinus").hidden = false; $("fPlus").hidden = false; $("fFace").hidden = false;
    $("back").href = "/read"; $("back").textContent = "‹ Library";
    var book = null, current = 0, savedPositions = {};   // `book` = fetched book DATA (toc, title…)
    var chapter = $("chapter"), pageport = $("pageport"), bookEl = $("book"), pagebar = $("pagebar");
    var stride = 1, pages = 1, page = 0, colGap = 56, numCols = 1, colsPer = 1, foliosBefore = 0, frontCols = 0, turnT, maxPage = 0;
    var pendingAnchor = null;   // child index to land on after (re)paginating
    var chapterName = "", openerCol = -1;
    // the inside follows the book's cover style: its ornament is the cover motif, its accents the cover foil
    function applyInterior(){
      if(!book){ return; }
      CS.load().then(function(){ return CS.getOptions(); }).then(function(o){
        var st = CS.resolve({slug: slug, sections: book.genres || []});
        var key = isDark() ? st.dark : st.light, th = null;
        (o.themes || []).forEach(function(t){ if(t.key === key){ th = t; } });
        var m = st.motif || "universal", mk = m;
        if(m === "shelf" || m.indexOf("shelf:") === 0){
          var shelf = m === "shelf" ? st.motifFrom : m.slice(6); mk = "universal";
          for(var i = 0; i < (o.motifs || []).length; i++){ if(o.motifs[i].shelf === shelf && o.motifs[i].key !== "universal"){ mk = o.motifs[i].key; break; } }
        }
        var src = mk === "universal" ? "/api/house-cover/motif/library/universal.png" : "/api/house-cover/motif/" + mk + ".png";
        root.style.setProperty("--ex-orn", "url('" + src + "')");
        if(th){ root.style.setProperty("--ex-foil", th.foil); root.style.setProperty("--ex-text", th.text || th.foil); }
      }).catch(function(){});
    }
    window.__exegRestyle = applyInterior;

    var narrow = function(){ return matchMedia("(max-width:820px)").matches; };
    function setToc(open){
      $("toc").classList.toggle("hidden", !open);
      $("stage").classList.toggle("wide", !open);
      $("backdrop").classList.toggle("show", open && narrow());
      pendingAnchor = firstVisibleBlockIndex();
      requestAnimationFrame(paginate);   // sidebar changed the width → re-measure, keep place
    }
    if(narrow()){ $("toc").classList.add("hidden"); $("stage").classList.add("wide"); }
    $("tocToggle").addEventListener("click", function(){ setToc($("toc").classList.contains("hidden")); });
    $("backdrop").addEventListener("click", function(){ setToc(false); });

    // ---- pagination engine ----
    function firstVisibleBlockIndex(){
      var kids = chapter.children, x = page * stride;
      for(var i = 0; i < kids.length; i++){ if(kids[i].offsetLeft >= x - 2){ return i; } }
      return Math.max(0, kids.length - 1);
    }
    function paginate(){
      var host = $("stage").clientWidth;            // width available for the book + side "desk"
      if(host <= 0){ return; }                      // not laid out yet; a settle pass will retry
      var scale = SCALES[scaleIdx] || 1.15;
      colGap = narrow() ? 52 : 76;                  // gutter = inner margins (split across the seam)
      var margin = narrow() ? 30 : 66;              // outer page margin (kept ≤ gutter, so no bleed)
      var measure = Math.round(560 * scale / 1.15); // hardcover line ≈ 62 chars; scales with text size
      var minCol = narrow() ? 260 : 420;            // go two-up only when each column clears this
      var cols = ((host - 2 * margin - colGap) / 2 >= minCol) ? 2 : 1;
      var contentW = Math.min(cols * measure + (cols - 1) * colGap, host - 2 * margin);
      var colW = Math.floor((contentW - (cols - 1) * colGap) / cols);
      bookEl.style.width = (contentW + 2 * margin) + "px";     // the centered page card; desk shows on the sides
      pageport.style.paddingLeft = pageport.style.paddingRight = margin + "px";
      pagebar.style.paddingLeft = pagebar.style.paddingRight = margin + "px";   // folios align under each page
      chapter.classList.remove("fading");           // never leave a re-measure mid-fade
      chapter.style.columnGap = colGap + "px";
      chapter.style.columnWidth = colW + "px";
      stride = chapter.clientWidth + colGap;        // one page = `cols` columns; stride is content width + gutter
      pages = Math.max(1, Math.ceil(chapter.scrollWidth / stride - 0.05));
      // gutter (two-up only) + continuous folio numbering estimated from word counts
      colsPer = cols;
      $("stage").classList.toggle("twoup", cols === 2);
      var opener = chapter.querySelector(".ex-open");
      var firstBody = opener || chapter.querySelector(":scope > :not(.fm-page):not(.fm-toc)");
      frontCols = (current === 1 && firstBody) ? Math.round(firstBody.offsetLeft / (colW + colGap)) : 0;   // title, colophon, contents
      openerCol = opener ? Math.round(opener.offsetLeft / (colW + colGap)) : -1;
      numCols = Math.max(1, Math.round((chapter.scrollWidth + colGap) / (colW + colGap)));
      foliosBefore = 0;
      var curWords = (book.toc[current - 1] && book.toc[current - 1].words) || 0;
      if(curWords > 0){
        var wpc = curWords / Math.max(1, numCols - frontCols);  // words per CONTENT page (excl. front matter)
        for(var k = 0; k < current - 1; k++){
          foliosBefore += Math.max(1, Math.round(((book.toc[k] && book.toc[k].words) || 0) / wpc));
        }
      }
      var target = 0;
      if(pendingAnchor != null && chapter.children[pendingAnchor]){
        target = Math.floor(chapter.children[pendingAnchor].offsetLeft / stride);
      }
      pendingAnchor = null;
      goToPage(Math.min(Math.max(target, 0), pages - 1), false);
    }
    function updateBar(){
      var toc = book.toc || [], entry = toc[current - 1];
      var title = (entry && entry.title) ? entry.title : ("Section " + current);
      var leftIdx = page * colsPer;                 // 0-based column (page) within this chapter
      var contentIdx = leftIdx - frontCols;         // < 0 → blank/title front matter: no folio, no header
      var shortHead = function(t){ t = String(t || "").split(/:\s|;\s|,?\s+or,?\s+/i)[0]; return t.length > 46 ? t.slice(0, 44).replace(/\s+\S*$/, "") + "…" : t; };
      var headFor = function(col){ return (col < frontCols || col === openerCol || col >= numCols) ? "" : null; };
      if(colsPer === 2){
        $("rhL").textContent = headFor(leftIdx) === "" ? "" : shortHead(book.title);
        $("rhR").textContent = headFor(leftIdx + 1) === "" ? "" : shortHead(chapterName || book.title);
      } else {
        $("rhL").textContent = ""; $("rhR").textContent = headFor(leftIdx) === "" ? "" : shortHead(chapterName || book.title);
      }
      $("rhL").style.display = colsPer === 2 ? "" : "none";
      if(contentIdx < 0){
        $("pbL").textContent = ""; $("pbR").textContent = ""; $("pbC").textContent = "";
      } else {
        var folioL = foliosBefore + contentIdx + 1;
        if(folioL > maxPage){ maxPage = folioL; }   // furthest overall page reached → gates "Continue Reading"
        if(colsPer === 2){                          // two-up: a folio under each visible page
          $("pbL").textContent = folioL;
          $("pbR").textContent = (leftIdx + 1 < numCols) ? (folioL + 1) : "";
        } else {                                    // single page: one folio, outer corner
          $("pbL").textContent = "";
          $("pbR").textContent = folioL;
        }
        $("pbC").textContent = "";
      }
      var frac = pages > 1 ? page / (pages - 1) : 1;
      var overall = ((current - 1) + frac) / (book.chapter_count || 1);
      $("pbFill").style.width = Math.max(0, Math.min(100, overall * 100)).toFixed(1) + "%";
      $("pgPrev").disabled = (page <= 0 && current <= 1);
      $("pgNext").disabled = (page >= pages - 1 && current >= (book.chapter_count || 1));
    }
    function goToPage(p, animate){
      page = Math.min(Math.max(p, 0), pages - 1);
      closePop();
      var apply = function(){
        chapter.style.transform = "translateX(" + (-page * stride) + "px)";   // reposition while hidden
        updateBar();
        savePosition();
      };
      clearTimeout(turnT);
      if(animate && !matchMedia("(prefers-reduced-motion: reduce)").matches){   // quick fade out → swap → fade in (no sliding); reduced motion turns at once
        chapter.classList.add("fading");
        turnT = setTimeout(function(){ apply(); chapter.classList.remove("fading"); }, 120);
      } else {
        chapter.classList.remove("fading");
        apply();
      }
    }
    function nextPage(){
      if(page < pages - 1){ goToPage(page + 1, true); }
      else if(current < (book.chapter_count || 1)){ loadChapter(current + 1, "start"); }
    }
    function prevPage(){
      if(page > 0){ goToPage(page - 1, true); }
      else if(current > 1){ loadChapter(current - 1, "end"); }
    }

    // ---- data + rendering ----
    Promise.all([
      fetch("/api/books/" + encodeURIComponent(slug)).then(function(r){ return r.ok ? r.json() : null; }),
      fetch("/api/reading/position").then(function(r){ return r.ok ? r.json() : {positions:{}}; }).catch(function(){ return {positions:{}}; })
    ]).then(function(res){
      book = res[0];
      if(!book){ chapter.innerHTML = '<div class="ch-eyebrow">Not found</div><p>This book isn’t in the Reading Room.</p>'; return; }
      savedPositions = (res[1] && res[1].positions) || {};
      document.title = book.title + " · Exegetica";
      $("tocBookTitle").textContent = book.title;
      $("tocBookAuthor").textContent = book.author || "";
      renderToc();
      applyInterior();
      var fromHash = parseInt((location.hash || "").replace("#", ""), 10);
      var start = fromHash || savedPositions[slug] || parseInt(lsGet("read-pos:" + slug) || "0", 10) || 1;
      start = Math.min(Math.max(start, 1), book.chapter_count || 1);
      loadChapter(start, "restore");
    });

    function renderToc(){
      var ol = $("tocList"); ol.innerHTML = "";
      (book.toc || []).forEach(function(c){
        var li = document.createElement("li"), a = document.createElement("a");
        a.href = "#" + c.section_number; a.dataset.n = c.section_number;
        a.innerHTML = '<span class="n">' + c.section_number + '</span>' + esc((c.label ? c.label + " · " : "") + (c.name || c.title || ("Section " + c.section_number)));
        a.addEventListener("click", function(ev){ ev.preventDefault(); loadChapter(c.section_number, "start"); if(narrow()){ setToc(false); } });
        li.appendChild(a); ol.appendChild(li);
      });
    }
    function markToc(){
      $("tocList").querySelectorAll("a").forEach(function(a){ a.classList.toggle("on", parseInt(a.dataset.n, 10) === current); });
      var on = $("tocList").querySelector("a.on"); if(on && on.scrollIntoView){ on.scrollIntoView({block:"nearest"}); }
    }
    function loadChapter(n, landing){
      fetch("/api/books/" + encodeURIComponent(slug) + "/chapter/" + n).then(function(r){ return r.ok ? r.json() : null; }).then(function(c){
        if(!c){ return; }
        current = c.section_number;
        chapterName = c.name || c.label || "";
        var front = "";
        if(current === 1){                            // title page, colophon, contents (Exegetica front matter)
          var tparts = book.title.split(/:\s+/), main = tparts.shift(), sub = tparts.join(": ");
          var face = root.getAttribute("data-face") === "literata" ? "Literata" : "EB Garamond";
          front = (narrow() ? "" : '<div class="fm-page" aria-hidden="true"></div>') +
            '<section class="fm-page fm-title"><div><i class="ex-orn"></i><h1>' + esc(main) + '</h1>' +
              (sub ? '<div class="fm-sub">' + esc(sub) + '</div>' : '') +
              '<div class="fm-rule"></div>' + (book.author ? '<div class="fm-by">' + esc(book.author) + '</div>' : '') +
            '</div><div class="fm-imp">Exegetica</div></section>' +
            '<section class="fm-page fm-colo"><i class="ex-orn"></i><div class="fm-imp">Exegetica</div>' +
              (book.source === "exegetica"                // an original work written for the library
                ? '<p><i>' + esc(main) + '</i> was written and designed for the Exegetica library.</p>'
                : '<p>This edition of <i>' + esc(main) + '</i> was set, corrected and designed for the Exegetica library.</p>') +
              (!book.license || /public domain|^pd\b|^pd-|cc0/i.test(book.license)
                ? '<p>Its text is in the public domain and belongs to everyone.</p>'
                : '<p>Text ' + esc(book.license) + '.</p>') +
              '<p>Set in ' + face + ' and Fraunces. Free to read; never for sale.</p></section>';
          if(book.front_html){                          // the author's dedication / epigraph, on a page of its own
            // a long dedication (a sonnet) and an epigraph each get a page; short ones share one
            var parts = book.front_html.match(/<div class="ex-(?:dedication|epigraph)"[\s\S]*?<\/div>(?=<div class="ex-|$)/g) || [book.front_html];
            var long = book.front_html.replace(/<[^>]+>/g, "").length > 500;
            (long && parts.length > 1 ? parts : [book.front_html]).forEach(function(p){
              front += '<section class="fm-page fm-ded">' + p + '</section>';
            });
          }
          if((book.toc || []).length > 1){
            // chapters known only by numerals set as a compact grid of numerals
            var bare = book.toc.filter(function(t){ return !t.label && /^(?:[IVXLCDM]+|\d+)\.?$/i.test(t.name || ""); }).length;
            var grid = bare === book.toc.length;
            front += '<section class="fm-toc' + (grid ? ' fm-grid' : '') + '"><h2>Contents</h2><div class="fm-rule"></div><ol>' +
              book.toc.map(function(t){
                return '<li><button data-go="' + t.section_number + '"><span class="fm-l">' + esc(t.label || "") + '</span>' +
                  '<span class="fm-n">' + esc(t.name || t.title || ("Section " + t.section_number)) +
                  (t.syn ? '<span class="fm-syn">' + esc(t.syn) + '</span>' : '') + '</span></button></li>';
              }).join("") + '</ol></section>';
          }
        }
        chapter.innerHTML = front + c.html;
        if(window.Shell && Shell.tagLanguages){ Shell.tagLanguages(chapter); }   // Greek and Hebrew set before the pages are measured
        typesetMath(chapter, c.html).then(function(){ laidOut(landing); });
      });
    }
    // Maths books store equations as TeX (\( \) inline, \[ \] display); KaTeX loads only when a
    // chapter needs it, and typesets before pagination measures the columns.
    var KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/";
    var mathLoad = null;
    function loadMath(){
      if(mathLoad){ return mathLoad; }
      function js(src){ return new Promise(function(ok, fail){ var s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = fail; document.head.appendChild(s); }); }
      var css = document.createElement("link"); css.rel = "stylesheet"; css.href = KATEX + "katex.min.css"; document.head.appendChild(css);
      mathLoad = js(KATEX + "katex.min.js").then(function(){ return js(KATEX + "contrib/auto-render.min.js"); })
        .catch(function(){ mathLoad = null; });   // offline: show the raw TeX, retry on the next chapter
      return mathLoad;
    }
    function typesetMath(el, html){
      if(html.indexOf("\\(") < 0 && html.indexOf("\\[") < 0){ return Promise.resolve(); }
      return loadMath().then(function(){
        if(!window.renderMathInElement){ return; }
        window.renderMathInElement(el, {delimiters: [{left: "\\[", right: "\\]", display: true}, {left: "\\(", right: "\\)", display: false}], throwOnError: false});
        // keep trailing punctuation on the formula's line ("… size as dx." never strands the ".")
        el.querySelectorAll(".katex").forEach(function(k){
          var t = k.nextSibling, m = t && t.nodeType === 3 && !k.closest(".katex-display") && t.data.match(/^[.,;:!?)\]]+/);
          if(!m){ return; }
          var w = document.createElement("span"); w.className = "math-np";
          k.parentNode.insertBefore(w, k); w.appendChild(k); w.appendChild(document.createTextNode(m[0]));
          t.data = t.data.slice(m[0].length);
        });
        return document.fonts && document.fonts.ready;
      });
    }
    function laidOut(landing){
      markToc();
      history.replaceState(null, "", "/read/" + encodeURIComponent(slug) + "#" + current);
      var savedAnchor = parseInt(lsGet("read-anchor:" + slug + ":" + current) || "0", 10);
      pendingAnchor = (landing === "restore" && savedAnchor > 0) ? savedAnchor : null;
      paginate();
      if(landing === "end"){ goToPage(pages - 1, false); }
      // re-measure once layout/webfonts settle (metrics shift how columns fill)
      var settle = function(){
        if(landing === "end"){ pendingAnchor = null; paginate(); goToPage(pages - 1, false); }
        else { pendingAnchor = firstVisibleBlockIndex(); paginate(); }
      };
      requestAnimationFrame(settle);
      if(document.fonts && document.fonts.ready){ document.fonts.ready.then(settle); }
    }
    var saveT;
    function savePosition(){
      lsSet("read-pos:" + slug, current);
      lsSet("read-anchor:" + slug + ":" + current, firstVisibleBlockIndex());
      clearTimeout(saveT);
      saveT = setTimeout(function(){
        fetch("/api/reading/position", {method:"PUT", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({slug: slug, section_number: current, pages: maxPage})}).catch(function(){});
      }, 700);
    }

    var pop = null;
    function closePop(){ if(pop){ pop.remove(); pop = null; } }
    chapter.addEventListener("click", function(e){
      var go = e.target.closest && e.target.closest("[data-go]");
      if(go){ e.preventDefault(); loadChapter(parseInt(go.dataset.go, 10), "start"); return; }
      var ref = e.target.closest && e.target.closest("a.ex-ref");
      if(ref){                                      // a footnote opens beside its marker, never turns the page
        e.preventDefault(); e.stopPropagation(); closePop();
        var note = chapter.querySelector("#fn" + ref.dataset.fn);
        if(!note){ return; }
        pop = document.createElement("div"); pop.className = "ex-pop"; pop.setAttribute("role", "note");
        pop.innerHTML = note.innerHTML; document.body.appendChild(pop);
        var r = ref.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
        var x = Math.min(Math.max(16, r.left - w / 2), innerWidth - w - 16);
        var y = (r.bottom + 10 + h < innerHeight - 50) ? r.bottom + 10 : Math.max(70, r.top - h - 10);
        pop.style.left = x + "px"; pop.style.top = y + "px";
      }
    });
    document.addEventListener("click", function(e){ if(pop && !pop.contains(e.target)){ closePop(); } });
    document.addEventListener("keydown", function(e){ if(e.key === "Escape"){ closePop(); } });
    // ---- input: edge zones, keys, swipe ----
    $("pgNext").addEventListener("click", nextPage);
    $("pgPrev").addEventListener("click", prevPage);
    document.addEventListener("keydown", function(e){
      if(e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)){ return; }
      if(e.key === "ArrowRight" || e.key === "PageDown" || e.key === " "){ e.preventDefault(); nextPage(); }
      else if(e.key === "ArrowLeft" || e.key === "PageUp"){ e.preventDefault(); prevPage(); }
      else if(e.key === "Home"){ goToPage(0, true); }
      else if(e.key === "End"){ goToPage(pages - 1, true); }
    });
    var tsx = 0, tsy = 0, tst = 0;
    pageport.addEventListener("touchstart", function(e){ var t = e.changedTouches[0]; tsx = t.clientX; tsy = t.clientY; tst = Date.now(); }, {passive:true});
    pageport.addEventListener("touchend", function(e){
      var t = e.changedTouches[0], dx = t.clientX - tsx, dy = t.clientY - tsy;
      if(Date.now() - tst < 600 && Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.6){
        if(dx < 0){ nextPage(); } else { prevPage(); }
      }
    }, {passive:true});

    // resize / text-size → re-paginate, keeping the reader's place
    var rz;
    window.addEventListener("resize", function(){ clearTimeout(rz); rz = setTimeout(function(){ pendingAnchor = firstVisibleBlockIndex(); paginate(); }, 150); });
    relayout = function(){ pendingAnchor = firstVisibleBlockIndex(); paginate(); };
  }
})();
