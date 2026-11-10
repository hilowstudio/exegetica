/* The chat page (templates/chat.html). Shell.openHelp and the rail come from static/js/shell.js. */
"use strict";
// ---------- tiny markdown renderer (handles our tool output incl. tables) ----------
function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function inline(s){
  return Passage.linkHtml(esc(s)
    .replace(/`([^`]+)`/g,(m,c)=>"<code>"+c+"</code>")
    .replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g,"$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>'));
}
// Every Scripture reference in a reply opens the passage beside the conversation (rule B1). The references are
// found and linked by the shared panel (static/js/passage.js): text only, never inside a tag, code or a link.
function renderMarkdown(src){
  const lines=src.replace(/\r\n/g,"\n").split("\n");
  let html="",i=0;
  const isTableSep=s=>/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(s);
  const cells=s=>s.replace(/^\s*\|/,"").replace(/\|\s*$/,"").split("|").map(c=>c.trim());
  while(i<lines.length){
    let line=lines[i];
    if(/^```/.test(line)){
      const lang=line.slice(3).trim();i++;let buf=[];
      while(i<lines.length&&!/^```/.test(lines[i])){buf.push(lines[i]);i++;}
      i++;html+="<pre><code>"+esc(buf.join("\n"))+"</code></pre>";continue;
    }
    if(/^\s*$/.test(line)){i++;continue;}
    if(/^#{2,4}\s/.test(line)){
      const lvl=line.match(/^#+/)[0].length;const t=line.replace(/^#+\s/,"");
      html+="<h"+lvl+">"+inline(t)+"</h"+lvl+">";i++;continue;
    }
    if(/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)){html+="<hr>";i++;continue;}
    if(/^\s*>/.test(line)){
      let buf=[];while(i<lines.length&&/^\s*>/.test(lines[i])){buf.push(lines[i].replace(/^\s*>\s?/,""));i++;}
      html+="<blockquote>"+renderMarkdown(buf.join("\n"))+"</blockquote>";continue;
    }
    if(line.includes("|")&&i+1<lines.length&&isTableSep(lines[i+1])){
      const head=cells(line);i+=2;const rows=[];
      while(i<lines.length&&lines[i].includes("|")&&!/^\s*$/.test(lines[i])){rows.push(cells(lines[i]));i++;}
      html+=Shell.table(head,rows,inline);continue;   // the shell's table (rule J2)
    }
    if(/^\s*[-*]\s+/.test(line)){
      let buf=[];while(i<lines.length&&/^\s*[-*]\s+/.test(lines[i])){buf.push("<li>"+inline(lines[i].replace(/^\s*[-*]\s+/,""))+"</li>");i++;}
      html+="<ul>"+buf.join("")+"</ul>";continue;
    }
    if(/^\s*\d+[.)]\s+/.test(line)){
      let buf=[];while(i<lines.length&&/^\s*\d+[.)]\s+/.test(lines[i])){buf.push("<li>"+inline(lines[i].replace(/^\s*\d+[.)]\s+/,""))+"</li>");i++;}
      html+="<ol>"+buf.join("")+"</ol>";continue;
    }
    let buf=[];
    while(i<lines.length&&!/^\s*$/.test(lines[i])&&!/^```/.test(lines[i])&&!/^#{2,4}\s/.test(lines[i])&&!/^\s*[-*]\s+/.test(lines[i])&&!/^\s*>/.test(lines[i])){buf.push(lines[i]);i++;}
    html+="<p>"+inline(buf.join("\n")).replace(/\n/g,"<br>")+"</p>";
  }
  return html;
}

