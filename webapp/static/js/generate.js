/* The Prep Room · Exegetica page (templates/generate.html). The rail, theme and Need help now? come from static/js/shell.js. */
"use strict";
// ---- shared compact markdown renderer ----
function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
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

// ---- state ----
const $=id=>document.getElementById(id);
document.addEventListener("keydown",e=>{if(e.key==="Escape"){if(typeof closeResults==="function")closeResults();}});

// The account panel is static/js/settings.js. Bringing your own key is off for now, so the
// Prep Room runs on the server's own model (policy.BYOK).
let CFG={}, FORMATS=[], FMT={}, BANDS={}, TREE=null, RECS=[], busy=false, rawDoc="";
let srcMode="book", pickedBook=null, _bkTimer=null;   // two source modes: a book (live text) or academic-spine standards
function pcfg(id){return (CFG.providers||[]).find(p=>p.id===id)||{};}
function curProvider(){return window.AppSettings?AppSettings.provider():"anthropic";}
function curModel(){return window.AppSettings?AppSettings.model():"";}
function curKey(){return window.AppSettings?AppSettings.key():"";}
function needsKey(){return !(curProvider()==="anthropic"&&CFG.server_anthropic_key)&&!curKey();}
window.addEventListener("appsettings:changed",function(){updateKeyBanner();});

Promise.all([
  fetch("/api/config").then(r=>r.json()),
  fetch("/api/formats").then(r=>r.json()),
  fetch("/api/standards/tree").then(r=>r.json()),
]).then(([cfg,fmts,tree])=>{
  CFG=cfg;FORMATS=fmts.formats;BANDS=fmts.grade_bands;TREE=tree;
  FORMATS.forEach(f=>FMT[f.id]=f);
  Object.keys(BANDS).forEach(b=>{const o=document.createElement("option");o.value=b;o.textContent=b[0].toUpperCase()+b.slice(1);$("sel-band").appendChild(o);});
  $("sel-band").value="secondary";
  FORMATS.forEach(f=>{const o=document.createElement("option");o.value=f.id;o.textContent=f.name;$("sel-format").appendChild(o);});
  fmtChanged();
  (TREE.subjects||[]).forEach(s=>{const o=document.createElement("option");o.value=s.id;o.textContent=s.name;$("sel-subject").appendChild(o);});
  $("sel-subject").insertAdjacentHTML("afterbegin","<option value=''>Select…</option>");
  $("sel-subject").value="";
  // Opened from the standards page with ?standard=<sub-topic id>: start in standards mode at that sub-topic.
  const deep=new URLSearchParams(location.search).get("standard"),p=(deep||"").split(".");
  if(p.length>=4){srcMode="standard";applySrcMode();
    gotoLocation({subject:p[0],sub_subject:p.slice(0,2).join("."),topic:p.slice(0,3).join("."),
                  sub_topic:p.slice(0,4).join("."),objective:p.length>4?deep:null});}
  updateKeyBanner();
}).catch(()=>{console.error("backend unavailable");});

function updateKeyBanner(){const b=$("keybanner");if(needsKey()){b.style.display="block";b.textContent="Drafting isn't available right now.";}else b.style.display="none";refreshGen();}

// ---- format recommendations ----
function loadRecs(subSubjectId){if(!subSubjectId){$("recs").innerHTML="";RECS=[];return;}
  fetch("/api/recommend?sub_subject="+encodeURIComponent(subSubjectId)).then(r=>r.json()).then(d=>{
    RECS=d.recommended||[];const box=$("recs");box.innerHTML="";
    RECS.slice(0,8).forEach(id=>{const b=document.createElement("button");b.className="rec";b.textContent=(FMT[id]||{}).name||id;
      b.onclick=()=>{$("sel-format").value=id;fmtChanged();};box.appendChild(b);});
    fmtChanged();
  });}
$("sel-format").addEventListener("change",fmtChanged);
function fmtChanged(){const id=$("sel-format").value;$("fmtdef").textContent=(FMT[id]||{}).definition||"";
  Array.prototype.forEach.call($("recs").children,b=>b.classList.toggle("on",((FMT[[...FORMATS].find(f=>f.name===b.textContent)?.id]||{}).id||"")===id||b.textContent===(FMT[id]||{}).name));
  refreshGen();}

