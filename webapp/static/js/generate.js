/* The Prep Room · Exegetica page (templates/generate.html, decision 0026). Units hold sources, objectives and
   resources; the Make panel is the gallery of kinds; every draft, revision and edit is saved as a version.
   The rail, theme and Need help now? come from static/js/shell.js. */
"use strict";
// ---- shared compact markdown renderer ----
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function inl(s){return esc(s).replace(/`([^`]+)`/g,(m,c)=>"<code>"+c+"</code>").replace(/_{3,}/g,m=>"<span class='blank' style='min-width:"+Math.min(26,Math.max(3,m.length*0.55)).toFixed(1)+"em'></span>").replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/(^|[^*])\*([^*\n]+)\*/g,"$1<em>$2</em>").replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');}
function md(src){const L=src.replace(/\r\n/g,"\n").split("\n");let h="",i=0;const sep=s=>/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(s);const cells=s=>s.replace(/^\s*\|/,"").replace(/\|\s*$/,"").split("|").map(c=>c.trim());
  while(i<L.length){let l=L[i];
    if(/^```/.test(l)){i++;let b=[];while(i<L.length&&!/^```/.test(L[i])){b.push(L[i]);i++;}i++;h+="<pre><code>"+esc(b.join("\n"))+"</code></pre>";continue;}
    if(/^\s*$/.test(l)){i++;continue;}
    if(/^#{1,4}\s/.test(l)){const n=l.match(/^#+/)[0].length;h+="<h"+n+">"+inl(l.replace(/^#+\s/,""))+"</h"+n+">";i++;continue;}
    if(/^\s*_{3,}\s*$/.test(l)){let n=0;while(i<L.length&&/^\s*_{3,}\s*$/.test(L[i])){n++;i++;}for(let k=0;k<n;k++)h+="<div class='writeline'></div>";continue;}
    if(/^\s*(-{3,}|\*{3,})\s*$/.test(l)){h+="<hr>";i++;continue;}
    if(/^\s*>/.test(l)){let b=[];while(i<L.length&&/^\s*>/.test(L[i])){b.push(L[i].replace(/^\s*>\s?/,""));i++;}h+="<blockquote>"+md(b.join("\n"))+"</blockquote>";continue;}
    if(l.includes("|")&&i+1<L.length&&sep(L[i+1])){const hd=cells(l);i+=2;const rs=[];while(i<L.length&&L[i].includes("|")&&!/^\s*$/.test(L[i])){rs.push(cells(L[i]));i++;}h+=Shell.table(hd,rs,inl);continue;}
    if(/^\s*[-*]\s+/.test(l)){let b=[];while(i<L.length&&/^\s*[-*]\s+/.test(L[i])){b.push("<li>"+inl(L[i].replace(/^\s*[-*]\s+/,""))+"</li>");i++;}h+="<ul>"+b.join("")+"</ul>";continue;}
    if(/^\s*\d+[.)]\s+/.test(l)){let b=[];while(i<L.length&&/^\s*\d+[.)]\s+/.test(L[i])){const mm=L[i].match(/^\s*(\d+)[.)]\s+/);b.push("<li value='"+mm[1]+"'>"+inl(L[i].replace(/^\s*\d+[.)]\s+/,""))+"</li>");i++;}h+="<ol>"+b.join("")+"</ol>";continue;}
    let b=[];while(i<L.length&&!/^\s*$/.test(L[i])&&!/^```/.test(L[i])&&!/^#{1,4}\s/.test(L[i])&&!/^\s*[-*]\s+/.test(L[i])&&!/^\s*>/.test(L[i])&&!/^\s*_{3,}\s*$/.test(L[i])&&!/^\s*(-{3,}|\*{3,})\s*$/.test(L[i])){b.push(L[i]);i++;}h+="<p>"+inl(b.join("\n")).replace(/\n/g,"<br>")+"</p>";}
  return h;}

// ---- the student copy: the teacher-only sections out (mirrors prep_catalog.student_copy) ----
const TEACHER_HEAD=/^(#{1,6})\s+(?:answer key|answers|teaching notes|teacher notes|notes for the teacher|for the teacher|teacher'?s? (?:guide|notes|key)|.*\((?:teacher|teacher only|for the teacher)\))\s*:?\s*$/i;
const TEACHER_LINE=/^\s*(?:\*\*)?(?:standards|objectives? \(teacher\))(?:\*\*)?\s*:/i;
function studentCopy(src){const out=[];let skip=0;
  for(const line of src.split("\n")){const head=line.match(/^(#{1,6})\s/);
    if(skip){if(head&&head[1].length<=skip)skip=0;else continue;}
    const m=line.trim().match(TEACHER_HEAD);
    if(m){skip=m[1].length;while(out.length&&/^\s*(---|\*\*\*|___)?\s*$/.test(out[out.length-1]))out.pop();continue;}
    if(TEACHER_LINE.test(line))continue;out.push(line);}
  while(out.length&&/^\s*(---|\*\*\*|___)?\s*$/.test(out[out.length-1]))out.pop();
  return out.join("\n")+"\n";}
function hasTeacherPart(src){return src.split("\n").some(l=>TEACHER_HEAD.test(l.trim()));}

// ---- state ----
const $=id=>document.getElementById(id);
const app=$("app");
const S={units:[],quick:[],unit:null,res:null,gallery:null,courses:[],kind:null,busy:false,quickSources:[],viewing:null,savedDoc:"",settings:{}};
let rawDoc="",audience="teacher",mode="view",docBand="";
const ICON={
  book:'<svg viewBox="0 0 24 24"><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H12v15H5.5A1.5 1.5 0 0 0 4 20.5z"/><path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H12v15h6.5a1.5 1.5 0 0 1 1.5 1.5z"/></svg>',
  outline:'<svg viewBox="0 0 24 24"><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/></svg>',
  passage:'<svg viewBox="0 0 24 24"><path d="M6 4h12v16l-6-4-6 4z"/></svg>',
  library:'<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 9l5 3-5 3z"/></svg>',
  upload:'<svg viewBox="0 0 24 24"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/></svg>',
  link:'<svg viewBox="0 0 24 24"><path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1"/><path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/></svg>',
  kebab:'<svg viewBox="0 0 24 24"><circle cx="12" cy="6" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="18" r="1.5"/></svg>',
  star:'<svg viewBox="0 0 24 24"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.8l-5.2 2.8 1-5.8-4.3-4.1 5.9-.9z"/></svg>'};
const KIND_WORD={book:"Book",outline:"Outline",passage:"Passage",library:"Living Library",upload:"Upload",link:"Link"};

async function api(method,url,body){
  const o={method,headers:{}};
  if(body!==undefined){o.headers["Content-Type"]="application/json";o.body=JSON.stringify(body);}
  const r=await fetch(url,o);let d={};try{d=await r.json();}catch(e){}
  if(!r.ok)throw new Error(d.error||"That didn't work. Check your connection and try again.");
  return d;}
function ago(iso){if(!iso)return "";const s=(Date.now()-new Date(iso).getTime())/1000;
  if(s<60)return "just now";if(s<3600)return Math.round(s/60)+" min ago";if(s<86400)return Math.round(s/3600)+" h ago";
  return new Date(iso).toLocaleDateString(undefined,{month:"short",day:"numeric"});}
function when(iso){return new Date(iso).toLocaleString(undefined,{month:"short",day:"numeric",hour:"numeric",minute:"2-digit"});}
function plural(n,w){return n+" "+w+(n===1?"":/(ch|sh|s|x)$/.test(w)?"es":"s");}
function bandLabel(b){return b?b.charAt(0).toUpperCase()+b.slice(1):"";}
function courseName(k){const c=S.courses.find(c=>c.key===k);return c?c.name:"";}
function kindOf(id){for(const g of (S.gallery||{groups:[]}).groups)for(const k of g.kinds)if(k.id===id)return k;return null;}

// ---- addresses: /generate, /generate/new, /generate/unit/<id>[/r/<resource>], /generate/r/<resource> ----
const UUID="[0-9a-f-]{36}";
function route(){const p=location.pathname.replace(/\/+$/,"");let m;
  if((m=p.match(new RegExp("^/generate/unit/("+UUID+")(?:/r/("+UUID+"))?$"))))return {view:"unit",unit:m[1],res:m[2]||null};
  if((m=p.match(new RegExp("^/generate/r/("+UUID+")$"))))return {view:"unit",unit:null,res:m[1]};
  if(p==="/generate/new")return {view:"unit",unit:null,res:null};
  return {view:"home"};}
function go(path){if(location.pathname!==path)history.pushState({},"",path);load();}
function resPath(rid){return S.unit?"/generate/unit/"+S.unit.id+(rid?"/r/"+rid:""):(rid?"/generate/r/"+rid:"/generate/new");}
window.addEventListener("popstate",load);
document.addEventListener("click",e=>{const a=e.target.closest("a[data-nav]");if(!a||e.metaKey||e.ctrlKey||e.shiftKey||e.button)return;e.preventDefault();go(a.getAttribute("href"));});

async function load(){
  const r=route();closeMenus();
  if(!S.gallery)await loadGallery();
  if(S.busy&&r.view==="home"){history.pushState({},"",resPath(S.res&&S.res.id));Shell.toast("Wait for the draft to finish, or stay here: it's saved when it's done.");return;}
  app.dataset.view=r.view;
  if(r.view==="home"){tellPanel();await loadHome();return;}
  if(r.unit){
    if(!S.unit||S.unit.id!==r.unit){
      try{S.unit=(await api("GET","/api/prep/units/"+r.unit)).unit;}
      catch(e){S.unit=null;app.dataset.view="home";await loadHome();Shell.toast(e.message);return;}
    }
  }else if(S.unit){S.unit=null;S.quickSources=[];}
  renderUnit();
  if(r.res){if(!S.res||S.res.id!==r.res)await openResource(r.res);}
  else{S.res=null;clearDoc();}
  document.title=(S.unit?S.unit.title:"Quick resource")+" · Prep Room · Exegetica";
}

async function loadGallery(){
  try{const d=await api("GET","/api/prep/gallery");S.gallery=d;S.courses=d.courses||[];renderKinds();fillBands();}
  catch(e){$("kinds").innerHTML='<p class="knone">'+esc(e.message)+'</p>';}
}

// ---- home: the units ----
async function loadHome(){
  document.title="Prep Room · Exegetica";
  $("unitgrid").innerHTML='<p class="empty-line">Loading your units…</p>';
  try{const d=await api("GET","/api/prep/units");S.units=d.units;S.quick=d.quick;}
  catch(e){$("unitgrid").innerHTML='<div class="home-empty"><h2>Your units didn\'t load</h2><p>'+esc(e.message)+'</p><button type="button" class="btn-quiet" data-act="reload">Try again</button></div>';return;}
  renderHome();
}
function unitCounts(u){const parts=[plural(u.n_sources,"source"),plural(u.n_resources,"resource")];return parts.join(" · ")+" · edited "+ago(u.updated_at);}
function renderHome(){
  const g=$("unitgrid");
  if(!S.units.length){
    g.innerHTML='<div class="home-empty"><h2>Start your first unit</h2><p>Name it the way you plan, such as “John 7 and 8” or “Module 3: Percents”. Then add what you teach from, and make handouts, quizzes and guides from it. Everything you make is kept here.</p><button type="button" class="btn-primary" data-act="new-unit">New unit</button></div>';
  }else{
    g.innerHTML=S.units.map(u=>'<article class="ucard" data-id="'+u.id+'"><h3><a href="/generate/unit/'+u.id+'" data-nav>'+esc(u.title)+'</a></h3>'+
      '<p class="u-course">'+esc([courseName(u.course_key),bandLabel(u.grade_band)].filter(Boolean).join(" · "))+'</p>'+
      '<p class="u-counts">'+unitCounts(u)+'</p>'+
      '<button type="button" class="icobtn kebab" data-umenu="'+u.id+'" aria-label="Options for '+esc(u.title)+'" aria-haspopup="true">'+ICON.kebab+'</button></article>').join("");
  }
  $("quick").hidden=!S.quick.length;
  $("quicklist").innerHTML=S.quick.map(r=>resRow(r,"/generate/r/"+r.id)).join("");
}
document.addEventListener("click",e=>{
  const act=e.target.closest("[data-act]");if(!act)return;
  if(act.dataset.act==="new-unit")newUnit();
  if(act.dataset.act==="reload")loadHome();
});
$("new-unit").addEventListener("click",newUnit);
async function newUnit(){
  const title=await Shell.ask({title:"New unit",body:"Name it the way you plan. You can add its course and grade band next.",ok:"Create unit",
    input:{label:"Unit name",value:"",max:160},validate:t=>t?"":"Give the unit a name."});
  if(!title)return;
  try{const d=await api("POST","/api/prep/units",{title,grade_band:"secondary"});S.unit=d.unit;go("/generate/unit/"+d.unit.id);setTab("unit");}
  catch(e){Shell.toast(e.message);}
}

// ---- menus (the kebab): click, Enter or Space opens; arrows move; Escape or a click outside closes ----
let openMenuEl=null,menuOpener=null;
function closeMenus(){if(openMenuEl){openMenuEl.remove();openMenuEl=null;if(menuOpener)menuOpener.setAttribute("aria-expanded","false");}
  $("vmenu").hidden=true;$("versions").setAttribute("aria-expanded","false");}
function openMenu(btn,items){
  const was=openMenuEl&&menuOpener===btn;closeMenus();if(was)return;
  const m=document.createElement("div");m.className="menu";m.setAttribute("role","menu");
  items.forEach(it=>{const b=document.createElement("button");b.type="button";b.setAttribute("role","menuitem");b.textContent=it.label;if(it.danger)b.className="danger";
    b.onclick=ev=>{ev.stopPropagation();closeMenus();btn.focus();it.act();};m.appendChild(b);});
  btn.parentElement.appendChild(m);openMenuEl=m;menuOpener=btn;btn.setAttribute("aria-expanded","true");
  m.addEventListener("keydown",ev=>{const bs=[...m.querySelectorAll("button")],i=bs.indexOf(document.activeElement);
    if(ev.key==="ArrowDown"){ev.preventDefault();bs[(i+1)%bs.length].focus();}
    if(ev.key==="ArrowUp"){ev.preventDefault();bs[(i-1+bs.length)%bs.length].focus();}
    if(ev.key==="Escape"){ev.preventDefault();closeMenus();btn.focus();}});
  m.querySelector("button").focus();
}
document.addEventListener("click",e=>{if(openMenuEl&&!e.target.closest(".menu")&&!e.target.closest(".kebab")&&!e.target.closest("[data-umenu]"))closeMenus();
  if(!$("vmenu").hidden&&!e.target.closest("#vmenu")&&!e.target.closest("#versions"))closeMenus();});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!e.defaultPrevented){if(!$("vmenu").hidden){closeMenus();$("versions").focus();}if(app.classList.contains("make-open")&&!$("dlg").open)closeMake();}});

// A removal happens at once and can be taken back for a few seconds (rule F3); the server hears of it after.
const pending=new Map();
function removeLater(url,message,undo){
  const key=url+Math.random();
  const t=setTimeout(()=>{pending.delete(key);api("DELETE",url).catch(err=>{Shell.toast(err.message);undo();});},6500);
  pending.set(key,{t,url});
  Shell.toast(message,{undo:()=>{clearTimeout(t);pending.delete(key);undo();}});
}
window.addEventListener("pagehide",()=>{pending.forEach(p=>{clearTimeout(p.t);fetch(p.url,{method:"DELETE",keepalive:true});});pending.clear();saveEditNow(true);});

document.addEventListener("click",e=>{
  const b=e.target.closest("[data-umenu]");if(!b)return;e.stopPropagation();
  const u=S.units.find(x=>x.id===b.dataset.umenu);if(!u)return;
  openMenu(b,[{label:"Rename",act:()=>renameUnit(u)},
    {label:"Delete unit",danger:true,act:()=>{const i=S.units.indexOf(u);S.units.splice(i,1);renderHome();
      removeLater("/api/prep/units/"+u.id,"Deleted “"+u.title+"” and its resources",()=>{S.units.splice(i,0,u);renderHome();});}}]);
});
async function renameUnit(u){
  const t=await Shell.ask({title:"Rename unit",ok:"Rename",input:{label:"Unit name",value:u.title,max:160},validate:t=>t?"":"Give the unit a name."});
  if(!t||t===u.title)return;
  try{await api("PATCH","/api/prep/units/"+u.id,{title:t});u.title=t;if(S.unit&&S.unit.id===u.id){S.unit.title=t;renderUnit();}renderHome();}
  catch(e){Shell.toast(e.message);}
}

// ---- the unit pane ----
function sourceSub(s){
  const r=s.ref||{};
  if(s.kind==="book"){const c=r.coverage||{};const d=c.through?"Read through "+(r.through_title||"section "+c.through):"Whole book";return esc(d);}
  if(s.kind==="outline")return '<span class="badge outline">Outline only</span> '+esc((r.parts||[]).length?r.parts.join("; "):"All parts");
  if(s.kind==="passage")return esc(r.translation||"ESV");
  if(s.kind==="upload")return "Your upload · "+(s.words||0).toLocaleString()+" words";
  if(s.kind==="link"){let h="";try{h=new URL(r.url).hostname.replace(/^www\./,"");}catch(e){}return esc(h)+" · "+(s.words||0).toLocaleString()+" words";}
  if(s.kind==="library"){const n=(r.excerpts||[]).length;return "From your Living Library"+(n?" · "+n+" saved moment"+(n===1?"":"s"):"");}
  return "";}
// The passage panel (static/js/passage.js) lists the open unit first under "Add to a unit".
function tellPanel(){if(window.Passage)Passage.currentUnit=app.dataset.view!=="home"&&S.unit?{id:S.unit.id,title:S.unit.title}:null;}
document.addEventListener("prep:sources-changed",e=>{if(S.unit&&e.detail&&e.detail.unit===S.unit.id)refreshUnit();});
// A source opens where it lives: a passage in the panel, a book in the Reading Room at the class's place, a page
// in a new tab. Outlines, uploads and Living Library items have nothing to open here.
function sourceLabel(s){
  const r=s.ref||{},t=esc(s.label);
  if(s.kind==="passage"){const n=window.Passage&&(Passage.normalize(r.ref)||Passage.chapter(r.ref));
    if(n)return '<a class="s-label s-open ref" href="/?passage='+encodeURIComponent(n)+'" data-ref="'+esc(n)+'">'+t+'</a>';}
  if(s.kind==="book"&&r.slug){const at=(r.coverage||{}).through;
    return '<a class="s-label s-open" href="/read/'+encodeURIComponent(r.slug)+(at?"#"+at:"")+'">'+t+'</a>';}
  if(s.kind==="link"&&r.url)return '<a class="s-label s-open" href="'+esc(r.url)+'" target="_blank" rel="noopener noreferrer">'+t+'<span class="shell-sr"> (opens in a new tab)</span></a>';
  return '<span class="s-label">'+t+'</span>';}
function renderUnit(){
  const u=S.unit,quick=!u;tellPanel();
  $("u-title").textContent=quick?"Quick resource":u.title;
  $("u-meta").textContent=quick?"A one-off, kept with your quick resources. Its sources aren't kept.":[courseName(u.course_key)||"No course chosen",bandLabel(u.grade_band)].join(" · ");
  $("u-edit").hidden=quick;
  const sources=quick?S.quickSources:u.sources;
  $("n-sources").textContent=sources.length||"";
  $("srclist").innerHTML=sources.length?sources.map((s,i)=>'<li data-i="'+i+'"><span class="s-ic" aria-hidden="true">'+(ICON[s.kind]||ICON.upload)+'</span>'+
    '<span class="s-txt">'+sourceLabel(s)+'<span class="s-sub">'+sourceSub(s)+'</span></span>'+
    '<button type="button" class="icobtn kebab" data-smenu="'+i+'" aria-label="Options for '+esc(s.label)+'" aria-haspopup="true">'+ICON.kebab+'</button></li>').join(""):
    '<li class="empty-line">No sources yet. A draft with none works from the objectives and the study tools alone.</li>';
  $("add-source").closest(".u-sec").querySelector(".u-hint").hidden=!sources.length;
  for(const id of ["h-objs","h-note","h-res"])$(id).closest(".u-sec").hidden=quick;
  if(!quick){
    $("n-objs").textContent=u.objectives.length||"";
    $("objchips").innerHTML=u.objectives.map((o,i)=>'<span class="chip"><span><span class="oid">'+esc(o.id)+'</span>'+esc(o.t.length>110?o.t.slice(0,108)+"…":o.t)+'</span><button type="button" data-unobj="'+i+'" aria-label="Remove objective '+esc(o.id)+'">×</button></span>').join("")||'<span class="empty-line">None yet. Objectives keep drafts aimed at what you are teaching.</span>';
    if(document.activeElement!==$("u-note"))$("u-note").value=u.notes||"";
    $("n-res").textContent=u.resources.length||"";
    $("reslist").innerHTML=u.resources.length?u.resources.map(r=>resRow(r,"/generate/unit/"+u.id+"/r/"+r.id)).join(""):'<li class="empty-line">Nothing made yet.</li>';
  }
  updateDraws();
}
function resRow(r,href){const k=kindOf(r.format_id);const on=S.res&&S.res.id===r.id?" on":"";
  return '<li class="'+on+'"><a class="r-open" href="'+href+'" data-nav><span class="r-title">'+esc(r.title)+'</span><span class="r-sub">'+esc(k?k.name.split(/ \/ | \(/)[0]:r.format_id)+(r.latest?" · version "+r.latest:"")+" · "+ago(r.updated_at)+'</span></a>'+
    '<button type="button" class="icobtn kebab" data-rmenu="'+r.id+'" aria-label="Options for '+esc(r.title)+'" aria-haspopup="true">'+ICON.kebab+'</button></li>';}
$("u-edit").addEventListener("click",editUnit);
document.addEventListener("click",e=>{
  const sm=e.target.closest("[data-smenu]");
  if(sm){e.stopPropagation();const i=+sm.dataset.smenu;const list=S.unit?S.unit.sources:S.quickSources;const s=list[i];if(!s)return;
    const items=[];if(s.kind==="book")items.push({label:"Change how far the class has read",act:()=>coverDialog(s)});
    if(s.kind==="outline")items.push({label:"Choose parts",act:()=>partsDialog(s)});
    items.push({label:"Remove source",danger:true,act:()=>removeSource(s)});openMenu(sm,items);return;}
  const rm=e.target.closest("[data-rmenu]");
  if(rm){e.stopPropagation();const list=S.unit?S.unit.resources:S.quick;const r=list.find(x=>x.id===rm.dataset.rmenu);if(!r)return;
    openMenu(rm,[{label:"Rename",act:()=>renameRes(r)},{label:"Delete resource",danger:true,act:()=>deleteRes(r,list)}]);return;}
  const uo=e.target.closest("[data-unobj]");
  if(uo){const i=+uo.dataset.unobj,old=S.unit.objectives.slice(),gone=old[i];S.unit.objectives.splice(i,1);saveObjectives();
    Shell.toast("Removed "+gone.id,{undo:()=>{S.unit.objectives=old;saveObjectives();}});}
});
function removeSource(s){
  if(!S.unit){const i=S.quickSources.indexOf(s);S.quickSources.splice(i,1);renderUnit();Shell.toast("Removed “"+s.label+"”",{undo:()=>{S.quickSources.splice(i,0,s);renderUnit();}});return;}
  const i=S.unit.sources.indexOf(s);S.unit.sources.splice(i,1);renderUnit();
  removeLater("/api/prep/sources/"+s.id,"Removed “"+s.label+"”",()=>{S.unit.sources.splice(i,0,s);renderUnit();});
}
async function saveObjectives(){renderUnit();
  try{await api("PATCH","/api/prep/units/"+S.unit.id,{objectives:S.unit.objectives});}catch(e){Shell.toast(e.message);}}
let noteTimer=null;
$("u-note").addEventListener("input",()=>{clearTimeout(noteTimer);$("note-state").textContent="";noteTimer=setTimeout(saveNote,900);});
$("u-note").addEventListener("blur",()=>{if(noteTimer){clearTimeout(noteTimer);saveNote();}});
async function saveNote(){noteTimer=null;if(!S.unit)return;const v=$("u-note").value;if(v===(S.unit.notes||""))return;
  try{await api("PATCH","/api/prep/units/"+S.unit.id,{notes:v});S.unit.notes=v;$("note-state").textContent="Saved";}
  catch(e){$("note-state").textContent="Not saved";Shell.toast(e.message);}}
async function renameRes(r){
  const t=await Shell.ask({title:"Rename resource",ok:"Rename",input:{label:"Title",value:r.title,max:160},validate:t=>t?"":"Give it a title."});
  if(!t||t===r.title)return;
  try{await api("PATCH","/api/prep/resources/"+r.id,{title:t});r.title=t;if(S.res&&S.res.id===r.id){S.res.title=t;$("outtitle").textContent=t;}renderUnit();if(app.dataset.view==="home")renderHome();}
  catch(e){Shell.toast(e.message);}
}
function deleteRes(r,list){
  const i=list.indexOf(r);list.splice(i,1);const wasOpen=S.res&&S.res.id===r.id;
  if(wasOpen){go(resPath(null));}else if(app.dataset.view==="home")renderHome();else renderUnit();
  removeLater("/api/prep/resources/"+r.id,"Deleted “"+r.title+"”",()=>{list.splice(i,0,r);if(app.dataset.view==="home")renderHome();else renderUnit();});
}
async function refreshUnit(){if(!S.unit)return;try{S.unit=(await api("GET","/api/prep/units/"+S.unit.id)).unit;renderUnit();}catch(e){}}

// ---- dialogs: one native <dialog>, its body drawn for each job ----
const dlg=$("dlg");let dlgOpener=null;
function openDlg(title,html){$("dlg-title").textContent=title;$("dlg-body").innerHTML=html;dlgOpener=document.activeElement;if(!dlg.open)dlg.showModal();
  const f=$("dlg-body").querySelector("[autofocus],input,select,button");if(f)f.focus();}
function closeDlg(){if(dlg.open)dlg.close();}
dlg.addEventListener("close",()=>{if(dlgOpener&&dlgOpener.isConnected)dlgOpener.focus();});
dlg.addEventListener("click",e=>{if(e.target===dlg||e.target.closest("[data-close]"))closeDlg();});
function dlgError(msg){let p=$("dlg-body").querySelector(".derr");if(!p){p=document.createElement("p");p.className="derr";p.setAttribute("role","alert");$("dlg-body").appendChild(p);}p.textContent=msg;}

async function editUnit(){
  const u=S.unit,bands=Object.keys((S.gallery||{}).grade_bands||{});
  openDlg("Edit unit",'<form id="f-unit"><div class="fld"><label class="flabel" for="eu-title">Unit name</label><input id="eu-title" maxlength="160" value="'+esc(u.title)+'"></div>'+
    '<div class="fld"><label class="flabel" for="eu-course">Course</label><select id="eu-course"><option value="">No course</option>'+
    S.courses.map(c=>'<option value="'+c.key+'"'+(c.key===u.course_key?" selected":"")+'>'+esc(c.name)+' ('+esc(c.grades)+')</option>').join("")+'</select></div>'+
    '<div class="fld"><label class="flabel" for="eu-band">Grade band</label><select id="eu-band">'+bands.map(b=>'<option value="'+b+'"'+(b===u.grade_band?" selected":"")+'>'+bandLabel(b)+'</option>').join("")+'</select></div>'+
    '<div class="dactions"><button type="button" class="btn-quiet" data-close>Cancel</button><button type="submit" class="btn-primary">Save</button></div></form>');
  $("f-unit").onsubmit=async ev=>{ev.preventDefault();const title=$("eu-title").value.trim();if(!title)return dlgError("Give the unit a name.");
    const body={title,course_key:$("eu-course").value,grade_band:$("eu-band").value};
    try{await api("PATCH","/api/prep/units/"+u.id,body);Object.assign(u,body);closeDlg();renderUnit();fillBands();}catch(e){dlgError(e.message);}};
}

// Add a source: a book (full text or outline only), a passage, a Living Library item, an upload or a link.
$("add-source").addEventListener("click",()=>addSource("book"));
function addSource(tab){
  const tabs=[["book","Book"],["passage","Passage"],["library","Living Library"]].concat(S.unit?[["upload","Upload"],["link","Link"]]:[]);
  openDlg("Add a source",'<div class="dtabs" role="tablist">'+tabs.map(([k,l])=>'<button type="button" role="tab" data-stab="'+k+'" aria-selected="'+(k===tab)+'">'+l+'</button>').join("")+'</div><div id="stab" role="tabpanel"></div>');
  $("dlg-body").querySelectorAll("[data-stab]").forEach(b=>b.onclick=()=>{$("dlg-body").querySelectorAll("[data-stab]").forEach(x=>x.setAttribute("aria-selected",String(x===b)));sourceTab(b.dataset.stab);});
  sourceTab(tab);
}
async function addRef(kind,ref,label){
  if(!S.unit){S.quickSources.push({kind,ref,label});closeDlg();renderUnit();Shell.toast("Added “"+label+"”");return;}
  try{const d=await api("POST","/api/prep/units/"+S.unit.id+"/sources",{kind,ref,label});S.unit.sources.push(d.source);closeDlg();renderUnit();Shell.toast("Added “"+label+"”");}
  catch(e){dlgError(e.message);}
}
function sourceTab(tab){
  const box=$("stab");
  if(tab==="book"){
    box.innerHTML='<p class="dhelp">Reading Room books give drafts their full text. Works marked “Outline only” are school texts Exegetica doesn\'t have yet: drafts get their contents and what each part covers.</p>'+
      '<label class="flabel" for="bk-q">Find a book</label><input id="bk-q" type="search" autocomplete="off" placeholder="Title, author, or course"><ul class="dres" id="bk-res"></ul>';
    let t=null;$("bk-q").oninput=()=>{clearTimeout(t);t=setTimeout(()=>bookSearch($("bk-q").value.trim()),250);};$("bk-q").focus();
  }else if(tab==="passage"){
    box.innerHTML='<form id="f-pass"><div class="fld"><label class="flabel" for="ps-ref">Passage</label><input id="ps-ref" autocomplete="off" placeholder="John 7:14-24"></div>'+
      '<div class="fld"><label class="flabel" for="ps-tr">Translation</label><select id="ps-tr"><option>ESV</option><option>KJV</option><option>BSB</option><option>WEB</option><option>ASV</option></select></div>'+
      '<div class="dactions"><button type="submit" class="btn-primary">Add passage</button></div></form>';
    $("ps-ref").focus();
    $("f-pass").onsubmit=ev=>{ev.preventDefault();const ref=$("ps-ref").value.trim();if(!/\d/.test(ref))return dlgError("Give a book and chapter, such as John 7:14-24.");
      addRef("passage",{ref,translation:$("ps-tr").value},ref+" ("+$("ps-tr").value+")");};
  }else if(tab==="library"){
    box.innerHTML='<p class="dhelp">Videos, podcasts and books on your Living Library shelf. A video or podcast brings its transcript and the excerpts you saved.</p><label class="flabel" for="lb-q">Filter your shelf</label><input id="lb-q" type="search" autocomplete="off"><ul class="dres" id="lb-res"><li class="empty-line">Loading your shelf…</li></ul>';
    fetch("/api/library/shelf").then(r=>r.json()).then(d=>{const items=d.items||[];
      const draw=q=>{const L=items.filter(it=>!q||(it.title+" "+it.sub).toLowerCase().includes(q.toLowerCase()));
        $("lb-res").innerHTML=L.length?L.map(it=>'<li><button type="button" data-lib="'+it.id+'"><span class="d-t">'+esc(it.title)+'</span><span class="d-s">'+esc([it.type,it.sub].filter(Boolean).join(" · "))+'</span></button></li>').join(""):
          '<li class="empty-line">'+(items.length?"Nothing on your shelf matches.":'Your shelf is empty. Add videos, podcasts and books in the <a href="/library">Living Library</a> first.')+'</li>';
        $("lb-res").querySelectorAll("[data-lib]").forEach(b=>b.onclick=()=>{const it=items.find(x=>x.id===b.dataset.lib);addRef("library",{item_id:it.id},it.title);});};
      draw("");$("lb-q").oninput=()=>draw($("lb-q").value.trim());
    }).catch(()=>{$("lb-res").innerHTML='<li class="empty-line">Your shelf didn\'t load. Try again.</li>';});
  }else if(tab==="upload"){
    box.innerHTML='<form id="f-up"><p class="dhelp">Your own handouts, notes or a department PDF. Exegetica reads the text now and keeps it encrypted, for your drafts only.</p>'+
      '<div class="fld"><label class="flabel" for="up-file">File (PDF, Word, EPUB or text, up to 15 MB)</label><input id="up-file" type="file" accept=".pdf,.docx,.txt,.md,.epub"></div>'+
      '<div class="fld"><label class="flabel" for="up-label">Name (optional)</label><input id="up-label" maxlength="200" placeholder="The file\'s name"></div>'+
      '<div class="dactions"><button type="submit" class="btn-primary" id="up-go">Upload</button></div></form>';
    $("f-up").onsubmit=async ev=>{ev.preventDefault();const f=$("up-file").files[0];if(!f)return dlgError("Choose a file.");
      const fd=new FormData();fd.append("file",f);fd.append("label",$("up-label").value.trim());$("up-go").disabled=true;$("up-go").textContent="Reading the file…";
      try{const r=await fetch("/api/prep/units/"+S.unit.id+"/upload",{method:"POST",body:fd});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||"That upload didn't work.");
        S.unit.sources.push(d.source);closeDlg();renderUnit();Shell.toast("Added “"+d.source.label+"”");}
      catch(e){dlgError(e.message);$("up-go").disabled=false;$("up-go").textContent="Upload";}};
  }else if(tab==="link"){
    box.innerHTML='<form id="f-link"><p class="dhelp">An article or an online PDF. Exegetica reads it now and keeps the text encrypted, for your drafts only. Videos and podcasts go in the Living Library, so their transcripts come with them.</p>'+
      '<div class="fld"><label class="flabel" for="ln-url">Web address</label><input id="ln-url" type="url" autocomplete="off" placeholder="https://"></div>'+
      '<div class="dactions"><button type="submit" class="btn-primary" id="ln-go">Add link</button></div></form>';
    $("ln-url").focus();
    $("f-link").onsubmit=async ev=>{ev.preventDefault();const url=$("ln-url").value.trim();if(!/^https?:\/\//.test(url))return dlgError("Give a full address, starting with https://");
      $("ln-go").disabled=true;$("ln-go").textContent="Reading the page…";
      try{const d=await api("POST","/api/prep/units/"+S.unit.id+"/link",{url});S.unit.sources.push(d.source);closeDlg();renderUnit();Shell.toast("Added “"+d.source.label+"”");}
      catch(e){dlgError(e.message);$("ln-go").disabled=false;$("ln-go").textContent="Add link";}};
  }
}
async function bookSearch(q){
  const out=$("bk-res");if(!out)return;if(q.length<2){out.innerHTML="";return;}
  out.innerHTML='<li class="empty-line">Searching…</li>';
  try{
    const [b,o]=await Promise.all([api("GET","/api/prep/books?q="+encodeURIComponent(q)),api("GET","/api/prep/outlines?q="+encodeURIComponent(q))]);
    const books=(b.results||[]).map(x=>'<li><button type="button" data-book="'+esc(x.slug)+'" data-title="'+esc(x.title)+'"><span class="d-t">'+esc(x.title)+'</span><span class="d-s">'+esc([x.author,"full text, "+x.access].filter(Boolean).join(" · "))+'</span></button></li>');
    const year=e=>{const m=String(e||"").match(/(19|20)\d\d(?:[/-](19|20)?\d\d)?/);return m?m[0]:"";};
    const outs=(o.results||[]).map(x=>'<li><button type="button" data-outline="'+esc(x.key)+'"><span class="d-t">'+esc(x.title)+' <span class="badge outline">Outline only</span></span><span class="d-s">'+esc([year(x.edition),x.courses.join(", ")].filter(Boolean).join(" · "))+'</span></button></li>');
    if($("bk-q").value.trim()!==q)return;
    out.innerHTML=(outs.concat(books).join(""))||'<li class="empty-line">No book matches. The Reading Room holds the school\'s copies and public-domain books; other school texts appear here once they have an outline.</li>';
    out.querySelectorAll("[data-book]").forEach(btn=>btn.onclick=()=>chooseCoverage({slug:btn.dataset.book,title:btn.dataset.title}));
    out.querySelectorAll("[data-outline]").forEach(btn=>btn.onclick=()=>{const x=(o.results||[]).find(r=>r.key===btn.dataset.outline);choosePartsNew(x);});
  }catch(e){out.innerHTML='<li class="empty-line">'+esc(e.message)+'</li>';}
}
async function bookToc(slug){const d=await fetch("/api/books/"+encodeURIComponent(slug)).then(r=>r.json());return (d.toc||[]).map(c=>({n:c.section_number,title:c.title}));}
function coverageForm(toc,current){
  return '<div class="fld"><label class="flabel" for="cv-sel">How far has the class read?</label><select id="cv-sel"><option value="">The whole book (no limit)</option>'+
    toc.map(c=>'<option value="'+c.n+'"'+(current===c.n?" selected":"")+'>Through '+esc(c.title||("section "+c.n))+'</option>').join("")+'</select></div>'+
    '<p class="dhelp">Drafts ask only about what the class has read, and keep later events out of what students see.</p>';}
function coverRef(slug,toc,n){const c=toc.find(x=>x.n===n);return n?{slug,coverage:{through:n},through_title:c?c.title:""}:{slug,coverage:{}};}
async function chooseCoverage(book){
  openDlg("Add “"+book.title+"”",'<p class="empty-line">Loading its contents…</p>');
  let toc=[];try{toc=await bookToc(book.slug);}catch(e){}
  openDlg("Add “"+book.title+"”",'<form id="f-cov">'+coverageForm(toc,null)+'<div class="dactions"><button type="button" class="btn-quiet" data-back>Back</button><button type="submit" class="btn-primary">Add book</button></div></form>');
  $("dlg-body").querySelector("[data-back]").onclick=()=>addSource("book");
  $("f-cov").onsubmit=ev=>{ev.preventDefault();const n=parseInt($("cv-sel").value,10);addRef("book",coverRef(book.slug,toc,n),book.title);};
}
async function coverDialog(s){
  openDlg("How far has the class read?",'<p class="empty-line">Loading its contents…</p>');
  let toc=[];try{toc=await bookToc(s.ref.slug);}catch(e){}
  openDlg("How far has the class read?",'<form id="f-cov"><p class="dhelp">'+esc(s.label)+'</p>'+coverageForm(toc,(s.ref.coverage||{}).through)+'<div class="dactions"><button type="button" class="btn-quiet" data-close>Cancel</button><button type="submit" class="btn-primary">Save</button></div></form>');
  $("f-cov").onsubmit=async ev=>{ev.preventDefault();const n=parseInt($("cv-sel").value,10);const ref=coverRef(s.ref.slug,toc,n);
    if(S.unit){try{await api("PATCH","/api/prep/sources/"+s.id,{kind:"book",ref});}catch(e){return dlgError(e.message);}}
    s.ref=ref;closeDlg();renderUnit();};
}
function partsForm(parts,chosen){return '<p class="dhelp">Leave every box clear to give drafts the whole outline.</p><div class="dchecks">'+
  parts.map((p,i)=>'<label><input type="checkbox" value="'+i+'"'+(chosen.includes(p)?" checked":"")+'> '+esc(p)+'</label>').join("")+'</div>';}
function choosePartsNew(x){
  openDlg("Add “"+x.title+"”",'<form id="f-parts">'+partsForm(x.parts,[])+'<div class="dactions"><button type="button" class="btn-quiet" data-back>Back</button><button type="submit" class="btn-primary">Add outline</button></div></form>');
  $("dlg-body").querySelector("[data-back]").onclick=()=>addSource("book");
  $("f-parts").onsubmit=ev=>{ev.preventDefault();const parts=[...$("f-parts").querySelectorAll("input:checked")].map(c=>x.parts[+c.value]);addRef("outline",{key:x.key,parts},x.title);};
}
async function partsDialog(s){
  let x=null;try{const d=await api("GET","/api/prep/outlines?q="+encodeURIComponent(s.label));x=(d.results||[]).find(r=>r.key===s.ref.key);}catch(e){}
  if(!x){Shell.toast("That outline didn't load. Try again.");return;}
  openDlg("Choose parts",'<form id="f-parts"><p class="dhelp">'+esc(s.label)+'</p>'+partsForm(x.parts,s.ref.parts||[])+'<div class="dactions"><button type="button" class="btn-quiet" data-close>Cancel</button><button type="submit" class="btn-primary">Save</button></div></form>');
  $("f-parts").onsubmit=async ev=>{ev.preventDefault();const ref={key:s.ref.key,parts:[...$("f-parts").querySelectorAll("input:checked")].map(c=>x.parts[+c.value])};
    if(S.unit){try{await api("PATCH","/api/prep/sources/"+s.id,{kind:"outline",ref});}catch(e){return dlgError(e.message);}}
    s.ref=ref;closeDlg();renderUnit();};
}

// Objectives: one search over the standards, each pick kept with its anchors.
$("add-obj").addEventListener("click",()=>{
  openDlg("Add an objective",'<p class="dhelp">Search the standards by subject, topic or the words of an objective. Pick a topic to see its objectives.</p><label class="flabel" for="ob-q">Search the standards</label><input id="ob-q" type="search" autocomplete="off" placeholder="For example: Feast of Tabernacles, percent change, theme"><ul class="dres" id="ob-res"></ul>');
  let t=null;$("ob-q").oninput=()=>{clearTimeout(t);t=setTimeout(()=>objSearch($("ob-q").value.trim()),250);};
});
async function objSearch(q){const out=$("ob-res");if(q.length<3){out.innerHTML="";return;}
  try{const d=await api("GET","/api/standards/search?q="+encodeURIComponent(q));if($("ob-q").value.trim()!==q)return;
    const rs=(d.results||[]).filter(r=>r.level==="objective"||r.level==="sub-topic").slice(0,14);
    out.innerHTML=rs.map((r,i)=>'<li><button type="button" data-ob="'+i+'"><span class="d-t">'+(r.level==="objective"?"":"Topic: ")+esc(r.label)+'</span><span class="d-s">'+esc(r.path.join(" › "))+(r.grade?" · grade "+r.grade:"")+'</span></button></li>').join("")||'<li class="empty-line">No standard matches. Try fewer or plainer words.</li>';
    out.querySelectorAll("[data-ob]").forEach(b=>b.onclick=()=>{const r=rs[+b.dataset.ob];r.level==="objective"?pickObjective(r.ids.sub_topic,r.ids.objective,r.path):subtopicObjectives(r);});
  }catch(e){out.innerHTML='<li class="empty-line">'+esc(e.message)+'</li>';}}
async function subtopicObjectives(r){
  const d=await api("GET","/api/standards/objectives?sub_topic="+encodeURIComponent(r.ids.sub_topic)).catch(()=>({objectives:[]}));
  const os=d.objectives||[];
  $("ob-res").innerHTML='<li><button type="button" data-obback><span class="d-t">‹ Back to the search</span></button></li>'+os.map((o,i)=>'<li><button type="button" data-oo="'+i+'"><span class="d-t">'+esc(o.t)+'</span><span class="d-s">'+esc(o.id)+(o.g!=null?" · grade "+o.g:"")+'</span></button></li>').join("");
  $("ob-res").querySelector("[data-obback]").onclick=()=>objSearch($("ob-q").value.trim());
  $("ob-res").querySelectorAll("[data-oo]").forEach(b=>b.onclick=()=>addObjective(os[+b.dataset.oo],r.path.concat(r.label)));
}
async function pickObjective(subtopic,id,path){
  const d=await api("GET","/api/standards/objectives?sub_topic="+encodeURIComponent(subtopic)).catch(()=>({objectives:[]}));
  const o=(d.objectives||[]).find(x=>x.id===id);if(!o)return dlgError("That objective didn't load. Try again.");addObjective(o,path);}
function addObjective(o,path){
  if(S.unit.objectives.some(x=>x.id===o.id)){closeDlg();return;}
  S.unit.objectives.push({id:o.id,t:o.t||o.text,g:o.g,c:o.c,a:o.a||o.anchors||{},path:(path||[]).join(" › ")});
  closeDlg();saveObjectives();Shell.toast("Added "+o.id);}

// ---- the Make panel: the gallery of kinds, then the chosen kind's sheet ----
let favs=[];try{favs=JSON.parse(localStorage.getItem("exeg-prep-favs")||"[]");}catch(e){}
function renderKinds(){
  const q=$("kindsearch").value.trim().toLowerCase(),box=$("kinds");if(!S.gallery)return;
  const match=k=>!q||(k.name+" "+k.definition+" "+(k.aka||[]).join(" ")+" "+k.variants.map(v=>v.label).join(" ")).toLowerCase().includes(q);
  const row=k=>'<div class="kind"><button type="button" class="k-open" data-kind="'+k.id+'"><span class="k-n">'+esc(k.name)+(k.for_teacher?'<span class="k-t">for you</span>':"")+'</span><span class="k-d">'+esc(k.definition)+'</span></button>'+
    '<button type="button" class="fav" data-fav="'+k.id+'" aria-pressed="'+favs.includes(k.id)+'" aria-label="Favourite: '+esc(k.name)+'">'+ICON.star+'</button></div>';
  let html="";
  if(q){   // a search ranks the kinds named for it above those that only mention it
    const score=k=>{const n=k.name.toLowerCase();return n.startsWith(q)?0:n.includes(q)?1:(k.aka||[]).join(" ").toLowerCase().includes(q)?2:k.variants.map(v=>v.label).join(" ").toLowerCase().includes(q)?3:4;};
    const all=S.gallery.groups.flatMap(g=>g.kinds).filter(match).sort((a,b)=>score(a)-score(b));
    if(all.length)html='<section class="kgroup"><h3>'+plural(all.length,"match")+'</h3>'+all.map(row).join("")+'</section>';
  }else{
    const fk=favs.map(kindOf).filter(Boolean);
    if(fk.length)html+='<section class="kgroup"><h3>Your favourites</h3>'+fk.map(row).join("")+'</section>';
    for(const g of S.gallery.groups)html+='<section class="kgroup"><h3>'+esc(g.label)+'</h3>'+g.kinds.map(row).join("")+'</section>';
  }
  box.innerHTML=html||'<p class="knone">No kind matches “'+esc(q)+'”. Try a plainer word, such as quiz, guide or chart.</p>';
}
$("kindsearch").addEventListener("input",renderKinds);
$("kinds").addEventListener("click",e=>{
  const f=e.target.closest("[data-fav]");
  if(f){const id=f.dataset.fav;favs=favs.includes(id)?favs.filter(x=>x!==id):favs.concat(id);try{localStorage.setItem("exeg-prep-favs",JSON.stringify(favs));}catch(err){}renderKinds();
    const again=$("kinds").querySelector('[data-fav="'+id+'"]');if(again)again.focus();return;}
  const k=e.target.closest("[data-kind]");if(k)openKind(k.dataset.kind);
});
function fillBands(){const sel=$("k-band"),bands=Object.keys((S.gallery||{}).grade_bands||{});
  sel.innerHTML=bands.map(b=>'<option value="'+b+'">'+bandLabel(b)+'</option>').join("");sel.value=(S.unit&&S.unit.grade_band)||"secondary";}
function openKind(id){
  const k=kindOf(id);if(!k)return;S.kind=k;S.settings={variant:null,item_types:[],length:"standard"};
  $("gallery").hidden=true;$("sheet").hidden=false;
  $("k-name").textContent=k.name;$("k-def").textContent=k.definition+(k.use_when?" "+k.use_when:"");
  $("k-structure").innerHTML=k.structure.map(s=>"<li>"+esc(s)+"</li>").join("");
  $("f-variant").hidden=!k.variants.length;
  $("k-variants").innerHTML=k.variants.map(v=>'<button type="button" role="radio" aria-checked="false" data-var="'+esc(v.id)+'">'+esc(v.label)+'</button>').join("");
  $("f-items").hidden=!k.item_types.length;
  $("k-items").innerHTML=k.item_types.map(t=>'<button type="button" aria-pressed="false" data-item="'+t.id+'">'+esc(t.label)+'</button>').join("");
  $("k-length").innerHTML=(S.gallery.lengths||[]).map(l=>'<button type="button" role="radio" aria-checked="'+(l.id==="standard")+'" class="'+(l.id==="standard"?"on":"")+'" data-len="'+l.id+'">'+esc(l.label)+'</button>').join("");
  fillBands();updateDraws();$("sheet-back").focus();
}
$("sheet-back").addEventListener("click",()=>{$("sheet").hidden=true;$("gallery").hidden=false;const b=$("kinds").querySelector('[data-kind="'+(S.kind||{}).id+'"]');(b||$("kindsearch")).focus();});
$("k-variants").addEventListener("click",e=>{const b=e.target.closest("[data-var]");if(!b)return;const on=b.getAttribute("aria-checked")!=="true";
  $("k-variants").querySelectorAll("button").forEach(x=>x.setAttribute("aria-checked","false"));b.setAttribute("aria-checked",String(on));S.settings.variant=on?b.dataset.var:null;});
$("k-items").addEventListener("click",e=>{const b=e.target.closest("[data-item]");if(!b)return;const on=b.getAttribute("aria-pressed")!=="true";b.setAttribute("aria-pressed",String(on));
  S.settings.item_types=[...$("k-items").querySelectorAll('[aria-pressed="true"]')].map(x=>x.dataset.item);});
$("k-length").addEventListener("click",e=>{const b=e.target.closest("[data-len]");if(!b)return;
  $("k-length").querySelectorAll("button").forEach(x=>{const on=x===b;x.classList.toggle("on",on);x.setAttribute("aria-checked",String(on));});S.settings.length=b.dataset.len;});
function updateDraws(){
  const el=$("k-draws");if(!el)return;const srcs=S.unit?S.unit.sources:S.quickSources;const objs=S.unit?S.unit.objectives.length:0;
  const names=srcs.map(s=>s.label);let t=names.length?"Draws on "+(names.length>3?names.slice(0,3).join(", ")+" and "+(names.length-3)+" more":names.join(", ")):"No sources yet: the draft uses the study tools"+(objs?" and the objectives":"")+".";
  if(names.length&&objs)t+=", aimed at "+plural(objs,"objective");el.textContent=names.length?t+".":t;}
$("open-make").addEventListener("click",openMake);$("ph-make").addEventListener("click",openMake);
$("close-make").addEventListener("click",closeMake);
function openMake(){if(window.matchMedia("(max-width:900px)").matches){setTab("make");}else{app.classList.add("make-open");}($("sheet").hidden?$("kindsearch"):$("sheet-back")).focus();}
function closeMake(){if(!app.classList.contains("make-open"))return;app.classList.remove("make-open");$("open-make").focus();}
function setTab(t){app.dataset.tab=t;$("tabbar").querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.tab===t)));window.scrollTo(0,0);}
$("tabbar").addEventListener("click",e=>{const b=e.target.closest("[data-tab]");if(b)setTab(b.dataset.tab);});