// ---------- what each library lookup is called on the page ----------
// [while it runs, once done]. {v} is what it looked at: the passages, words, names or questions, joined.
const TOOL_WORDS={
  lookup_verse:["Looking up a passage","Looked up {v}"], get_passage:["Reading a passage","Read {v}"],
  compare_translations:["Comparing translations","Compared translations of {v}"],
  vocabulary_list:["Listing the vocabulary","Listed the vocabulary of {v}"],
  word_study:["Studying a word","Studied the word {v}"], search_lexicon:["Searching the lexicon","Searched the lexicon for {v}"],
  search_by_strongs:["Finding where a word is used","Found where {v} is used"], parse_morphology:["Parsing a word form","Parsed {v}"],
  get_key_terms:["Reading a key term","Read the key term {v}"], get_cross_references:["Finding cross-references","Found cross-references for {v}"],
  get_parallel_passages:["Finding parallel passages","Found parallels to {v}"], get_septuagint:["Reading the Septuagint","Read the Septuagint of {v}"],
  get_commentary:["Reading commentaries","Read commentaries on {v}"], get_study_notes:["Reading study notes","Read study notes on {v}"],
  get_church_fathers:["Reading the church fathers","Read the church fathers on {v}"],
  find_confessions_by_verse:["Finding the confessions","Found the confessions that cite {v}"],
  get_confession:["Reading a confession","Read {v}"], get_confession_proofs:["Reading proof texts","Read the proof texts of {v}"],
  search_theology:["Searching the theology library","Searched the theology library for {v}"],
  get_bible_dictionary:["Reading the Bible dictionary","Read the Bible dictionary on {v}"],
  lookup_name:["Looking up a name","Looked up {v}"], explore_place:["Looking up a place","Looked up the place {v}"],
  explore_genealogy:["Tracing a family","Traced the family of {v}"], explore_person_events:["Tracing a life","Traced the life of {v}"],
  people_in_passage:["Finding the people in a passage","Found the people in {v}"], find_connection:["Tracing a connection","Traced a connection"],
  graph_enriched_search:["Finding people, places and events","Found the people, places and events in {v}"],
  get_devotional:["Reading a devotional","Read a devotional on {v}"],
  get_course_schedule:["Checking the course calendar","Checked the course calendar"], get_memory_verses:["Reading the memory verses","Read the memory verses"],
  get_reading_guide:["Reading the reading guide","Read the reading guide"], get_project:["Reading the project guide","Read the project guide"],
  list_john_curriculum:["Reading the course outline","Read the course outline"]
};
function toolSubject(i){
  i=i||{};
  const v=i.reference||i.word||i.strongs||i.query||i.name||i.person||i.place||i.term||i.topic||i.document||i.code||"";
  return typeof v==="string"?v.trim():"";
}
function toolLabel(name,inputs,done){
  const w=TOOL_WORDS[name];
  if(!w)return (done?"Used ":"Using ")+name.replace(/_/g," ");
  if(!done)return w[0];
  const seen=[];(inputs||[]).forEach(i=>{const v=toolSubject(i);if(v&&seen.indexOf(v)<0)seen.push(v);});
  if(!seen.length){   // nothing named: the running words, in the past ("Studying a word" -> "Studied a word")
    const past={Looking:"Looked",Reading:"Read",Comparing:"Compared",Listing:"Listed",Studying:"Studied",Searching:"Searched",
      Finding:"Found",Parsing:"Parsed",Tracing:"Traced",Checking:"Checked"};
    return w[0].replace(/^\w+/,m=>past[m]||m);
  }
  const list=seen.length>3?seen.slice(0,3).join(", ")+" and "+(seen.length-3)+" more":seen.join(", ");
  return w[1].replace("{v}",list);
}

// ---------- app state ----------
const thread=document.getElementById("thread"), input=document.getElementById("input"),
      sendBtn=document.getElementById("send"),
      titleEl=document.getElementById("thread-title");
let persona="professor", subject="bible", busy=false;
let stopper=null;   // aborts the reply in progress (the Send button reads Stop meanwhile)
let history=[]; // [{role, content}]

const LEGACY_PERSONA={theologian:"professor",study:"aide",neutral:"researcher"};
function setPersona(p){p=LEGACY_PERSONA[p]||p;persona=p;
  document.getElementById("p-professor").setAttribute("aria-pressed",p==="professor");
  document.getElementById("p-aide").setAttribute("aria-pressed",p==="aide");
  document.getElementById("p-researcher").setAttribute("aria-pressed",p==="researcher");}
