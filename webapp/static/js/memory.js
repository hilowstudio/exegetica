/* Scripture Memory (templates/memory.html, static/css/memory.css). The rail, theme and Need help now? come from
   static/js/shell.js. Designed 2026-11-09 under the exegetica-design skill:
   - home: a commonplace book of verses, grouped by book and chapter, with each verse set as Scripture
   - practice: eight steps on a ladder, where the verse fades to first letters and then to its shape, and
     what the student says or writes inks back in where it belongs
   - review: verses known by heart come back after 1, 3, 7, 14, 30 and 60 days, only inside this page
   - class: this week's verse from the Sophomore Bible calendar, and Recite together for a projector
   - paper: pocket cards to cut and fold, and a memory book with a house cover
   No model reads anything here. A signed-in student's verses are theirs (decision 0002). */
(function(){
"use strict";

// ---------------------------------------------------------------- constants
var STORE = "studybible.memory.v1", PREFS = "studybible.memory.prefs";
var API = "/api/memory/";

// The ladder: the text fades as the student climbs, from reading to writing it from memory.
var STEPS = [
  { id:1, name:"Read it",                         type:"read",   mode:"full",  say:"Read it slowly, once or twice." },
  { id:2, name:"Listen",                          type:"listen", mode:"full",  say:"Listen to it read aloud, and follow the words." },
  { id:3, name:"Say it aloud",                    type:"speak",  mode:"full",  say:"Say it aloud with the words in front of you." },
  { id:4, name:"Write it out",                    type:"type",   mode:"full",  say:"Write it out with the words in front of you." },
  { id:5, name:"Say it from the first letters",   type:"speak",  mode:"first", say:"Say it with only the first letters to guide you." },
  { id:6, name:"Write it from the first letters", type:"type",   mode:"first", say:"Write it with only the first letters to guide you." },
  { id:7, name:"Say it from memory",              type:"speak",  mode:"shape", say:"Say it from memory. The lines show only its shape." },
  { id:8, name:"Write it from memory",            type:"type",   mode:"shape", say:"Write it from memory." }
];
var REVIEW_DAYS = [1, 3, 7, 14, 30, 60];

var BOOKS = ["Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel",
  "1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes",
  "Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah",
  "Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew","Mark","Luke","John","Acts","Romans",
  "1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians","Colossians","1 Thessalonians","2 Thessalonians",
  "1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"];
var OT = 39;

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

var ESV_NOTICE = "Scripture quotations are from the ESV® Bible (The Holy Bible, English Standard Version®), © 2001 by Crossway, " +
  "a publishing ministry of Good News Publishers. Used by permission. All rights reserved.";

// The house ornaments, drawn for this page in the covers' engraved register (rule I7).
var FLEURON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3.2 12.4c2.6-.2 4.4 1 5.5 2.9.4-2.5 2.3-4.2 4.9-4.6-1.7 1.1-2.6 2.7-2.6 4.6 1.6-1.9 3.9-2.6 6.5-2.1 1.7.3 2.9 1.2 3.6 2.4-1.5-.6-3.1-.6-4.6.1-2.4 1.1-4 3.3-4.5 5.8-.6-2.3-2.2-3.9-4.6-4.6-1.6-.5-3.1-1.7-3.6-3.3-.2-.4-.4-.9-.6-1.2zM12.1 9.6c-.2-2.9 1.1-5.3 3.9-6.4-1 1.5-1.4 3-1.2 4.5-1 .4-1.9 1.1-2.7 1.9z"/></svg>';
var LAMP = '<svg viewBox="0 0 96 96" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M16 58c0-7 14-12 32-12s32 5 32 12c0 6-14 10-32 10s-32-4-32-10z"/><path d="M16 58c2 5 15 8 32 8"/>' +
  '<path d="M78 54l11-7c1.5-1 1.2-2.6-.6-2.4L74 47"/><path d="M17 55c-6 0-9-4-8-8 1-3 5-4 8-2"/>' +
  '<path d="M34 46c2-4 8-6 14-6s12 2 14 6"/><path d="M42 40v-3h12v3"/>' +
  '<path d="M38 68l-3 9h26l-3-9"/><path d="M31 77h34"/>' +
  '<path d="M88 41c-3-4-2-9 1-13 1 4 4 6 3 10-.5 2-2.3 3.3-4 3z" fill="currentColor" stroke="none"/>' +
  '<path d="M24 52c4-1.5 10-2.4 16-2.6M52 49.6c6 .2 12 1.1 16 2.6" stroke-width="1"/></svg>';
var ICON = {
  back:'<svg viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>',
  next:'<svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>',
  retry:'<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 1 2.6 6.3M3 20v-5h5"/></svg>',
  prefs:'<svg viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></svg>',
  mic:'<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6 11a6 6 0 0 0 12 0M12 17v3"/></svg>',
  play:'<svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z"/></svg>',
  pause:'<svg viewBox="0 0 24 24"><path d="M7 5h4v14H7zM13 5h4v14h-4z"/></svg>',
  listen:'<svg viewBox="0 0 24 24"><path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11"/></svg>',
  book:'<svg viewBox="0 0 24 24"><path d="M12 6.6C10.2 5.3 7.3 5 4.8 5.6v12.3c2.5-.6 5.4-.3 7.2 1 1.8-1.3 4.7-1.6 7.2-1V5.6C16.7 5 13.8 5.3 12 6.6z"/><path d="M12 6.6v11.7"/></svg>',
  orig:'<svg viewBox="0 0 24 24"><path d="M5 19c2-6 4-9 7-14 3 5 5 8 7 14M8 14h8"/></svg>',
  print:'<svg viewBox="0 0 24 24"><path d="M7 8V4h10v4"/><rect x="4" y="8" width="16" height="8" rx="2"/><path d="M7 13h10v7H7z"/></svg>',
  people:'<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M3.5 19c.6-3.3 2.8-5 5.5-5s4.9 1.7 5.5 5"/><circle cx="17" cy="9" r="2.4"/><path d="M15.5 14.2c2.6-.4 4.6 1.2 5 4.3"/></svg>',
  check:'<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>',
  kebab:'<svg viewBox="0 0 24 24"><circle cx="12" cy="6" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="12" cy="18" r="1.4"/></svg>',
  folder:'<svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  pen:'<svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  ask:'<svg viewBox="0 0 24 24"><path d="M4 5.5h16v11H9l-4 3.2V16.5H4z"/></svg>',                  // Chat's icon on the rail
  unit:'<svg viewBox="0 0 24 24"><path d="M6.5 3.5h8l4 4v13h-12z"/><path d="M14 3.5v4.2h4.2"/><path d="M9 12.5h6M9 15.5h6"/></svg>'   // the Prep Room's
};

// ---------------------------------------------------------------- state
var db = { verses:[], folders:[] };
var ui = { view:"home", tab:"learning", folderId:null, menuFor:null, selectedId:null, panel:null };
var practice = null, review = null, finished = null, course = null;
var AUTH = { signed:false, user:null };
var chapters = {}, originals = {}, audioUrls = {};
var prefs = loadPrefs();
var drawerWasOpen = true;

function uid(){ return "v"+Date.now().toString(36)+Math.random().toString(36).slice(2,7); }
function $(id){ return document.getElementById(id); }
function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];}); }
function toast(msg, o){ Shell.toast(msg, o); }   // the shell's toast, with Undo where an action can be taken back
function say(text){ if(window.Shell && Shell.say) Shell.say(text); }
function fmtDate(iso){
  if(!iso) return "";
  try{ return new Date(iso).toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}); }catch(e){ return ""; }
}
function fmtDay(iso){
  if(!iso) return "";
  try{ return new Date(iso).toLocaleDateString(undefined,{month:"short",day:"numeric"}); }catch(e){ return ""; }
}
function addDays(iso, n){ var d=new Date(iso||Date.now()); d.setHours(4,0,0,0); d.setDate(d.getDate()+n); return d.toISOString(); }
function isTeacher(){ return !!(AUTH.user && AUTH.user.role==="teacher"); }

function loadPrefs(){
  var p = { shape:"lines", size:"standard", haptics:false };
  try{ var raw=localStorage.getItem(PREFS); if(raw){ var d=JSON.parse(raw); for(var k in p){ if(d[k]!=null) p[k]=d[k]; } } }catch(e){}
  return p;
}
function savePrefs(){ try{ localStorage.setItem(PREFS, JSON.stringify(prefs)); }catch(e){} }

// ---------------------------------------------------------------- storage (signed in: the account; signed out: this browser)
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
  // shown at the top of the page's own column, so the verse list beside it never covers it, and spoken
  // through the shell, since on a phone the column waits behind the open list
  var text="Your saved verses didn't load, so changes here won't be saved. Refresh the page to try again.";
  var n=document.createElement("div"); n.className="loadnote"; n.textContent=text;
  var col=document.querySelector(".app > .col")||document.body;
  col.insertBefore(n, col.firstChild);
  say(text);
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
      var n=local && local.verses ? local.verses.length : 0;
      if(n && await Shell.ask({title:"Bring your verses into your account?",
            body:"This browser holds "+n+" saved verse"+(n===1?"":"s")+". Import "+(n===1?"it":"them")+" so "+(n===1?"it follows":"they follow")+" you to any device.",
            ok:"Import", cancel:"Not now"})){
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
  openFromAddress();
  render();
  fillTexts();
  fetch(API+"course").then(function(r){ return r.ok ? r.json() : null; }).then(function(c){ course=c; if(ui.view==="home") render(); }).catch(function(){});
}
window.addEventListener("pagehide", function(){ if(AUTH.signed) flushServer(true); });

// Another page can open a verse here: /memory?verse=John%2015:5. A kept verse is selected; one not kept yet is
// offered in the day strip, never added on its own. The address is cleared after, so a reload doesn't repeat it.
function openFromAddress(){
  var q=new URLSearchParams(location.search), raw=q.get("verse"); if(!raw) return;
  history.replaceState(null, "", location.pathname);
  if(phone && phone.matches) setDrawerOpen(false);   // on a phone the list would cover the verse that was asked for
  var ref=(window.Passage && Passage.normalize(raw)) || null; if(!ref) return;
  var have=db.verses.find(function(v){ return Passage.normalize(v.reference)===ref; });   // "Ps. 23:1" finds "Psalm 23:1"
  if(have){ ui.tab=byHeart(have)?"heart":"learning"; ui.folderId=have.folderId||null; ui.selectedId=have.id; }
  else ui.offer=ref;
}
function newVerse(ref, folderId){
  return { id:uid(), reference:ref, text:null, currentStep:0,
    masteredAt:null, lastPracticedAt:null, lastRefreshedAt:null, folderId:folderId||null,
    createdAt:new Date().toISOString() };
}
function verseById(id){ return db.verses.find(function(v){ return v.id===id; }); }
function verseByRef(ref){ var k=normRef(ref); return db.verses.find(function(v){ return normRef(v.reference)===k; }); }
function folderById(id){ return db.folders.find(function(f){ return f.id===id; }); }
function hasRef(ref){ return !!verseByRef(ref); }
function normRef(ref){ return String(ref||"").toLowerCase().replace(/[\u2013]/g,"-").replace(/\s+/g," ").trim(); }
function byHeart(v){ return v.currentStep>=8; }