function refreshGen(){
  const srcOk = srcMode==="book" ? !!(pickedBook && $("sel-cover").value) : !!(curSubtopic && selectedObjectives().length);
  $("gen").disabled = !(srcOk && $("sel-format").value && !needsKey() && !busy);
  const n=$("gennote");
  if(busy){n.textContent="Drafting…";n.className="note";}
  else if(needsKey()){n.textContent="Drafting isn't available right now.";n.className="note warn";}
  else if(!srcOk){n.textContent = srcMode==="book" ? "Pick a book, coverage, and a format." : "Pick a standard, an objective, and a format.";n.className="note";}
  else if(srcMode==="book"){n.textContent="Ready. "+pickedBook.title+" · through ch "+$("sel-cover").value+" · "+((FMT[$("sel-format").value]||{}).name||"")+".";n.className="note";}
  else{n.textContent="Ready. "+selectedObjectives().length+" objective(s) · "+((FMT[$("sel-format").value]||{}).name||"")+".";n.className="note";}
  updateSummaries();
}

// ---- builder accordion (single-open; content discloses instead of nesting scrolls) ----
function openSec(name){document.querySelectorAll(".acc-sec").forEach(s=>s.classList.toggle("open",s.dataset.sec===name));}
document.querySelectorAll(".acc-h").forEach(h=>h.addEventListener("click",()=>{
  const sec=h.closest(".acc-sec"),willOpen=!sec.classList.contains("open");
  document.querySelectorAll(".acc-sec").forEach(s=>s.classList.remove("open"));
  if(willOpen)sec.classList.add("open");
}));
function bandLabel(){const s=$("sel-band"),o=s.options[s.selectedIndex];return o?o.textContent:"";}
function updateSummaries(){
  function set(id,txt,sec,done){const el=$(id);if(el)el.textContent=txt;const s=document.querySelector('.acc-sec[data-sec="'+sec+'"]');if(s)s.classList.toggle("done",!!done);}
  set("sum-book", pickedBook ? (pickedBook.title + ($("sel-cover").value ? " · through ch "+$("sel-cover").value : "")) : "None",
      "book", !!(pickedBook && $("sel-cover").value));
  const path=[curSubject&&curSubject.name,curSub&&curSub.name,curTopic&&curTopic.name,curSubtopic&&curSubtopic.name].filter(Boolean);
  const nobj=selectedObjectives().length;
  set("sum-standard",path.length?path[path.length-1]:"Not chosen","standard",!!curSubtopic);
  set("sum-objectives",nobj?nobj+" selected":"None","objectives",nobj>0);
  set("sum-format",(FMT[$("sel-format").value]||{}).name||"None","format",!!$("sel-format").value);
  set("sum-audience",bandLabel(),"audience",true);
}
$("sel-band").addEventListener("change",updateSummaries);

// ---- standards navigation (academic-spine source mode) ----
function opts(sel,items,label){sel.innerHTML="<option value=''>Select…</option>";items.forEach(it=>{const o=document.createElement("option");o.value=it.id;o.textContent=label(it);sel.appendChild(o);});sel.disabled=items.length===0;}
let curSubject=null,curSub=null,curTopic=null,curSubtopic=null;
function setCrumb(){const parts=[curSubject&&curSubject.name,curSub&&curSub.name,curTopic&&curTopic.name,curSubtopic&&curSubtopic.name].filter(Boolean);$("crumb").textContent=parts.join("  ›  ");updateSummaries();}
$("sel-subject").addEventListener("change",()=>{curSubject=TREE.subjects.find(s=>s.id===$("sel-subject").value)||null;
  opts($("sel-subsubject"),curSubject?curSubject.sub_subjects:[],x=>x.name);resetFrom("subsubject");
  if(curSubject)loadRecs(null);setCrumb();});
$("sel-subsubject").addEventListener("change",()=>{curSub=curSubject?curSubject.sub_subjects.find(x=>x.id===$("sel-subsubject").value):null;
  opts($("sel-topic"),curSub?curSub.topics:[],x=>x.name);resetFrom("topic");
  if(curSub)loadRecs(curSub.id);setCrumb();});
$("sel-topic").addEventListener("change",()=>{curTopic=curSub?curSub.topics.find(x=>x.id===$("sel-topic").value):null;
  opts($("sel-subtopic"),curTopic?curTopic.sub_topics:[],x=>x.name+" ("+x.objective_count+")");resetFrom("subtopic");setCrumb();});
