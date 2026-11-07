/* The Study Bible Corpus page (templates/corpus.html). The rail, theme and Need help now? come from static/js/shell.js. */
  var FATHERS = JSON.parse(document.getElementById("fathers-data").textContent);
  var TOTAL_ENTRIES = FATHERS.reduce(function(s,f){return s+f.count;},0);

  var STATS = [
    [(985).toLocaleString(), "Grounding works"],
    [FATHERS.length, "Church fathers"],
    [TOTAL_ENTRIES.toLocaleString(), "Catena entries"],
    [9, "Commentaries"],
    [42, "Creeds & confessions"],
    [5, "Translations"]
  ];
  document.getElementById("stats").innerHTML = STATS.map(function(s){
    return '<div class="stat"><div class="n">'+s[0]+'</div><div class="l">'+s[1]+'</div></div>';
  }).join("");
  document.getElementById("fkey").textContent = FATHERS.length + " authors · " + TOTAL_ENTRIES.toLocaleString() + " entries";

  function esc(s){return (s||"").replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}
  var host = document.getElementById("fathers"), countEl = document.getElementById("fcount"), noneEl = document.getElementById("fnone");

  function render(q){
    q = (q||"").trim().toLowerCase();
    var shown = FATHERS.filter(function(f){ return !q || f.name.toLowerCase().indexOf(q)>=0; });
    countEl.textContent = shown.length===FATHERS.length ? (FATHERS.length+" shown") : (shown.length+" of "+FATHERS.length);
    noneEl.hidden = shown.length>0;
    host.hidden = shown.length===0;
    host.innerHTML = shown.map(function(f){
      var name = esc(f.name);
      if(q){ var i=f.name.toLowerCase().indexOf(q); if(i>=0){ name = esc(f.name.slice(0,i))+"<mark>"+esc(f.name.slice(i,i+q.length))+"</mark>"+esc(f.name.slice(i+q.length)); } }
      return '<div class="fentry"><span class="fn">'+name+'</span><span class="fc">'+f.count+'</span></div>';
    }).join("");
  }
  render("");
  document.getElementById("fsearch").addEventListener("input", function(e){ render(e.target.value); });

  (function(){
    var WORKS = JSON.parse(document.getElementById("corpus-data").textContent);
    var det=document.getElementById("corpus-disc"), listEl=document.getElementById("corpuslist"),
        cc=document.getElementById("ccount"), cnone=document.getElementById("cnone"), inp=document.getElementById("csearch");
    function esc(s){return (s||"").replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}
    function crender(q){
      q=(q||"").trim().toLowerCase();
      var shown=WORKS.filter(function(w){return !q || w.t.toLowerCase().indexOf(q)>=0 || w.a.toLowerCase().indexOf(q)>=0;});
      cc.textContent = shown.length===WORKS.length ? (WORKS.length+" works") : (shown.length+" of "+WORKS.length);
      cnone.hidden = shown.length>0; listEl.hidden = shown.length===0;
      listEl.innerHTML = shown.map(function(w){
        return '<div class="centry"><span class="ct">'+esc(w.t)+'</span> <span class="ca">\u2014 '+esc(w.a)+'</span></div>';
      }).join("");
    }
    var built=false;
    det.addEventListener("toggle", function(){ if(det.open && !built){ crender(""); built=true; } });
    inp.addEventListener("input", function(e){ crender(e.target.value); });
  })();

  /* The tool list comes from /api/config, which builds it with webapp/tool_catalog.py from the
     tools each chat mode registers, so the page cannot fall behind the app. */
  (function(){
    var host = document.getElementById("tool-groups"), key = document.getElementById("tkey");
    function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
    function count(groups){ return groups.reduce(function(n,g){ return n + g.tools.length; }, 0); }
    function groupsHtml(groups){
      return groups.map(function(g){
        var cards = g.tools.map(function(t){
          return '<div class="item"><div class="tool">' + esc(t.name) + '</div><div class="d">' + esc(t.desc) + '</div></div>';
        }).join("");
        return '<div class="subh">' + esc(g.group) + '</div><div class="grid">' + cards + '</div>';
      }).join("");
    }
    function fail(){ host.innerHTML = '<p class="fnone">The tool list did not load. Reload the page to try again.</p>'; }
    fetch("/api/config", {headers: {"Accept": "application/json"}, credentials: "same-origin"})
      .then(function(r){ if(!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(cfg){
        var cat = (cfg && cfg.catalog) || {}, bible = cat.bible || [], hist = cat.history || [];
        if(!bible.length){ fail(); return; }
        var nb = count(bible), nh = count(hist);
        key.textContent = "persona · " + nb + " tools";
        var html = '<h3 class="modeh">Bible mode <span>' + nb + ' tools</span></h3>' + groupsHtml(bible);
        if(nh){
          var shared = {};
          bible.forEach(function(g){ shared[g.group] = true; });
          var own = hist.filter(function(g){ return !shared[g.group]; });
          var reach = nh - count(own);
          html += '<h3 class="modeh">History mode <span>' + nh + ' tools</span></h3>'
               + '<p class="sec-note">History mode has the ' + count(own) + ' history tools below. It also reaches '
               + reach + ' Study Bible tools from the list above, every one except the Gospel of John course.</p>'
               + groupsHtml(own);
        }
        host.innerHTML = html;
      })
      .catch(fail);
  })();
