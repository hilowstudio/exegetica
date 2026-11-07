/* The Scripture Memory · Exegetica page (templates/memory.html). The rail, theme and Need help now? come from static/js/shell.js. */
(function(){
"use strict";

// ---------------------------------------------------------------- constants
var STORE = "studybible.memory.v1";
var API_TEXT = "/api/memory/text?ref=";
var API_AUDIO = "/api/memory/audio?ref=";

// The 8-step mastery flow (verbatim from Quill & Compass).
var STEPS = [
  { id:1, label:"Read Silently",        type:"read",   mode:"full" },
  { id:2, label:"Listen Aloud",         type:"listen", mode:"full" },
  { id:3, label:"Read Aloud",           type:"speak",  mode:"full" },
  { id:4, label:"Type",                 type:"type",   mode:"full" },
  { id:5, label:"Speak (First Letter)", type:"speak",  mode:"first-letter" },
  { id:6, label:"Type (First Letter)",  type:"type",   mode:"first-letter" },
  { id:7, label:"Speak (Hidden)",       type:"speak",  mode:"hidden" },
  { id:8, label:"Type (Hidden)",        type:"type",   mode:"hidden" }
];

// First-run seed: the 16 memory-verse anchors of the John course.
var SEED = ["John 20:31","John 1:14","John 1:12","John 3:16","John 4:24","John 6:35",
  "John 8:12","John 10:11","John 11:25","John 13:34-35","John 14:6","John 15:5",
  "John 16:33","John 17:3","John 19:30","John 21:17"];

// A broader library the user can add from (the Quill & Compass set).
var LIBRARY = ["Genesis 1:1-2","Genesis 1:27-31","Exodus 33:13-19","Exodus 34:6-9","Deuteronomy 6:4-9",
  "Deuteronomy 10:14-21","Psalm 23:1-6","Psalm 32:1-5","Psalm 51:17","Isaiah 53:1-12",
  "Daniel 3:17-18","Habakkuk 1:5","Zephaniah 3:17","Matthew 28:18-20","Mark 1:11",
  "John 1:1-5","John 3:3-8","John 6:63","John 8:56-58","John 10:14-18",
  "John 10:24-31","John 11:35","John 13:12-17","John 14:1-9","John 15:3-5",
  "Romans 5:1-11","Romans 6:1-11","Romans 8:1-39","1 Corinthians 15:3-11",
  "1 Corinthians 15:50-57","2 Corinthians 1:3-5","2 Corinthians 4:5-7","Galatians 5:1-6",
  "Ephesians 2:1-10","Philippians 2:1-11","Colossians 1:15-20","Colossians 2:6-14",
  "2 Thessalonians 2:16-17","1 Timothy 1:15-17","Hebrews 10:19-23","Hebrews 12:1-5",
  "Hebrews 13:20-21","James 1:2-5","James 4:13-14","James 5:13-16","1 Peter 4:12-14",
  "1 John 1:5-9","1 John 4:9-19","Jude 1:24-25","Revelation 21:1-6"];

// ---------------------------------------------------------------- state
var db = { verses:[], folders:[] };
var ui = { view:"dash", tab:"learning", folderId:null, menuFor:null, selectedId:null };
var practice = null;

function uid(){ return "v"+Date.now().toString(36)+Math.random().toString(36).slice(2,7); }

// Storage is auth-aware: signed-in users read/write their Neon account; anonymous
// users use localStorage exactly as before. AUTH is resolved once at init().
var AUTH = { signed:false, user:null };

function loadLocal(){
  try { var raw = localStorage.getItem(STORE);
    if(raw){ var d = JSON.parse(raw); return { verses:d.verses||[], folders:d.folders||[] }; }
  } catch(e){}
  return null;
}
function saveLocal(){ try{ localStorage.setItem(STORE, JSON.stringify(db)); }catch(e){} }
function seedNew(){ return { verses: SEED.map(function(r){ return newVerse(r); }), folders: [] }; }

// Debounced server write; whole-blob PUT. pagehide flushes any pending change.
var _saveTimer=null, _dirty=false, _loadFailed=false;
function showLoadNote(){
  var n=document.createElement("div"); n.setAttribute("role","status");
  n.textContent="Your saved verses didn't load, so changes here won't be saved. Refresh the page to try again.";
  n.style.cssText="margin:12px auto;max-width:640px;padding:10px 14px;border:1px solid var(--rule-strong);"+
    "border-radius:12px;background:var(--surface);color:var(--ink);font-size:14px;text-align:center";
  document.body.insertBefore(n, document.body.firstChild);
}
function flushServer(keepalive){
  if(!_dirty || _loadFailed) return;
  _dirty=false; clearTimeout(_saveTimer);
  try{
    fetch("/api/memory", { method:"PUT", credentials:"same-origin", keepalive:!!keepalive,
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ verses:db.verses, folders:db.folders }) }).catch(function(){});
  }catch(e){}
}
function save(){
  if(AUTH.signed){ _dirty=true; clearTimeout(_saveTimer); _saveTimer=setTimeout(function(){ flushServer(false); }, 500); }
  else { saveLocal(); }
}