$("sel-subtopic").addEventListener("change",()=>{curSubtopic=curTopic?curTopic.sub_topics.find(x=>x.id===$("sel-subtopic").value):null;loadObjectives();setCrumb();});
function resetFrom(level){const order=["subsubject","topic","subtopic"];const idx=order.indexOf(level);
  if(idx<=0){$("sel-topic").innerHTML="";$("sel-topic").disabled=true;curTopic=null;}
  if(idx<=1){$("sel-subtopic").innerHTML="";$("sel-subtopic").disabled=true;curSubtopic=null;}
  $("objs").innerHTML="<div class='empty'>Select a sub-topic to load objectives.</div>";refreshGen();}

// ---- fuzzy standards search ----
let _preselect=null,_stTimer=null,_sActive=-1,_sHits=[];
const stEl=$("stdsearch"),srEl=$("sresults");
function closeResults(){srEl.classList.remove("open");srEl.innerHTML="";_sActive=-1;_sHits=[];}
function fire(el){el.dispatchEvent(new Event("change"));}
function gotoLocation(ids){
  const sub=$("sel-subject");sub.value=ids.subject;if(sub.value!==ids.subject)return;fire(sub);
  if(ids.sub_subject){const e=$("sel-subsubject");e.value=ids.sub_subject;fire(e);}
  if(ids.topic){const e=$("sel-topic");e.value=ids.topic;fire(e);}
  if(ids.sub_topic){_preselect=ids.objective||null;const e=$("sel-subtopic");e.value=ids.sub_topic;fire(e);}
}
function chooseHit(i){const h=_sHits[i];if(!h)return;gotoLocation(h.ids);stEl.value=h.label;closeResults();}
function renderResults(hits){
  _sHits=hits;_sActive=-1;
  if(!hits.length){srEl.innerHTML="<div class='snone'>No matches. Try fewer or simpler words.</div>";srEl.classList.add("open");return;}
  srEl.innerHTML="";
  hits.forEach((h,i)=>{
    const it=document.createElement("button");it.type="button";it.className="sitem";
    const lvl=h.level==="sub-topic"?"Sub-topic":h.level.charAt(0).toUpperCase()+h.level.slice(1);
    const g=h.grade!=null?"<span class='si-g'>grade "+h.grade+"</span>":"";
    const path=(h.path||[]).length?"<div class='si-path'>"+esc(h.path.join("  ›  "))+"</div>":"";
    it.innerHTML="<div class='si-top'><span class='si-lvl "+h.level+"'>"+lvl+"</span><span class='si-lab'>"+esc(h.label)+"</span>"+g+"</div>"+path;
    it.onclick=()=>chooseHit(i);
    srEl.appendChild(it);
  });
  srEl.classList.add("open");
}
function runSearch(q){fetch("/api/standards/search?q="+encodeURIComponent(q)).then(r=>r.json())
  .then(d=>{if(stEl.value.trim()===q)renderResults(d.results||[]);}).catch(()=>{});}
stEl.addEventListener("input",()=>{clearTimeout(_stTimer);const q=stEl.value.trim();
  if(q.length<2){closeResults();return;}_stTimer=setTimeout(()=>runSearch(q),150);});
stEl.addEventListener("keydown",e=>{
  if(!srEl.classList.contains("open"))return;
  const items=srEl.querySelectorAll(".sitem");if(!items.length)return;
  if(e.key==="ArrowDown"){e.preventDefault();_sActive=Math.min(_sActive+1,items.length-1);}
  else if(e.key==="ArrowUp"){e.preventDefault();_sActive=Math.max(_sActive-1,0);}
  else if(e.key==="Enter"){e.preventDefault();if(_sActive>=0)chooseHit(_sActive);else if(items.length===1)chooseHit(0);return;}
  else if(e.key==="Escape"){closeResults();return;}
  else return;
  items.forEach((it,i)=>it.classList.toggle("active",i===_sActive));
  if(_sActive>=0)items[_sActive].scrollIntoView({block:"nearest"});
});
document.addEventListener("click",e=>{if(!e.target.closest(".searchbox"))closeResults();});

