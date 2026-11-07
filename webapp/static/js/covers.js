/* The Magazine Covers — Exegetica page (templates/covers.html). The rail, theme and Need help now? come from static/js/shell.js. */
(function(){
  var $ = function(id){ return document.getElementById(id); };
  var items = [], bySlug = {}, show = "needs", mag = "", busy = false;

  function el(tag, cls, text){ var e = document.createElement(tag); if(cls) e.className = cls; if(text != null) e.textContent = text; return e; }
  function visible(){ return items.filter(function(it){
    return (show === "all" || !it.custom || it.done) && (!mag || it.mag === mag); }); }
  function selected(){ return items.filter(function(it){ return it.sel && !it.done; }); }

  function img(src, alt){
    var i = el("img"); i.alt = alt || ""; i.loading = "lazy"; i.referrerPolicy = "no-referrer"; i.src = src;
    i.onerror = function(){ var n = el("div", "none", "No preview"); i.replaceWith(n); };
    return i;
  }
  function card(it){
    var c = el("article", "card" + (it.sel ? " sel" : "")); c.dataset.slug = it.slug;
    var covers = el("div", "covers"), now = el("div", "cv now"), nw = el("div", "cv new");
    var f1 = el("div", "fr"); if(it.current){ f1.appendChild(img(it.current, "Current cover")); } else { f1.appendChild(el("div", "none", "No cover")); }
    now.appendChild(f1); now.appendChild(el("span", "lbl", "Now"));
    var cand = it.candidates[it.pick], f2 = el("div", "fr");
    f2.appendChild(img(cand.thumb, it.issue)); f2.title = "Select or deselect";
    f2.addEventListener("click", function(){ toggle(it); });
    nw.appendChild(f2); nw.appendChild(el("span", "lbl", cand.domain));
    covers.appendChild(now); covers.appendChild(nw);
    var cb = el("input", "pick"); cb.type = "checkbox"; cb.checked = !!it.sel; cb.disabled = !!it.done;
    cb.setAttribute("aria-label", "Use the magazine cover for " + it.title);
    cb.addEventListener("change", function(){ toggle(it, cb.checked); });
    var m = el("div", "meta");
    m.appendChild(el("div", "t", it.title));
    if(it.author) m.appendChild(el("div", "a", it.author));
    m.appendChild(el("div", "iss", it.issue));
    if(it.candidates.length > 1){
      var alts = el("div", "alts");
      it.candidates.forEach(function(cd, i){
        var b = el("button", null, cd.domain); b.type = "button"; b.setAttribute("aria-pressed", i === it.pick ? "true" : "false");
        b.addEventListener("click", function(){ it.pick = i; redraw(it); });
        alts.appendChild(b);
      });
      m.appendChild(alts);
    }
    if(it.custom && !it.done) m.appendChild(el("span", "badge", "Custom cover" + (it.custom_source ? ": " + it.custom_source : "")));
    if(it.state) m.appendChild(el("div", "state " + (it.stateCls || ""), it.state));
    c.appendChild(covers); c.appendChild(cb); c.appendChild(m);
    return c;
  }
  function redraw(it){ var old = document.querySelector('.card[data-slug="' + CSS.escape(it.slug) + '"]'); if(old) old.replaceWith(card(it)); summary(); }
  function toggle(it, on){ if(it.done || busy) return; it.sel = on == null ? !it.sel : on; redraw(it); }
  function render(){
    var v = visible(); $("grid").replaceChildren.apply($("grid"), v.map(card));
    $("msg").hidden = !!v.length; if(!v.length) $("msg").textContent = "Nothing to review here.";
    summary();
  }
  function summary(){
    var v = visible(), s = selected();
    $("count").textContent = v.length + " shown · " + s.length + " selected";
    $("go").textContent = "Apply " + s.length + (s.length === 1 ? " cover" : " covers");
    $("go").disabled = busy || !s.length;
  }

  function apply(){
    var queue = selected(), total = queue.length, done = 0, failed = 0;
    if(!total) return;
    busy = true; summary();
    function next(){
      var it = queue.shift(); if(!it) return Promise.resolve();
      var cd = it.candidates[it.pick];
      it.state = "Saving…"; it.stateCls = ""; redraw(it);
      return fetch("/api/reading/cover", {method:"PUT", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({slug: it.slug, cover_url: cd.image, source: cd.source, source_page: cd.page || ""})})
        .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(j){ return {ok:r.ok, j:j}; }); })
        .then(function(res){
          if(res.ok){ it.done = true; it.sel = false; it.current = res.j.cover; it.state = "Applied"; it.stateCls = "ok"; }
          else { failed++; it.state = it.candidates.length > 1 ? "Couldn't download it. Try the other source." : "Couldn't download it. Try again later."; it.stateCls = "bad"; }
        })
        .catch(function(){ failed++; it.state = "Couldn't reach the server."; it.stateCls = "bad"; })
        .then(function(){ done++; redraw(it); $("prog").textContent = "Applied " + (done - failed) + " of " + total + (failed ? " · " + failed + " failed" : ""); return next(); });
    }
    $("prog").textContent = "Applying " + total + "…";
    Promise.all([next(), next(), next()]).then(function(){   // three at a time
      busy = false; summary();
      $("prog").textContent = "Done: " + (total - failed) + " applied" + (failed ? ", " + failed + " failed (still selectable to retry)" : "") + ".";
      items.forEach(function(it){ if(!it.done && it.stateCls === "bad") it.sel = true; });
      render();
    });
  }

  document.querySelectorAll("[data-show]").forEach(function(b){
    b.addEventListener("click", function(){
      show = b.dataset.show;
      document.querySelectorAll("[data-show]").forEach(function(x){ x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      render();
    });
  });
  $("mag").addEventListener("change", function(){ mag = this.value; render(); });
  $("selAll").addEventListener("click", function(){ if(busy) return; visible().forEach(function(it){ if(!it.done) it.sel = true; }); render(); });
  $("selNone").addEventListener("click", function(){ if(busy) return; items.forEach(function(it){ it.sel = false; }); render(); });
  $("go").addEventListener("click", function(){
    var n = selected().length;
    if(window.confirm("Download " + n + (n === 1 ? " cover" : " covers") + " and make " + (n === 1 ? "it the book's" : "them the books'") + " cover art?")) apply();
  });

  fetch("/api/reading/cover/review").then(function(r){
    if(r.status === 403){ throw new Error("forbidden"); }
    return r.json();
  }).then(function(d){
    items = d.items.map(function(it){
      it.mag = it.issue.split(",")[0]; it.pick = 0; it.sel = !it.custom; return it;
    });
    var mags = {}; items.forEach(function(it){ mags[it.mag] = (mags[it.mag] || 0) + 1; });
    Object.keys(mags).sort().forEach(function(k){ var o = el("option", null, k + " (" + mags[k] + ")"); o.value = k; $("mag").appendChild(o); });
    $("bar").hidden = false; $("dock").hidden = false;
    render();
  }).catch(function(e){
    $("msg").textContent = e.message === "forbidden" ? "Sign in as a library admin to review covers." : "Couldn't load the covers. Try again shortly.";
  });
})();