async function init(){
  try { var r=await fetch("/api/me",{credentials:"same-origin"}); var d=await r.json();
        AUTH.user=(d&&d.user)||null; AUTH.signed=!!AUTH.user; } catch(e){ AUTH.signed=false; }
  if(AUTH.signed){
    var server=null;
    try { var rr=await fetch("/api/memory",{credentials:"same-origin"}); if(rr.ok){ server=await rr.json(); } } catch(e){}
    if(!server){
      // A failed load is not an empty account: show this browser's copy and save nothing, or the
      // first change would overwrite every saved verse on the server.
      _loadFailed=true; db = loadLocal() || seedNew(); showLoadNote();
    } else if((server.verses&&server.verses.length) || (server.folders&&server.folders.length)){
      db = { verses:server.verses||[], folders:server.folders||[] };
    } else {
      // Empty account: offer a one-time import of this browser's verses, else seed.
      var local = loadLocal();
      if(local && local.verses && local.verses.length &&
         confirm("Import your "+local.verses.length+" saved verse"+(local.verses.length===1?"":"s")+" from this browser into your account?")){
        db = local;
      } else {
        db = seedNew();
      }
      _dirty=true; flushServer(false);
    }
  } else {
    var l = loadLocal();
    if(l){ db=l; } else { db=seedNew(); saveLocal(); }
  }
  render();
}
window.addEventListener("pagehide", function(){ if(AUTH.signed) flushServer(true); });

function newVerse(ref, folderId){
  return { id:uid(), reference:ref, text:null, currentStep:0,
    masteredAt:null, lastPracticedAt:null, lastRefreshedAt:null, folderId:folderId||null,
    createdAt:new Date().toISOString() };
}
function verseById(id){ return db.verses.find(function(v){ return v.id===id; }); }
function folderById(id){ return db.folders.find(function(f){ return f.id===id; }); }
function hasRef(ref){ return db.verses.some(function(v){ return v.reference.toLowerCase()===ref.toLowerCase(); }); }

// ---------------------------------------------------------------- API (ESV via server proxy)
function fetchText(ref){
  return fetch(API_TEXT + encodeURIComponent(ref)).then(function(r){
    if(!r.ok) throw new Error("text "+r.status);
    return r.json();
  }).then(function(d){ return (d && d.text) ? d.text : ""; });
}
function fetchAudio(ref){
  return fetch(API_AUDIO + encodeURIComponent(ref)).then(function(r){
    if(!r.ok) throw new Error("audio "+r.status);
    return r.json();
  }).then(function(d){ return d && d.audioUrl ? d.audioUrl : null; });
}
// Ensure a verse has its text, fetching + caching once.
function ensureText(v){
  if(v.text) return Promise.resolve(v.text);
  return fetchText(v.reference).then(function(t){ if(t){ v.text=t; save(); } return t; });
}

// ---------------------------------------------------------------- grading (verbatim logic)
function cleanText(t){
  return (t||"")
    .replace(/[‘’“”–—]/g, "")      // smart quotes / dashes
    .replace(/[.,/#!$%^&*;:{}=\-_`~()"']/g, "")
    .toLowerCase().replace(/\s+/g," ").trim();
}
function lev(a,b){
  var m=[]; var i,j;
  for(i=0;i<=b.length;i++) m[i]=[i];
  for(j=0;j<=a.length;j++) m[0][j]=j;
  for(i=1;i<=b.length;i++) for(j=1;j<=a.length;j++){
    if(b.charAt(i-1)===a.charAt(j-1)) m[i][j]=m[i-1][j-1];
    else m[i][j]=Math.min(m[i-1][j-1]+1, Math.min(m[i][j-1]+1, m[i-1][j]+1));
  }
  return m[b.length][a.length];
}
function similarity(s1,s2){
  if(!s1||!s2) return 0;
  var longer = s1.length>s2.length ? s1 : s2;
  if(longer.length===0) return 1;
  return (longer.length - lev(s1,s2))/longer.length;
}

// ---------------------------------------------------------------- helpers
function esc(s){ return (s||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];}); }
var toastT;
function toast(msg){
  var el=document.getElementById("toast"); el.textContent=msg; el.classList.add("show");
  clearTimeout(toastT); toastT=setTimeout(function(){ el.classList.remove("show"); }, 2400);
}
function fmtDate(iso){
  if(!iso) return "";
  try{ return new Date(iso).toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}); }catch(e){ return ""; }
}
function $(id){ return document.getElementById(id); }

// ---------------------------------------------------------------- render dispatch
function render(){
  ui.menuFor=null;
  if(ui.view==="practice" && practice){ renderPractice(); }
  else { renderDash(); }
}