document.getElementById("p-professor").onclick=()=>setPersona("professor");
document.getElementById("p-aide").onclick=()=>setPersona("aide");
document.getElementById("p-researcher").onclick=()=>setPersona("researcher");
/* Subject: Bible (Study Bible tools) or History (Social Sciences tools). A study stays in one
   subject, so switching mid-study starts a new one. */
function personaName(p){return p==="professor"?(subject==="history"?"Historian":"Professor"):p==="aide"?"Aide":"Researcher";}
function setSubject(sj,fresh){
  if(sj!=="history")sj="bible";
  const restart=fresh&&sj!==subject&&history.length;
  subject=sj;try{localStorage.setItem("exeg-subject",sj);}catch(e){}
  if(restart)newStudy();
  document.getElementById("s-bible").setAttribute("aria-pressed",sj==="bible");
  document.getElementById("s-history").setAttribute("aria-pressed",sj==="history");
  document.getElementById("p-professor").textContent=personaName("professor");
  const eb=document.querySelector("#empty .es-bible"),eh=document.querySelector("#empty .es-history");
  if(eb&&eh){eb.hidden=sj==="history";eh.hidden=sj!=="history";}
  const inp=document.getElementById("input");
  if(inp)inp.placeholder=sj==="history"?"Ask a history question…":"Ask a question about the Gospel of John…";
}
document.getElementById("s-bible").onclick=()=>setSubject("bible",true);
document.getElementById("s-history").onclick=()=>setSubject("history",true);
try{setSubject(localStorage.getItem("exeg-subject")||"bible",false);}catch(e){}


/* ---------- the About Exegetica window: an About tab and the FAQs (built from docs/faq.md) ---------- */
const srcBg=document.getElementById("src-bg");
let srcOpener=null;
function openSources(opener){
  srcTab(srcTabs[0],false);
  srcOpener=opener||null;srcBg.classList.add("open");document.getElementById("src-close").focus();
}
const srcTabs=[...document.querySelectorAll(".src-tab")];
function srcTab(tab,focus){
  srcTabs.forEach(t=>{const on=t===tab;t.setAttribute("aria-selected",on);t.tabIndex=on?0:-1;
    document.getElementById(t.getAttribute("aria-controls")).hidden=!on;});
  if(focus)tab.focus();
}
srcTabs.forEach((t,i)=>{
  t.onclick=()=>srcTab(t,false);
  t.onkeydown=e=>{const n=srcTabs.length,k=e.key;
    const j=k==="ArrowRight"?(i+1)%n:k==="ArrowLeft"?(i+n-1)%n:k==="Home"?0:k==="End"?n-1:-1;
    if(j>=0){e.preventDefault();srcTab(srcTabs[j],true);}};
});
document.getElementById("about-to-faq").onclick=()=>srcTab(srcTabs[1],true);
function closeSources(){srcBg.classList.remove("open");if(srcOpener){srcOpener.focus();srcOpener=null;}}
document.addEventListener("click",e=>{const b=e.target.closest&&e.target.closest("[data-src]");if(b){e.preventDefault();openSources(b);}});
document.getElementById("src-close").onclick=closeSources;
srcBg.addEventListener("click",e=>{if(e.target===srcBg)closeSources();});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&srcBg.classList.contains("open"))closeSources();});