// ---- the document: paper / teacher-student / view-edit / versions / change it / pdf ----
const paper=$("paper"),editor=$("editor"),placeholder=$("placeholder"),paperwrap=$("paperwrap"),modrow=$("modrow"),tools=$("tools");
function slug(){const t=$("outtitle").textContent||"resource";return t.replace(/[^\w \-]/g,"").slice(0,60).trim().replace(/\s+/g,"_");}
function shown(){return audience==="student"?studentCopy(rawDoc):rawDoc;}
// The credit line (Adam, 2026-11-08: an option at download). It ends the PDF and the .md file, shows at the
// foot of the document while on, and the teacher's choice is kept in this browser.
const CREDIT="Drafted with Exegetica from its library's sources and reviewed by the teacher.";
const creditBox=$("credit");
try{const v=localStorage.getItem("exeg-credit");creditBox.checked=v===null?true:v==="1";}catch(e){creditBox.checked=true;}
creditBox.addEventListener("change",()=>{try{localStorage.setItem("exeg-credit",creditBox.checked?"1":"0");}catch(e){}if(rawDoc)render();});
function withCredit(text){return creditBox.checked?text.replace(/\s*$/,"")+"\n\n---\n\n*"+CREDIT+"*\n":text;}
function render(){
  paper.innerHTML=md(shown());
  if(window.Passage)Passage.linkRefs(paper);   // a reference in the document opens the passage beside it
  paper.dataset.band=docBand||"secondary";
  if(creditBox.checked){const p=document.createElement("p");p.className="credit";p.textContent=CREDIT;paper.appendChild(p);}
  printReady();
}
// The printed faces (fonts/doc.css) load only when something uses them, and the print dialog will not wait
// for them. So they load as soon as a document shows, and the PDF button waits until they have.
function printReady(){
  const faces=['400 1em "EB Garamond"','italic 400 1em "EB Garamond"','600 1em "EB Garamond"','600 1em "Fraunces"'];
  return Promise.all(faces.map(f=>document.fonts.load(f).catch(()=>[]))).then(()=>document.fonts.ready);
}
// Every printed page carries the document's title and copy (rule H2): the page's margin boxes, written
// just before printing because the title changes with each document.
function setPrintHead(){
  let st=document.getElementById("print-head");
  if(!st){st=document.createElement("style");st.id="print-head";document.head.appendChild(st);}
  const q=s=>'"'+String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/\s+/g," ")+'"';
  let title=($("outtitle").textContent||"Resource").trim();if(title.length>60)title=title.slice(0,59)+"…";
  const copy=audience==="student"?"Student copy":"Teacher copy";
  // the page's margin boxes do not see the tokens, so they name the faces (the same as --sans and --doc)
  st.textContent="@page{@top-left{content:"+q(title)+";font:8pt 'Public Sans',sans-serif;color:#555}"+
    "@top-right{content:"+q(copy)+";font:8pt 'Public Sans',sans-serif;color:#555}"+
    "@bottom-center{content:counter(page);font:10pt 'EB Garamond',serif;color:#333}}"+
    "@page:first{@top-left{content:none}@top-right{content:none}}";
}
window.addEventListener("beforeprint",setPrintHead);
function setOutButtons(on){$("download").disabled=!on;$("copy").disabled=!on;$("pdf").disabled=!on;
  const student=$("aud").querySelector('[data-v=student]');student.disabled=!hasTeacherPart(rawDoc);
  student.title=student.disabled?"This resource has no teacher-only part, so both copies are the same.":"";
  $("versions").disabled=!(S.res&&S.res.versions&&S.res.versions.length);}