// ---------------------------------------------------------------- dashboard
function renderDash(){
  $("topsub").textContent="Hide his word in your heart";
  $("topactions").innerHTML="";   // add / library actions live in the drawer now

  var inFolder = ui.folderId ? folderById(ui.folderId) : null;
  if(ui.folderId && !inFolder){ ui.folderId=null; inFolder=null; } // folder was deleted

  var scoped = db.verses.filter(function(v){
    return ui.folderId ? v.folderId===ui.folderId : v.folderId==null;
  });
  var learning = scoped.filter(function(v){ return v.currentStep<8; });
  var mastered = scoped.filter(function(v){ return v.currentStep>=8; });
  var list = ui.tab==="mastered" ? mastered : learning;
  var folders = ui.folderId ? [] : db.folders.slice().sort(function(a,b){return a.name.localeCompare(b.name);});

  // keep a valid selection inside the current list
  if(!list.some(function(v){return v.id===ui.selectedId;})){
    ui.selectedId = list.length ? list[0].id : null;
  }
  var selected = list.filter(function(v){return v.id===ui.selectedId;})[0] || null;

  // ---- drawer: the verse list (folders + verse rows, with tabs + crumbs) ----
  var rows = "";
  folders.forEach(function(f){ rows += folderRow(f); });
  if(list.length){ list.forEach(function(v){ rows += verseRow(v); }); }
  else { rows += '<div class="none">'+(ui.tab==="mastered"?"No mastered verses in this view yet.":"No verses here yet.")+'</div>'; }
  $("verse-list").innerHTML =
    (inFolder?crumbHtml(inFolder):"") + toolbarHtml(learning,mastered) + '<div class="vlist">'+rows+'</div>';

  // ---- main pane: the selected verse's reading + practice, or an invite ----
  if(!selected && list.length===0 && folders.length===0){
    $("view").innerHTML = '<div class="detailwrap">'+emptyState()+'</div>';
  } else {
    $("view").innerHTML = '<div class="detailwrap">'+verseDetail(selected)+'</div>';
  }

  wireDash();
  wireVerseCards();
  wireRowSelect();
  hydrateDetail(selected);
}

function crumbHtml(inFolder){
  return '<div class="crumbs"><a id="crumb-root" href="#">All verses</a> <span>›</span> <b>'+esc(inFolder.name)+'</b>'+
    ' <button class="icobtn" id="fld-rename" title="Rename folder"><svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg></button></div>';
}

function toolbarHtml(learning, mastered){
  var h = '<div class="toolbar"><div class="tabs" role="tablist">'+
    '<button role="tab" aria-selected="'+(ui.tab==="learning")+'" id="tab-learn">Learning<span class="cnt">'+learning.length+'</span></button>'+
    '<button role="tab" aria-selected="'+(ui.tab==="mastered")+'" id="tab-master">Mastered<span class="cnt">'+mastered.length+'</span></button>'+
    '</div><span style="flex:1"></span>';
  if(!ui.folderId){ h += '<button class="btn" id="btn-folder">＋ New folder</button>'; }
  return h + '</div>';
}

function folderRow(f){
  var cnt = db.verses.filter(function(v){return v.folderId===f.id;}).length;
  return '<div class="frow" data-folder="'+f.id+'">'+
    '<div class="fico2"><svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg></div>'+
    '<button type="button" class="fname2">'+esc(f.name)+'</button>'+
    '<span class="fcnt">'+cnt+'</span>'+
    '<button class="icobtn kebab" type="button" data-fmenu="'+f.id+'" aria-label="Folder options for '+esc(f.name)+'" title="Folder options"><svg viewBox="0 0 24 24"><circle cx="12" cy="6" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="12" cy="18" r="1.4"/></svg></button>'+
    '</div>';
}

function wireDash(){
  if($("crumb-root")) $("crumb-root").onclick=function(e){ e.preventDefault(); ui.folderId=null; ui.menuFor=null; render(); };
  if($("fld-rename")) $("fld-rename").onclick=function(){ renameFolder(ui.folderId); };
  if($("tab-learn")) $("tab-learn").onclick=function(){ ui.tab="learning"; render(); };
  if($("tab-master")) $("tab-master").onclick=function(){ ui.tab="mastered"; render(); };
  if($("btn-folder")) $("btn-folder").onclick=function(){ newFolderModal(); };
  if($("empty-add")) $("empty-add").onclick=function(){ addVerseModal(); };
  if($("empty-lib")) $("empty-lib").onclick=function(){ libraryModal(); };
  document.querySelectorAll(".frow").forEach(function(el){
    var fid=el.getAttribute("data-folder");
    el.onclick=function(e){ if(e.target.closest("[data-fmenu]")||e.target.closest(".menu"))return; ui.folderId=fid; ui.tab="learning"; ui.menuFor=null; ui.selectedId=null; render(); };
    el.addEventListener("dragover",function(e){ e.preventDefault(); el.classList.add("drop"); });
    el.addEventListener("dragleave",function(){ el.classList.remove("drop"); });
    el.addEventListener("drop",function(e){ e.preventDefault(); el.classList.remove("drop");
      var vid=e.dataTransfer.getData("text/plain"); if(vid){ moveVerse(vid, fid); } });
  });
  document.querySelectorAll("[data-fmenu]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); openFolderMenu(b.getAttribute("data-fmenu"), b); };
  });
}

function verseRow(v){
  var mastered = v.currentStep>=8;
  var pct = Math.round((v.currentStep/8)*100);
  var meta = mastered
    ? '<svg viewBox="0 0 24 24" style="width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:2;vertical-align:-2px;margin-right:3px"><path d="M20 6L9 17l-5-5"/></svg>Mastered '+esc(fmtDate(v.masteredAt))
    : 'Step '+v.currentStep+' of 8 · '+pct+'%';
  return '<div class="vrow'+(mastered?" mastered":"")+(v.id===ui.selectedId?" sel":"")+'" draggable="true" data-vcard="'+v.id+'" data-select="'+v.id+'">'+
    '<button type="button" class="vref"'+(v.id===ui.selectedId?' aria-current="true"':'')+'>'+esc(v.reference)+'</button>'+
    '<div class="vmeta">'+meta+'</div>'+
    '<div class="bar"><i style="width:'+pct+'%"></i></div>'+
    '<button class="icobtn kebab" type="button" data-vmenu="'+v.id+'" aria-label="Options for '+esc(v.reference)+'" title="Verse options"><svg viewBox="0 0 24 24"><circle cx="12" cy="6" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="12" cy="18" r="1.4"/></svg></button>'+
    '</div>';
}