// ---------------------------------------------------------------- the library's lookups (ESV through the server, and the tagged originals)
// A failed lookup carries its status and body, so "the library has none" reads differently from "it didn't answer".
function getJSON(url){
  return fetch(url,{credentials:"same-origin"}).then(function(r){
    if(r.ok) return r.json();
    return r.json().catch(function(){ return null; }).then(function(body){ var e=new Error(r.status); e.status=r.status; e.body=body; throw e; });
  });
}
function fetchText(ref){ return getJSON(API+"text?ref="+encodeURIComponent(ref)).then(function(d){ return (d && d.text) || ""; }); }
function ensureText(v){
  if(v.text) return Promise.resolve(v.text);
  return fetchText(v.reference).then(function(t){ if(t){ v.text=t; save(); } return t; });
}
// One call for every verse still without its text, so the list can show each verse's opening words.
function fillTexts(){
  var missing=db.verses.filter(function(v){ return !v.text; }).slice(0, 40);
  if(!missing.length) return;
  getJSON(API+"texts?refs="+encodeURIComponent(missing.map(function(v){ return v.reference; }).join("|"))).then(function(d){
    var got=false;
    missing.forEach(function(v){ var t=d.texts && d.texts[v.reference]; if(t){ v.text=t; got=true; } });
    if(got){ save(); if(ui.view==="home") render(); }
  }).catch(function(){});
}
function chapterKey(ref){ var p=parseRef(ref); return p ? p.book+" "+p.ch : null; }
function fetchChapter(ref){
  var k=chapterKey(ref); if(!k) return Promise.resolve(null);
  if(chapters[k]!==undefined) return Promise.resolve(chapters[k]);
  return getJSON(API+"chapter?ref="+encodeURIComponent(ref)).then(function(d){ chapters[k]=d; return d; })
    .catch(function(){ return null; });   // not remembered, so the next try asks again
}
function fetchOriginal(ref){
  if(originals[ref]!==undefined) return Promise.resolve(originals[ref]);
  return getJSON(API+"original?ref="+encodeURIComponent(ref)).then(function(d){ originals[ref]=d; return d; })
    .catch(function(e){
      if(e && e.status===404 && e.body && e.body.error==="not in the library"){ originals[ref]=false; return false; }   // a real answer: none
      return null;   // no answer just now: not remembered
    });
}
function fetchAudio(ref){
  if(audioUrls[ref]) return Promise.resolve(audioUrls[ref]);
  return getJSON(API+"audio?ref="+encodeURIComponent(ref)).then(function(d){ audioUrls[ref]=(d&&d.audioUrl)||null; return audioUrls[ref]; });
}

// ---------------------------------------------------------------- references and books
function parseRef(ref){
  var m=/^\s*(.+?)\s+(\d+):(\d+)(?:\s*[-\u2013]\s*(\d+))?\s*$/.exec(ref||"");
  if(!m) return null;
  var v1=+m[3];
  return { book:m[1], ch:+m[2], v1:v1, v2:Math.max(v1, +(m[4]||v1)) };
}
function bookName(b){ var x=String(b||"").replace(/\s+/g," ").trim(); if(/^psalm$/i.test(x)) return "Psalms"; return x; }
function bookIndex(b){
  var x=bookName(b).toLowerCase();
  for(var i=0;i<BOOKS.length;i++){ if(BOOKS[i].toLowerCase()===x) return i; }
  return 999;
}
function sortKey(v){ var p=parseRef(v.reference); return p ? [bookIndex(p.book), p.ch, p.v1] : [999,0,0]; }
function cmpVerse(a,b){ var x=sortKey(a), y=sortKey(b); for(var i=0;i<3;i++){ if(x[i]!==y[i]) return x[i]-y[i]; } return 0; }
function chapterName(p){ var b=bookName(p.book); return (b==="Psalms"?"Psalm":b)+" "+p.ch; }
function groupLabel(v){ var p=parseRef(v.reference); if(!p) return "Other"; var b=bookName(p.book); return b==="Psalms" ? "Psalms" : b; }
function isHebrew(ref){ var p=parseRef(ref); return p ? bookIndex(p.book)<OT : false; }