function segOn(seg,pred){Array.from($(seg).children).forEach(x=>{const on=pred(x);x.classList.toggle("on",on);x.setAttribute("aria-pressed",String(on));});}
function showDoc(){placeholder.hidden=true;paperwrap.hidden=mode==="edit";editor.hidden=mode!=="edit";modrow.hidden=!S.res||!!S.viewing;}
function clearDoc(){rawDoc="";S.savedDoc="";S.viewing=null;mode="view";audience="teacher";segOn("aud",x=>x.dataset.v==="teacher");segOn("mode",x=>x.dataset.m==="view");
  paperwrap.hidden=true;editor.hidden=true;modrow.hidden=true;$("oldver").hidden=true;tools.innerHTML="";$("report").hidden=true;
  placeholder.hidden=false;$("outtitle").textContent=S.unit?S.unit.title:"Quick resource";setOutButtons(false);
  const has=(S.unit?S.unit.resources.length:0);
  $("ph-title").textContent=has?"Open a resource, or make another":"Make your first resource";
  $("ph-body").textContent=has?"Your resources are listed in the unit. Pick a kind under Make for a new one: it draws on this unit's sources and objectives.":
    "Pick a kind under Make. The draft draws on "+(S.unit?"this unit's":"the")+" sources"+(S.unit?" and objectives":"")+", and it's saved with every change you make.";
  renderUnit();}