function verseDetail(v){
  if(!v){
    return '<div class="detail-empty"><h3>Select a verse</h3><p>Choose a verse from the list to read it and practice.</p></div>';
  }
  var mastered = v.currentStep>=8;
  var pct = Math.round((v.currentStep/8)*100);
  var tx = v.text ? esc(v.text) : 'Loading verse text…';
  var txcls = v.text ? '' : ' loading';
  var actions;
  if(mastered){
    actions = '<div class="badge"><svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg> Mastered '+esc(fmtDate(v.masteredAt))+'</div>'+
      '<button class="btn" data-refresh="'+v.id+'"><svg viewBox="0 0 24 24" style="width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.9;margin-right:2px"><path d="M3 12a9 9 0 1 1 2.6 6.3M3 20v-5h5"/></svg> Refresh</button>';
  } else {
    actions = '<div class="dstep">Step '+v.currentStep+' of 8 · '+pct+'%</div>'+
      '<div class="bar"><i style="width:'+pct+'%"></i></div>'+
      '<button class="btn primary big" data-practice="'+v.id+'">'+(v.currentStep>0?"Continue":"Start")+' practice</button>';
  }
  return '<div class="detail">'+
    '<div class="dref">'+esc(v.reference)+'</div>'+
    '<div class="dtext'+txcls+'" data-dtext>'+tx+'</div>'+
    actions + '</div>';
}

// Lazily fill the detail pane's verse text once fetched, if that verse is still shown.
function hydrateDetail(v){
  if(!v || v.text) return;
  ensureText(v).then(function(t){
    if(ui.view!=="dash" || ui.selectedId!==v.id) return;
    var el=document.querySelector("[data-dtext]");
    if(el){ el.textContent = t || "(text unavailable)"; el.classList.remove("loading"); }
  });
}

function wireRowSelect(){
  document.querySelectorAll("[data-select]").forEach(function(el){
    el.addEventListener("click",function(e){
      if(e.target.closest("[data-vmenu]")||e.target.closest(".menu")) return;
      var id=el.getAttribute("data-select");
      ui.selectedId=id; ui.menuFor=null;
      setDrawerOpen(false);   // reveal the exercise once a verse is chosen
      render();
      if(e.detail===0){       // chosen from the keyboard: land on the verse's practice button
        var go=document.querySelector("[data-practice],[data-refresh]"); if(go) go.focus();
      }
    });
  });
}

function wireVerseCards(){
  document.querySelectorAll("[data-practice]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); startPractice(b.getAttribute("data-practice")); };
  });
  document.querySelectorAll("[data-refresh]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); startPractice(b.getAttribute("data-refresh"), {initialStep:6, isRefresh:true}); };
  });
  document.querySelectorAll("[data-vmenu]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); openVerseMenu(b.getAttribute("data-vmenu"), b); };
  });
  document.querySelectorAll("[data-vcard]").forEach(function(el){
    var vid=el.getAttribute("data-vcard");
    el.addEventListener("dragstart",function(e){ e.dataTransfer.setData("text/plain",vid); e.dataTransfer.effectAllowed="move"; $("trash").classList.add("show"); });
    el.addEventListener("dragend",function(){ $("trash").classList.remove("show","drop"); });
  });
}

function emptyState(){
  if(ui.tab==="mastered"){
    return '<div class="empty"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></svg>'+
      '<h3>No mastered verses yet</h3><p>Work a verse through all eight steps and it lands here. Keep going.</p></div>';
  }
  if(ui.folderId){
    return '<div class="empty"><svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>'+
      '<h3>This folder is empty</h3><p>Drag a verse card onto this folder, or use a verse’s menu to move it here.</p></div>';
  }
  return '<div class="empty"><svg viewBox="0 0 24 24"><rect x="3.5" y="6.5" width="12" height="12" rx="2"/><path d="M8 4.5h10a2 2 0 0 1 2 2v10"/></svg>'+
    '<h3>Start memorizing</h3><p>Add a verse by reference, or pick from the library, and work it through the eight steps.</p>'+
    '<button class="btn primary" id="empty-add">＋ Add a verse</button> <button class="btn" id="empty-lib">Browse library</button></div>';
}