// ---------------------------------------------------------------- the text model: lines, words and phrases
// A word keeps its lead punctuation, first letter, rest and trailing punctuation, so the page can fade each
// part on its own. Poetry keeps its lines (rule G5).
function tokens(text){
  var lines=[], words=[], phrase=0;
  String(text||"").replace(/\r/g,"").split("\n").forEach(function(line){
    if(!line.trim()){ if(lines.length && !lines[lines.length-1].gap) lines.push({gap:true}); return; }
    var ln={ ind:/^\s{2,}/.test(line), items:[] };
    line.trim().split(/\s+/).forEach(function(raw){
      var m=/^([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*)$/.exec(raw);
      var core=m[2];
      if(!core){ ln.items.push({punct:true, raw:raw}); return; }
      var w={ raw:raw, lead:m[1], f:core.charAt(0), r:core.slice(1), trail:m[3], norm:normWord(core), i:words.length, ph:phrase };
      words.push(w); ln.items.push(w);
      if(/[,;:.?!\u2013\u2014]/.test(m[3])) phrase++;
    });
    lines.push(ln);
  });
  return { lines:lines, words:words, phrases:phrase+1 };
}
function normWord(s){ return String(s||"").toLowerCase().replace(/[\u2018\u2019']/g,"").replace(/[^a-z0-9]/g,""); }
function typedWords(s){ return String(s||"").split(/[\s\u2013\u2014]+/).map(normWord).filter(Boolean); }

// ---------------------------------------------------------------- grading (the first version's scoring, kept)
function cleanText(t){
  return (t||"")
    .replace(/[\u2018\u2019\u201C\u201D\u2013\u2014]/g, "")      // smart quotes / dashes
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
function near(a,b){ return a.length>3 && b.length>3 && Math.abs(a.length-b.length)<=1 && lev(a,b)<=1; }

// Where each word of the verse stands against what was said or written: 0 waiting, 1 inked, 2 slipped
// (left out or said differently). A word half typed waits until it is whole.
function align(W, input, spoken){
  var typed=typedWords(input);
  var ends=spoken || /[\s.,;:!?]$/.test(input||"");
  var partial=(!ends && typed.length) ? typed.pop() : null;
  var n=W.length, marks=[], ptr=0, wrong=false, i, j;
  for(i=0;i<n;i++) marks.push(0);
  for(i=0;i<typed.length && ptr<n;i++){
    var w=typed[i];
    if(w===W[ptr].norm || near(w,W[ptr].norm)){ marks[ptr]=1; ptr++; wrong=false; continue; }
    var k=-1;
    for(j=1;j<=3 && ptr+j<n;j++){ if(w===W[ptr+j].norm){ k=j; break; } }
    if(k>0){ for(j=0;j<k;j++) marks[ptr+j]=2; marks[ptr+k]=1; ptr+=k+1; wrong=false; continue; }
    // started further on (a psalm's title left out, a line skipped): two words in a row that match a little
    // way ahead pick up the place, and what was passed over counts as slipped
    if(i+1<typed.length){
      for(j=4;j<=12 && ptr+j+1<n;j++){ if(w===W[ptr+j].norm && typed[i+1]===W[ptr+j+1].norm){ k=j; break; } }
      if(k>0){ for(j=0;j<k;j++) marks[ptr+j]=2; marks[ptr+k]=1; ptr+=k+1; wrong=false; continue; }
    }
    if(i+1<typed.length && ptr+1<n && typed[i+1]===W[ptr+1].norm){ marks[ptr]=2; ptr++; continue; }
    wrong=true;
  }
  if(partial && ptr<n && partial===W[ptr].norm){ marks[ptr]=1; ptr++; }
  var inked=0, slips=0; marks.forEach(function(m){ if(m===1) inked++; else if(m===2) slips++; });
  return { marks:marks, ptr:ptr, wrong:wrong, inked:inked, slips:slips };
}
// Proofreader's marks: a word-level comparison of the verse and an attempt.
function diff(A, B){
  var n=A.length, m=B.length, L=[], i, j;
  for(i=0;i<=n;i++){ L.push(new Array(m+1).fill(0)); }
  for(i=n-1;i>=0;i--) for(j=m-1;j>=0;j--){
    L[i][j] = (A[i].norm===B[j].norm || near(A[i].norm,B[j].norm)) ? L[i+1][j+1]+1 : Math.max(L[i+1][j], L[i][j+1]);
  }
  var ops=[]; i=0; j=0;
  while(i<n && j<m){
    if(A[i].norm===B[j].norm || near(A[i].norm,B[j].norm)){ ops.push({op:"eq", a:A[i]}); i++; j++; }
    else if(L[i+1][j]>=L[i][j+1]){ ops.push({op:"miss", a:A[i]}); i++; }
    else { ops.push({op:"extra", b:B[j]}); j++; }
  }
  while(i<n){ ops.push({op:"miss", a:A[i]}); i++; }
  while(j<m){ ops.push({op:"extra", b:B[j]}); j++; }
  var out=[];   // a word left out next to a word that wasn't in the verse reads as one changed word
  for(i=0;i<ops.length;i++){
    var o=ops[i], p=ops[i+1];
    if(p && ((o.op==="miss" && p.op==="extra") || (o.op==="extra" && p.op==="miss"))){
      out.push({op:"sub", a:o.a||p.a, b:o.b||p.b}); i++; continue;
    }
    out.push(o);
  }
  return out;
}

// ---------------------------------------------------------------- setting a verse on the page
function wordHtml(w, opts){
  var d = (opts && opts.sweep) ? ' style="--d:'+Math.min(w.i*0.014, 0.7).toFixed(3)+'s"' : "";
  return '<span class="w" data-i="'+w.i+'"'+d+'><span class="p">'+esc(w.lead)+'</span><span class="f">'+esc(w.f)+
    '</span><span class="r">'+esc(w.r)+'</span><span class="p">'+esc(w.trail)+'</span> </span>';
}
function pageHtml(tk, opts){
  return tk.lines.map(function(ln){
    if(ln.gap) return '<span class="gap"></span>';
    return '<span class="ln'+(ln.ind?' ind':'')+'">'+ln.items.map(function(it){
      return it.punct ? '<span class="pu">'+esc(it.raw)+' </span>' : wordHtml(it, opts);
    }).join("")+'</span>';
  }).join("");
}
// The plain reading of a verse: its lines, for the verse page, the finished verse and print.
function linesHtml(text, n){
  var first=true;
  return String(text||"").replace(/\r/g,"").split("\n").map(function(line){
    if(!line.trim()) return '<span class="gap"></span>';
    var num = (n && first) ? '<sup>'+n+'</sup>' : ""; first=false;
    return '<span class="ln'+(/^\s{2,}/.test(line)?' ind':'')+'">'+num+esc(line.trim())+'</span>';
  }).join("");
}
function firstLetters(text){
  return String(text||"").split(/\s+/).map(function(raw){
    var m=/^([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*)$/.exec(raw);
    return m[2] ? m[1]+m[2].charAt(0)+m[3] : raw;
  }).join(" ");
}
function ladderHtml(done, size, nowIdx){
  var h='<ol class="ladder'+(size?" "+size:"")+'" aria-hidden="true">';
  for(var i=0;i<8;i++){ h+='<li class="'+(i<done?"done":(i===nowIdx?"now":""))+'"></li>'; }
  return h+'</ol>';
}

// ---------------------------------------------------------------- render dispatch
function render(){
  ui.menuFor=null;
  if(ui.view==="practice" && practice) renderPractice();
  else if(ui.view==="review" && review) renderReview();
  else if(ui.view==="finished" && finished) renderFinished();
  else { ui.view="home"; renderHome(); }
}
// Practice, review and a finished verse fill the column; the list waits beside it, closed.
function setFocus(on){
  var app=document.querySelector(".app"); if(!app) return;
  if(on && !app.classList.contains("focus")){ drawerWasOpen=sideEl.classList.contains("open"); setDrawerOpen(false); }
  if(!on && app.classList.contains("focus") && drawerWasOpen && !(phone && phone.matches)) setDrawerOpen(true);
  app.classList.toggle("focus", !!on);
  $("scroller").scrollTop=0;
}

// ---------------------------------------------------------------- home: the list beside, the verse page in the column
function scoped(){
  return db.verses.filter(function(v){ return ui.folderId ? v.folderId===ui.folderId : v.folderId==null; });
}
function reviewOf(v){
  if(v.review && v.review.next) return v.review;
  return { level:0, next:addDays(v.lastRefreshedAt||v.masteredAt, 1) };
}
function isDue(v){ return byHeart(v) && new Date(reviewOf(v).next).getTime() <= Date.now(); }
function dueVerses(){ return db.verses.filter(isDue).sort(function(a,b){ return new Date(reviewOf(a).next)-new Date(reviewOf(b).next); }); }

function renderHome(){
  setFocus(false);
  $("topsub").textContent="Hide his word in your heart";
  var inFolder = ui.folderId ? folderById(ui.folderId) : null;
  if(ui.folderId && !inFolder){ ui.folderId=null; inFolder=null; }
  var list=scoped(), learning=list.filter(function(v){ return !byHeart(v); }), heart=list.filter(byHeart);
  var shown=(ui.tab==="heart" ? heart : learning).slice().sort(cmpVerse);
  if(!verseById(ui.selectedId||"")) ui.selectedId = shown.length ? shown[0].id : null;
  renderList(inFolder, learning, heart, shown);
  var v=verseById(ui.selectedId||"");
  var html=dayStrip();
  if(!v){ html+=emptyState(); }
  else { html+=leafHtml(v)+footHtml(v)+'<div id="panel"></div>'; }
  html+='<p class="credit">'+esc(ESV_NOTICE)+'</p>';
  $("view").innerHTML=html;
  wireHome(v);
  if(v){ hydrateLeaf(v); if(ui.panel) openPanel(ui.panel, v, true); }
}

function dayStrip(){
  var parts=[], due=dueVerses();
  if(ui.offer && !verseByRef(ui.offer)){
    parts.push('<div class="part"><p><b>'+esc(ui.offer)+'</b> isn’t in your verses yet.</p><button class="btn" id="day-offer">Add it</button></div>');
  }
  if(course && course.current){
    var have=verseByRef(course.current.reference);
    parts.push('<div class="part"><p>'+esc(course.course)+' this week: <b>'+esc(course.current.reference)+'</b>'+
      (course.current.unit?' · '+esc(course.current.unit):'')+'</p>'+
      '<button class="btn" id="day-week">'+(have?"Open it":"Add it")+'</button></div>');
  }
  if(due.length){
    parts.push('<div class="part"><p><span class="fl">'+FLEURON+'</span> '+due.length+' verse'+(due.length===1?"":"s")+' to say again today</p>'+
      '<button class="btn" id="day-review">Begin</button></div>');
  }
  return parts.length ? '<div class="day">'+parts.join("")+'</div>' : "";
}

function emptyState(){
  if(ui.tab==="heart" && db.verses.length){
    return '<div class="empty"><span class="lamp">'+LAMP+'</span><h2>Nothing by heart yet</h2>'+
      '<p>A verse comes here once you can write it from memory. Then it comes back now and then, so it stays.</p></div>';
  }
  if(ui.folderId){
    return '<div class="empty"><h2>This folder is empty</h2><p>Drag a verse onto it, or use a verse’s menu to move it here.</p></div>';
  }
  return '<div class="empty"><span class="lamp">'+LAMP+'</span><h2>Begin with one verse</h2>'+
    '<p class="verse-q">“Your word is a lamp to my feet and a light to my path.” Psalm 119:105</p>'+
    '<p>Add a verse by its reference, or choose one from the library. Each one climbs eight short steps, from reading it to writing it from memory.</p>'+
    '<div class="actions" style="justify-content:center"><button class="btn primary" id="empty-add">Add a verse</button> <button class="btn" id="empty-lib">Browse library</button></div></div>';
}

function leafHtml(v){
  var unit=course && course.anchors && course.anchors[v.reference];
  return '<article class="leaf" aria-labelledby="leaf-ref">'+
    '<header class="leaf-head"><span id="leaf-ref">'+esc(v.reference)+'</span>'+(unit?'<span>'+esc(course.course)+' · '+esc(unit)+'</span>':'')+'</header>'+
    '<p class="ctx before" id="ctx-before" hidden></p>'+
    '<div class="leaf-verse'+(v.text?'':' loading')+'" id="leaf-verse">'+(v.text ? linesHtml(v.text) : 'Fetching the verse…')+'</div>'+
    '<p class="ctx after" id="ctx-after" hidden></p>'+
    '<p class="leaf-cite">'+esc(v.reference)+' (ESV)</p>'+
  '</article>';
}
function footHtml(v){
  // The tools come in two groups, kept whole when the line wraps: ways to take in the verse, then places to take it.
  var status, primary, p=parseRef(v.reference), see=[], go=[];
  if(byHeart(v)){
    var r=reviewOf(v), due=isDue(v);
    status='<span class="fl">'+FLEURON+'</span><span><b>By heart</b> since '+esc(fmtDate(v.masteredAt))+'</span>'+
      '<span>'+(due?'Ready to say again today':'Comes back '+esc(fmtDay(r.next)))+'</span>';
    primary='<button class="btn primary big" id="go-review">Say it again</button>'+
      '<button class="btn quiet" id="go-refresh">'+ICON.retry+' Practise again</button>';
  } else {
    var at=v.currentStep||0;
    status=ladderHtml(at,"",at)+'<span><b>Step '+Math.min(at+1,8)+' of 8</b> · '+esc(STEPS[Math.min(at,7)].name)+'</span>';
    primary='<button class="btn primary big" id="go-practice" data-practice="'+v.id+'">'+(at>0?"Continue practice":"Start practice")+'</button>';
  }
  see.push('<button class="btn quiet" id="t-listen" aria-pressed="'+(ui.panel==="listen")+'">'+ICON.listen+' Listen</button>');
  see.push('<button class="btn quiet" id="t-orig" aria-pressed="'+(ui.panel==="original")+'">'+ICON.orig+' In '+(isHebrew(v.reference)?"Hebrew":"Greek")+'</button>');
  if(p) see.push('<button class="btn quiet" id="t-chap" aria-pressed="'+(ui.panel==="chapter")+'">'+ICON.book+' Read '+esc(chapterName(p))+'</button>');
  if(window.Passage) go.push('<button class="btn quiet" id="t-ask">'+ICON.ask+' Ask about it</button>');
  go.push('<button class="btn quiet" id="t-card">'+ICON.print+' Print card</button>');
  if(isTeacher()) go.push('<button class="btn quiet" id="t-recite">'+ICON.people+' Recite together</button>');
  if(isTeacher() && window.Passage) go.push('<button class="btn quiet" id="t-unit" aria-haspopup="true" aria-expanded="false">'+ICON.unit+' Add to a unit</button>');
  return '<div class="leaf-foot"><div class="status">'+status+'</div>'+
    '<div class="actions">'+primary+'</div><div class="tools"><div class="tgroup" role="group" aria-label="The verse">'+see.join("")+
    '</div><div class="tgroup" role="group" aria-label="Take it elsewhere">'+go.join("")+'</div></div></div>';
}
// The verses either side, faint, so a verse is learned in its place (rule B1).
function hydrateLeaf(v){
  if(!v.text){
    ensureText(v).then(function(t){
      if(ui.view!=="home" || ui.selectedId!==v.id) return;
      var el=$("leaf-verse"); if(el){ el.classList.remove("loading"); el.innerHTML=t?linesHtml(t):"The verse couldn’t be fetched. Try again in a minute."; }
      renderList(ui.folderId?folderById(ui.folderId):null, scoped().filter(function(x){ return !byHeart(x); }), scoped().filter(byHeart),
        (ui.tab==="heart"?scoped().filter(byHeart):scoped().filter(function(x){ return !byHeart(x); })).sort(cmpVerse));
    }).catch(function(){ var el=$("leaf-verse"); if(el && ui.selectedId===v.id) el.textContent="The verse couldn’t be fetched. Try again in a minute."; });
  }
  var p=parseRef(v.reference); if(!p) return;
  fetchChapter(v.reference).then(function(c){
    if(!c || ui.view!=="home" || ui.selectedId!==v.id) return;
    var before=c.verses.filter(function(x){ return x.n===p.v1-1; })[0], after=c.verses.filter(function(x){ return x.n===p.v2+1; })[0];
    if(before && $("ctx-before")){ $("ctx-before").innerHTML='<sup>'+before.n+'</sup>'+esc(before.text.replace(/\s+/g," ")); $("ctx-before").hidden=false; }
    if(after && $("ctx-after")){ $("ctx-after").innerHTML='<sup>'+after.n+'</sup>'+esc(after.text.replace(/\s+/g," ")); $("ctx-after").hidden=false; }
    if(p.v2>p.v1 && $("leaf-verse")){   // a passage shows its verse numbers
      $("leaf-verse").innerHTML=c.verses.filter(function(x){ return x.n>=p.v1 && x.n<=p.v2; }).map(function(x){ return linesHtml(x.text, x.n); }).join("");
    }
  });
}

function wireHome(v){
  if($("day-week")) $("day-week").onclick=function(){
    var ref=course.current.reference, have=verseByRef(ref);
    if(!have){ have=newVerse(ref); db.verses.push(have); save(); fillTexts(); toast("Added "+ref); }
    ui.tab=byHeart(have)?"heart":"learning"; ui.folderId=have.folderId||null; ui.selectedId=have.id; ui.panel=null; render();
  };
  if($("day-review")) $("day-review").onclick=function(){ startReview(dueVerses()); };
  if($("empty-add")) $("empty-add").onclick=addVerseModal;
  if($("empty-lib")) $("empty-lib").onclick=libraryModal;
  if(!v) return;
  if($("go-practice")) $("go-practice").onclick=function(){ startPractice(v.id); };
  if($("go-review")) $("go-review").onclick=function(){ startReview([v]); };
  if($("go-refresh")) $("go-refresh").onclick=function(){ startPractice(v.id, {initialStep:5, isRefresh:true}); };
  $("t-listen").onclick=function(){ togglePanel("listen", v); };
  $("t-orig").onclick=function(){ togglePanel("original", v); };
  if($("t-chap")) $("t-chap").onclick=function(){ togglePanel("chapter", v); };
  $("t-card").onclick=function(){ printCards([v]); };
  if($("t-recite")) $("t-recite").onclick=function(){ openRecite(v, $("t-recite")); };
  if($("t-ask")) $("t-ask").onclick=function(){ Passage.ask(v.reference); };
  if($("t-unit")) $("t-unit").onclick=function(){
    Passage.addToUnit({kind:"passage", ref:{ref:v.reference, translation:"ESV"}, label:v.reference+" (ESV)"}, $("t-unit")); };
  if($("day-offer")) $("day-offer").onclick=function(){
    var ref=ui.offer, have=verseByRef(ref); ui.offer=null;
    if(!have){ have=newVerse(ref); db.verses.push(have); save(); fillTexts(); toast("Added "+ref); }
    ui.tab=byHeart(have)?"heart":"learning"; ui.folderId=have.folderId||null; ui.selectedId=have.id; ui.panel=null; render();
  };
}

// ---------------------------------------------------------------- the panels under a verse: listen, the original, the chapter
function togglePanel(name, v){
  ui.panel = ui.panel===name ? null : name;
  ["listen","original","chapter"].forEach(function(k){
    var b=$({listen:"t-listen",original:"t-orig",chapter:"t-chap"}[k]); if(b) b.setAttribute("aria-pressed", String(ui.panel===k));
  });
  if(!ui.panel){ $("panel").innerHTML=""; stopAudio(); return; }
  openPanel(ui.panel, v, false);
}
function openPanel(name, v, quiet){
  var el=$("panel"); if(!el) return;
  if(name==="listen"){
    el.innerHTML='<section class="panel" aria-labelledby="pn-h"><div class="panel-head"><h2 id="pn-h">Listen</h2></div>'+playerHtml()+'</section>';
    wirePlayer(v);
  } else if(name==="original"){
    var lang=isHebrew(v.reference)?"Hebrew":"Greek";
    el.innerHTML='<section class="panel" aria-labelledby="pn-h"><div class="panel-head"><h2 id="pn-h">'+esc(v.reference)+' in '+lang+'</h2></div><p class="note">Loading the library’s '+lang+' text…</p></section>';
    fetchOriginal(v.reference).then(function(d){
      if(ui.panel!=="original" || !$("panel")) return;
      if(d===false){ $("panel").innerHTML='<section class="panel"><p class="note">The library has no '+lang+' text for '+esc(v.reference)+'.</p></section>'; return; }
      if(!d){ panelRetry("The "+lang+" couldn’t be loaded just now.", function(){ openPanel("original", v, true); }); return; }
      var words=d.words.map(function(w,i){ return '<button type="button" data-ow="'+i+'" aria-pressed="false">'+esc(w.word)+'</button>'; }).join("");
      $("panel").innerHTML='<section class="panel" aria-labelledby="pn-h"><div class="panel-head"><h2 id="pn-h">'+esc(v.reference)+' in '+esc(d.language)+'</h2></div>'+
        '<div class="orig" dir="'+d.dir+'">'+words+'</div><div id="gloss" aria-live="polite"></div>'+
        '<p class="note">From the library’s tagged '+esc(d.language)+' text. Choose a word to see what it means.</p></section>';
      $("panel").querySelectorAll("[data-ow]").forEach(function(b){
        b.onclick=function(){
          $("panel").querySelectorAll("[data-ow]").forEach(function(x){ x.setAttribute("aria-pressed","false"); });
          b.setAttribute("aria-pressed","true");
          var w=d.words[+b.getAttribute("data-ow")], bare=function(x){ return String(x||"").replace(/[.,;:?!·;׃]+$/,""); };
          $("gloss").innerHTML='<div class="gloss"><span class="gw">'+esc(bare(w.word))+'</span><span class="gt">'+esc(bare(w.translit))+'</span>'+
            '<span class="gg">'+esc(bare(w.gloss))+'</span><span class="gd">'+esc(w.definition||"")+(w.strongs?' <span class="gs">'+esc(w.strongs)+'</span>':'')+'</span></div>';
        };
      });
    });
  } else if(name==="chapter"){
    var p=parseRef(v.reference), title=chapterName(p);
    el.innerHTML='<section class="panel" aria-labelledby="pn-h"><div class="panel-head"><h2 id="pn-h">'+esc(title)+' (ESV)</h2></div><p class="note">Fetching the chapter…</p></section>';
    fetchChapter(v.reference).then(function(c){
      if(ui.panel!=="chapter" || !$("panel")) return;
      if(!c){ panelRetry("The chapter couldn’t be loaded just now.", function(){ openPanel("chapter", v, true); }); return; }
      var body=c.verses.map(function(x){
        var t='<sup>'+x.n+'</sup>'+esc(x.text.replace(/\s+/g," "))+' ';
        return (x.n>=p.v1 && x.n<=p.v2) ? '<mark class="here">'+t+'</mark>' : t;
      }).join("");
      $("panel").innerHTML='<section class="panel" aria-labelledby="pn-h"><div class="panel-head"><h2 id="pn-h">'+esc(title)+' (ESV)</h2></div><div class="chap" tabindex="0" role="region" aria-label="'+esc(title)+'">'+body+'</div></section>';
      var here=$("panel").querySelector(".here"), box=$("panel").querySelector(".chap");
      if(here && box) box.scrollTop=Math.max(0, here.offsetTop-box.offsetTop-60);
    });
  }
  if(!quiet){ var s=$("panel").querySelector("section"); if(s) s.scrollIntoView({block:"nearest", behavior:"smooth"}); }
}

function panelRetry(text, again){
  $("panel").innerHTML='<section class="panel"><p class="note" role="status">'+esc(text)+'</p><div class="actions" style="margin-top:10px"><button class="btn" id="pn-retry">Try again</button></div></section>';
  $("pn-retry").onclick=again;
}

// ---------------------------------------------------------------- the listening player
var audioEl=null;
function playerHtml(){
  return '<div class="player"><button type="button" class="play" id="pl-play" aria-label="Play">'+ICON.play+'</button>'+
    '<button type="button" class="btn" id="pl-slow" aria-pressed="false">Slower</button>'+
    '<button type="button" class="btn" id="pl-again">From the start</button><span class="msg" id="pl-msg" aria-live="polite"></span></div>';
}
function stopAudio(){ if(audioEl){ try{ audioEl.pause(); }catch(e){} } }
function wirePlayer(v){
  stopAudio();
  var play=$("pl-play"), slow=$("pl-slow"), again=$("pl-again"), msg=$("pl-msg");
  function show(on){ play.innerHTML=on?ICON.pause:ICON.play; play.setAttribute("aria-label", on?"Pause":"Play"); }
  function ready(){
    return fetchAudio(v.reference).then(function(url){
      if(!url) throw new Error("none");
      if(!audioEl){ audioEl=new Audio(); audioEl.preload="none"; }
      if(audioEl.dataset.ref!==v.reference){ audioEl.src=url; audioEl.dataset.ref=v.reference; }
      audioEl.playbackRate = slow.getAttribute("aria-pressed")==="true" ? 0.75 : 1;
      audioEl.onplay=function(){ show(true); }; audioEl.onpause=function(){ show(false); }; audioEl.onended=function(){ show(false); };
      return audioEl;
    });
  }
  play.onclick=function(){
    msg.textContent="";
    ready().then(function(a){ if(a.paused) a.play().catch(function(){ msg.textContent="The audio couldn’t start. Try again."; }); else a.pause(); })
      .catch(function(){ msg.textContent="Audio isn’t available for this passage right now."; });
  };
  slow.onclick=function(){ var on=slow.getAttribute("aria-pressed")!=="true"; slow.setAttribute("aria-pressed", String(on)); if(audioEl) audioEl.playbackRate=on?0.75:1; };
  again.onclick=function(){ ready().then(function(a){ a.currentTime=0; a.play().catch(function(){}); }).catch(function(){ msg.textContent="Audio isn’t available for this passage right now."; }); };
}

// ---------------------------------------------------------------- the list: a contents page of verses
function renderList(inFolder, learning, heart, shown){
  var h="", due=dueVerses();
  if(due.length && !ui.folderId && phone && phone.matches){
    h+='<div class="duerow"><span class="fl">'+FLEURON+'</span><span>'+due.length+' verse'+(due.length===1?"":"s")+' to say again today</span>'+
      '<button class="btn quiet" id="due-begin">Begin</button></div>';
  }
  if(inFolder){
    h+='<div class="crumbs"><a id="crumb-root" href="#">All verses</a> <span aria-hidden="true">›</span> <b>'+esc(inFolder.name)+'</b>'+
      ' <button class="icobtn" id="fld-rename" title="Rename folder" aria-label="Rename folder">'+ICON.pen+'</button></div>';
  }
  h+='<div class="toolbar"><div class="tabs" role="tablist" aria-label="Your verses">'+
    '<button role="tab" aria-selected="'+(ui.tab==="learning")+'" id="tab-learn">Learning<span class="cnt">'+learning.length+'</span></button>'+
    '<button role="tab" aria-selected="'+(ui.tab==="heart")+'" id="tab-heart">By heart<span class="cnt">'+heart.length+'</span></button>'+
    '</div><span style="flex:1"></span>'+(ui.folderId?'':'<button class="btn quiet" id="btn-folder">＋ Folder</button>')+'</div>';
  var rows="";
  if(!ui.folderId){
    db.folders.slice().sort(function(a,b){ return a.name.localeCompare(b.name); }).forEach(function(f){
      var cnt=db.verses.filter(function(v){ return v.folderId===f.id; }).length;
      rows+='<div class="frow" data-folder="'+f.id+'"><span class="fico2">'+ICON.folder+'</span>'+
        '<button type="button" class="fname2">'+esc(f.name)+'</button><span class="fcnt">'+cnt+'</span>'+
        '<button class="icobtn kebab" type="button" data-fmenu="'+f.id+'" aria-label="Folder options for '+esc(f.name)+'" title="Folder options">'+ICON.kebab+'</button></div>';
    });
  }
  var last=null;
  shown.forEach(function(v){
    var g=groupLabel(v);
    if(g!==last){ rows+='<div class="grp">'+esc(g)+'</div>'; last=g; }
    rows+=verseRow(v);
  });
  if(!shown.length) rows+='<div class="none">'+(ui.tab==="heart"?"A verse joins this list once you can write it from memory.":"No verses here yet.")+'</div>';
  $("verse-list").innerHTML=h+'<div class="vlist">'+rows+'</div>';
  wireList();
}
function verseRow(v){
  var heart=byHeart(v), due=isDue(v);
  var open=v.text ? v.text.replace(/\s+/g," ").trim().split(" ").slice(0,8).join(" ")+"…" : "";
  var mark=heart ? '<span class="fl" title="By heart">'+FLEURON+'</span>' : ladderHtml(v.currentStep||0, "small", -1);
  return '<div class="vrow'+(v.id===ui.selectedId?" sel":"")+'" draggable="true" data-vcard="'+v.id+'" data-select="'+v.id+'">'+
    '<button type="button" class="vref"'+(v.id===ui.selectedId?' aria-current="true"':'')+'>'+(due?'<span class="due" aria-hidden="true"></span>':'')+
      esc(v.reference)+'<span class="sr">'+(heart?(due?", by heart, ready to say again":", by heart"):", step "+Math.min((v.currentStep||0)+1,8)+" of 8")+'</span></button>'+
    (open?'<span class="open">'+esc(open)+'</span>':'')+
    '<span class="mark">'+mark+'</span>'+
    '<button class="icobtn kebab" type="button" data-vmenu="'+v.id+'" aria-label="Options for '+esc(v.reference)+'" title="Verse options">'+ICON.kebab+'</button></div>';
}

var phone=window.matchMedia?matchMedia("(max-width:640px)"):null;   // the verse list covers the page below this
function wireList(){
  if($("due-begin")) $("due-begin").onclick=function(){ startReview(dueVerses()); };
  if($("crumb-root")) $("crumb-root").onclick=function(e){ e.preventDefault(); ui.folderId=null; ui.selectedId=null; render(); };
  if($("fld-rename")) $("fld-rename").onclick=function(){ renameFolder(ui.folderId); };
  $("tab-learn").onclick=function(){ ui.tab="learning"; ui.selectedId=null; ui.panel=null; render(); };
  $("tab-heart").onclick=function(){ ui.tab="heart"; ui.selectedId=null; ui.panel=null; render(); };
  if($("btn-folder")) $("btn-folder").onclick=newFolderModal;
  document.querySelectorAll(".frow").forEach(function(el){
    var fid=el.getAttribute("data-folder");
    el.onclick=function(e){ if(e.target.closest("[data-fmenu]")||e.target.closest(".menu")) return; ui.folderId=fid; ui.tab="learning"; ui.selectedId=null; render(); };
    el.addEventListener("dragover",function(e){ e.preventDefault(); el.classList.add("drop"); });
    el.addEventListener("dragleave",function(){ el.classList.remove("drop"); });
    el.addEventListener("drop",function(e){ e.preventDefault(); el.classList.remove("drop");
      var vid=e.dataTransfer.getData("text/plain"); if(vid) moveVerse(vid, fid); });
  });
  document.querySelectorAll("[data-fmenu]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); openFolderMenu(b.getAttribute("data-fmenu"), b); };
  });
  document.querySelectorAll("[data-vmenu]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); openVerseMenu(b.getAttribute("data-vmenu"), b); };
  });
  document.querySelectorAll("[data-vcard]").forEach(function(el){
    var vid=el.getAttribute("data-vcard");
    el.addEventListener("dragstart",function(e){ e.dataTransfer.setData("text/plain",vid); e.dataTransfer.effectAllowed="move"; $("trash").classList.add("show"); });
    el.addEventListener("dragend",function(){ $("trash").classList.remove("show","drop"); });
  });
  wireRowSelect();
}
function wireRowSelect(){
  document.querySelectorAll("[data-select]").forEach(function(el){
    el.addEventListener("click",function(e){
      if(e.target.closest("[data-vmenu]")||e.target.closest(".menu")) return;
      var id=el.getAttribute("data-select");
      if(id!==ui.selectedId) ui.panel=null;
      ui.selectedId=id; ui.menuFor=null; stopAudio();
      if(phone && phone.matches) setDrawerOpen(false);   // on a phone, reveal the exercise once a verse is chosen
      render();
      if(e.detail===0){       // chosen from the keyboard: land on the verse's practice button
        var go=document.querySelector("#go-practice,#go-review"); if(go) go.focus();
      }
    });
  });
}
var trashEl=$("trash");
trashEl.addEventListener("dragover",function(e){ e.preventDefault(); trashEl.classList.add("drop"); });
trashEl.addEventListener("dragleave",function(){ trashEl.classList.remove("drop"); });
trashEl.addEventListener("drop",function(e){ e.preventDefault(); trashEl.classList.remove("show","drop"); var vid=e.dataTransfer.getData("text/plain"); if(vid) deleteVerse(vid); });

// ---------------------------------------------------------------- menus
function closeMenus(){ document.querySelectorAll(".menu").forEach(function(m){m.remove();}); ui.menuFor=null; }
function openVerseMenu(vid, anchor){
  closeMenus();
  var v=verseById(vid); if(!v) return;
  var card=anchor.closest(".vrow, .frow");
  var m=document.createElement("div"); m.className="menu";
  var folderItems = db.folders.slice().sort(function(a,b){return a.name.localeCompare(b.name);}).map(function(f){
    return '<button data-move="'+f.id+'">'+(v.folderId===f.id?"✓ ":"")+esc(f.name)+'</button>';
  }).join("");
  m.innerHTML =
    (isTeacher()?'<button data-recite>Recite together</button>':'')+
    '<button data-card>Print pocket card</button>'+
    (byHeart(v)?'<button data-back>Move back to Learning</button>':'')+
    '<div class="sep"></div><div class="lab">Move to folder</div>'+
    '<button data-move="__none__">'+(v.folderId==null?"✓ ":"")+"None (unfiled)"+'</button>'+ folderItems +
    '<div class="sep"></div><button class="danger" data-del="'+vid+'">Delete verse</button>';
  card.appendChild(m);
  m.querySelectorAll("[data-move]").forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); var t=b.getAttribute("data-move"); moveVerse(vid, t==="__none__"?null:t); };
  });
  if(m.querySelector("[data-recite]")) m.querySelector("[data-recite]").onclick=function(e){ e.stopPropagation(); closeMenus(); openRecite(v, anchor); };
  m.querySelector("[data-card]").onclick=function(e){ e.stopPropagation(); closeMenus(); printCards([v]); };
  if(m.querySelector("[data-back]")) m.querySelector("[data-back]").onclick=function(e){ e.stopPropagation(); closeMenus(); backToLearning(v); };
  m.querySelector("[data-del]").onclick=function(e){ e.stopPropagation(); deleteVerse(vid); };
  var first=m.querySelector("button"); if(first) first.focus();
}
function openFolderMenu(fid, anchor){
  closeMenus();
  var card=anchor.closest(".vrow, .frow");
  var m=document.createElement("div"); m.className="menu";
  m.innerHTML = '<button data-ren="'+fid+'">Rename</button><button class="danger" data-delf="'+fid+'">Delete folder</button>';
  card.appendChild(m);
  m.querySelector("[data-ren]").onclick=function(e){ e.stopPropagation(); renameFolder(fid); };
  m.querySelector("[data-delf]").onclick=function(e){ e.stopPropagation(); deleteFolder(fid); };
  m.querySelector("button").focus();
}
document.addEventListener("click",function(e){
  if(!e.target.closest(".menu") && !e.target.closest("[data-vmenu]") && !e.target.closest("[data-fmenu]")) closeMenus();
  if(!e.target.closest(".prefs") && !e.target.closest("#p-prefs") && !e.target.closest("#r-prefs")) closePrefs();
});
document.addEventListener("keydown",function(e){   // Escape closes an open menu (only), back to its kebab
  var m=document.querySelector(".menu"); if(e.key!=="Escape" || !m) return;
  var k=m.parentNode.querySelector(".kebab"), inMenu=m.contains(document.activeElement);
  closeMenus(); e.stopImmediatePropagation();
  if(inMenu && k) k.focus();
});