// ---------- conversation persistence ----------
// Auth-aware: signed-in users read/write their Neon account; anonymous users use
// localStorage exactly as before. AUTH is resolved once at boot (initChats).
const CKEY="studybible.chats.v1";
let curChatId=null;
var AUTH={signed:false,user:null};
// Studies kept in this browser (from before sign-in) are dropped after 30 days.
const LOCAL_DAYS=30;
function _loadLocalChats(){
  try{
    const all=JSON.parse(localStorage.getItem(CKEY))||[],cut=Date.now()-LOCAL_DAYS*864e5;
    const kept=all.filter(c=>(c.updated||0)>=cut);
    if(kept.length!==all.length){if(kept.length)localStorage.setItem(CKEY,JSON.stringify(kept));else localStorage.removeItem(CKEY);}
    return kept;
  }catch(e){return[]}
}
var chatsMem=_loadLocalChats(); // in-memory source of truth once booted
function loadChats(){return chatsMem;}
var _chatTimer=null,_chatDirty=false;
// A failed load must never be mistaken for an empty account: saving then would overwrite
// every saved study on the server with only the new one.
var _chatLoadFailed=false;
function flushChats(keepalive){
  if(!_chatDirty||_chatLoadFailed)return;_chatDirty=false;clearTimeout(_chatTimer);
  try{fetch("/api/chats",{method:"PUT",credentials:"same-origin",keepalive:!!keepalive,
    headers:{"Content-Type":"application/json"},body:JSON.stringify({chats:chatsMem})}).catch(function(){});}catch(e){}
}
function saveChats(a){
  chatsMem=a||[];
  if(AUTH.signed){_chatDirty=true;clearTimeout(_chatTimer);_chatTimer=setTimeout(function(){flushChats(false);},500);}
  else{try{localStorage.setItem(CKEY,JSON.stringify(chatsMem));}catch(e){}}
}
window.addEventListener("pagehide",function(){if(AUTH.signed)flushChats(true);});
function uid(){return Date.now().toString(36)+Math.random().toString(36).slice(2,7);}
function titleFrom(msgs){const u=msgs.find(m=>m.role==="user");return u?u.content.replace(/\s+/g," ").trim().slice(0,60):"New study";}