// ---------------------------------------------------------------- menus
function closeMenus(){ document.querySelectorAll(".menu").forEach(function(m){m.remove();}); ui.menuFor=null; }
function openVerseMenu(vid, anchor){
  closeMenus();
  var v=verseById(vid); if(!v) return;
  var card=anchor.closest(".card, .vrow, .frow");
  var m=document.createElement("div"); m.className="menu";
  var folderItems = db.folders.slice().sort(function(a,b){return a.name.localeCompare(b.name);}).map(function(f){
    var cur = v.folderId===f.id;
    return '<button data-move="'+f.id+'">'+(cur?"✓ ":"")+esc(f.name)+'</button>';
  }).join("");
  m.innerHTML =
    '<div class="lab">Move to folder</div>'+
    '<button data-move="__none__">'+(v.folderId==null?"✓ ":"")+"None (unfiled)"+'</button>'+
    folderItems +
    '<div class="sep"></div>'+
    '<button class="danger" data-del="'+vid+'"><svg viewBox="0 0 24 24" style="width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.8"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg> Delete verse</button>';
  card.appendChild(m);
  m.querySelectorAll("[data-move]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); var t=b.getAttribute("data-move"); moveVerse(vid, t==="__none__"?null:t); };
  });
  m.querySelector("[data-del]").onclick=function(e){ e.stopPropagation(); deleteVerse(vid); };
}
function openFolderMenu(fid, anchor){
  closeMenus();
  var card=anchor.closest(".card, .vrow, .frow");
  var m=document.createElement("div"); m.className="menu";
  m.innerHTML =
    '<button data-ren="'+fid+'"><svg viewBox="0 0 24 24" style="width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg> Rename</button>'+
    '<button class="danger" data-delf="'+fid+'"><svg viewBox="0 0 24 24" style="width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.8"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg> Delete folder</button>';
  card.appendChild(m);
  m.querySelector("[data-ren]").onclick=function(e){ e.stopPropagation(); renameFolder(fid); };
  m.querySelector("[data-delf]").onclick=function(e){ e.stopPropagation(); deleteFolder(fid); };
}
document.addEventListener("click",function(e){
  if(!e.target.closest(".menu") && !e.target.closest("[data-vmenu]") && !e.target.closest("[data-fmenu]")) closeMenus();
});
document.addEventListener("keydown",function(e){   // Escape closes an open menu (only), back to its kebab
  var m=document.querySelector(".menu"); if(e.key!=="Escape" || !m) return;
  var k=m.parentNode.querySelector(".kebab"), inMenu=m.contains(document.activeElement);
  closeMenus(); e.stopImmediatePropagation();
  if(inMenu && k) k.focus();
});

// ---------------------------------------------------------------- verse + folder ops
function moveVerse(vid, folderId){
  var v=verseById(vid); if(!v) return;
  v.folderId=folderId; save(); closeMenus(); render();
  toast(folderId ? ("Moved to "+(folderById(folderId)||{}).name) : "Moved to unfiled");
}
function deleteVerse(vid){
  var v=verseById(vid); if(!v) return;
  if(!confirm('Delete "'+v.reference+'"? This removes it and its progress.')) return;
  db.verses = db.verses.filter(function(x){ return x.id!==vid; });
  save(); closeMenus(); render();
}
function deleteFolder(fid){
  var f=folderById(fid); if(!f) return;
  if(!confirm('Delete folder "'+f.name+'"? Verses inside it are kept and become unfiled.')) return;
  db.verses.forEach(function(v){ if(v.folderId===fid) v.folderId=null; });
  db.folders = db.folders.filter(function(x){ return x.id!==fid; });
  if(ui.folderId===fid) ui.folderId=null;
  save(); closeMenus(); render();
}
function renameFolder(fid){
  var f=folderById(fid); if(!f) return;
  var name=prompt("Rename folder:", f.name);
  if(name==null) return;
  name=name.trim();
  if(name.length<1||name.length>50){ toast("Name must be 1–50 characters."); return; }
  f.name=name; save(); closeMenus(); render();
}

// ---------------------------------------------------------------- modals
function openModal(html){ $("modal").innerHTML=html; $("scrim").classList.add("show"); }
function closeModal(){ $("scrim").classList.remove("show"); $("modal").innerHTML=""; }
$("scrim").addEventListener("click",function(e){ if(e.target===$("scrim")) closeModal(); });
document.addEventListener("keydown",function(e){ if(e.key==="Escape"){ if($("scrim").classList.contains("show")) closeModal(); } });

function newFolderModal(){
  openModal('<h2>New folder</h2><p class="hint">Group related verses together.</p>'+
    '<label class="field"><span>Folder name</span><input type="text" id="f-name" maxlength="50" placeholder="e.g. Psalms" autofocus></label>'+
    '<div class="row"><button class="btn ghost" id="f-cancel">Cancel</button><button class="btn primary" id="f-save">Create</button></div>');
  $("f-cancel").onclick=closeModal;
  $("f-name").addEventListener("keydown",function(e){ if(e.key==="Enter") $("f-save").click(); });
  $("f-save").onclick=function(){
    var name=$("f-name").value.trim();
    if(name.length<1||name.length>50){ toast("Name must be 1–50 characters."); return; }
    db.folders.push({ id:"f"+uid(), name:name }); save(); closeModal(); render();
  };
  setTimeout(function(){ $("f-name").focus(); },30);
}

function addVerseModal(){
  openModal('<h2>Add a verse</h2><p class="hint">Enter a reference (e.g. <b>John 3:16</b> or <b>Romans 8:1-4</b>). We fetch the ESV text for you.</p>'+
    '<label class="field"><span>Reference</span><input type="text" id="a-ref" placeholder="John 3:16" autofocus></label>'+
    '<div class="row"><button class="btn ghost" id="a-cancel">Cancel</button><button class="btn primary" id="a-save">Add verse</button></div>');
  $("a-cancel").onclick=closeModal;
  $("a-ref").addEventListener("keydown",function(e){ if(e.key==="Enter") $("a-save").click(); });
  $("a-save").onclick=function(){
    var ref=$("a-ref").value.trim();
    if(ref.length<2){ toast("Enter a reference."); return; }
    if(hasRef(ref)){ toast("That reference is already in your list."); return; }
    var btn=$("a-save"); btn.disabled=true; btn.textContent="Adding…";
    fetchText(ref).then(function(text){
      var v=newVerse(ref, ui.folderId); v.text=text||null;
      db.verses.push(v); save(); closeModal(); render();
      toast(text ? ("Added "+ref) : ("Added "+ref+" (text will load on practice)"));
    }).catch(function(){
      // Still add it; text will lazy-load on practice.
      var v=newVerse(ref, ui.folderId); db.verses.push(v); save(); closeModal(); render();
      toast("Added "+ref+" (couldn’t reach ESV; text loads later)");
    });
  };
  setTimeout(function(){ $("a-ref").focus(); },30);
}

