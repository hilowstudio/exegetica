/* The chat page (templates/chat.html). Shell.openHelp and the rail come from static/js/shell.js. */
"use strict";
// ---------- tiny markdown renderer (handles our tool output incl. tables) ----------
function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function inline(s){
  return esc(s)
    .replace(/`([^`]+)`/g,(m,c)=>"<code>"+c+"</code>")
    .replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g,"$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
}
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
      let t="<div class='tablewrap'><table><thead><tr>"+head.map(h=>"<th>"+inline(h)+"</th>").join("")+"</tr></thead><tbody>";
      for(const r of rows){t+="<tr>"+r.map(c=>"<td>"+inline(c)+"</td>").join("")+"</tr>";}
      html+=t+"</tbody></table></div>";continue;
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
  box.innerHTML="";
  list.forEach(c=>{
    const it=document.createElement("div");it.className="chat-item"+(c.id===curChatId?" on":"");
    const t=document.createElement("button");t.type="button";t.className="ci-t";t.textContent=c.title||"Untitled study";
    if(c.id===curChatId)t.setAttribute("aria-current","true");
    const del=document.createElement("button");del.className="del";del.type="button";del.title="Delete";del.textContent="×";
    del.setAttribute("aria-label","Delete study: "+(c.title||"Untitled study"));
    del.onclick=(e)=>{e.stopPropagation();deleteChat(c.id);};
    it.appendChild(t);it.appendChild(del);
    it.onclick=()=>openChat(c.id);
    box.appendChild(it);
  });
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
  saveChats(loadChats().filter(c=>c.id!==id));
  if(id===curChatId)newStudy();else renderChatList();
}
function clearThread(){thread.querySelectorAll(".msg").forEach(m=>m.remove());}
function showEmpty(on){const e=document.getElementById("empty");if(e)e.style.display=on?"":"none";}
function newStudy(){
  closedWhy="";syncComposer();
  curChatId=null;history=[];clearThread();
  let e=document.getElementById("empty");
  if(!e){location.reload();return;} // empty node was consumed; simplest reset
  e.style.display="";titleEl.textContent="New study";renderChatList();closeSide();
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
        m.tools.forEach(t=>{const name=t.name||"tool";chips.start(name);chips.finish(name,!!t.is_error);});
        b.appendChild(tb);
      }
      const pr=document.createElement("div");pr.className="prose";pr.innerHTML=renderMarkdown(m.content);b.appendChild(pr);
      if(m.note)addSourceNote(b,m.note);
      addCopy(b,m.content);}
  });
  titleEl.textContent=c.title;renderChatList();closeSide();scroll();
  closedWhy=studyClosed(c,history);syncComposer();
}
document.getElementById("new-chat").onclick=newStudy;
document.getElementById("closed-new").onclick=newStudy;

// the studies panel: the Studies button opens and closes it, and a desktop remembers it open
const sideEl=document.getElementById("side"),menuBtn=document.getElementById("menu-btn");
const wide=()=>!(window.matchMedia&&matchMedia("(max-width:640px)").matches);
function setStudiesOpen(o){
  sideEl.classList.toggle("open",o);
  menuBtn.setAttribute("aria-expanded",String(o));
  if(wide()){try{localStorage.setItem("studybible.side.open",o?"1":"0");}catch(e){}}
}
function openSide(){setStudiesOpen(true);}
function closeSide(){setStudiesOpen(false);}
menuBtn.onclick=()=>setStudiesOpen(!sideEl.classList.contains("open"));
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

document.addEventListener("keydown",e=>{if(e.key==="Escape"){closeSide();}});

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
function scroll(){const main=document.getElementById("main");main.scrollTop=main.scrollHeight;}
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
  addMsg("user").innerHTML="<div class='prose'>"+renderMarkdown(text)+"</div>";
  history.push({role:"user",content:text});
  if(history.length===1){titleEl.textContent=titleFrom(history);}

  const bubble=addMsg("assistant");
  const toolsBox=document.createElement("div");toolsBox.className="tools";bubble.appendChild(toolsBox);
  const thinkEl=document.createElement("div");thinkEl.className="thinking";thinkEl.style.display="none";bubble.appendChild(thinkEl);
  const prose=document.createElement("div");prose.className="prose";bubble.appendChild(prose);
  const caret=document.createElement("span");caret.className="caret";prose.appendChild(caret);
  let raw="",thinkBuf="",note="",srcNote="",ended=false;const chips=Shell.chips(toolsBox);const turnTools=[];

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
        if(ev.type==="text"){raw+=ev.text;if(thinkEl.style.display!=="none"){thinkEl.style.display="none";}paint();}
        else if(ev.type==="thinking"){thinkBuf+=ev.text;thinkEl.style.display="block";thinkEl.textContent="Thinking… "+thinkBuf.slice(-160);scroll();}
        else if(ev.type==="tool_call"){chips.start(ev.name);}
        else if(ev.type==="tool_done"){chips.finish(ev.name,!!ev.error);
          turnTools.push({name:ev.name,input:ev.input||{},output:ev.output||"",is_error:!!ev.error});}
        else if(ev.type==="notice"){const n=document.createElement("div");n.className="notice";n.textContent=ev.message;bubble.insertBefore(n,prose);scroll();}
        else if(ev.type==="safety"){Shell.openHelp(ev.resources,"You matter, and you don't have to carry this alone. These people can help right now — free and private. Please also tell a parent, pastor, teacher, or friend you trust.");}
        else if(ev.type==="error"){note="**"+ev.message+"**";paint();}
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
  }finally{busy=false;stopper=null;sendBtn.textContent="Send";sendBtn.removeAttribute("aria-label");input.focus();}
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
      if(local.length && confirm("Import your "+local.length+" saved stud"+(local.length===1?"y":"ies")+" from this browser into your account?")){
        chatsMem=local;
        fetch("/api/chats",{method:"PUT",credentials:"same-origin",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({chats:local})}).then(function(r){if(r.ok){try{localStorage.removeItem(CKEY);}catch(e){}}}).catch(function(){});
      } else { chatsMem=[]; }
    }
  }
  renderChatList();
  applyGate();   // chat needs a signed-in school account
}
renderChatList(); // immediate paint from localStorage; initChats re-renders after auth resolves
initChats();