// ---------------------------------------------------------------- verse and folder actions
function moveVerse(vid, folderId){
  var v=verseById(vid); if(!v) return;
  v.folderId=folderId; save(); closeMenus(); render();
  toast(folderId ? ("Moved to "+(folderById(folderId)||{}).name) : "Moved to unfiled");
}
function deleteVerse(vid){
  var i=db.verses.findIndex(function(x){ return x.id===vid; }); if(i<0) return;
  var v=db.verses[i];
  db.verses.splice(i,1);
  if(ui.selectedId===vid) ui.selectedId=null;
  save(); closeMenus(); render();
  toast('Deleted "'+v.reference+'"', {undo:function(){
    db.verses.splice(Math.min(i, db.verses.length), 0, v); save(); render();
  }});
}
function backToLearning(v){
  var before={currentStep:v.currentStep, masteredAt:v.masteredAt, lastRefreshedAt:v.lastRefreshedAt, review:v.review};
  v.currentStep=4; v.masteredAt=null; v.lastRefreshedAt=null; v.review=null; save();
  ui.tab="learning"; ui.selectedId=v.id; render();
  toast("Back to Learning, at the first-letter steps.", {undo:function(){
    v.currentStep=before.currentStep; v.masteredAt=before.masteredAt; v.lastRefreshedAt=before.lastRefreshedAt; v.review=before.review;
    save(); ui.tab="heart"; render();
  }});
}
function deleteFolder(fid){
  var i=db.folders.findIndex(function(x){ return x.id===fid; }); if(i<0) return;
  var f=db.folders[i], wasOpen=ui.folderId===fid;
  var inside=db.verses.filter(function(v){ return v.folderId===fid; });
  inside.forEach(function(v){ v.folderId=null; });
  db.folders.splice(i,1);
  if(wasOpen) ui.folderId=null;
  save(); closeMenus(); render();
  toast('Deleted folder "'+f.name+'". Its verses are kept, unfiled.', {undo:function(){
    db.folders.splice(Math.min(i, db.folders.length), 0, f);
    inside.forEach(function(v){ v.folderId=fid; });
    if(wasOpen) ui.folderId=fid;
    save(); render();
  }});
}
async function renameFolder(fid){
  var f=folderById(fid); if(!f) return;
  closeMenus();
  var name=await Shell.ask({title:"Rename folder", ok:"Rename", input:{label:"Folder name", value:f.name, max:50},
    validate:function(t){ return t.length<1 ? "A folder needs a name." : ""; }});
  if(name==null) return;
  f.name=name; save(); render();
}