function renderChatList(){
  const box=document.getElementById("chats");const list=loadChats().sort((a,b)=>b.updated-a.updated);
  if(!list.length){box.innerHTML="<div class='none'>"+(AUTH.signed?"Your studies are saved to your school account.":"Sign in with your school account to keep your studies.")+"</div>";return;}
  box.innerHTML="";let lastGroup="";
  list.forEach(c=>{
    const g=dayGroup(c.updated||c.created||0);
    if(g!==lastGroup){const h=document.createElement("div");h.className="grp";h.textContent=g;box.appendChild(h);lastGroup=g;}
    const it=document.createElement("div");it.className="chat-item"+(c.id===curChatId?" on":"");
    const t=document.createElement("button");t.type="button";t.className="ci-t";
    const tt=document.createElement("span");tt.className="tt";tt.textContent=c.title||"Untitled study";t.appendChild(tt);
    if(studyClosed(c,c.messages||[])){const ro=document.createElement("span");ro.className="ro";ro.textContent="Read only";t.appendChild(ro);}
    if(c.id===curChatId)t.setAttribute("aria-current","true");
    const del=document.createElement("button");del.className="del";del.type="button";del.title="Delete";del.textContent="×";
    del.setAttribute("aria-label","Delete study: "+(c.title||"Untitled study"));
    del.onclick=(e)=>{e.stopPropagation();deleteChat(c.id);};
    it.appendChild(t);it.appendChild(del);
    it.onclick=()=>openChat(c.id);
    box.appendChild(it);
  });
}
function dayGroup(ts){
  const now=new Date(),start=new Date(now.getFullYear(),now.getMonth(),now.getDate()).getTime();
  if(ts>=start)return "Today";
  if(ts>=start-864e5)return "Yesterday";
  if(ts>=start-6*864e5)return "Earlier this week";
  return "Earlier";
}
// Decision F (docs/decisions/0015): a student's study takes new messages for one day after it began,
// and every study stops at the server's message limit (policy.MAX_MESSAGES). After that it opens
// for reading only.
const OPEN_HOURS=24,MAX_MESSAGES=48;
let closedWhy="";
function studyClosed(c,msgs){
  if(msgs.length+1>MAX_MESSAGES)return "This study has reached its length limit, so it is open for reading only.";
  const start=c&&(c.created||c.updated);
  if(!isTeacher()&&start&&Date.now()-start>OPEN_HOURS*36e5)return "This study began more than a day ago, so it is open for reading only.";
  return "";
}
function syncComposer(){
  const off=!AUTH.signed||!!closedWhy;
  document.getElementById("input").disabled=off;document.getElementById("send").disabled=off;
  document.getElementById("closed-note").hidden=!AUTH.signed||!closedWhy;
  document.getElementById("closed-msg").textContent=closedWhy;
}
function persistCurrent(){
  if(!history.length)return;
  const chats=loadChats();let c=chats.find(x=>x.id===curChatId);
  if(!c){c={id:curChatId,title:titleFrom(history),persona,subject,messages:[],created:Date.now(),updated:0};chats.push(c);}
  c.messages=history.slice();c.persona=persona;c.subject=subject;c.title=titleFrom(history);c.updated=Date.now();
  saveChats(chats);renderChatList();
  titleEl.textContent=c.title;
  closedWhy=studyClosed(c,history);syncComposer();
}
function deleteChat(id){
  const all=loadChats(),i=all.findIndex(c=>c.id===id);if(i<0)return;
  const gone=all[i],wasOpen=id===curChatId;
  saveChats(all.filter(c=>c.id!==id));
  if(wasOpen)newStudy();else renderChatList();
  // Undo puts it back.
  Shell.toast("Study deleted",{undo:()=>{
    const now=loadChats();if(now.some(c=>c.id===id))return;
    now.splice(Math.min(i,now.length),0,gone);saveChats(now);
    if(wasOpen)openChat(id);else renderChatList();
  }});
}
function clearThread(){thread.querySelectorAll(".msg").forEach(m=>m.remove());}
function showEmpty(on){const e=document.getElementById("empty");if(e)e.style.display=on?"":"none";}
function newStudy(){
  closedWhy="";syncComposer();
  curChatId=null;history=[];clearThread();
  let e=document.getElementById("empty");
  if(!e){location.reload();return;} // empty node was consumed; simplest reset
  e.style.display="";titleEl.textContent="New study";renderChatList();if(!wide())closeSide();
}
function openChat(id){
  const c=loadChats().find(x=>x.id===id);if(!c)return;
  curChatId=id;history=c.messages.slice();setSubject(c.subject||"bible",false);   // persona stays the default (modes are hidden)
  clearThread();showEmpty(false);
  history.forEach(m=>{
    const b=addMsg(m.role);
    if(m.role==="user")b.innerHTML="<div class='prose'>"+renderMarkdown(m.content)+"</div>";
    else{
      if(Array.isArray(m.tools)&&m.tools.length){
        const tb=document.createElement("div");tb.className="tools";const chips=Shell.chips(tb);
        const seen={};
        m.tools.forEach(t=>{const name=t.name||"tool";(seen[name]=seen[name]||[]).push(t.input||{});
          chips.start(name);chips.finish(name,!!t.is_error);chips.label(name,toolLabel(name,seen[name],true));});
        b.appendChild(tb);
      }
      const pr=document.createElement("div");pr.className="prose";pr.innerHTML=renderMarkdown(m.content);b.appendChild(pr);
      if(m.note)addSourceNote(b,m.note);
      addCopy(b,m.content);}
  });
  titleEl.textContent=c.title;renderChatList();if(!wide())closeSide();scroll(true);
  closedWhy=studyClosed(c,history);syncComposer();
}
document.getElementById("new-chat").onclick=newStudy;
document.getElementById("closed-new").onclick=newStudy;

// the studies panel: the Studies button at the top left opens it, and its own hide control at its top edge
// closes it (the familiar sidebar pattern). Focus follows, since the button pressed is hidden by the change.
// A desktop remembers the list open.
const sideEl=document.getElementById("side"),menuBtn=document.getElementById("menu-btn"),sideX=document.getElementById("side-x");
const wide=()=>!(window.matchMedia&&matchMedia("(max-width:640px)").matches);
function setStudiesOpen(o,moveFocus){
  const inside=sideEl.contains(document.activeElement);
  sideEl.classList.toggle("open",o);
  menuBtn.setAttribute("aria-expanded",String(o));
  if(wide()){try{localStorage.setItem("studybible.side.open",o?"1":"0");}catch(e){}}
  if(o&&moveFocus)sideX.focus({preventScroll:true});
  if(!o&&(moveFocus||inside))menuBtn.focus({preventScroll:true});
}
function openSide(){setStudiesOpen(true);}
function closeSide(){setStudiesOpen(false);}
menuBtn.onclick=()=>setStudiesOpen(true,true);
sideX.onclick=()=>setStudiesOpen(false,true);
try{ if(wide()&&localStorage.getItem("studybible.side.open")==="1") setStudiesOpen(true); }catch(e){}