function loadObjectives(){const box=$("objs");if(!curSubtopic){box.innerHTML="<div class='empty'>Select a sub-topic.</div>";return;}
  box.innerHTML="<div class='empty'>Loading…</div>";
  fetch("/api/standards/objectives?sub_topic="+encodeURIComponent(curSubtopic.id)).then(r=>r.json()).then(d=>{
    const os=d.objectives||[];if(!os.length){box.innerHTML="<div class='empty'>No objectives.</div>";return;}
    box.innerHTML="";os.forEach(o=>{const lab=document.createElement("label");lab.className="obj";
      lab.innerHTML="<input type='checkbox' data-id='"+o.id+"'><span><span class='oid'>"+o.id+"</span> "+esc(o.t)+" <span class='og'>g"+o.g+"</span></span>";
      lab.querySelector("input").addEventListener("change",refreshGen);
      lab.__obj=o;box.appendChild(lab);});
    if(_preselect){const cb=box.querySelector("input[data-id='"+_preselect+"']");
      if(cb){cb.checked=true;const ob=cb.closest(".obj");if(ob)ob.scrollIntoView({block:"nearest"});}_preselect=null;}
    refreshGen();openSec("objectives");
  }).catch(()=>{box.innerHTML="<div class='empty'>Failed to load.</div>";});}
function selectedObjectives(){return Array.prototype.map.call($("objs").querySelectorAll("input:checked"),i=>i.closest(".obj").__obj).map(o=>({id:o.id,t:o.t,g:o.g,c:o.c}));}

// ---- source mode toggle: a book (live text) vs. academic-spine standards ----
function setNums(map){for(const k in map){const s=document.querySelector('.acc-sec[data-sec="'+k+'"] .acc-n');if(s)s.textContent=map[k];}}
function applySrcMode(){
  const book = srcMode==="book";
  $("stdsearchwrap").style.display = book ? "none" : "";
  document.querySelector('.acc-sec[data-sec="book"]').style.display = book ? "" : "none";
  document.querySelector('.acc-sec[data-sec="standard"]').style.display = book ? "none" : "";
  document.querySelector('.acc-sec[data-sec="objectives"]').style.display = book ? "none" : "";
  setNums(book ? {book:"1",format:"2",audience:"3"} : {standard:"1",objectives:"2",format:"3",audience:"4"});
  document.querySelectorAll(".srcbtn").forEach(b=>b.classList.toggle("on",b.dataset.src===srcMode));
  openSec(book ? "book" : "standard");
  refreshGen();
}
document.querySelectorAll(".srcbtn").forEach(b=>b.addEventListener("click",()=>{if(srcMode===b.dataset.src)return;srcMode=b.dataset.src;applySrcMode();}));
applySrcMode();   // set the initial mode (book) and its step layout

// ---- book picker (generation reads the book's live text at request time) ----
$("booksearch").addEventListener("input",()=>{clearTimeout(_bkTimer);const q=$("booksearch").value.trim();
  if(q.length<2){$("bookresults").classList.remove("open");$("bookresults").innerHTML="";return;}
  _bkTimer=setTimeout(()=>bookSearch(q),180);});
function bookSearch(q){fetch("/api/books?q="+encodeURIComponent(q)+"&limit=12").then(r=>r.json()).then(d=>{
  const box=$("bookresults");box.innerHTML="";
  (d.items||[]).forEach(b=>{const it=document.createElement("button");it.type="button";it.className="sitem";
    it.innerHTML="<div class='si-top'><span class='si-lab'>"+esc(b.title)+"</span></div>"
      +"<div class='si-path'>"+esc(b.author||"")+" · "+b.chapter_count+" ch</div>";
    it.onclick=()=>chooseBook(b);box.appendChild(it);});
  box.classList.toggle("open",(d.items||[]).length>0);}).catch(()=>{});}
function chooseBook(b){fetch("/api/books/"+encodeURIComponent(b.slug)).then(r=>r.json()).then(d=>{
  pickedBook={slug:b.slug,title:b.title,author:b.author,toc:d.toc||[]};
  $("booksearch").value=b.title;$("bookresults").classList.remove("open");$("bookresults").innerHTML="";
  const sel=$("sel-cover");sel.innerHTML="";
  (pickedBook.toc||[]).forEach(t=>{const o=document.createElement("option");o.value=t.section_number;
    o.textContent="Ch "+t.section_number+(t.title?": "+t.title:"");sel.appendChild(o);});
  if(pickedBook.toc.length)sel.value=pickedBook.toc[pickedBook.toc.length-1].section_number;  // default: whole book
  $("coverwrap").style.display=pickedBook.toc.length?"":"none";
  refreshGen();}).catch(()=>{});}
$("sel-cover").addEventListener("change",refreshGen);
document.addEventListener("click",e=>{if(!e.target.closest("#sum-book")&&!e.target.closest("#coverwrap")&&!e.target.closest(".searchbox"))$("bookresults").classList.remove("open");});