function libraryModal(){
  var rows = LIBRARY.map(function(ref){
    var added = hasRef(ref);
    return '<div class="librow"><span class="lref">'+esc(ref)+'</span>'+
      (added ? '<span class="added">Added</span>'
             : '<button class="btn" data-libadd="'+esc(ref)+'">Add</button>')+'</div>';
  }).join("");
  openModal('<h2>Library</h2><p class="hint">Classic passages to memorize. Adding one fetches its ESV text.</p>'+
    '<div class="liblist">'+rows+'</div>'+
    '<div class="row"><button class="btn primary" id="l-done">Done</button></div>');
  $("l-done").onclick=function(){ closeModal(); render(); };
  $("modal").querySelectorAll("[data-libadd]").forEach(function(b){
    b.onclick=function(){
      var ref=b.getAttribute("data-libadd");
      if(hasRef(ref)) return;
      b.disabled=true; b.textContent="…";
      fetchText(ref).then(function(t){ addFromLib(ref,t,b); }).catch(function(){ addFromLib(ref,null,b); });
    };
  });
}
function addFromLib(ref, text, btn){
  var v=newVerse(ref, ui.folderId); v.text=text||null;
  db.verses.push(v); save();
  var row=btn.closest(".librow"); if(row){ btn.remove(); var s=document.createElement("span"); s.className="added"; s.textContent="Added"; row.appendChild(s); }
  toast("Added "+ref);
}

// ================================================================ PRACTICE
var recognition=null, recogSupported=false;
(function setupRecog(){
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(SR){
    recogSupported=true;
    recognition=new SR();
    recognition.continuous=true; recognition.interimResults=true; recognition.lang="en-US";
    recognition.onresult=function(ev){
      var t=""; for(var i=0;i<ev.results.length;i++) t+=ev.results[i][0].transcript;
      if(practice){ practice.input=t; evaluate(); updateSpeakUI(); }
    };
    recognition.onend=function(){ if(practice){ practice.listening=false; updateSpeakUI(); } };
    recognition.onerror=function(){ if(practice){ practice.listening=false; updateSpeakUI(); } };
  }
})();

function startPractice(vid, opts){
  opts=opts||{};
  var v=verseById(vid); if(!v) return;
  var startIdx;
  if(opts.initialStep){ startIdx=Math.min(Math.max(0, opts.initialStep-1),7); }
  else { startIdx=Math.min(Math.max(0, v.currentStep||0),7); }
  practice = { verse:v, idx:startIdx, isRefresh:!!opts.isRefresh, input:"", listening:false,
    feedback:"neutral", accuracy:0, audioUrl:null };
  ui.view="practice"; closeMenus();
  // Ensure text is available.
  ensureText(v).then(function(){ if(practice) render(); });
  render();
}
function exitPractice(){
  if(recognition && practice && practice.listening){ try{recognition.stop();}catch(e){} }
  practice=null; ui.view="dash"; render();
}

function stepObj(){ return STEPS[practice.idx]; }

function evaluate(){
  var v=practice.verse, s=stepObj();
  if(s.type==="read"||s.type==="listen"){ practice.feedback="neutral"; return; }
  if(!v.text){ return; }
  var target=cleanText(v.text), inp=cleanText(practice.input);
  if(!target) return;
  var acc=Math.round(similarity(inp,target)*100);
  practice.accuracy=acc;
  if(acc>=85){ practice.feedback="success"; if(practice.listening && recognition){ try{recognition.stop();}catch(e){} } }
  else { practice.feedback="neutral"; }
}

function renderPractice(){
  var v=practice.verse, s=stepObj();
  $("topsub").textContent = "";
  $("topactions").innerHTML = "";

  var pct=(practice.idx/8)*100;
  var html='<div class="pr">'+
    '<div class="pr-head">'+
      '<button class="btn ghost" id="p-exit"><svg viewBox="0 0 24 24" style="width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.9;margin-right:2px"><path d="M15 18l-6-6 6-6"/></svg>'+(practice.isRefresh?"Done":"Exit")+'</button>'+
      '<div class="mid"><h2>'+esc(v.reference)+'</h2><div class="step">'+(practice.isRefresh?"Mastery refresh":("Step "+s.id+" of 8: "+esc(s.label)))+'</div></div>'+
      '<div style="display:flex;gap:4px;justify-content:flex-end;min-width:80px">'+
        (practice.idx>0?'<button class="icobtn" id="p-back" title="Previous step"><svg viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg></button>':'')+
        '<button class="icobtn" id="p-retry" title="Reset step"><svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 1 2.6 6.3M3 20v-5h5"/></svg></button>'+
      '</div>'+
    '</div>'+
    '<div class="pr-bar"><i style="width:'+pct+'%"></i></div>'+
    '<div class="pr-card">'+
      (practice.isRefresh?'<button class="btn ghost needs" id="p-needs" style="color:var(--warn)">I need practice 😓</button>':'')+
      '<div class="versebox" id="versebox">'+verseDisplay()+'</div>'+
      '<div class="act" id="act">'+actArea()+'</div>'+
    '</div></div>';

  $("view").innerHTML=html;
  $("p-exit").onclick=exitPractice;
  if($("p-back")) $("p-back").onclick=stepBack;
  $("p-retry").onclick=stepRetry;
  if($("p-needs")) $("p-needs").onclick=needsPractice;
  wireAct();
}