// ---------- config: the server's tools and help resources ----------
let CFG={providers:[],server_anthropic_key:false,tools:0,crisis_resources:[]};
// Chat runs on one model for everyone (docs/decisions/0024), so it sends no provider, model, or key.
function isTeacher(){return !!(AUTH.user&&AUTH.user.role==="teacher");}
function applyGate(){
  const off=!AUTH.signed,g=document.getElementById("signin-gate");
  g.hidden=!off;syncComposer();
  if(off&&/[?&]auth=domain/.test(location.search))
    document.getElementById("gate-msg").textContent="That Google account isn't a school account. Use your school account.";
}

document.addEventListener("keydown",e=>{
  if(e.key!=="Escape"||e.defaultPrevented||srcBg.classList.contains("open"))return;
  closeSide();
});

fetch("/api/config").then(r=>r.json()).then(c=>{CFG=c;
  if((c.history_tools||[]).length){document.getElementById("subj").hidden=false;document.getElementById("subj-lab").hidden=false;}
  else if(subject==="history")setSubject("bible",false);})
  .catch(()=>{console.error("backend unavailable");});

function addMsg(role){
  showEmpty(false);
  const m=document.createElement("div");m.className="msg "+role;
  const who=document.createElement("div");who.className="who";who.textContent=role==="user"?"You":"Exegetica";
  const bubble=document.createElement("div");bubble.className="bubble";
  m.appendChild(who);m.appendChild(bubble);thread.appendChild(m);
  scroll();return bubble;
}
// The page follows a reply only while the reader is at the bottom. Scrolled up to read, they stay put, and a
// button offers the way back down (rule G12).
const mainEl=document.getElementById("main"),jumpBtn=document.getElementById("jump");
let follow=true;
function atBottom(){return mainEl.scrollHeight-mainEl.scrollTop-mainEl.clientHeight<90;}
mainEl.addEventListener("scroll",()=>{follow=atBottom();if(follow)jumpBtn.hidden=true;});
function scroll(force){
  if(force)follow=true;
  if(follow){mainEl.scrollTop=mainEl.scrollHeight;jumpBtn.hidden=true;}
  else if(busy)jumpBtn.hidden=false;
}
jumpBtn.onclick=()=>{scroll(true);input.focus();};
// What the reply drew on (webapp/citations.py): "No library resource was consulted for this response.",
// or quotations no source holds. Saved with the message for display only; the server drops it before the model sees history.
function addSourceNote(bubble,text){
  const p=document.createElement("p");p.className="srcnote";p.textContent=text;bubble.appendChild(p);
}
function addCopy(bubble,text){
  const row=document.createElement("div");row.className="msg-actions";
  const b=document.createElement("button");b.type="button";b.textContent="Copy";
  b.onclick=()=>{if(navigator.clipboard){navigator.clipboard.writeText(text);b.textContent="Copied";setTimeout(()=>b.textContent="Copy",1200);}};
  row.appendChild(b);bubble.appendChild(row);
}