$("aud").addEventListener("click",e=>{const b=e.target.closest("button");if(!b||b.disabled)return;
  if(mode==="edit"){leaveEdit();}
  audience=b.dataset.v;segOn("aud",x=>x===b);render();});
function syncMode(){segOn("mode",x=>x.dataset.m===mode);showDoc();
  if(mode==="edit"){editor.value=rawDoc;editor.focus();}else render();}
$("mode").addEventListener("click",e=>{const b=e.target.closest("button");if(!b||S.busy)return;
  if(b.dataset.m==="edit"&&S.viewing)return Shell.toast("Bring this version back first, or go back to the newest, to edit it.");
  if(b.dataset.m==="view"&&mode==="edit"){leaveEdit();return;}mode=b.dataset.m;syncMode();});
editor.addEventListener("input",()=>{rawDoc=editor.value;});
function leaveEdit(){rawDoc=editor.value;mode="view";syncMode();saveEditNow(false);}
// A hand edit is saved as a version when the teacher goes back to View (and on leaving the page).
async function saveEditNow(leaving){
  if(!S.res||S.viewing||rawDoc===S.savedDoc||!rawDoc.trim())return;
  const doc=rawDoc;
  if(leaving){fetch("/api/prep/resources/"+S.res.id+"/versions",{method:"POST",keepalive:true,headers:{"Content-Type":"application/json"},body:JSON.stringify({origin:"edit",document:doc})});return;}
  try{const d=await api("POST","/api/prep/resources/"+S.res.id+"/versions",{origin:"edit",document:doc});S.savedDoc=doc;await reloadVersions();Shell.toast("Saved your edits as version "+d.n);}
  catch(e){Shell.toast("Your edits weren't saved: "+e.message);}
}

