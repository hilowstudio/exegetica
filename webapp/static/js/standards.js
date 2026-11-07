/* The academic standards page (/prep-room/standards, webapp/about.py): objectives load when a sub-topic
   opens, and the search reveals a match in the tree. */
(function(){
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function grade(g){return g===0?"K":String(g);}
  function load(d){
    if(d.dataset.loaded)return Promise.resolve();
    d.dataset.loaded="1";
    var box=d.querySelector(".objs");box.textContent="Loading objectives…";
    return fetch("/api/standards/objectives?sub_topic="+encodeURIComponent(d.dataset.st)).then(function(r){return r.json();}).then(function(j){
      var objs=(j.objectives||[]).slice().sort(function(a,b){return a.c-b.c;});
      box.innerHTML="<ol>"+objs.map(function(o){
        var a=o.a||{},anc=[].concat(a.scripture||[],a.confessions||[],a.standards||[]);
        return '<li id="o-'+esc(o.id)+'"><span class="gr">Grade '+grade(o.g)+'</span>'+esc(o.t)+
          (anc.length?'<span class="anc">'+esc(anc.join(" · "))+'</span>':"")+"</li>";}).join("")+"</ol>";
    }).catch(function(){d.dataset.loaded="";box.textContent="The objectives could not be loaded. Close and open this again.";});
  }
  document.querySelectorAll("details.st").forEach(function(d){d.addEventListener("toggle",function(){if(d.open)load(d);});});
  function reveal(ids){
    ["subject","sub_subject","sub_topic"].forEach(function(k){var e=ids[k]&&document.getElementById("S-"+ids[k]);if(e)e.open=true;});
    var st=ids.sub_topic&&document.getElementById("S-"+ids.sub_topic);
    var target=st||document.getElementById("S-"+(ids.sub_subject||ids.subject));
    if(!target)return;
    (st?load(st):Promise.resolve()).then(function(){
      var o=ids.objective&&document.getElementById("o-"+ids.objective);
      document.querySelectorAll("li.hit").forEach(function(x){x.classList.remove("hit");});
      if(o)o.classList.add("hit");
      (o||target).scrollIntoView({block:"center"});
      target.querySelector("summary").focus({preventScroll:true});
    });
  }
  var q=document.getElementById("q"),hits=document.getElementById("hits"),timer=null;
  q.addEventListener("input",function(){
    clearTimeout(timer);var v=q.value.trim();
    if(v.length<2){hits.innerHTML="";return;}
    timer=setTimeout(function(){
      fetch("/api/standards/search?q="+encodeURIComponent(v)).then(function(r){return r.json();}).then(function(j){
        var rs=(j.results||[]).slice(0,10);
        if(!rs.length){hits.innerHTML='<p class="path">No matches. Try fewer or simpler words.</p>';return;}
        hits.innerHTML="";
        rs.forEach(function(h){
          var b=document.createElement("button");b.type="button";
          b.innerHTML=esc(h.label)+'<span class="path">'+esc(h.path.join(" › "))+(h.grade!=null?" · grade "+grade(h.grade):"")+"</span>";
          b.addEventListener("click",function(){reveal(h.ids);});
          hits.appendChild(b);
        });
      }).catch(function(){hits.innerHTML='<p class="path">Search is not available right now.</p>';});
    },200);
  });
})();