async function send(text){
  if(busy){if(stopper)stopper.abort();return;}
  if(!text.trim())return;
  if(!AUTH.signed){applyGate();return;}
  if(curChatId){closedWhy=studyClosed(loadChats().find(x=>x.id===curChatId),history);if(closedWhy){syncComposer();return;}}
  busy=true;stopper=new AbortController();sendBtn.textContent="Stop";sendBtn.setAttribute("aria-label","Stop the reply");
  if(!curChatId)curChatId=uid();
  addMsg("user").innerHTML="<div class='prose'>"+renderMarkdown(text)+"</div>";scroll(true);
  history.push({role:"user",content:text});
  if(history.length===1){titleEl.textContent=titleFrom(history);}

  const bubble=addMsg("assistant");
  const toolsBox=document.createElement("div");toolsBox.className="tools";bubble.appendChild(toolsBox);
  const status=Shell.status(bubble);   // what the reply is doing until its text arrives
  const thinkEl=document.createElement("div");thinkEl.className="thinking";thinkEl.style.display="none";bubble.appendChild(thinkEl);
  const prose=document.createElement("div");prose.className="prose";bubble.appendChild(prose);
  const caret=document.createElement("span");caret.className="caret";prose.appendChild(caret);
  let raw="",thinkBuf="",note="",srcNote="",ended=false;const chips=Shell.chips(toolsBox);const turnTools=[];const used={};
  // A fixed reply arrives at once; anything slower says what it is doing.
  const early=setTimeout(()=>{if(!raw&&!note)status.set("studying");},400);

  // `note` (an error line) is shown but never saved into history, so it never goes back to the model.
  function paint(){prose.innerHTML=renderMarkdown(raw+(note?"\n\n"+note:""));prose.appendChild(caret);scroll();}

  try{
    const resp=await fetch("/api/chat",{method:"POST",signal:stopper.signal,headers:{"Content-Type":"application/json"},
      body:JSON.stringify({persona,subject,messages:history})});
    if(!resp.ok||!resp.body){
      let m="";try{m=(await resp.json()).error||"";}catch(_){}
      if(resp.status===401){AUTH.signed=false;applyGate();}
      const err=new Error(m||("HTTP "+resp.status));err.server=!!m;throw err;}
    const reader=resp.body.getReader(),dec=new TextDecoder();let buf="";
    while(true){
      const {value,done}=await reader.read();if(done)break;
      buf+=dec.decode(value,{stream:true});
      const frames=buf.split("\n\n");buf=frames.pop();
      for(const f of frames){
        const line=f.split("\n").find(l=>l.startsWith("data:"));if(!line)continue;
        const ev=JSON.parse(line.slice(5).trim());
        if(ev.type==="text"){status.done(prose);raw+=ev.text;if(thinkEl.style.display!=="none"){thinkEl.style.display="none";}paint();}
        else if(ev.type==="status"){if(!raw)status.set(ev.stage,ev.words);}
        else if(ev.type==="thinking"){thinkBuf+=ev.text;thinkEl.style.display="block";thinkEl.textContent="Thinking… "+thinkBuf.slice(-160);scroll();}
        else if(ev.type==="tool_call"){chips.start(ev.name);chips.label(ev.name,toolLabel(ev.name,used[ev.name],false));}
        else if(ev.type==="tool_done"){chips.finish(ev.name,!!ev.error);(used[ev.name]=used[ev.name]||[]).push(ev.input||{});
          chips.label(ev.name,toolLabel(ev.name,used[ev.name],true));
          turnTools.push({name:ev.name,input:ev.input||{},output:ev.output||"",is_error:!!ev.error});}
        else if(ev.type==="notice"){status.done();const n=document.createElement("div");n.className="notice";n.textContent=ev.message;bubble.insertBefore(n,prose);scroll();}
        else if(ev.type==="safety"){Shell.openHelp(ev.resources,"You matter, and you don't have to carry this alone. These people can help right now. It's free and private. Please also tell a parent, pastor, teacher, or friend you trust.");}
        else if(ev.type==="error"){status.done();note="**"+ev.message+"**";paint();}
        else if(ev.type==="end"){ended=true;}
        else if(ev.type==="source_note"){srcNote=ev.text;}
        else if(ev.type==="done"){/* finished */}
      }
    }
    // Every reply ends with an "end" event; a stream without one was cut off on the way.
    if(!ended&&!note){note="**The reply was interrupted. Send your message again.**";paint();}
    caret.remove();
    const amsg={role:"assistant",content:raw||"(no response)"};
    if(turnTools.length)amsg.tools=turnTools;
    if(srcNote){amsg.note=srcNote;addSourceNote(bubble,srcNote);}
    history.push(amsg);
    addCopy(bubble,raw||"");
    persistCurrent();
  }catch(e){
    const stopped=e.name==="AbortError";
    caret.remove();prose.innerHTML=renderMarkdown(raw+"\n\n"+(stopped?"**Stopped.**":e.server?"**"+e.message+"**":"**Connection error:** "+e.message));
    const amsg={role:"assistant",content:raw};
    if(turnTools.length)amsg.tools=turnTools;
    history.push(amsg);persistCurrent();
  }finally{clearTimeout(early);status.done();busy=false;stopper=null;sendBtn.textContent="Send";sendBtn.removeAttribute("aria-label");input.focus({preventScroll:true});}
}