// ---------------------------------------------------------------- dialogs
var modalOpener=null;
function openModal(html, label){
  modalOpener=document.activeElement;
  $("modal").innerHTML=html; $("modal").setAttribute("aria-label", label||"Dialog"); $("scrim").classList.add("show");
}
function closeModal(){
  $("scrim").classList.remove("show"); $("modal").innerHTML="";
  if(modalOpener && modalOpener.isConnected) modalOpener.focus();
}
$("scrim").addEventListener("click",function(e){ if(e.target===$("scrim")) closeModal(); });
document.addEventListener("keydown",function(e){ if(e.key==="Escape" && $("scrim").classList.contains("show")){ e.preventDefault(); closeModal(); } });

async function newFolderModal(){
  var name=await Shell.ask({title:"New folder", body:"Group verses that belong together.", ok:"Create",
    input:{label:"Folder name", value:"", max:50}, validate:function(t){ return t.length<1 ? "A folder needs a name." : ""; }});
  if(name==null) return;
  db.folders.push({ id:"f"+uid(), name:name }); save(); render();
}

function addVerseModal(){
  openModal('<h2>Add a verse</h2><p class="hint">Write a reference, such as <b>John 3:16</b> or <b>Romans 8:1-4</b>. Exegetica fetches the ESV text.</p>'+
    '<label class="field"><span>Reference</span><input type="text" id="a-ref" placeholder="John 3:16" autocomplete="off"></label>'+
    '<p class="hint" id="a-err" role="alert" style="color:var(--err);margin:-6px 0 10px" hidden></p>'+
    '<div class="row"><button class="btn ghost" id="a-cancel">Cancel</button><button class="btn primary" id="a-save">Add verse</button></div>', "Add a verse");
  $("a-cancel").onclick=closeModal;
  $("a-ref").addEventListener("keydown",function(e){ if(e.key==="Enter") $("a-save").click(); });
  function err(t){ var el=$("a-err"); el.textContent=t; el.hidden=!t; }
  $("a-save").onclick=function(){
    var ref=$("a-ref").value.trim();
    if(!parseRef(ref)){ err("Write the book, chapter and verse, such as John 3:16."); return; }
    if(hasRef(ref)){ err("That reference is already in your list."); return; }
    var btn=$("a-save"); btn.disabled=true; btn.textContent="Adding…";
    fetchText(ref).then(function(text){
      var v=newVerse(ref, ui.folderId); v.text=text||null;
      db.verses.push(v); save(); closeModal(); ui.tab="learning"; ui.selectedId=v.id; ui.panel=null; render();
      toast(text ? ("Added "+ref) : ("Added "+ref+". Its text loads when it can."));
    }).catch(function(){
      var v=newVerse(ref, ui.folderId); db.verses.push(v); save(); closeModal(); ui.tab="learning"; ui.selectedId=v.id; render();
      toast("Added "+ref+". The ESV couldn’t be reached, so its text loads later.");
    });
  };
  setTimeout(function(){ $("a-ref").focus(); },30);
}

function libraryModal(){
  var rows = LIBRARY.map(function(ref){
    return '<div class="librow"><span class="lref">'+esc(ref)+'</span>'+
      (hasRef(ref) ? '<span class="added">Added</span>' : '<button class="btn" data-libadd="'+esc(ref)+'">Add</button>')+'</div>';
  }).join("");
  openModal('<h2>Library</h2><p class="hint">Passages worth knowing by heart. Adding one fetches its ESV text.</p>'+
    '<div class="liblist">'+rows+'</div><div class="row"><button class="btn primary" id="l-done">Done</button></div>', "Library");
  $("l-done").onclick=function(){ closeModal(); render(); };
  $("modal").querySelectorAll("[data-libadd]").forEach(function(b){
    b.onclick=function(){
      var ref=b.getAttribute("data-libadd"); if(hasRef(ref)) return;
      b.disabled=true; b.textContent="…";
      fetchText(ref).then(function(t){ addFromLib(ref,t,b); }).catch(function(){ addFromLib(ref,null,b); });
    };
  });
  setTimeout(function(){ var f=$("modal").querySelector("button"); if(f) f.focus(); },30);
}
function addFromLib(ref, text, btn){
  var v=newVerse(ref, ui.folderId); v.text=text||null;
  db.verses.push(v); save();
  var row=btn.closest(".librow"); if(row){ btn.remove(); var s=document.createElement("span"); s.className="added"; s.textContent="Added"; row.appendChild(s); }
  toast("Added "+ref);
}

// ================================================================ PRACTICE: the fading page
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

var recognition=null, recogSupported=false;
(function setupRecog(){
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR) return;
  recogSupported=true;
  recognition=new SR();
  recognition.continuous=true; recognition.interimResults=true; recognition.lang="en-US";
  recognition.onresult=function(ev){
    var t=""; for(var i=0;i<ev.results.length;i++) t+=ev.results[i][0].transcript+" ";
    var who = practice || review;
    if(who){ who.input=t; who.spoken=true; if(practice) updatePractice(); else updateReview(); }
  };
  function ended(){ if(practice) practice.listening=false; if(review) review.listening=false; updateMic(); }
  recognition.onend=ended; recognition.onerror=ended;
})();
function micOn(){ return !!((practice && practice.listening) || (review && review.listening)); }
function toggleMic(){
  if(!recogSupported) return;
  var who=practice||review; if(!who) return;
  if(who.listening){ try{ recognition.stop(); }catch(e){} who.listening=false; }
  else { who.input=""; who.spoken=true; try{ recognition.start(); who.listening=true; }catch(e){} if(practice) updatePractice(); else updateReview(); }
  updateMic();
}
function stopMic(){ if(recognition && micOn()){ try{ recognition.stop(); }catch(e){} } if(practice) practice.listening=false; if(review) review.listening=false; }
function updateMic(){
  var mic=$("a-mic"), lab=$("a-miclab"); if(!mic) return;
  var on=micOn();
  mic.classList.toggle("on", on); mic.setAttribute("aria-pressed", String(on));
  mic.setAttribute("aria-label", on?"Stop listening":"Start speaking");
  if(lab) lab.textContent = !recogSupported ? "Speech isn’t available in this browser." : (on ? "Listening. Tap to stop." : "Tap to speak");
}