// ---- output: paper / teacher-student / view-edit / modify / pdf ----
const paper=$("paper"),editor=$("editor"),placeholder=$("placeholder"),paperwrap=$("paperwrap"),modrow=$("modrow"),tools=$("tools");
let audience="teacher",mode="view";
function slug(){const t=srcMode==="book"?(pickedBook?pickedBook.title:"resource"):(curSubtopic?curSubtopic.name:"resource");const f=(FMT[$("sel-format").value]||{}).name||"";return (f+" - "+t).replace(/[^\w \-]/g,"").slice(0,60).trim().replace(/\s+/g,"_");}
function splitKey(raw){const L=raw.split("\n");let idx=-1;for(let i=0;i<L.length;i++){if(/^#{1,3}\s*Answer Key\b/i.test(L[i].trim())){idx=i;}}
  if(idx<0)return {body:raw,key:""};let cut=idx;while(cut>0&&(/^\s*-{3,}\s*$/.test(L[cut-1])||/^\s*$/.test(L[cut-1])))cut--;
  return {body:L.slice(0,cut).join("\n").trimEnd(),key:L.slice(idx).join("\n")};}
function hasKey(){return !!splitKey(rawDoc).key;}
function shown(){return audience==="student"?splitKey(rawDoc).body:rawDoc;}
// The credit line (Adam, 2026-11-08: an option at download). It ends the PDF and the .md file, shows at the
// foot of the document while on, and the teacher's choice is kept in this browser.
const CREDIT="Drafted with Exegetica from its library's sources and reviewed by the teacher.";
const creditBox=$("credit");
try{const v=localStorage.getItem("exeg-credit");creditBox.checked=v===null?true:v==="1";}catch(e){creditBox.checked=true;}
creditBox.addEventListener("change",()=>{try{localStorage.setItem("exeg-credit",creditBox.checked?"1":"0");}catch(e){}if(rawDoc)render();});
function withCredit(text){return creditBox.checked?text.replace(/\s*$/,"")+"\n\n---\n\n*"+CREDIT+"*\n":text;}
let docBand="";   // the grade band the document was drafted for: the print size follows it
function render(){
  paper.innerHTML=md(shown());
  paper.dataset.band=docBand||$("sel-band").value;
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
  $("aud").querySelector('[data-v=student]').disabled=!hasKey();}
function segOn(seg,pred){Array.from($(seg).children).forEach(x=>x.classList.toggle("on",pred(x)));}
$("aud").addEventListener("click",e=>{const b=e.target.closest("button");if(!b||b.disabled)return;
  if(mode==="edit"){rawDoc=editor.value;mode="view";syncMode();}
  audience=b.dataset.v;segOn("aud",x=>x===b);render();});
function syncMode(){segOn("mode",x=>x.dataset.m===mode);
  if(mode==="edit"){editor.value=rawDoc;editor.style.display="block";paperwrap.style.display="none";}
  else{editor.style.display="none";paperwrap.style.display="flex";render();}}
$("mode").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;
  if(b.dataset.m==="view"&&mode==="edit")rawDoc=editor.value;mode=b.dataset.m;syncMode();});
editor.addEventListener("input",()=>{rawDoc=editor.value;});

// The source check sent after a finished document (webapp/citations.py). It reports what was found where,
// and never holds up the download.
function showReport(r){
  const el=$("report"),q=s=>"“"+esc(s)+"”";
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
async function streamInto(url,body){
  tools.innerHTML="";const chips=Shell.chips(tools),status=Shell.status(tools);status.set("studying");
  paper.innerHTML="<span class='caret'></span>";setOutButtons(false);
  $("report").hidden=true;$("report").innerHTML="";
  function live(){if(mode==="view")paper.innerHTML=md(shown())+"<span class='caret'></span>";}
  let ok=true;   // false on an error, a dropped connection, or a cut-off reply
  let started=false;   // the document's first text fades in; later pauses for a lookup only show the line
  try{
    const resp=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if(!resp.ok||!resp.body)throw new Error("HTTP "+resp.status);
    const rd=resp.body.getReader(),dec=new TextDecoder();let buf="";
    while(true){const {value,done}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});
      const fr=buf.split("\n\n");buf=fr.pop();
      for(const f of fr){const ln=f.split("\n").find(x=>x.startsWith("data:"));if(!ln)continue;const ev=JSON.parse(ln.slice(5).trim());
        if(ev.type==="text"){status.done(started?null:paper);started=true;rawDoc+=ev.text;live();}
        else if(ev.type==="status"){status.set(ev.stage,ev.words);}
        else if(ev.type==="tool_call"){chips.start(ev.name);}
        else if(ev.type==="tool_done"){chips.finish(ev.name,!!ev.error);}
        else if(ev.type==="notice"){status.done();const n=document.createElement("div");n.className="tool-chip";n.textContent=ev.message;tools.appendChild(n);if(ev.incomplete)ok=false;}
        else if(ev.type==="error"){status.done();ok=false;rawDoc+="\n\n**Error:** "+ev.message;live();}
        else if(ev.type==="report"){showReport(ev);}
      }}
  }catch(e){ok=false;rawDoc+="\n\n**Connection error:** "+e.message;}
  status.done();
  if(mode==="view")render();else editor.value=rawDoc;
  setOutButtons(!!rawDoc.trim());
  return ok;
}