function verseDisplay(){
  var v=practice.verse, s=stepObj();
  if(!v.text){ return '<div class="note">Fetching verse text…</div>'; }
  if(s.mode==="hidden"){ return '<div class="verse hidden">(verse hidden)</div>'; }
  var words=v.text.split(/\s+/);
  var out=words.map(function(w){
    if(s.mode==="first-letter" && w.length>1){
      var fl=(w.match(/[a-zA-Z0-9]/)||[""])[0];
      var punct=(w.match(/[^a-zA-Z0-9]*$/)||[""])[0];
      return '<span>'+esc(fl)+'___'+esc(punct)+'</span>';
    }
    return '<span>'+esc(w)+'</span>';
  }).join("");
  return '<div class="verse">'+out+'</div>';
}

function actArea(){
  var v=practice.verse, s=stepObj();
  var disabled = !v.text;
  if(s.type==="read"){
    return '<button class="btn primary big" id="a-next"'+(disabled?" disabled":"")+'>I have read it silently →</button>';
  }
  if(s.type==="listen"){
    return '<div class="audiocard"><div class="lab">ESV audio Bible</div><div id="audioslot">'+
        (practice.audioUrl ? audioTag(practice.audioUrl) : '<div class="note">Loading audio…</div>')+
      '</div></div>'+
      '<button class="btn primary big" id="a-next"'+(disabled?" disabled":"")+'>I have listened →</button>';
  }
  if(s.type==="speak"){
    return '<button class="mic'+(practice.listening?" on":"")+'" id="a-mic"'+((!recogSupported||disabled)?" disabled":"")+'>'+
        '<span class="disc"><svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6 11a6 6 0 0 0 12 0M12 17v3"/></svg></span>'+
        '<span>'+(!recogSupported?"Speech input not supported — use the button below":(practice.listening?"Listening…":"Tap to speak"))+'</span>'+
      '</button>'+
      '<div class="transcript" id="a-trans">'+speakTrans()+'</div>'+
      '<div id="a-adv">'+speakAdvance()+'</div>';
  }
  if(s.type==="type"){
    return '<textarea id="a-input" placeholder="Type the passage here…" '+(disabled?"disabled":"")+'>'+esc(practice.input)+'</textarea>'+
      '<div id="a-adv">'+typeAdvance()+'</div>';
  }
  return "";
}

function audioTag(url){
  return '<audio controls preload="none" src="'+esc(url)+'"></audio>';
}
// Mask profanity in the spoken-transcript display (school setting). Display-only:
// grading still uses the raw recognition text, and profanity never matches
// Scripture, so scoring is unaffected. Whole-word matching avoids false positives
// (e.g. "class"/"assess" are never touched).
var PROFANITY_LIST = window.PROFANITY_LIST || ("fuck fucks fucked fucking fuckin fucker fuckers motherfucker motherfuckers motherfucking "
  + "shit shits shitty shitting shithead bullshit dipshit "
  + "ass asshole assholes asses asshat dumbass jackass "
  + "bitch bitches bitching bastard bastards bollocks "
  + "damn dammit goddamn goddamnit dick dickhead dicks "
  + "cunt cunts cock cocks cocksucker piss pissed prick pricks "
  + "whore whores slut sluts wanker twat pussy pussies arse arsehole bugger "
  + "nigger niggers nigga niggas fag faggot faggots fags dyke retard retarded "
  + "spic chink kike wetback coon gook").split(/\s+/);
