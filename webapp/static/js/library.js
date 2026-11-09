/* The Living Library · Exegetica page (templates/library.html). The rail, theme and Need help now? come from static/js/shell.js. */
"use strict";
var $=function(id){return document.getElementById(id);};
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function cssurl(u){return "'"+String(u).replace(/'/g,"%27").replace(/\)/g,"%29")+"'";}
function initials(s){return s.replace(/^(the|a|an)\s+/i,"").split(/\s+/).slice(0,2).map(function(w){return w[0]||"";}).join("").toUpperCase();}
var ACCENTS=["#8f2533","#2f4d5c","#5b4b8a","#3f6b4f","#9a7c3d","#7a3b52","#2e5b57"];
var ai=0; function nextAccent(){return ACCENTS[ai++%ACCENTS.length];}
function uid(){return "r"+Math.random().toString(36).slice(2,8);}

// ---------- seed library (skin only) ----------
var DEMO_SEED=[
  {id:uid(),type:"book",title:"The Pilgrim's Progress",sub:"John Bunyan",meta:"1678",accent:"#8f2533"},
  {id:uid(),type:"book",title:"Confessions",sub:"Augustine of Hippo",meta:"AD 397",accent:"#2f4d5c"},
  {id:uid(),type:"podcast",title:"Renewing Your Mind",sub:"Ligonier Ministries",meta:"1,200+ episodes",accent:"#5b4b8a"},
  {id:uid(),type:"video",title:"The Water Cycle, Explained",sub:"Crash Course Kids",meta:"9:14",accent:"#3f6b4f"}
];
var LIB=[], booting=true, anon=false;

var TYPE_UI={
  book:{title:"Bring a book into your library",placeholder:"Search a book by title, author, or ISBN…",add:"Search",
    hint:"Searches OpenLibrary and Google Books. Pick an edition to add.",
    lead:'<svg viewBox="0 0 24 24"><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H12v15H5.5A1.5 1.5 0 0 0 4 20.5z"/><path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H12v15h6.5a1.5 1.5 0 0 1 1.5 1.5z"/></svg>'},
  podcast:{title:"Bring a podcast into your library",placeholder:"Search Apple Podcasts by show or host…",add:"Search",
    hint:"Searches Apple Podcasts. Pick a show and we save its feed.",
    lead:'<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4"/></svg>'},
  video:{title:"Bring a video into your library",placeholder:"Search YouTube, or paste a link…",add:"Search",
    hint:"Search YouTube by topic, re-ranked by meaning, or paste a link.",
    lead:'<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 9l5 3-5 3z"/></svg>'}
};

var curType="book", curFilter="all";
var AUTH={signed:false,user:null,admin:false};  // resolved in initLibrary(); shelf persists to Neon when signed in
var wrap=(function(){try{return localStorage.getItem("studybible.lib.wrap")==="on";}catch(e){return false;}})();
var sortKey=(function(){try{return localStorage.getItem("studybible.lib.sort")==="title"?"title":"author";}catch(e){return "author";}})();

// ---------- render ----------
function coverHTML(it){
  if(it.type==="book"){
    if(!wrap&&it.cover) return '<div class="media cover-img" style="background-image:url('+cssurl(it.cover)+')"></div>';
    return '<div class="media book" style="--c:'+it.accent+'"><span class="spine"></span><div class="bk-t">'+esc(it.title)+'</div><div class="bk-a">'+esc(it.sub)+'</div></div>';
  }
  if(it.type==="podcast"){
    if(!wrap&&it.artwork) return '<div class="media cover-img" style="background-image:url('+cssurl(it.artwork)+')"></div>';
    var bars=[10,15,7,13,9].map(function(h){return '<i style="height:'+h+'px"></i>';}).join("");
    return '<div class="media podcast" style="--c:'+it.accent+'"><span class="init">'+esc(initials(it.title))+'</span><span class="wave">'+bars+'</span></div>';
  }
  if(!wrap&&it.thumbnail) return '<div class="media cover-img vidthumb" style="background-image:url('+cssurl(it.thumbnail)+')"><span class="play">▶</span></div>';
  return '<div class="media video" style="--c:'+it.accent+'"><span class="thumbtint"></span><span class="play">▶</span>'+(it.meta?'<span class="dur">'+esc(it.meta)+'</span>':'')+'</div>';
}
function cardHTML(it){
  var label=it.type==="book"?"Book":it.type==="podcast"?"Podcast":"Video";
  var metaRight=it.type==="video"?'<span class="c-meta"></span>':('<span class="c-meta">'+esc(it.meta||"")+'</span>');
  var status=(it.type==="book"&&it.ready)
    ? '<span class="status ready" title="Study materials ready">Materials ready</span>'
    : (it.type==="book" ? '<span class="status">Not built yet</span>' : '');
  return '<div class="card'+(it.fresh?" fresh":"")+'" data-id="'+it.id+'" role="button" tabindex="0">'+   // keyboard: Enter/Space open it (see #grid keydown)
    coverHTML(it)+
    '<span class="c-badge '+it.type+'"><span class="dot"></span>'+label+'</span>'+
    '<div class="c-title">'+esc(it.title)+'</div>'+
    '<div class="c-sub">'+esc(it.sub)+'</div>'+
    '<div class="c-foot">'+metaRight+status+'</div>'+
  '</div>';
}
function counts(){
  var c={all:LIB.length,book:0,podcast:0,video:0};
  LIB.forEach(function(it){c[it.type]++;});
  $("n-all").textContent=c.all;$("n-book").textContent=c.book;$("n-podcast").textContent=c.podcast;$("n-video").textContent=c.video;
}
function stripArticle(s){return String(s||"").trim().replace(/^(the|a|an)\s+/i,"");}
// Filing key for an author: strips suffixes (Jr, III, PhD, OP...), files a
// medieval byname ("Augustine of Hippo", "Thomas a Kempis") under the given
// name, and keys a particled surname on its main word (van Beethoven -> b).
function authorSortKey(a){
  a=String(a||"").trim();
  if(!a||/^unknown\b/i.test(a)) return "";
  var raw=a.split(/\s+/).map(function(t){return t.replace(/^[('"\[]+|[.,)'"\]]+$/g,"");}).filter(Boolean);
  var SUF={jr:1,jnr:1,sr:1,snr:1,ii:1,iii:1,iv:1,vi:1,vii:1,viii:1,ix:1,xi:1,xii:1,xiii:1,xiv:1,xv:1,
           phd:1,md:1,dd:1,dphil:1,esq:1,op:1,sj:1,ofm:1,cssr:1,cm:1,fsc:1};
  var tokens=raw.slice(),last;
  while(tokens.length>1){last=tokens[tokens.length-1].toLowerCase().replace(/\./g,"");if(SUF[last])tokens.pop();else break;}
  var lower=tokens.map(function(t){return t.toLowerCase();}),full=a.toLowerCase();
  function k(base){return base.toLowerCase()+"|"+full;}
  if(tokens.length===1) return k(tokens[0]);
  var BYNAME={of:1,"à":1,the:1};
  for(var i=1;i<tokens.length;i++){if(BYNAME[lower[i]])return k(tokens[0]);}
  return k(tokens[tokens.length-1]);
}
function sortValue(it){
  if(sortKey==="title") return stripArticle(it.title).toLowerCase();
  return authorSortKey(it.sub)||("zzzz|"+stripArticle(it.title).toLowerCase());
}
function sortBooks(items){
  return items.slice().sort(function(x,y){return sortValue(x).localeCompare(sortValue(y),undefined,{sensitivity:"base",numeric:true});});
}
function shelfBookHTML(it,i){
  var inner=(!wrap&&it.cover)
    ? '<img class="bk-cover" src="'+esc(it.cover)+'" alt="" loading="lazy">'
    : '<div class="bk-cover ph" style="--c:'+it.accent+'"><span class="sp"></span><div class="t">'+esc(it.title)+'</div><div class="a">'+esc(it.sub)+'</div></div>';
  var badge=it.ready?'<span class="bk-ready" title="Study materials ready">✓</span>':"";
  var tip=it.title+(it.ready?" · study materials ready":"");
  return '<button class="book" style="--i:'+i+'" data-id="'+it.id+'" type="button" title="'+esc(tip)+'">'+badge+inner+'</button>';
}
function renderShelf(items){
  var host=$("shelf"),w=host.clientWidth||host.parentNode.clientWidth||900;
  var slot=window.innerWidth<=640?114:152;
  var per=Math.max(1,Math.floor((w-16)/slot)),html="",i=0;
  for(var s=0;s<items.length;s+=per){
    html+='<div class="shelf"><div class="books">'+items.slice(s,s+per).map(function(it){return shelfBookHTML(it,i++);}).join("")+'</div><div class="ledge"></div></div>';
  }
  host.innerHTML=html;
}
function render(){
  counts();
  if(booting){["grid","shelf","records","films"].forEach(function(x){$(x).style.display="none";});$("empty").innerHTML='<h3>Loading your library\u2026</h3><p>One moment.</p>';$("empty").classList.remove("hidden");return;}
  $("sortby").style.display=curFilter==="book"?"":"none";
  var items=curFilter==="all"?LIB:LIB.filter(function(it){return it.type===curFilter;});
  $("grid").style.display="none";$("shelf").style.display="none";$("records").style.display="none";$("films").style.display="none";
  if(items.length){
    if(curFilter==="book"){renderShelf(sortBooks(items));$("shelf").style.display="";}
    else if(curFilter==="podcast"){renderRecords(items);$("records").style.display="";}
    else if(curFilter==="video"){renderFilms(items);$("films").style.display="";}
    else{$("grid").innerHTML=items.map(cardHTML).join("");$("grid").style.display="";}
  }
  if(!items.length){
    var E={all:["Your library is empty","Add a book, podcast, or video with the omnibox above, or browse the ready library for titles already built into study materials."],
           book:["No books on your shelf yet","Search a title above, or browse the ready library for books already built into study materials, which open instantly."],
           podcast:["No podcasts yet","Search Apple Podcasts with the omnibox above to add a show."],
           video:["No videos yet","Search YouTube or paste a link with the omnibox above."]}[curFilter]||["Nothing here yet","Add a book, podcast, or video with the omnibox above."];
    $("empty").innerHTML='<h3>'+esc(E[0])+'</h3><p>'+esc(E[1])+'</p>';
  }
  $("empty").classList.toggle("hidden",items.length>0);
  LIB.forEach(function(it){it.fresh=false;});
}
function openBook(id){
  var it=null,k;for(k=0;k<LIB.length;k++){if(LIB[k].id===id){it=LIB[k];break;}}
  if(!it)return;
  var cover=(!wrap&&it.cover)
    ? '<img src="'+esc(it.cover)+'" alt="">'
    : '<div class="ph" style="--c:'+it.accent+'"><span class="sp"></span><div class="t">'+esc(it.title)+'</div><div class="a">'+esc(it.sub)+'</div></div>';
  var facts=[it.meta,it.isbn?("ISBN "+it.isbn):""].filter(Boolean).join("  ·  ");
  _curBook=it;
  var coverEdit='<button type="button" class="cover-edit-btn" id="cover-edit-btn">Change cover</button>'+
    '<div class="cover-edit" id="cover-edit" hidden>'+
      '<input type="url" id="cover-url" placeholder="https://…/cover.jpg" value="'+esc(it.cover||"")+'">'+
      '<div class="cover-edit-row"><button type="button" class="csave" id="cover-save">Save</button>'+
      '<button type="button" class="creset" id="cover-reset">Reset</button></div>'+
      (AUTH.admin?'<div class="cover-edit-note">Admin: this sets the cover for everyone.</div>':'')+
    '</div>';
  $("read-body").innerHTML='<div class="read-grid"><div class="read-cover">'+cover+coverEdit+'</div>'+
    '<div class="read-meta"><div class="r-eyebrow">Book</div><h2 class="r-title">'+esc(it.title)+'</h2>'+
    '<div class="r-author">'+esc(it.sub)+'</div>'+(facts?'<div class="r-facts">'+esc(facts)+'</div>':'')+
    (AUTH.signed
      ? '<div class="ex-actions"><button type="button" class="lib-extract">'+(it.ready?'View':'Build')+' study materials</button><button type="button" class="lib-upload">⬆ Upload a copy</button></div>'
      : '<div class="r-note">Sign in to build study materials from this book.</div>')+
    '<div id="extract-out" class="extract-out"></div>'+
    _rmBtn(it)+'</div></div>';
  $("read-bg").classList.add("open");
  var ceb=$("cover-edit-btn"); if(ceb)ceb.onclick=function(){var f=$("cover-edit");f.hidden=!f.hidden;if(!f.hidden)$("cover-url").focus();};
  var cs=$("cover-save"); if(cs)cs.onclick=function(){setCover(it,$("cover-url").value);};
  var cr=$("cover-reset"); if(cr)cr.onclick=function(){setCover(it,"");};
  var cu=$("cover-url"); if(cu)cu.addEventListener("keydown",function(e){if(e.key==="Enter"){e.preventDefault();setCover(it,this.value);}});
  if(AUTH.signed&&it.ready)loadExtraction(it.id,$("extract-out"));  // seeded → show instantly
}
function setCover(it,url){
  url=(url||"").trim();
  if(url&&!/^https?:\/\//i.test(url)){toast("Enter an http(s) image link.");return;}
  function apply(eff,canonical){it.cover=eff||null;render();openBook(it.id);
    toast(url?(canonical?"Catalog cover updated for everyone":"Cover updated"):(canonical?"Catalog cover reset":"Cover reset"));}
  if(AUTH.signed){
    fetch("/api/library/shelf/"+encodeURIComponent(it.id)+"/cover",{method:"POST",credentials:"same-origin",
      headers:{"Content-Type":"application/json"},body:JSON.stringify({cover:url})})
      .then(function(r){return r.ok?r.json():r.json().then(function(e){throw e;});})
      .then(function(d){apply(d.cover,d.canonical);})
      .catch(function(e){toast((e&&e.error)||"Could not update cover.");});
  }else{apply(url||null,false);}
}
$("shelf").addEventListener("click",function(e){var b=e.target.closest(".book");if(b)openBook(b.dataset.id);});
$("read-close").addEventListener("click",function(){$("read-bg").classList.remove("open");});

// ---------- podcasts: records on a turntable ----------
function discLabel(it){
  var art=(!wrap&&it.artwork);
  var inner=art?'<img src="'+esc(it.artwork)+'" alt="">':'<span>'+esc(initials(it.title))+'</span>';
  return '<span class="label'+(art?'':' ph')+'"'+(art?'':' style="--c:'+it.accent+'"')+'>'+inner+'</span><span class="hole"></span>';
}
function recordHTML(it,i){
  return '<button class="rec" style="--i:'+i+'" data-id="'+it.id+'" type="button" title="'+esc(it.title)+'"><span class="disc">'+discLabel(it)+'</span><span class="rec-cap"><span class="rc-t">'+esc(it.title)+'</span><span class="rc-s">'+esc(it.sub)+'</span></span></button>';
}
function renderRecords(items){$("records").innerHTML=items.map(function(it,i){return recordHTML(it,i);}).join("");}
function openPlayer(id){
  var it=null,k;for(k=0;k<LIB.length;k++){if(LIB[k].id===id){it=LIB[k];break;}}
  if(!it)return;
  $("play-body").innerHTML='<div class="play-grid"><div class="deck-holder"><div class="deck"><div class="plinth"></div><div class="platter"></div><div class="disc spinning">'+discLabel(it)+'</div><div class="tonearm"><span class="arm"><span class="head"></span></span><span class="pivot"></span></div></div></div>'+
    '<div class="play-meta"><div class="r-eyebrow">Podcast</div><h2 class="r-title">'+esc(it.title)+'</h2><div class="r-author">'+esc(it.sub)+'</div>'+(it.meta?'<div class="r-facts">'+esc(it.meta)+'</div>':'')+
    '<div class="r-note">Ready to ingest. Turning an episode into a study set comes in the next phase.</div>'+_rmBtn(it)+'</div></div>';
  $("play-bg").classList.add("open");
}
$("records").addEventListener("click",function(e){var b=e.target.closest(".rec");if(b)openPlayer(b.dataset.id);});
$("play-close").addEventListener("click",function(){$("play-bg").classList.remove("open");});

// ---------- videos: film frames + screening room ----------
function videoThumb(it){
  var art=(!wrap&&it.thumbnail);
  return '<span class="thumb'+(art?'':' ph')+'">'+(art?'<img src="'+esc(it.thumbnail)+'" alt="" loading="lazy">':'')+'<span class="play">▶</span></span>';
}
function filmFrameHTML(it,i){
  return '<button class="film" style="--i:'+i+'" data-id="'+it.id+'" type="button" title="'+esc(it.title)+'"><span class="frame"><span class="perf"></span>'+videoThumb(it)+'<span class="perf"></span></span><span class="film-cap"><span class="ft">'+esc(it.title)+'</span><span class="fs">'+esc(it.sub)+'</span></span></button>';
}
function renderFilms(items){$("films").innerHTML=items.map(function(it,i){return filmFrameHTML(it,i);}).join("");}
function openScreen(id){
  var it=null,k;for(k=0;k<LIB.length;k++){if(LIB[k].id===id){it=LIB[k];break;}}
  if(!it)return;
  var art=(!wrap&&it.thumbnail);
  var screen='<div class="screen'+(art?'':' ph')+'">'+(art?'<img src="'+esc(it.thumbnail)+'" alt="">':'')+'<span class="glow"></span><span class="play">▶</span></div>';
  var projector='<div class="projector"><div class="p-reels"><span class="p-reel small spin"></span><span class="p-reel big spin"></span></div><div class="p-body"></div><div class="p-lens"></div></div>';
  $("screen-body").innerHTML='<div class="screening"><div class="scene-holder"><div class="proj-scene">'+projector+'<div class="beam"></div>'+screen+'</div></div>'+
    '<div class="play-meta"><div class="r-eyebrow">Video</div><h2 class="r-title">'+esc(it.title)+'</h2><div class="r-author">'+esc(it.sub)+'</div>'+(it.meta?'<div class="r-facts">'+esc(it.meta)+'</div>':'')+
    '<div class="r-note">Ready to ingest. Turning a video into a lesson set comes in the next phase.</div>'+_rmBtn(it)+'</div></div>';
  $("screen-bg").classList.add("open");
}
$("films").addEventListener("click",function(e){var b=e.target.closest(".film");if(b)openScreen(b.dataset.id);});
$("screen-close").addEventListener("click",function(){$("screen-bg").classList.remove("open");});
$("grid").addEventListener("click",function(e){var c=e.target.closest(".card");if(!c)return;var it=null,k;for(k=0;k<LIB.length;k++){if(LIB[k].id===c.dataset.id){it=LIB[k];break;}}if(!it)return;if(it.type==="book")openBook(it.id);else if(it.type==="podcast")openPlayer(it.id);else openScreen(it.id);});
$("grid").addEventListener("keydown",function(e){if(e.key!=="Enter"&&e.key!==" ")return;var c=e.target.closest(".card");if(!c||c!==e.target)return;e.preventDefault();c.click();});
var _rz;window.addEventListener("resize",function(){clearTimeout(_rz);_rz=setTimeout(function(){if(curFilter==="book")render();},160);});
function _rmBtn(it){return '<button type="button" class="lib-remove" data-remove="'+it.id+'">Remove from library</button>';}
function _place(it){ if(curFilter!=="all"&&curFilter!==it.type){curFilter="all";syncFilters();} }
function addItem(it,cb){
  if(AUTH.signed){
    fetch("/api/library/shelf",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(it)})
      .then(function(r){return r.ok?r.json():null;}).then(function(d){
        if(!d||!d.item){toast("Could not save. Try again.");return;}
        var x=d.item;x.fresh=true;
        if(!LIB.some(function(y){return y.id===x.id;}))LIB.unshift(x);
        _place(x);render();toast("“"+x.title+"” added to your library");
        if(cb)cb(x);
      }).catch(function(){toast("Could not save. Try again.");});
  }else{
    it.id=uid();it.fresh=true;LIB.unshift(it);_place(it);render();
    toast("Added for this visit. Sign in to save it to your library.");if(cb)cb(it);
  }
}
function removeItem(id){
  LIB=LIB.filter(function(x){return x.id!==id;});render();
  ["read-bg","play-bg","screen-bg"].forEach(function(m){var el=$(m);if(el)el.classList.remove("open");});
  if(AUTH.signed){fetch("/api/library/shelf/"+encodeURIComponent(id),{method:"DELETE",credentials:"same-origin"}).catch(function(){});}
  toast("Removed from your library");
}
document.addEventListener("click",function(e){var rb=e.target.closest("[data-remove]");if(rb)removeItem(rb.getAttribute("data-remove"));});

// ---------- extraction: build study materials from a book ----------
var _curBook=null;
function startExtract(it){
  if(!it||!AUTH.signed)return;
  var out=$("extract-out");if(!out)return;
  out.innerHTML='<div class="ex-status">Building study materials… this can take a minute.</div>';
  fetch("/api/library/extract",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({title:it.title,author:it.sub})})
    .then(function(r){return r.ok?r.json():null;}).then(function(d){
      if(!d||!d.extraction_id){out.innerHTML='<div class="ex-status err">Could not start. Try again.</div>';return;}
      pollExtract(d.extraction_id,out,0);
    }).catch(function(){out.innerHTML='<div class="ex-status err">Could not start. Try again.</div>';});
}
function _exLabel(s){
  if(s.status==="pending"||!s.sections)return "Finding and reading the source…";
  var bits=[];
  if(s.sections)bits.push(s.sections+" section"+(s.sections===1?"":"s"));
  if(s.objectives)bits.push(s.objectives+" objective"+(s.objectives===1?"":"s")+" so far");
  return "Building study materials… "+(bits.join(" · ")||"working");
}
function pollExtract(id,out,tries){
  fetch("/api/library/extract/"+encodeURIComponent(id),{credentials:"same-origin"}).then(function(r){return r.ok?r.json():null;})
    .then(function(s){
      if(!s){out.innerHTML='<div class="ex-status err">Lost track of the extraction.</div>';return;}
      if(s.status==="extracted"){loadExtraction(id,out);return;}
      if(s.status==="failed"){out.innerHTML='<div class="ex-status err">'+esc(s.error||"Extraction failed. This may not be a public-domain title.")+'</div>';return;}
      var msg='<div class="ex-status">'+esc(_exLabel(s))+'</div>';
      if(s.summary)msg+='<div class="ex-sec"><div class="ex-h">Summary (preview)</div><p>'+esc(s.summary)+'</p></div>';
      if(tries>=140)msg+='<div class="ex-status" style="margin-top:8px;font-size:12px;opacity:.75">Taking a while. You can leave this page and it keeps building. Reopen the book later to see the finished materials.</div>';
      out.innerHTML=msg;
      if(tries>=300){out.innerHTML='<div class="ex-status">Still building after several minutes. Reopen this book later, and the materials will be here when it finishes.</div>';return;}
      var delay=tries<20?3000:(tries<60?5000:9000);
      setTimeout(function(){pollExtract(id,out,tries+1);},delay);
    }).catch(function(){setTimeout(function(){pollExtract(id,out,tries+1);},5000);});
}
function loadExtraction(id,out){
  fetch("/api/library/extraction/"+encodeURIComponent(id),{credentials:"same-origin"}).then(function(r){return r.ok?r.json():null;})
    .then(function(d){ if(!d){out.innerHTML='<div class="ex-status err">Could not load results.</div>';return;} renderExtraction(d,out); });
}
var _curExtraction=null;
function _groupObjectives(objs){
  // Group objectives by their section, preserving first-seen order (server returns them ordered by section position).
  var groups=[],idx={};
  objs.forEach(function(o){
    var key=o.section||"";
    if(!(key in idx)){idx[key]=groups.length;groups.push({title:o.section||null,items:[]});}
    groups[idx[key]].items.push(o);
  });
  return groups;
}
function renderExtraction(d,out){
  _curExtraction=d;
  var h='<div class="ex-result">';
  var has=d.summary||(d.themes&&d.themes.length)||d.reading_level||(d.objectives&&d.objectives.length)||(d.alignments&&d.alignments.length);
  if(has)h+='<div class="ex-top"><div class="ex-h">Study materials</div><button class="ex-export" onclick="exportMaterials()">Print / save PDF</button></div>';
  if(d.summary)h+='<div class="ex-sec"><div class="ex-h">Summary</div><p>'+esc(d.summary)+'</p></div>';
  if(d.themes&&d.themes.length)h+='<div class="ex-sec"><div class="ex-h">Themes</div><div class="ex-tags">'+d.themes.map(function(t){return '<span class="ex-tag">'+esc(t)+'</span>';}).join("")+'</div></div>';
  if(d.reading_level)h+='<div class="ex-sec"><div class="ex-h">Reading level</div><p>'+esc(d.reading_level)+'</p></div>';
  if(d.objectives&&d.objectives.length){
    var groups=_groupObjectives(d.objectives),single=groups.length===1&&!groups[0].title;
    h+='<div class="ex-sec"><div class="ex-h">Learning objectives<span class="ex-n">'+d.objectives.length+'</span></div>'+
      groups.map(function(g){
        return '<div class="ex-group">'+(single||!g.title?'':'<div class="ex-gh">'+esc(g.title)+'</div>')+
          g.items.map(function(o){
            return '<div class="ex-obj"><div class="ex-obj-t">'+esc(o.text)+'</div>'+
              (o.citation?'<div class="ex-obj-cite">'+esc(o.citation)+'</div>':'')+'</div>';
          }).join("")+'</div>';
      }).join("")+'</div>';
  }
  if(d.alignments&&d.alignments.length)h+='<div class="ex-sec"><div class="ex-h">Standards alignment<span class="ex-n">'+d.alignments.length+'</span></div><ul class="ex-list">'+
    d.alignments.map(function(a){return '<li>'+esc(a.node||a.code)+'<span class="ex-cite">'+esc(a.level)+(a.section?' · Ch. '+esc(a.section):'')+'</span></li>';}).join("")+'</ul></div>';
  if(!has)h+='<div class="ex-status">No study materials were produced for this title.</div>';
  out.innerHTML=h+'</div>';
}
function exportMaterials(){
  var d=_curExtraction;if(!d)return;
  var title=(_curBook&&_curBook.title)||d.title||"Study materials",author=(_curBook&&_curBook.sub)||d.author||"";
  var w=window.open("","_blank");if(!w)return;
  var css="body{font:15px/1.6 Georgia,'Times New Roman',serif;color:#1a1a1a;max-width:720px;margin:40px auto;padding:0 28px}"+
    "h1{font-size:25px;margin:0 0 2px;line-height:1.2}.by{color:#666;font-size:14px;margin:0 0 26px}"+
    "h2{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#8a8a8a;border-bottom:1px solid #e0ddd4;padding-bottom:5px;margin:30px 0 13px;font-family:Arial,sans-serif}"+
    "p{margin:0 0 10px}.ch{font-size:16px;font-weight:bold;margin:20px 0 9px}"+
    ".ob{margin:0 0 13px;padding-left:14px;border-left:3px solid #d8d4c8}"+
    ".ci{color:#555;font-style:italic;font-size:13px;margin-top:4px}"+
    ".tag{display:inline-block;background:#f2f0e9;border:1px solid #e4e1d7;border-radius:4px;padding:2px 9px;margin:0 5px 5px 0;font-size:13px}"+
    ".foot{margin-top:34px;padding-top:12px;border-top:1px solid #e0ddd4;color:#999;font-size:11px;font-family:Arial,sans-serif}"+
    "@media print{body{margin:0}}";
  var b='<h1>'+esc(title)+'</h1>';
  if(author)b+='<div class="by">'+esc(author)+'</div>';
  if(d.summary)b+='<h2>Summary</h2><p>'+esc(d.summary)+'</p>';
  if(d.reading_level)b+='<h2>Reading level</h2><p>'+esc(d.reading_level)+'</p>';
  if(d.themes&&d.themes.length)b+='<h2>Themes</h2><p>'+d.themes.map(function(t){return '<span class="tag">'+esc(t)+'</span>';}).join("")+'</p>';
  if(d.objectives&&d.objectives.length){
    b+='<h2>Learning objectives</h2>';
    _groupObjectives(d.objectives).forEach(function(g){
      if(g.title)b+='<div class="ch">'+esc(g.title)+'</div>';
      g.items.forEach(function(o){
        b+='<div class="ob">'+esc(o.text)+(o.citation?'<div class="ci">“'+esc(o.citation)+'”</div>':'')+'</div>';
      });
    });
  }
  b+='<div class="foot">Study materials from Exegetica · exegetica.app</div>';
  w.document.write('<!doctype html><meta charset="utf-8"><title>'+esc(title)+' · study materials</title><style>'+css+'</style>'+b);
  w.document.close();
  setTimeout(function(){try{w.focus();w.print();}catch(e){}},300);
}
document.addEventListener("click",function(e){if(e.target.closest(".lib-extract")){var o=$("extract-out");if(_curBook&&_curBook.ready&&o){loadExtraction(_curBook.id,o);}else{startExtract(_curBook);}}});

// ---------- upload a copy (in-copyright / accessibility) ----------
function openUpload(it){
  if(!it||!AUTH.signed)return;
  _curBook=it;
  $("up-book").textContent=it.title+(it.sub?": "+it.sub:"");
  $("up-file").value="";$("up-attest").checked=false;$("up-acq").value="owned";$("up-out").innerHTML="";
  $("upload-bg").classList.add("open");
}
function submitUpload(){
  var it=_curBook,out=$("up-out");if(!it)return;
  var f=$("up-file").files&&$("up-file").files[0];
  if(!f){out.innerHTML='<div class="ex-status err">Choose a file first.</div>';return;}
  if(!$("up-attest").checked){out.innerHTML='<div class="ex-status err">Please confirm you are authorized to access this copy.</div>';return;}
  var ext=((f.name||"").split(".").pop()||"").toLowerCase(),acq=$("up-acq").value;
  out.innerHTML='<div class="ex-status">Uploading…</div>';
  fetch("/api/library/upload/presign",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({source_format:ext,size:f.size})})
    .then(function(r){if(r.status===503)throw{msg:"Uploads aren't set up yet."};return r.ok?r.json():r.json().then(function(e){throw{msg:(e&&e.error)||"Upload failed."};});})
    .then(function(p){
      return fetch(p.upload_url,{method:"PUT",body:f,headers:{"Content-Type":p.content_type}}).then(function(pr){
        if(!pr.ok)throw{msg:"Upload to storage failed."};
        return fetch("/api/library/upload/complete",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({object_key:p.object_key,title:it.title,author:it.sub,acquisition:acq,source_format:ext,attested:true})});
      });
    })
    .then(function(r){return r.ok?r.json():r.json().then(function(e){throw{msg:(e&&e.error)||"Could not queue extraction."};});})
    .then(function(d){if(!d||!d.extraction_id)throw{msg:"Could not start extraction."};
      out.innerHTML='<div class="ex-status">Building study materials from your copy… this can take a minute.</div>';
      pollExtract(d.extraction_id,out,0);})
    .catch(function(err){out.innerHTML='<div class="ex-status err">'+esc((err&&err.msg)||"Upload failed.")+'</div>';});
}
document.addEventListener("click",function(e){if(e.target.closest(".lib-upload"))openUpload(_curBook);});
$("up-cancel").addEventListener("click",function(){$("upload-bg").classList.remove("open");});
$("up-submit").addEventListener("click",submitUpload);
$("upload-bg").addEventListener("click",function(e){if(e.target===$("upload-bg"))$("upload-bg").classList.remove("open");});

// ---------- omnibox ----------
function syncType(){
  var ui=TYPE_UI[curType];
  $("omni-title").textContent=ui.title;
  $("omni-input").placeholder=ui.placeholder;
  $("omni-add").textContent=ui.add;
  $("omni-lead").innerHTML=ui.lead;
  $("omni-hint").innerHTML='<span class="k">tip</span> '+ui.hint;
  Array.prototype.forEach.call($("types").children,function(b){b.classList.toggle("on",b.dataset.t===curType);});
}
$("types").addEventListener("click",function(e){var b=e.target.closest("button");if(!b)return;curType=b.dataset.t;syncType();});
$("omni-add").addEventListener("click",openAdd);
$("omni-input").addEventListener("keydown",function(e){if(e.key==="Enter"){e.preventDefault();openAdd();}});
function openAdd(){openSearch(curType,$("omni-input").value.trim());}

// ---------- live search (books via OpenLibrary/Google Books, podcasts via iTunes) ----------
var SEARCH_KIND="book", SR=[], CAT=[], stTimer=null, SEARCH_NOTE="No matches found.";
function openSearch(kind,prefill){
  SEARCH_KIND=kind;
  var T={book:["Find a book","Search by title, author, or ISBN, then pick the edition to add.","Search books","e.g. The Pilgrim's Progress, or Homer"],
         podcast:["Find a podcast","Search Apple Podcasts, then pick the show to add.","Search podcasts","e.g. Renewing Your Mind"],
         video:["Find a video","Search YouTube, or paste a link, then pick the video to add.","Search videos","e.g. photosynthesis, or paste a YouTube link"]}[kind];
  $("search-title").textContent=T[0];$("search-sub").textContent=T[1];$("search-label").textContent=T[2];$("search-q").placeholder=T[3];
  $("search-q").value=prefill||"";
  SR=[];$("search-results").innerHTML='<div class="s-note">Type to search.</div>';
  $("search-bg").classList.add("open");setTimeout(function(){$("search-q").focus();},30);
  if(prefill&&prefill.trim().length>=2){$("search-results").innerHTML='<div class="s-note">Searching…</div>';runSearch(prefill.trim());}
}
$("search-q").addEventListener("input",function(){
  clearTimeout(stTimer);var q=$("search-q").value.trim();
  if(q.length<2){SR=[];$("search-results").innerHTML='<div class="s-note">Type to search.</div>';return;}
  $("search-results").innerHTML='<div class="s-note">Searching…</div>';
  stTimer=setTimeout(function(){runSearch(q);},280);
});
function runSearch(q){
  if(SEARCH_KIND==="book"){
    // Ready (already-seeded) catalog first, external Google Books second, fetched in parallel.
    Promise.all([
      fetch("/api/library/catalog?q="+encodeURIComponent(q),{credentials:"same-origin"}).then(function(r){return r.ok?r.json():{catalog:[]};}).catch(function(){return {catalog:[]};}),
      fetch("/api/library/books?q="+encodeURIComponent(q)).then(function(r){return r.ok?r.json():{results:[],__err:true};}).catch(function(){return {results:[],__err:true};})
    ]).then(function(res){
      if($("search-q").value.trim()!==q)return;
      CAT=res[0].catalog||[];SR=res[1].results||[];
      SEARCH_NOTE=res[1].__err?"Book search failed. Try again.":"No matches found.";
      renderSearch();
    });
    return;
  }
  var url,ytUrl=false;CAT=[];SEARCH_NOTE="No matches found.";
  if(SEARCH_KIND==="podcast")url="/api/library/podcasts?q="+encodeURIComponent(q);
  else if(/youtube\.com\/watch|youtu\.be\//i.test(q)){url="/api/library/video?url="+encodeURIComponent(q);ytUrl=true;}
  else url="/api/library/youtube?q="+encodeURIComponent(q);
  fetch(url).then(function(r){return r.json();}).then(function(d){
    if($("search-q").value.trim()!==q)return;
    if(ytUrl){var p=d.preview;SR=(d.ok&&p)?[{title:p.title,author:p.author,thumbnail:p.thumbnail,url:p.url,duration:""}]:[];if(!d.ok)SEARCH_NOTE="Couldn’t read that link. Paste a public YouTube URL.";}
    else{SR=d.results||[];if(SEARCH_KIND==="video"&&d.configured===false)SEARCH_NOTE="YouTube search isn’t set up on this server yet.";}
    renderSearch();
  }).catch(function(){SR=[];SEARCH_NOTE="Search failed. Try again.";renderSearch();});
}
function catResultHTML(x,i){
  var mini=x.cover?'<img class="mini-img" src="'+esc(x.cover)+'" alt="" loading="lazy">':'<span class="mini" style="--c:'+ACCENTS[i%ACCENTS.length]+'"></span>';
  return '<button class="result ready" type="button" data-cat="'+i+'">'+mini+
    '<span><span class="r-t">'+esc(x.title)+'</span><br><span class="r-a">'+esc(x.sub||"")+'</span></span>'+
    '<span class="r-ready">Ready'+(x.objectives?' · '+x.objectives+' objectives':'')+'</span></button>';
}
function renderSearch(){
  if(SEARCH_KIND==="book"){
    var h="";
    if(CAT.length)h+='<div class="s-note ready-head">Ready in the library: instant, no wait</div>'+CAT.map(catResultHTML).join("");
    if(SR.length)h+=(CAT.length?'<div class="s-note">Or build a new one</div>':'')+SR.map(function(x,i){
      var mini=x.cover?'<img class="mini-img" src="'+esc(x.cover)+'" alt="" loading="lazy">':'<span class="mini" style="--c:'+ACCENTS[i%ACCENTS.length]+'"></span>';
      return '<button class="result" type="button" data-i="'+i+'">'+mini+'<span><span class="r-t">'+esc(x.title)+'</span><br><span class="r-a">'+esc(x.author||"Unknown author")+'</span></span><span class="r-y">'+esc(x.year||"")+'</span></button>';
    }).join("");
    $("search-results").innerHTML=h||'<div class="s-note">'+esc(SEARCH_NOTE)+'</div>';
    return;
  }
  if(!SR.length){$("search-results").innerHTML='<div class="s-note">'+esc(SEARCH_NOTE)+'</div>';return;}
  $("search-results").innerHTML=SR.map(function(x,i){
    if(SEARCH_KIND==="video"){
      var vt=x.thumbnail?'<img class="mini-img vid" src="'+esc(x.thumbnail)+'" alt="" loading="lazy">':'<span class="mini vid" style="--c:'+ACCENTS[i%ACCENTS.length]+'"></span>';
      return '<button class="result" type="button" data-i="'+i+'">'+vt+'<span><span class="r-t">'+esc(x.title)+'</span><br><span class="r-a">'+esc(x.author||"")+'</span></span>'+(x.duration?'<span class="r-y">'+esc(x.duration)+'</span>':'')+'</button>';
    }
    var art=x.artwork?'<img class="mini-img sq" src="'+esc(x.artwork)+'" alt="" loading="lazy">':'<span class="mini sq" style="--c:'+ACCENTS[i%ACCENTS.length]+'"></span>';
    var eps=x.episodes?(x.episodes+" eps"):"";
    return '<button class="result" type="button" data-i="'+i+'">'+art+'<span><span class="r-t">'+esc(x.title)+'</span><br><span class="r-a">'+esc(x.author||"")+'</span></span><span class="r-y">'+esc(eps)+'</span></button>';
  }).join("");
}
$("search-results").addEventListener("click",function(e){
  var b=e.target.closest(".result");if(!b)return;
  if(b.dataset.cat!==undefined){  // a ready, already-seeded book: add it and open its materials
    var c=CAT[+b.dataset.cat];if(!c)return;
    addItem({type:"book",title:c.title,sub:c.sub,meta:(c.objectives?c.objectives+" objectives ready":""),accent:nextAccent(),cover:c.cover||null},function(item){$("search-bg").classList.remove("open");openBook(item.id);});
    return;
  }
  var x=SR[+b.dataset.i];if(!x)return;
  if(SEARCH_KIND==="book"){
    addItem({type:"book",title:x.title,sub:x.author||"Unknown author",meta:x.year||"",accent:nextAccent(),cover:x.cover||null,isbn:x.isbn||null});
  }else if(SEARCH_KIND==="video"){
    addItem({type:"video",title:x.title,sub:x.author||"YouTube",meta:x.duration||"",accent:nextAccent(),thumbnail:x.thumbnail||null,url:x.url||null});
  }else{
    addItem({type:"podcast",title:x.title,sub:x.author||"",meta:x.episodes?(x.episodes+" episodes"):"Podcast",accent:nextAccent(),artwork:x.artwork||null,feed:x.feed||null});
  }
  $("search-bg").classList.remove("open");
});
$("search-cancel").addEventListener("click",function(){$("search-bg").classList.remove("open");});

// ---------- browse the ready (seeded) library ----------
var BROWSE=[], BROWSE_TOTAL=0, browseTimer=null;
function loadBrowseCount(){
  if(!AUTH.signed)return;
  fetch("/api/library/catalog",{credentials:"same-origin"}).then(function(r){return r.ok?r.json():null;}).then(function(d){
    var n=(d&&typeof d.total==="number")?d.total:((d&&d.catalog||[]).length), btn=$("browse-open"); if(!btn)return;
    if(n>0){$("browse-count").textContent=n+" book"+(n===1?"":"s")+" built and ready to use";btn.hidden=false;}
  }).catch(function(){});
}
function openBrowse(){$("browse-bg").classList.add("open");$("browse-q").value="";runBrowse("");setTimeout(function(){$("browse-q").focus();},30);}
function runBrowse(q){
  $("browse-grid").innerHTML='<div class="s-note">Loading…</div>';
  fetch("/api/library/catalog?q="+encodeURIComponent(q),{credentials:"same-origin"}).then(function(r){return r.ok?r.json():{catalog:[]};}).then(function(d){
    BROWSE=d.catalog||[];BROWSE_TOTAL=(typeof d.total==="number")?d.total:BROWSE.length;renderBrowse();
  }).catch(function(){$("browse-grid").innerHTML='<div class="s-note">Could not load.</div>';});
}
function renderBrowse(){
  var g=$("browse-grid"),c2=$("browse-count2");
  if(c2)c2.textContent=BROWSE_TOTAL?(BROWSE_TOTAL+" ready"+(BROWSE_TOTAL>BROWSE.length?(" · showing "+BROWSE.length):"")):"";
  if(!BROWSE.length){g.innerHTML='<div class="s-note">No ready books match.</div>';return;}
  g.innerHTML=BROWSE.map(function(x,i){
    var cover=x.cover?'<img src="'+esc(x.cover)+'" alt="" loading="lazy">':'<span class="bg-ph" style="--c:'+ACCENTS[i%ACCENTS.length]+'">'+esc(initials(x.title))+'</span>';
    return '<button class="bg-card" type="button" data-i="'+i+'">'+cover+'<span class="bg-t">'+esc(x.title)+'</span><span class="bg-a">'+esc(x.sub||"")+'</span><span class="bg-n">'+x.objectives+' objectives</span></button>';
  }).join("");
}
(function(){
  var bo=$("browse-open"); if(bo)bo.addEventListener("click",openBrowse);
  var bc=$("browse-close"); if(bc)bc.addEventListener("click",function(){$("browse-bg").classList.remove("open");});
  var bq=$("browse-q"); if(bq)bq.addEventListener("input",function(){clearTimeout(browseTimer);var q=this.value.trim();browseTimer=setTimeout(function(){runBrowse(q);},220);});
  var bg=$("browse-grid"); if(bg)bg.addEventListener("click",function(e){
    var b=e.target.closest(".bg-card");if(!b)return;var x=BROWSE[+b.dataset.i];if(!x)return;
    addItem({type:"book",title:x.title,sub:x.sub,meta:(x.objectives+" objectives ready"),accent:nextAccent(),cover:x.cover||null},function(item){
      $("browse-bg").classList.remove("open");openBook(item.id);
    });
  });
})();

// ---------- filters ----------
function syncFilters(){Array.prototype.forEach.call($("filters").children,function(b){b.classList.toggle("on",b.dataset.f===curFilter);});}
$("filters").addEventListener("click",function(e){var b=e.target.closest("button");if(!b)return;curFilter=b.dataset.f;syncFilters();render();});
function syncWrap(){$("cwrap").setAttribute("aria-checked",wrap?"true":"false");}
$("cwrap").addEventListener("click",function(){wrap=!wrap;try{localStorage.setItem("studybible.lib.wrap",wrap?"on":"off");}catch(e){}syncWrap();render();});
function syncSort(){Array.prototype.forEach.call($("sortseg").children,function(b){b.classList.toggle("on",b.dataset.s===sortKey);});}
$("sortseg").addEventListener("click",function(e){var b=e.target.closest("button");if(!b)return;sortKey=b.dataset.s;try{localStorage.setItem("studybible.lib.sort",sortKey);}catch(e){}syncSort();render();});

// ---------- misc ----------
function toast(msg, o){ Shell.toast(msg, o); }   // the shell's toast
Array.prototype.forEach.call(document.querySelectorAll(".modal-bg"),function(bg){bg.addEventListener("click",function(e){if(e.target===bg)bg.classList.remove("open");});});
document.addEventListener("keydown",function(e){if(e.key==="Escape")Array.prototype.forEach.call(document.querySelectorAll(".modal-bg"),function(bg){bg.classList.remove("open");});});

syncType();syncFilters();syncWrap();syncSort();render();
// Signed-in users get their persisted Neon shelf (replacing the demo seed);
// anonymous visitors keep the in-memory demo shelf.
function initLibrary(){
  fetch("/api/me",{credentials:"same-origin"}).then(function(r){return r.json();}).then(function(d){
    AUTH.user=(d&&d.user)||null;AUTH.signed=!!AUTH.user;AUTH.admin=!!(d&&d.admin);
    if(!AUTH.signed){anon=true;LIB=DEMO_SEED.slice();booting=false;render();return;}
    fetch("/api/library/shelf",{credentials:"same-origin"}).then(function(r){return r.ok?r.json():Promise.reject();}).then(function(s){
      LIB=(s&&s.items)||[];booting=false;render();
    }).catch(function(){booting=false;LIB=[];render();
      $("empty").innerHTML='<h3>Couldn\u2019t load your library</h3><p>Something went wrong reaching the server. Refresh to try again.</p>';$("empty").classList.remove("hidden");});
    loadBrowseCount();
    if(AUTH.user.role==="teacher")loadReviews();
  }).catch(function(){anon=true;LIB=DEMO_SEED.slice();booting=false;render();});
}
initLibrary();

// --- Borderline copy-review queue (teacher-only) ---
var REVIEWS=[];
function loadReviews(){
  fetch("/api/library/reviews",{credentials:"same-origin"}).then(function(r){return r.ok?r.json():null;}).then(function(d){
    REVIEWS=(d&&d.reviews)||[];
    var pill=document.getElementById("review-open"),n=document.getElementById("review-n");
    if(!pill)return;
    n.textContent=REVIEWS.length;
    pill.hidden=REVIEWS.length===0;
  }).catch(function(){});
}
function fmtQ(q){return (q==null)?"n/a":Number(q).toFixed(2);}
function renderReviews(){
  var box=document.getElementById("review-list");
  if(!REVIEWS.length){box.innerHTML='<div class="rv-empty">No copies awaiting review.</div>';return;}
  box.innerHTML=REVIEWS.map(function(r){
    var inc=r.incumbent||{},cand=r.candidate||{};
    var incLabel=(inc.source&&inc.source.indexOf("upload:")===0)?"Current copy":("Current ("+(inc.source||"unknown")+")");
    return '<div class="rv-card" data-ex="'+r.extraction_id+'" data-uid="'+cand.user_id+'">'
      +'<h4>'+esc(r.title||"Untitled")+'</h4>'
      +'<p class="rv-by">'+esc(r.creator||"")+'</p>'
      +'<div class="rv-copies">'
        +'<div class="rv-copy"><div class="rv-tag">'+esc(incLabel)+'</div><div class="rv-q">'+fmtQ(inc.quality)+'</div>quality score</div>'
        +'<div class="rv-copy"><div class="rv-tag">New copy · '+esc((cand.format||"").toUpperCase())+'</div><div class="rv-q">'+fmtQ(cand.quality)+'</div>quality score · '+esc(cand.acquisition||"")+'</div>'
      +'</div>'
      +'<div class="rv-actions"><button class="btn-solid rv-promote" type="button">Make this the shared copy</button>'
      +'<button class="btn-ghost rv-reject" type="button">Keep private</button></div>'
    +'</div>';
  }).join("");
}
function reviewAct(card,action){
  var ex=card.getAttribute("data-ex"),uid=card.getAttribute("data-uid");
  card.querySelectorAll("button").forEach(function(b){b.disabled=true;});
  fetch("/api/library/reviews/"+action,{method:"POST",credentials:"same-origin",
    headers:{"Content-Type":"application/json"},body:JSON.stringify({extraction_id:ex,user_id:uid})})
    .then(function(r){return r.ok?r.json():Promise.reject();}).then(function(){
      toast(action==="promote"?"Rebuilding shared materials from the chosen copy…":"Kept private.");
      REVIEWS=REVIEWS.filter(function(x){return !(x.extraction_id===ex&&(x.candidate||{}).user_id===uid);});
      renderReviews();
      var n=document.getElementById("review-n");n.textContent=REVIEWS.length;
      if(!REVIEWS.length){document.getElementById("review-open").hidden=true;$("review-bg").classList.remove("open");}
    }).catch(function(){toast("Could not complete that action.");card.querySelectorAll("button").forEach(function(b){b.disabled=false;});});
}
(function(){
  var open=document.getElementById("review-open");
  if(open)open.addEventListener("click",function(){renderReviews();$("review-bg").classList.add("open");});
  var close=document.getElementById("review-close");
  if(close)close.addEventListener("click",function(){$("review-bg").classList.remove("open");});
  var list=document.getElementById("review-list");
  if(list)list.addEventListener("click",function(e){
    var card=e.target.closest(".rv-card");if(!card)return;
    if(e.target.closest(".rv-promote"))reviewAct(card,"promote");
    else if(e.target.closest(".rv-reject"))reviewAct(card,"reject");
  });
})();