function modeFor(s){
  if(s.mode==="first") return "first";
  if(s.mode==="shape") return prefs.shape==="blank" ? "blank" : "shape";
  if(s.type==="speak") return "say";
  if(s.type==="type") return "type";
  return "full";
}
function startPractice(vid, opts){
  opts=opts||{};
  var v=verseById(vid); if(!v) return;
  var idx = opts.initialStep ? opts.initialStep-1 : Math.min(Math.max(0, v.currentStep||0), 7);
  practice = { verse:v, idx:Math.min(Math.max(idx,0),7), isRefresh:!!opts.isRefresh, input:"", spoken:false, listening:false,
    hints:{}, success:false, prevMode:null, tk:v.text?tokens(v.text):null, said:0 };
  ui.view="practice"; closeMenus(); stopAudio();
  if(!v.text) ensureText(v).then(function(){ if(practice && practice.verse===v){ practice.tk=tokens(v.text); render(); } }).catch(function(){});
  render();
}
function exitPractice(){
  stopMic(); stopAudio();
  var v=practice && practice.verse;
  practice=null; ui.view="home"; if(v) ui.selectedId=v.id; render();
  var go=document.querySelector("#go-practice,#go-review"); if(go) go.focus();
}
function instruction(s){
  if(s.mode==="shape" && prefs.shape==="blank") return s.type==="speak" ? "Say it from memory." : "Write it from memory.";
  return s.say;
}
function renderPractice(){
  var v=practice.verse, s=STEPS[practice.idx], tk=practice.tk;
  setFocus(true);
  var mode=modeFor(s), from=practice.prevMode||mode;
  var head='<div class="pr-top">'+
      '<button class="btn ghost" id="p-exit">'+ICON.back+' Done</button>'+
      '<div class="pr-mid"><div class="pr-ref" id="p-ref">'+esc(v.reference)+'</div>'+ladderHtml(practice.idx, "", practice.idx)+'</div>'+
      '<div class="tools">'+
        '<button class="icobtn" id="p-back" title="Previous step" aria-label="Previous step"'+(practice.idx>0?'':' disabled')+'>'+ICON.back+'</button>'+
        '<button class="icobtn" id="p-retry" title="Start this step over" aria-label="Start this step over">'+ICON.retry+'</button>'+
        '<button class="icobtn" id="p-prefs" title="Practice settings" aria-label="Practice settings" aria-expanded="false">'+ICON.prefs+'</button>'+
      '</div></div>'+
    '<p class="pr-say" id="p-say" tabindex="-1"><span class="n">'+(practice.isRefresh?"Practising again · ":"")+'Step '+s.id+' of 8 · '+esc(s.name)+'</span>'+esc(instruction(s))+'</p>';
  var page = tk ? '<div class="page m-'+from+(prefs.size==="large"?" large":"")+'" id="pg" aria-hidden="true">'+pageHtml(tk,{sweep:true})+'</div><p class="sr" id="pg-sr">'+esc(srText(s, tk))+'</p>'
                : '<p class="note" style="text-align:center">Fetching the verse…</p>';
  $("view").innerHTML='<div class="pr">'+head+'<div class="sheet">'+page+'</div><div class="pr-act'+((tk && tk.words.length>40 && (s.type==="type"||s.type==="speak"))?" stick":"")+'" id="act">'+(tk?actHtml(s):"")+'</div>'+
    '<div class="proof" id="proof" hidden></div></div>';
  if(tk && from!==mode){
    requestAnimationFrame(function(){ requestAnimationFrame(function(){ var pg=$("pg"); if(pg){ pg.classList.remove("m-"+from); pg.classList.add("m-"+mode); } }); });
  }
  practice.prevMode=mode;
  $("p-exit").onclick=exitPractice;
  $("p-back").onclick=stepBack;
  $("p-retry").onclick=stepRetry;
  $("p-prefs").onclick=function(e){ e.stopPropagation(); togglePrefs(); };
  if(tk){ wireAct(s); updatePractice(); }
  var target = s.type==="type" ? $("a-input") : $("p-say");
  if(target) target.focus({preventScroll:true});
}
function srText(s, tk){
  if(s.mode==="full") return practice.verse.text.replace(/\s+/g," ");
  if(s.mode==="first") return "First letters: "+tk.words.map(function(w){ return w.f; }).join(" ")+".";
  return "The verse is hidden. It has "+tk.words.length+" words.";
}
function actHtml(s){
  var nextName = practice.idx<7 ? STEPS[practice.idx+1].name : null;
  if(s.type==="read"){
    return '<div class="row"><button class="btn primary big wide" id="a-next">I’ve read it</button></div>';
  }
  if(s.type==="listen"){
    return playerHtml()+'<div class="row"><button class="btn primary big wide" id="a-next">Next: '+esc(nextName)+'</button></div>';
  }
  var h="";
  if(s.type==="speak"){
    h+='<button type="button" class="mic" id="a-mic" aria-pressed="false" aria-label="Start speaking"'+(recogSupported?'':' disabled')+'>'+ICON.mic+'</button>'+
       '<p class="miclab" id="a-miclab">'+(recogSupported?"Tap to speak":"Speech isn’t available in this browser.")+'</p>'+
       '<p class="heard" id="a-heard"></p>';
  } else {
    h+='<label class="sr" for="a-input">Write '+esc(practice.verse.reference)+'</label>'+
       '<textarea class="write" id="a-input" rows="2" placeholder="Write it here" autocomplete="off" autocapitalize="sentences" spellcheck="false"></textarea>';
  }
  h+='<p class="count" id="a-count" aria-hidden="true"></p><div id="a-adv"></div>'+
     '<div class="row"><button type="button" class="btn ghost" id="a-hint">Show the next word</button>'+
     (s.type==="type"?'<button type="button" class="btn ghost" id="a-proof" disabled>Show me where I slipped</button>':'')+'</div>';
  return h;
}
function wireAct(s){
  if($("a-next")) $("a-next").onclick=stepNext;
  if(s.type==="listen") wirePlayer(practice.verse);
  if($("a-mic")) $("a-mic").onclick=toggleMic;
  if($("a-hint")) $("a-hint").onclick=giveHint;
  if($("a-proof")) $("a-proof").onclick=function(){ toggleProof($("a-proof")); };
  var ta=$("a-input");
  if(ta){
    ta.oninput=function(){ practice.input=ta.value; practice.spoken=false; ta.style.height="auto"; ta.style.height=ta.scrollHeight+"px"; updatePractice(); };
    ta.onkeydown=function(e){ if(e.key==="Enter" && !e.shiftKey && practice.success){ e.preventDefault(); stepNext(); } };
  }
}
var _sayTimer=null;
function updatePractice(){
  if(!practice || !practice.tk) return;
  var s=STEPS[practice.idx], W=practice.tk.words;
  if(s.type!=="speak" && s.type!=="type") return;
  var a=align(W, practice.input, practice.spoken);
  var pg=$("pg");
  if(pg){
    var long=W.length>40, curPh = a.ptr<W.length ? W[a.ptr].ph : -1;
    pg.querySelectorAll(".w").forEach(function(el){
      var i=+el.getAttribute("data-i"), m=a.marks[i];
      el.classList.toggle("ink", m===1);
      el.classList.toggle("slip", m===2);
      el.classList.toggle("hint", !!practice.hints[i] && m!==1);
      el.classList.toggle("cur", i===a.ptr && practice.input.length>0);
      el.classList.toggle("on", long && W[i].ph===curPh);
    });
  }
  if(a.inked>practice.said && prefs.haptics && navigator.vibrate){ try{ navigator.vibrate(8); }catch(e){} }
  if(a.inked!==practice.said){
    practice.said=a.inked;
    clearTimeout(_sayTimer); _sayTimer=setTimeout(function(){ if(practice) say(a.inked+" of "+W.length+" words"); }, 1400);
  }
  var cnt=$("a-count"); if(cnt) cnt.textContent = practice.input ? a.inked+" of "+W.length+" words" : "";
  var heard=$("a-heard"); if(heard) heard.textContent = (practice.spoken && practice.input) ? "“"+maskProfanity(practice.input.trim())+"”" : "";
  var close=similarity(cleanText(practice.input), cleanText(practice.verse.text))>=0.85;
  var was=practice.success;
  practice.success = close || (a.ptr===W.length && a.slips<=Math.max(1, Math.round(W.length*0.05)));
  if(practice.success && !was){ say(a.ptr===W.length && a.slips===0 ? "Word for word." : "Nearly there."); if(micOn() && recognition){ try{ recognition.stop(); }catch(e){} } }
  if(W.length>40 && pg){ var cur=pg.querySelector(".w.cur"); if(cur) keepInView(cur); }
  var adv=$("a-adv");
  if(adv){
    var label = practice.idx<7 ? "Next: "+STEPS[practice.idx+1].name : (practice.isRefresh?"Done":"Finish");
    var exact = a.ptr===W.length && a.slips===0;
    if(practice.success) adv.innerHTML=(exact ? '<p class="done">'+ICON.check+' Word for word.</p>'
        : '<p class="done near">Nearly. '+(a.slips||1)+' word'+((a.slips||1)===1?'':'s')+' slipped.</p>')+'<button class="btn primary big wide" id="a-next">'+esc(label)+'</button>';
    else if(practice.input.length>5 || (s.type==="speak" && !recogSupported)) adv.innerHTML='<button class="btn quiet wide" id="a-next">'+(s.type==="type"?"I wrote it, go on":"I said it, go on")+'</button>';
    else adv.innerHTML="";
    if($("a-next")) $("a-next").onclick=stepNext;
  }
  var pf=$("a-proof"); if(pf) pf.disabled = typedWords(practice.input).length<2;
  if($("proof") && !$("proof").hidden) renderProof();
}
// keep the current word in sight on a long passage, without jumping for every keystroke
var _viewTimer=null;
function keepInView(el){
  clearTimeout(_viewTimer);
  _viewTimer=setTimeout(function(){
    var r=el.getBoundingClientRect(), act=$("act"), bottom=act ? act.getBoundingClientRect().top : window.innerHeight;
    if(r.top<70 || r.bottom>bottom-16) el.scrollIntoView({block:"center", behavior:"smooth"});
  }, 120);
}
function giveHint(){
  if(!practice || !practice.tk) return;
  var a=align(practice.tk.words, practice.input, practice.spoken);
  var i=a.ptr; while(i<practice.tk.words.length && practice.hints[i]) i++;
  if(i>=practice.tk.words.length) return;
  practice.hints[i]=true; updatePractice();
  say("The next word is "+practice.tk.words[i].f+practice.tk.words[i].r+".");
}
function toggleProof(btn){
  var p=$("proof"); p.hidden=!p.hidden;
  if(btn) btn.textContent = p.hidden ? "Show me where I slipped" : "Hide the marks";
  if(!p.hidden) renderProof();
}
function renderProof(){
  var W=practice.tk.words;
  var B=String(practice.input||"").split(/\s+/).filter(Boolean).map(function(raw){ return { raw:raw, norm:normWord(raw) }; }).filter(function(b){ return b.norm; });
  var ops=diff(W, B), h="";
  var shown=function(w){ return esc(w.lead+w.f+w.r+w.trail); };
  ops.forEach(function(o){
    if(o.op==="eq") h+=shown(o.a)+" ";
    else if(o.op==="miss") h+='<ins title="Left out">'+shown(o.a)+'</ins> ';
    else if(o.op==="extra") h+='<del title="Not in the verse">'+esc(o.b.raw)+'</del> ';
    else h+='<span class="sub"><del>'+esc(o.b.raw)+'</del><ins>'+shown(o.a)+'</ins></span> ';
  });
  var errs=ops.filter(function(o){ return o.op!=="eq"; }).length;
  $("proof").innerHTML='<h3>Where it slipped</h3><div aria-live="polite">'+(errs ? h : 'Nothing to mark. It matches word for word.')+'</div>'+
    (errs?'<p class="key">‸ a word left out · a struck word is not in the verse · a small word above is what the verse says</p>':'');
}
function stepNext(){
  var v=practice.verse;
  stopMic(); stopAudio();
  if(!practice.isRefresh){
    v.currentStep=Math.max(v.currentStep||0, STEPS[practice.idx].id);
    v.lastPracticedAt=new Date().toISOString();
    if(v.currentStep>=8 && !v.masteredAt){ v.masteredAt=new Date().toISOString(); v.review={ level:0, next:addDays(null,1) }; }
    save();
  }
  if(practice.idx<7){
    practice.idx++; practice.input=""; practice.spoken=false; practice.hints={}; practice.success=false; practice.said=0;
    renderPractice();
    return;
  }
  if(practice.isRefresh){
    v.lastRefreshedAt=new Date().toISOString(); save();
    toast("Practised "+v.reference);
    exitPractice();
    return;
  }
  finished={ verse:v }; practice=null; ui.view="finished"; render();
}
function stepBack(){
  if(practice.idx>0){ stopMic(); stopAudio(); practice.idx--; practice.input=""; practice.spoken=false; practice.hints={}; practice.success=false; practice.said=0; renderPractice(); }
}
function stepRetry(){
  stopMic(); practice.input=""; practice.spoken=false; practice.hints={}; practice.success=false; practice.said=0;
  var ta=$("a-input"); if(ta){ ta.value=""; ta.style.height="auto"; ta.focus(); }
  $("proof").hidden=true; var pf=$("a-proof"); if(pf) pf.textContent="Show me where I slipped";
  updatePractice();
}