// Context-dependent masks: words that are innocent alone (screw/suck/balls/laid)
// but crude in these phrasings. Masks only the offensive token, keeps the connector
// (so "suck my balls" -> "••• my •••", "screw you" -> "••• you").
var PROFANITY_PHRASES = [
  [/\bscrew(?:ed|ing|s)?(\s+(?:you|u|ya|him|her|them|it))\b/gi, "•••$1"],
  [/\bsuck(?:ed|ing|s)?(\s+my)\b/gi, "•••$1"],
  [/(\bmy\s+)balls?\b/gi, "$1•••"],
  [/(\bget(?:s|ting)?\s+)laid\b/gi, "$1•••"],
  [/\b(?:jack|jerk|beat)(?:ed|ing|s|in)?\s+off\b/gi, "•••"],
  [/\b(?:hand|blow|rim)\s*jobs?\b/gi, "•••"]
];
var _profSet = null;
function maskProfanity(text){
  if(!text) return text;
  for(var i=0;i<PROFANITY_PHRASES.length;i++){ text = text.replace(PROFANITY_PHRASES[i][0], PROFANITY_PHRASES[i][1]); }
  if(!_profSet){ _profSet = {}; PROFANITY_LIST.forEach(function(w){ _profSet[w]=1; }); }
  return text.replace(/[A-Za-z][A-Za-z'’]*/g, function(w){
    return _profSet[w.toLowerCase().replace(/[’']/g,"")] ? "•••" : w;
  });
}

function speakTrans(){
  if(!practice.input) return '<span style="opacity:.6">…</span>';
  return '<div class="said">&ldquo;'+esc(maskProfanity(practice.input))+'&rdquo;</div><div class="acc">Accuracy: '+practice.accuracy+'%</div>';
}
function speakAdvance(){
  if(practice.feedback==="success") return '<button class="btn ok big" id="a-next">Perfect! Next step →</button>';
  // Speech can't always be auto-verified (no mic, unsupported browser), so never trap the user.
  return '<button class="btn ghost" id="a-next" style="width:100%">I said it aloud, mark as done</button>';
}
function typeAdvance(){
  if(practice.feedback==="success") return '<button class="btn ok big" id="a-next">Correct! Next step →</button>';
  if(practice.input.length>5) return '<button class="btn ghost" id="a-next" style="width:100%">I typed it correctly, mark as done</button>';
  return "";
}

function wireAct(){
  var s=stepObj();
  if($("a-next")) $("a-next").onclick=stepNext;
  if(s.type==="listen" && !practice.audioUrl){
    fetchAudio(practice.verse.reference).then(function(url){
      if(practice && stepObj().type==="listen"){ practice.audioUrl=url;
        var slot=$("audioslot"); if(slot) slot.innerHTML = url?audioTag(url):'<div class="note">Audio unavailable for this reference.</div>'; }
    }).catch(function(){ var slot=$("audioslot"); if(slot) slot.innerHTML='<div class="note">Audio unavailable.</div>'; });
  }
  if(s.type==="type"){
    var ta=$("a-input");
    if(ta){ ta.focus(); ta.oninput=function(){ practice.input=ta.value; evaluate(); updateTypeUI(); }; }
  }
  if(s.type==="speak"){
    var mic=$("a-mic");
    if(mic) mic.onclick=toggleMic;
  }
}
function updateSpeakUI(){
  if(ui.view!=="practice") return;
  var t=$("a-trans"); if(t) t.innerHTML=speakTrans();
  var adv=$("a-adv"); if(adv){ adv.innerHTML=speakAdvance(); if($("a-next")) $("a-next").onclick=stepNext; }
  var mic=$("a-mic"); if(mic){ mic.classList.toggle("on",practice.listening);
    var lbl=mic.querySelector("span:last-child"); if(lbl && recogSupported) lbl.textContent=practice.listening?"Listening…":"Tap to speak"; }
}
function updateTypeUI(){
  var adv=$("a-adv"); if(adv){ adv.innerHTML=typeAdvance(); if($("a-next")) $("a-next").onclick=stepNext; }
}
function toggleMic(){
  if(!recogSupported) return;
  if(practice.listening){ try{recognition.stop();}catch(e){} practice.listening=false; }
  else { practice.input=""; evaluate(); try{recognition.start(); practice.listening=true;}catch(e){} }
  updateSpeakUI();
}

// step transitions
function stepNext(){
  var v=practice.verse;
  if(!practice.isRefresh){
    v.currentStep = stepObj().id;      // record the step just completed
    v.lastPracticedAt = new Date().toISOString();
    if(v.currentStep>=8){ v.masteredAt = new Date().toISOString(); }
    save();
  }
  if(practice.idx < STEPS.length-1){
    practice.idx++; practice.input=""; practice.feedback="neutral"; practice.accuracy=0; practice.audioUrl=null;
    if(practice.listening && recognition){ try{recognition.stop();}catch(e){} practice.listening=false; }
    renderPractice();
  } else {
    // completed step 8
    if(practice.isRefresh){
      v.lastRefreshedAt=new Date().toISOString(); v.lastPracticedAt=new Date().toISOString(); save();
      toast("Refreshed "+v.reference);
    } else {
      toast("Mastered "+v.reference+" 🎉");
    }
    exitPractice();
  }
}
function stepBack(){
  if(practice.idx>0){
    practice.idx--; practice.input=""; practice.feedback="neutral"; practice.accuracy=0; practice.audioUrl=null;
    if(practice.listening && recognition){ try{recognition.stop();}catch(e){} practice.listening=false; }
    renderPractice();
  }
}
function stepRetry(){
  practice.input=""; practice.feedback="neutral"; practice.accuracy=0;
  if(practice.listening && recognition){ try{recognition.stop();}catch(e){} practice.listening=false; }
  renderPractice();
}
function needsPractice(){
  if(!confirm("Move this verse back to Learning? This resets its progress to the start.")) return;
  var v=practice.verse;
  v.currentStep=0; v.masteredAt=null; v.lastRefreshedAt=null; save();
  toast("Back to Learning");
  exitPractice();
}

// ---------------------------------------------------------------- verse drawer
var sideEl=$("side");
function setDrawerOpen(o){
  sideEl.classList.toggle("open", !!o);
  var tb=$("menu-btn"); if(tb) tb.setAttribute("aria-expanded", o?"true":"false");
}
function toggleDrawer(){ setDrawerOpen(!sideEl.classList.contains("open")); }
$("menu-btn").onclick=toggleDrawer;
$("drawer-close").onclick=function(){ setDrawerOpen(false); $("menu-btn").focus(); };
$("drawer-add").onclick=function(){ addVerseModal(); };
$("drawer-lib").onclick=function(){ libraryModal(); };
document.addEventListener("keydown",function(e){
  if(e.key==="Escape" && sideEl.classList.contains("open") && !$("scrim").classList.contains("show")){ setDrawerOpen(false); }
});
setDrawerOpen(true);   // start open so the verse list is the first thing you see

init();
})();