// The source check sent after a finished document (webapp/citations.py). It reports what was found where,
// and never holds up the download.
function showReport(r){
  const el=$("report"),q=s=>"“"+esc(s)+"”";
  if(!r){el.hidden=true;el.innerHTML="";return;}
  const lines=[];
  if(!r.references&&!r.quotations){lines.push("No Scripture references or quotations to check.");}
  else{
    let refs=r.references+" Scripture reference"+(r.references===1?"":"s")+" checked against the bundled Bible.";
    if((r.missing_references||[]).length)refs+=" Not found there: "+r.missing_references.map(esc).join(", ")+".";
    lines.push(refs);
    let quo=r.quotations+" quotation"+(r.quotations===1?"":"s")+" checked.";
    const nf=r.quotations_not_found||[];
    if(nf.length)quo+=" Not found in this run's sources or the bundled Bible text: "+nf.map(q).join(", ")+".";
    lines.push(quo);
  }
  if(r.quotations)lines.push("A quotation not found here may still be accurate, such as ESV wording, which Exegetica does not store.");
  el.innerHTML="<h3>Source check</h3>"+lines.map(l=>"<p>"+l+"</p>").join("");el.hidden=false;
}
function note(text){const n=document.createElement("div");n.className="tool-chip";n.textContent=text;tools.appendChild(n);}
function drewOn(list){if(list&&list.length)note("Drew on: "+list.join("; "));}
async function streamInto(url,body,onEvent){
  tools.innerHTML="";const chips=Shell.chips(tools),status=Shell.status(tools);status.set("studying");
  paper.innerHTML="<span class='caret'></span>";setOutButtons(false);
  $("report").hidden=true;$("report").innerHTML="";
  function live(){if(mode==="view")paper.innerHTML=md(shown())+"<span class='caret'></span>";}
  let ok=true;   // false on an error, a dropped connection, or a cut-off reply
  let started=false;   // the document's first text fades in; later pauses for a lookup only show the line
  try{
    const resp=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if(!resp.ok||!resp.body){let msg="";try{msg=(await resp.json()).error;}catch(e){}throw new Error(msg||("the server answered "+resp.status));}
    const rd=resp.body.getReader(),dec=new TextDecoder();let buf="";
    while(true){const {value,done}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});
      const fr=buf.split("\n\n");buf=fr.pop();
      for(const f of fr){const ln=f.split("\n").find(x=>x.startsWith("data:"));if(!ln)continue;const ev=JSON.parse(ln.slice(5).trim());
        if(ev.type==="text"){status.done(started?null:paper);started=true;rawDoc+=ev.text;live();}
        else if(ev.type==="status"){status.set(ev.stage,ev.words);}
        else if(ev.type==="tool_call"){chips.start(ev.name);}
        else if(ev.type==="tool_done"){chips.finish(ev.name,!!ev.error);}
        else if(ev.type==="start"){drewOn(ev.drew_on);(ev.notices||[]).forEach(note);}
        else if(ev.type==="notice"){status.done();note(ev.message);if(ev.incomplete){ok=false;S.lastNotice=ev.message;}}
        else if(ev.type==="error"){status.done();ok=false;rawDoc+="\n\n**Error:** "+ev.message;live();}
        else if(ev.type==="report"){showReport(ev);}
        else if(onEvent)onEvent(ev);
      }}
  }catch(e){ok=false;rawDoc+="\n\n**That didn't finish:** "+e.message;}
  status.done();
  if(mode==="view")render();else editor.value=rawDoc;
  setOutButtons(!!rawDoc.trim());
  return ok;
}