// ---------------------------------------------------------------- practice settings
function closePrefs(){ var p=document.querySelector(".prefs"); if(p){ p.remove(); var b=$("p-prefs")||$("r-prefs"); if(b) b.setAttribute("aria-expanded","false"); } }
function togglePrefs(){
  if(document.querySelector(".prefs")){ closePrefs(); return; }
  var b=$("p-prefs")||$("r-prefs"); if(!b) return;
  var box=document.createElement("div"); box.className="prefs"; box.setAttribute("role","group"); box.setAttribute("aria-label","Practice settings");
  box.innerHTML=
    '<fieldset><legend>The last two steps show</legend>'+
      '<label><input type="radio" name="pf-shape" value="lines"'+(prefs.shape==="lines"?" checked":"")+'> The verse’s shape, a line for each word</label>'+
      '<label><input type="radio" name="pf-shape" value="blank"'+(prefs.shape==="blank"?" checked":"")+'> Nothing at all</label></fieldset>'+
    '<fieldset><legend>Text</legend>'+
      '<label><input type="radio" name="pf-size" value="standard"'+(prefs.size==="standard"?" checked":"")+'> Standard</label>'+
      '<label><input type="radio" name="pf-size" value="large"'+(prefs.size==="large"?" checked":"")+'> Larger</label></fieldset>'+
    '<fieldset style="margin:0"><legend>On a phone</legend>'+
      '<label><input type="checkbox" id="pf-tap"'+(prefs.haptics?" checked":"")+'> A small tap when a word lands</label></fieldset>';
  b.parentNode.appendChild(box); b.setAttribute("aria-expanded","true");
  box.querySelectorAll('input[name="pf-shape"]').forEach(function(r){ r.onchange=function(){ prefs.shape=r.value; savePrefs(); if(practice) practice.prevMode=null; render(); }; });
  box.querySelectorAll('input[name="pf-size"]').forEach(function(r){ r.onchange=function(){ prefs.size=r.value; savePrefs(); render(); }; });
  $("pf-tap").onchange=function(){ prefs.haptics=this.checked; savePrefs(); };
  box.querySelector("input").focus();
}
document.addEventListener("keydown",function(e){ if(e.key==="Escape" && document.querySelector(".prefs")){ e.preventDefault(); closePrefs(); var b=$("p-prefs")||$("r-prefs"); if(b) b.focus(); } });

// ---------------------------------------------------------------- the finished verse
function renderFinished(){
  var v=finished.verse; setFocus(true);
  var tk=tokens(v.text), nxt=nextLearning(v);
  var words=tk.lines.map(function(ln){
    if(ln.gap) return '<span class="gap"></span>';
    return '<span class="ln'+(ln.ind?' ind':'')+'">'+ln.items.map(function(it){
      return it.punct ? esc(it.raw)+" " : '<span class="w" style="--d:'+Math.min(it.i*0.035,1.4).toFixed(2)+'s">'+esc(it.raw)+' </span>';
    }).join("")+'</span>';
  }).join("");
  $("view").innerHTML='<div class="fin" role="region" aria-labelledby="fin-k"><span class="fl">'+FLEURON+'</span>'+
    '<p class="kick" id="fin-k" tabindex="-1">By heart</p><blockquote>'+words+'</blockquote>'+
    '<p class="ref">'+esc(v.reference)+'</p>'+
    '<p class="note">You can write it from memory now. It comes back tomorrow, and then less and less often, so it stays.</p>'+
    '<div class="actions">'+(nxt?'<button class="btn primary big" id="f-next">Next verse: '+esc(nxt.reference)+'</button>':'')+
    '<button class="btn" id="f-home">Back to your verses</button></div></div>';
  if($("f-next")) $("f-next").onclick=function(){ finished=null; ui.selectedId=nxt.id; ui.tab="learning"; startPractice(nxt.id); };
  $("f-home").onclick=function(){ finished=null; ui.view="home"; ui.tab="heart"; ui.selectedId=v.id; render(); };
  $("fin-k").focus({preventScroll:true});
  say(v.reference+", by heart.");
}
function nextLearning(after){
  var learning=db.verses.filter(function(v){ return !byHeart(v) && v.id!==after.id; });
  if(!learning.length) return null;
  if(course && course.order){
    for(var i=0;i<course.order.length;i++){
      var ref=course.order[i], hit=learning.filter(function(v){ return normRef(v.reference)===normRef(ref); })[0];
      if(hit) return hit;
    }
  }
  return learning.slice().sort(cmpVerse)[0];
}

// ================================================================ REVIEW: a small stack of verses to say again
function startReview(list){
  if(!list || !list.length) return;
  review={ queue:list.map(function(v){ return v.id; }), i:0, how:recogSupported?"say":"write", input:"", spoken:false, listening:false, shown:false, tk:null };
  ui.view="review"; closeMenus(); stopAudio(); render();
  list.forEach(function(v){ if(!v.text) ensureText(v).then(function(){ if(review) render(); }).catch(function(){}); });
}
function exitReview(){ stopMic(); review=null; ui.view="home"; render(); }
function renderReview(){
  setFocus(true);
  if(review.i>=review.queue.length){
    $("view").innerHTML='<div class="fin"><span class="fl">'+FLEURON+'</span><p class="kick" id="rv-end" tabindex="-1">Said again</p>'+
      '<p class="note">That’s today’s. Each one comes back when it’s due.</p><div class="actions"><button class="btn primary" id="rv-home">Back to your verses</button></div></div>';
    $("rv-home").onclick=exitReview; $("rv-end").focus({preventScroll:true}); return;
  }
  var v=verseById(review.queue[review.i]); if(!v){ review.i++; renderReview(); return; }
  var tk=v.text ? tokens(v.text) : null; review.tk=tk;
  var left=review.queue.length-review.i;
  var mode = review.shown ? "full" : (prefs.shape==="blank" ? "blank" : "shape");
  var h='<div class="pr"><div class="pr-top"><button class="btn ghost" id="rv-x">'+ICON.back+' Done</button>'+
    '<div class="pr-ref">Say again · '+(review.i+1)+' of '+review.queue.length+'</div>'+
    '<div class="tools"><button class="icobtn" id="r-prefs" title="Practice settings" aria-label="Practice settings" aria-expanded="false">'+ICON.prefs+'</button></div></div>'+
    '<p class="pr-say" id="rv-say" tabindex="-1"><span class="n">'+esc(v.reference)+'</span>'+(review.shown?"Here it is. How did it go?":"Say it or write it from memory.")+'</p>'+
    '<div class="stack'+(left<=1?" one":"")+'"><div class="sheet in">'+
      (tk?'<div class="page m-'+mode+(prefs.size==="large"?" large":"")+'" id="pg" aria-hidden="true">'+pageHtml(tk)+'</div>'+
          '<p class="sr">'+(review.shown?esc(v.text.replace(/\s+/g," ")):"The verse is hidden. It has "+tk.words.length+" words.")+'</p>'
         :'<p class="note" style="text-align:center">Fetching the verse…</p>')+
    '</div></div><div class="pr-act">';
  if(!review.shown){
    h+='<div class="seg" role="group" aria-label="How to answer"><button type="button" id="rv-say-b" aria-pressed="'+(review.how==="say")+'"'+(recogSupported?'':' disabled')+'>Say it</button>'+
       '<button type="button" id="rv-write-b" aria-pressed="'+(review.how==="write")+'">Write it</button></div>';
    if(review.how==="say") h+='<button type="button" class="mic" id="a-mic" aria-pressed="false" aria-label="Start speaking">'+ICON.mic+'</button><p class="miclab" id="a-miclab">Tap to speak</p><p class="heard" id="a-heard"></p>';
    else h+='<label class="sr" for="a-input">Write '+esc(v.reference)+' from memory</label><textarea class="write" id="a-input" rows="2" placeholder="Write it here" autocomplete="off" spellcheck="false">'+esc(review.input)+'</textarea>';
    h+='<p class="count" id="a-count" aria-hidden="true"></p><div class="row"><button type="button" class="btn quiet" id="rv-show">Show the verse</button></div>';
  } else {
    var acc=tk ? similarity(cleanText(review.input), cleanText(v.text)) : 0;
    var sug = !review.input ? "" : acc>=0.95 ? "had" : acc>=0.75 ? "close" : "not";
    var names={had:"Had it",close:"Close",not:"Not yet"};
    h+='<div class="grades" role="group" aria-label="How did it go?">'+
      '<button class="btn'+(sug==="had"?" suggest":"")+'" data-grade="had">Had it</button>'+
      '<button class="btn'+(sug==="close"?" suggest":"")+'" data-grade="close">Close</button>'+
      '<button class="btn'+(sug==="not"?" suggest":"")+'" data-grade="not">Not yet</button></div>'+
      '<p class="count">'+(sug?"From what you "+(review.spoken?"said":"wrote")+", it looks like “"+names[sug]+"”. You choose.":"Choose how it went.")+'</p>';
  }
  h+='</div></div>';
  $("view").innerHTML=h;
  $("rv-x").onclick=exitReview;
  $("r-prefs").onclick=function(e){ e.stopPropagation(); togglePrefs(); };
  if($("rv-say-b")) $("rv-say-b").onclick=function(){ review.how="say"; review.input=""; renderReview(); };
  if($("rv-write-b")) $("rv-write-b").onclick=function(){ stopMic(); review.how="write"; review.input=""; renderReview(); };
  if($("a-mic")) $("a-mic").onclick=toggleMic;
  var ta=$("a-input");
  if(ta){ ta.oninput=function(){ review.input=ta.value; review.spoken=false; ta.style.height="auto"; ta.style.height=ta.scrollHeight+"px"; updateReview(); }; }
  if($("rv-show")) $("rv-show").onclick=function(){ stopMic(); review.shown=true; renderReview(); var g=document.querySelector("[data-grade]"); if(g) g.focus(); };
  document.querySelectorAll("[data-grade]").forEach(function(b){ b.onclick=function(){ grade(v, b.getAttribute("data-grade")); }; });
  if(!review.shown){ var t=ta||$("rv-say"); if(t) t.focus({preventScroll:true}); }
  updateReview();
}
function updateReview(){
  if(!review || !review.tk || review.shown) return;
  var W=review.tk.words, a=align(W, review.input, review.spoken), pg=$("pg");
  if(pg) pg.querySelectorAll(".w").forEach(function(el){ var i=+el.getAttribute("data-i"); el.classList.toggle("ink", a.marks[i]===1); el.classList.toggle("slip", a.marks[i]===2); });
  var cnt=$("a-count"); if(cnt) cnt.textContent = review.input ? a.inked+" of "+W.length+" words" : "";
  var heard=$("a-heard"); if(heard) heard.textContent = (review.spoken && review.input) ? "“"+maskProfanity(review.input.trim())+"”" : "";
  updateMic();
  if(a.ptr===W.length && a.slips===0 && review.input) stopMic();
}
function grade(v, g){
  var r=reviewOf(v), level=r.level||0, days;
  if(g==="had"){ level=Math.min(level+1, REVIEW_DAYS.length-1); days=REVIEW_DAYS[level]; }
  else if(g==="close"){ days=Math.max(1, Math.round(REVIEW_DAYS[level]/2)); }
  else { level=0; days=1; }
  v.review={ level:level, next:addDays(null, days) };
  v.lastRefreshedAt=new Date().toISOString(); save();
  say(v.reference+" comes back in "+days+" day"+(days===1?"":"s")+".");
  if(g==="not") toast(v.reference+" comes back tomorrow. Practise it from the first letters any time.");
  review.i++; review.input=""; review.spoken=false; review.shown=false; stopMic();
  renderReview();
}