sendBtn.onclick=()=>{if(busy){if(stopper)stopper.abort();return;}const t=input.value;input.value="";auto();send(t);};
input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();if(!busy)sendBtn.click();}});
function auto(){input.style.height="auto";input.style.height=Math.min(input.scrollHeight,180)+"px";}
input.addEventListener("input",auto);
document.getElementById("empty").addEventListener("click",e=>{
  const b=e.target.closest(".exgroups button");if(b){input.value=b.textContent;auto();sendBtn.click();}});

/* boot: resolve auth, load this user's chats from Neon (or keep localStorage) */
async function initChats(){
  try{ var r=await fetch("/api/me",{credentials:"same-origin"}); var d=await r.json();
       AUTH.user=(d&&d.user)||null; AUTH.signed=!!AUTH.user; }catch(e){ AUTH.signed=false; }
  if(AUTH.signed){
    var server=null;
    try{ var rr=await fetch("/api/chats",{credentials:"same-origin"}); if(rr.ok){ server=await rr.json(); } }catch(e){}
    var srvChats=(server&&server.chats)||[];
    if(!server){ _chatLoadFailed=true; chatsMem=[]; document.getElementById("load-note").hidden=false; }
    else if(srvChats.length){ chatsMem=srvChats; }
    else{
      // Empty account: offer a one-time import of this browser's studies, else start clean.
      var local=_loadLocalChats();
      const n=local.length;
      if(n && await Shell.ask({title:"Bring your studies into your account?",
            body:"This browser holds "+n+" saved stud"+(n===1?"y":"ies")+". Import "+(n===1?"it":"them")+" so "+(n===1?"it follows":"they follow")+" you to any device.",
            ok:"Import",cancel:"Not now"})){
        chatsMem=local;
        fetch("/api/chats",{method:"PUT",credentials:"same-origin",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({chats:local})}).then(function(r){if(r.ok){try{localStorage.removeItem(CKEY);}catch(e){}}}).catch(function(){});
      } else { chatsMem=[]; }
    }
  }
  renderChatList();
  applyGate();   // chat needs a signed-in school account
  openFromAddress();
}
renderChatList(); // immediate paint from localStorage; initChats re-renders after auth resolves
initChats();

/* ---------- the passage beside the conversation (rule B1) ----------
   The panel is shared by every page (static/js/passage.js). In chat, "Ask about it" puts the question in this
   study's own box instead of opening a new page. The box is filled, never sent: the student decides what to ask.
   None of this calls a model. */
Passage.ask=function(r){
  if(input.disabled){Shell.toast("This study is open for reading only. Start a new study to ask about "+r+".");return;}
  input.value="Help me study "+r+".";auto();if(!wide())Passage.close();input.focus();
};
// Another page can open chat on a passage: /?passage=John%207:37 shows it, and /?ask=John%207:37 also readies the
// question in a new study. The address is cleared after, so a reload doesn't repeat it.
function openFromAddress(){
  const q=new URLSearchParams(location.search),ref=Passage.normalize(q.get("ask")||q.get("passage")||"");
  if(!ref)return;
  window.history.replaceState(null,"",location.pathname);   // window.: chat keeps its messages in a variable named history
  Passage.open(ref);
  if(q.get("ask")&&AUTH.signed){            // after the panel opens, so the student lands in the box
    if(input.disabled)document.getElementById("new-chat").click();
    Passage.ask(ref);
  }
}