$("draft").addEventListener("click",draft);
async function draft(){
  if(S.busy||!S.kind)return;
  const k=S.kind;S.busy=true;$("draft").disabled=true;$("draft").textContent="Drafting…";
  const settings=Object.assign({},S.settings,{grade_band:$("k-band").value,brief:$("k-brief").value});
  const body={unit_id:S.unit?S.unit.id:null,format_id:k.id,settings,sources:S.unit?undefined:S.quickSources};
  S.res=null;S.viewing=null;$("oldver").hidden=true;docBand=settings.grade_band;
  $("outtitle").textContent=k.name.split(/ \/ | \(/)[0]+" · drafting";
  audience="teacher";mode="view";segOn("aud",x=>x.dataset.v==="teacher");segOn("mode",x=>x.dataset.m==="view");
  rawDoc="";S.lastNotice="";placeholder.hidden=true;paperwrap.hidden=false;editor.hidden=true;modrow.hidden=true;
  closeMake();setTab("doc");
  let saved=null;
  await streamInto("/api/prep/draft",body,ev=>{if(ev.type==="saved")saved=ev;});
  S.busy=false;$("draft").disabled=false;$("draft").textContent="Draft resource";
  if(saved){S.savedDoc=rawDoc;history.replaceState({},"",resPath(saved.resource_id));
    S.res={id:saved.resource_id,title:saved.title,format_id:k.id,settings,versions:[]};$("outtitle").textContent=saved.title;
    await reloadVersions();modrow.hidden=false;await refreshUnit();Shell.toast("Saved as version 1 of “"+saved.title+"”");
    if(!S.unit){S.quick.unshift({id:saved.resource_id,title:saved.title,format_id:k.id,latest:1,updated_at:new Date().toISOString()});}}
  else if(!rawDoc.trim()&&S.lastNotice){   // a cap or a closed run: say so where the document would be
    $("outtitle").textContent=k.name.split(/ \/ | \(/)[0];paperwrap.hidden=true;placeholder.hidden=false;
    $("ph-title").textContent="Not drafted";$("ph-body").textContent=S.lastNotice;}
  else $("outtitle").textContent=k.name.split(/ \/ | \(/)[0]+" (not saved)";
}

async function openResource(rid,n){
  if(S.busy)return;
  tools.innerHTML="";
  try{const d=await api("GET","/api/prep/resources/"+rid+(n?"?n="+n:""));S.res=d.resource;}
  catch(e){Shell.toast(e.message);go(resPath(null));return;}
  const v=S.res.version;S.viewing=null;rawDoc=v?v.document:"";S.savedDoc=rawDoc;docBand=(S.res.settings||{}).grade_band||"secondary";
  $("outtitle").textContent=S.res.title;audience="teacher";mode="view";segOn("aud",x=>x.dataset.v==="teacher");segOn("mode",x=>x.dataset.m==="view");
  $("oldver").hidden=true;showDoc();render();showReport(v&&v.report);if(v)drewOn(v.drew_on);setOutButtons(!!rawDoc.trim());renderUnit();
}
async function reloadVersions(){if(!S.res)return;try{const d=await api("GET","/api/prep/resources/"+S.res.id);S.res.versions=d.resource.versions;setOutButtons(!!rawDoc.trim());}catch(e){}}
function originWords(v){return v.origin==="draft"?"First draft":v.origin==="revise"?"Changed: “"+(v.instruction||"")+"”":v.origin==="restore"?(v.instruction||"Brought back"):"Your edits";}
$("versions").addEventListener("click",e=>{e.stopPropagation();const m=$("vmenu");if(!m.hidden){closeMenus();return;}
  const vs=S.res.versions||[],newest=vs.length?vs[0].n:0;
  m.innerHTML=vs.map(v=>'<button type="button" data-v="'+v.n+'"><span class="v-n">v'+v.n+'</span><span class="v-what">'+esc(originWords(v))+'</span>'+(v.n===newest?'<span class="v-now">newest</span>':"")+'<span class="v-when">'+when(v.created_at)+'</span></button>').join("");
  m.hidden=false;$("versions").setAttribute("aria-expanded","true");m.querySelector("button").focus();});
$("vmenu").addEventListener("click",async e=>{const b=e.target.closest("[data-v]");if(!b)return;const n=+b.dataset.v;closeMenus();await viewVersion(n);});
$("vmenu").addEventListener("keydown",e=>{const bs=[...$("vmenu").querySelectorAll("button")],i=bs.indexOf(document.activeElement);
  if(e.key==="ArrowDown"){e.preventDefault();bs[(i+1)%bs.length].focus();}if(e.key==="ArrowUp"){e.preventDefault();bs[(i-1+bs.length)%bs.length].focus();}});
async function viewVersion(n){
  if(mode==="edit")leaveEdit();
  const newest=S.res.versions[0].n;
  if(n===newest){await openResource(S.res.id);return;}
  let d;try{d=await api("GET","/api/prep/resources/"+S.res.id+"?n="+n);}catch(e){Shell.toast(e.message);return;}
  const v=d.resource.version;S.viewing=n;rawDoc=v.document;render();showReport(v.report);showDoc();
  const meta=S.res.versions.find(x=>x.n===n);
  $("oldver").innerHTML='<p>You\'re looking at version '+n+' ('+esc(originWords(meta).toLowerCase())+'), from '+when(meta.created_at)+'. The newest is version '+newest+'.</p>'+
    '<button type="button" class="btn-primary" id="restore">Bring back this version</button><button type="button" class="btn-quiet" id="to-newest">Back to the newest</button>';
  $("oldver").hidden=false;$("restore").onclick=()=>restore(n);$("to-newest").onclick=()=>openResource(S.res.id);$("restore").focus();
}
async function restore(n){
  try{const d=await api("POST","/api/prep/resources/"+S.res.id+"/versions",{origin:"restore",from_n:n});await openResource(S.res.id);
    Shell.toast("Brought back version "+n+" as version "+d.n);refreshUnit();}
  catch(e){Shell.toast(e.message);}
}

modrow.addEventListener("submit",async e=>{
  e.preventDefault();const instr=$("modin").value.trim();if(!instr||S.busy||!S.res||!rawDoc.trim())return;
  if(mode==="edit")leaveEdit();
  if(rawDoc!==S.savedDoc){await saveEditNow(false);if(rawDoc!==S.savedDoc)return;}
  S.busy=true;$("modbtn").disabled=true;$("modbtn").textContent="Changing…";
  const prev=rawDoc,prevReport=$("report").innerHTML;let saved=null;
  rawDoc="";const ok=await streamInto("/api/prep/revise",{resource_id:S.res.id,instruction:instr},ev=>{if(ev.type==="saved")saved=ev;});
  // Any failure or cut-off keeps the teacher's document exactly as it was, with its source check.
  if(!ok||!rawDoc.trim()||!saved){rawDoc=prev;render();setOutButtons(true);
    if(prevReport){$("report").innerHTML=prevReport;$("report").hidden=false;}
    note("The change didn't finish, so your resource was left as it was.");}
  else{S.savedDoc=rawDoc;$("modin").value="";await reloadVersions();refreshUnit();Shell.toast("Saved the change as version "+saved.n);}
  $("modbtn").textContent="Apply";$("modbtn").disabled=false;S.busy=false;
});

$("pdf").addEventListener("click",()=>{if(mode==="edit")leaveEdit();render();setPrintHead();printReady().then(()=>window.print());});
$("download").addEventListener("click",()=>{const blob=new Blob([withCredit(shown())],{type:"text/markdown"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=slug()+(audience==="student"?"_student":"")+".md";a.click();URL.revokeObjectURL(a.href);});
$("copy").addEventListener("click",()=>{navigator.clipboard&&navigator.clipboard.writeText(shown());$("copy").textContent="Copied";setTimeout(()=>$("copy").textContent="Copy",1200);});

load();