$("gen").addEventListener("click",generate);
async function generate(){
  if($("gen").disabled)return;busy=true;refreshGen();
  let body, title, url;
  if(srcMode==="book"){
    url="/api/generate/book";
    body={format_id:$("sel-format").value,book_slug:pickedBook.slug,coverage:{through:parseInt($("sel-cover").value,10)},
      grade_band:$("sel-band").value,brief:$("brief").value,provider:curProvider(),model:curModel(),api_key:curKey()};
    title=(FMT[body.format_id]||{}).name+" · "+pickedBook.title;
  } else {
    url="/api/generate";
    const context={subject_name:curSubject?curSubject.name:"",sub_subject_name:curSub?curSub.name:"",topic_name:curTopic?curTopic.name:"",sub_topic_name:curSubtopic?curSubtopic.name:""};
    body={format_id:$("sel-format").value,objectives:selectedObjectives(),grade_band:$("sel-band").value,context,brief:$("brief").value,
      provider:curProvider(),model:curModel(),api_key:curKey()};
    title=(FMT[body.format_id]||{}).name+" · "+(curSubtopic?curSubtopic.name:"");
  }
  $("outtitle").textContent=title;docBand=$("sel-band").value;
  audience="teacher";mode="view";segOn("aud",x=>x.dataset.v==="teacher");segOn("mode",x=>x.dataset.m==="view");
  placeholder.style.display="none";paperwrap.style.display="flex";editor.style.display="none";modrow.style.display="flex";
  rawDoc="";
  await streamInto(url,body);
  busy=false;refreshGen();
}

$("modbtn").addEventListener("click",applyMod);
$("modin").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();applyMod();}});
async function applyMod(){
  const instr=$("modin").value.trim();if(!instr||busy||!rawDoc.trim())return;
  if(needsKey()){updateKeyBanner();AppSettings.open();return;}
  if(mode==="edit"){rawDoc=editor.value;mode="view";syncMode();}
  busy=true;refreshGen();$("modbtn").textContent="Applying…";
  const prev=rawDoc,prevReport=$("report").innerHTML;
  const body={document:rawDoc,instruction:instr,provider:curProvider(),model:curModel(),api_key:curKey()};
  rawDoc="";const ok=await streamInto("/api/revise",body);
  // Any failure or cut-off keeps the teacher's document exactly as it was, with its source check.
  // A finished revision gets no source check, since its sources were the first run's.
  if(!ok||!rawDoc.trim()){rawDoc=prev;render();setOutButtons(true);
    if(prevReport){$("report").innerHTML=prevReport;$("report").hidden=false;}
    const n=document.createElement("div");n.className="tool-chip";n.textContent="The change didn't finish, so your document was left as it was.";tools.appendChild(n);}
  else $("modin").value="";
  $("modbtn").textContent="Apply";busy=false;refreshGen();
}

$("pdf").addEventListener("click",()=>{if(mode==="edit"){rawDoc=editor.value;mode="view";syncMode();}render();setPrintHead();printReady().then(()=>window.print());});
$("download").addEventListener("click",()=>{const blob=new Blob([withCredit(shown())],{type:"text/markdown"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=slug()+(audience==="student"?"_student":"")+".md";a.click();URL.revokeObjectURL(a.href);});
$("copy").addEventListener("click",()=>{navigator.clipboard&&navigator.clipboard.writeText(shown());$("copy").textContent="Copied";setTimeout(()=>$("copy").textContent="Copy",1200);});