// ================================================================ RECITE TOGETHER: the verse for a projector
var recite=null;
var RC_MODES=[["full","Full text"],["first","First letters"],["shape","Its shape"],["blank","Blank"]];
function openRecite(v, opener){
  ensureText(v).then(function(){
    if(!v.text) return;
    recite={ verse:v, i:0, opener:opener||document.activeElement };
    var el=$("recite"), tk=tokens(v.text);
    el.innerHTML='<div class="rc-stage"><div class="page m-full" id="rc-pg" aria-hidden="true">'+pageHtml(tk,{sweep:true})+'</div></div>'+
      '<div class="rc-bar"><span class="ref" id="rc-ref">'+esc(v.reference)+'</span><span class="mode" id="rc-mode" aria-live="polite">Full text</span>'+
      '<button class="btn" id="rc-prev">'+ICON.back+' Previous</button><button class="btn" id="rc-next">Next '+ICON.next+'</button>'+
      '<button class="btn" id="rc-done">Done</button></div>';
    el.hidden=false;
    if(el.requestFullscreen) el.requestFullscreen().catch(function(){});
    $("rc-prev").onclick=function(){ reciteStep(-1); };
    $("rc-next").onclick=function(){ reciteStep(1); };
    $("rc-done").onclick=closeRecite;
    $("rc-next").focus();
  }).catch(function(){ toast("The verse couldn’t be fetched. Try again in a minute."); });
}
function reciteStep(d){
  if(!recite) return;
  var pg=$("rc-pg"), from=RC_MODES[recite.i][0];
  recite.i=Math.max(0, Math.min(RC_MODES.length-1, recite.i+d));
  pg.classList.remove("m-"+from); pg.classList.add("m-"+RC_MODES[recite.i][0]);
  $("rc-mode").textContent=RC_MODES[recite.i][1];
}
function closeRecite(){
  if(!recite) return;
  var el=$("recite"); el.hidden=true; el.innerHTML="";
  if(document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(function(){});
  var o=recite.opener; recite=null; if(o && o.isConnected) o.focus();
}
document.addEventListener("keydown",function(e){
  if(!recite) return;
  if(e.key==="ArrowRight" || e.key==="PageDown" || (e.key===" " && e.target.tagName!=="BUTTON")){ e.preventDefault(); reciteStep(1); }
  else if(e.key==="ArrowLeft" || e.key==="PageUp"){ e.preventDefault(); reciteStep(-1); }
  else if(e.key==="Escape"){ e.preventDefault(); closeRecite(); }
  else if(e.key==="Tab"){   // focus stays inside while it is open
    var b=$("recite").querySelectorAll("button"), first=b[0], last=b[b.length-1];
    if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
    else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
  }
});

// ================================================================ PAPER: pocket cards and the memory book
function printModal(){
  var list=scoped(), learning=list.filter(function(v){ return !byHeart(v); }), heart=list.filter(byHeart);
  openModal('<h2>Print</h2><p class="hint">Verses travel well on paper. Cut the cards out and fold them in half, or print the verses you know by heart as a small book.</p>'+
    '<div class="choice" role="radiogroup" aria-label="What to print">'+
      '<label><input type="radio" name="pr-what" value="cards-l"'+(learning.length?' checked':' disabled')+'><span><b>Pocket cards, the verses you’re learning</b><small>'+learning.length+' card'+(learning.length===1?"":"s")+'. The front gives the first letters, the back the verse.</small></span></label>'+
      '<label><input type="radio" name="pr-what" value="cards-h"'+(heart.length?(learning.length?'':' checked'):' disabled')+'><span><b>Pocket cards, the verses you know by heart</b><small>'+heart.length+' card'+(heart.length===1?"":"s")+'.</small></span></label>'+
      '<label><input type="radio" name="pr-what" value="book"'+(heart.length?'':' disabled')+'><span><b>Your memory book</b><small>The verses you know by heart, one to a page, with a house cover you choose.</small></span></label>'+
    '</div><div class="row"><button class="btn ghost" id="pr-cancel">Cancel</button><button class="btn primary" id="pr-go">Continue</button></div>', "Print");
  $("pr-cancel").onclick=closeModal;
  $("pr-go").onclick=function(){
    var what=($("modal").querySelector('input[name="pr-what"]:checked')||{}).value;
    if(what==="cards-l"){ closeModal(); printCards(learning.slice().sort(cmpVerse)); }
    else if(what==="cards-h"){ closeModal(); printCards(heart.slice().sort(cmpVerse)); }
    else if(what==="book"){ coverModal(heart.slice().sort(function(a,b){ return new Date(a.masteredAt)-new Date(b.masteredAt); })); }
  };
  setTimeout(function(){ var c=$("modal").querySelector("input:checked")||$("pr-cancel"); if(c) c.focus(); },30);
}
function withTexts(list){
  var missing=list.filter(function(v){ return !v.text; });
  if(!missing.length) return Promise.resolve(list);
  return getJSON(API+"texts?refs="+encodeURIComponent(missing.map(function(v){ return v.reference; }).join("|"))).then(function(d){
    missing.forEach(function(v){ var t=d.texts && d.texts[v.reference]; if(t) v.text=t; }); save(); return list;
  }).catch(function(){ return list; });
}
function printNow(html, cls){
  var root=$("printroot"); root.className=cls; root.innerHTML=html;
  document.body.classList.add("printing");
  var imgs=[].slice.call(root.querySelectorAll("img")).map(function(im){ return im.complete ? Promise.resolve() : new Promise(function(r){ im.onload=im.onerror=r; }); });
  var faces = document.fonts ? [document.fonts.load('400 16px "EB Garamond"'), document.fonts.load('italic 400 16px "EB Garamond"'),
      document.fonts.load('400 30px "Fraunces"')].map(function(p){ return p.catch(function(){}); }) : [];
  Promise.all(imgs.concat(faces)).then(function(){ return document.fonts ? document.fonts.ready : null; }).then(function(){
    requestAnimationFrame(function(){ window.print(); });
  });
}
window.addEventListener("afterprint",function(){ document.body.classList.remove("printing"); $("printroot").innerHTML=""; });
function printCards(list){
  withTexts(list).then(function(list){
    var cards=list.filter(function(v){ return v.text; });
    var tooLong=cards.filter(function(v){ return v.text.split(/\s+/).length>120; });
    cards=cards.filter(function(v){ return v.text.split(/\s+/).length<=120; });
    if(!cards.length){ toast(tooLong.length ? "That passage is too long for a pocket card. Print it in your memory book instead." : "There’s no verse text to print yet."); return; }
    var html=cards.map(function(v){
      var n=v.text.split(/\s+/).length, fs = n<=40 ? "11pt" : n<=70 ? "9.5pt" : "8pt";
      return '<div class="card" style="--fs:'+fs+'">'+
        '<div class="half back"><p class="ref">'+esc(v.reference)+'</p><p class="txt">'+esc(v.text.replace(/\s+/g," "))+'</p><p class="cr">ESV</p></div>'+
        '<div class="half front"><p class="ref">'+esc(v.reference)+'</p><p class="fls">'+esc(firstLetters(v.text.replace(/\s+/g," ")))+'</p><span class="orn">'+FLEURON+'</span></div></div>';
    }).join("");
    if(tooLong.length) toast(tooLong.map(function(v){ return v.reference; }).join(", ")+" is too long for a card, so it was left out.");
    printNow('<div class="cards">'+html+'</div>', "print-cards");
  });
}
var coverOpts=null;
function coverModal(list){
  var theme=null, motif="universal";
  function src(){ return API+"cover?t="+encodeURIComponent(theme||"")+"&m="+encodeURIComponent(motif); }
  openModal('<h2>Your memory book</h2><p class="hint">'+list.length+' verse'+(list.length===1?"":"s")+', one to a page, in the order you learned them. Choose its cover.</p>'+
    '<div class="coverpick"><img id="cv-img" alt="The cover of your memory book, titled By Heart"><div>'+
      '<p class="hint" style="margin-bottom:6px">Cloth</p><div class="swatches" id="cv-sw" role="group" aria-label="Cloth colour"></div>'+
      '<label class="field"><span>Ornament</span><select id="cv-motif"><option value="universal">The Exegetica sprig</option></select></label></div></div>'+
    '<div class="row"><button class="btn ghost" id="cv-cancel">Cancel</button><button class="btn primary" id="cv-go">Print the book</button></div>', "Your memory book");
  $("cv-cancel").onclick=closeModal;
  function refresh(){ $("cv-img").src=src(); }
  var load = coverOpts ? Promise.resolve(coverOpts) : getJSON("/api/house-cover/options").then(function(o){ coverOpts=o; return o; });
  load.then(function(o){
    var themes=o.themes.filter(function(t){ return t.mode==="light"; }).slice(0, 12);
    theme = (o.house && o.house.light) || (themes[0] && themes[0].key);
    $("cv-sw").innerHTML=themes.map(function(t){
      return '<button type="button" data-th="'+esc(t.key)+'" aria-pressed="'+(t.key===theme)+'" title="'+esc(t.name)+'" aria-label="'+esc(t.name)+'" style="background:linear-gradient(135deg,'+esc(t.cloth)+' 55%,'+esc(t.foil)+' 55%)"></button>';
    }).join("");
    var motifs=o.motifs.filter(function(m){ return m.key==="universal" || /bibl|theolog|church|devot|relig|christ|psalm|scriptur/i.test(m.shelf+" "+m.subject); }).slice(0, 24);
    $("cv-motif").innerHTML=motifs.map(function(m){ return '<option value="'+esc(m.key)+'">'+esc(m.key==="universal"?"The Exegetica sprig":m.subject)+'</option>'; }).join("");
    $("cv-sw").querySelectorAll("[data-th]").forEach(function(b){ b.onclick=function(){ theme=b.getAttribute("data-th"); $("cv-sw").querySelectorAll("[data-th]").forEach(function(x){ x.setAttribute("aria-pressed", String(x===b)); }); refresh(); }; });
    $("cv-motif").onchange=function(){ motif=this.value; refresh(); };
    refresh();
  }).catch(function(){ refresh(); });
  $("cv-go").onclick=function(){ var url=src(); closeModal(); printBook(list, url); };
}
function printBook(list, coverUrl){
  withTexts(list).then(function(list){
    var verses=list.filter(function(v){ return v.text; });
    var years=verses.map(function(v){ return new Date(v.masteredAt||Date.now()).getFullYear(); });
    var lo=Math.min.apply(null,years), hi=Math.max.apply(null,years);
    var span=years.length ? (lo===hi ? String(lo) : lo+"–"+hi) : "";
    var html='<div class="book"><div class="bk-cover"><img src="'+esc(coverUrl)+'" alt=""></div>'+
      '<div class="bk-title"><h1>By Heart</h1><p>Scripture kept by heart'+(span?", "+esc(span):"")+'</p></div>'+
      verses.map(function(v){
        return '<div class="bk-page"><p class="txt">'+linesHtml(v.text)+'</p><p class="ref">'+esc(v.reference)+'</p>'+
          '<p class="kept">Kept '+esc(fmtDate(v.masteredAt))+'</p><span class="orn">'+FLEURON+'</span></div>';
      }).join("")+
      '<div class="bk-colophon"><p>'+esc(ESV_NOTICE)+'</p><p>Set and designed by Exegetica.</p></div></div>';
    printNow(html, "print-book");
  });
}

// ---------------------------------------------------------------- verse drawer
var sideEl=$("side");
function setDrawerOpen(o){
  sideEl.classList.toggle("open", !!o);
  var tb=$("menu-btn"), label=o?"Hide verses":"Show verses";
  if(tb){ tb.setAttribute("aria-expanded", o?"true":"false"); tb.setAttribute("aria-label", label); tb.title=label; }
  // wider screens dock the list beside the page (memory.css). On a phone it covers the page, so the page
  // waits behind it, out of reach, until the list closes.
  var col=document.querySelector(".app > .col"); if(col) col.inert = !!o && !!(phone && phone.matches);
}
if(phone && phone.addEventListener) phone.addEventListener("change", function(){ setDrawerOpen(sideEl.classList.contains("open")); });
function toggleDrawer(){ setDrawerOpen(!sideEl.classList.contains("open")); }
$("menu-btn").onclick=toggleDrawer;
$("drawer-close").onclick=function(){ setDrawerOpen(false); $("menu-btn").focus(); };
$("drawer-add").onclick=function(){ addVerseModal(); };
$("drawer-lib").onclick=function(){ libraryModal(); };
$("drawer-print").onclick=function(){ printModal(); };
document.addEventListener("keydown",function(e){
  if(e.key==="Escape" && !e.defaultPrevented && sideEl.classList.contains("open") && !$("scrim").classList.contains("show") && !recite && !document.querySelector(".prefs,.menu")){ setDrawerOpen(false); }
});
setDrawerOpen(true);   // start open so the verse list is the first thing you see

init();
})();
