/* "For your classes" on the Living Library (decision 0026): the school's texts for the courses a teacher
   teaches, each with its state (full text in the Reading Room, an outline only, or no text yet), the picker
   for those courses, and an outline's contents. Served by webapp/teacher_courses.py. */
(function(){
"use strict";
var el=function(id){return document.getElementById(id);};
var sec=el("classes");if(!sec)return;
var e=function(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");};
var D={courses:[],mine:[],works:[],saving:false},only="";
var dlg=el("cl-dlg"),opener=null;

function load(){
  fetch("/api/library/courses",{credentials:"same-origin"}).then(function(r){return r.ok?r.json():null;}).then(function(d){
    if(!d)return;            // not a teacher: the section stays hidden
    D=d;sec.hidden=false;render();
  }).catch(function(){});
}
function name(k){var c=D.courses.find(function(x){return x.key===k;});return c?c.name:k;}
function render(){
  el("classes-edit").textContent=D.mine.length?"Change your classes":"Choose your classes";
  if(!D.mine.length){
    el("cl-courses").innerHTML="";
    el("cl-works").innerHTML='<li class="cl-empty">Choose the classes you teach, and the school\'s books for them will wait here: the ones Exegetica can read in full, and the ones it knows by their contents.</li>';
    return;
  }
  if(only&&D.mine.indexOf(only)<0)only="";
  el("cl-courses").innerHTML=(D.mine.length>1?'<button type="button" data-c="" aria-pressed="'+(!only)+'">All your classes</button>':"")+
    D.mine.map(function(k){return '<button type="button" data-c="'+e(k)+'" aria-pressed="'+(only===k||D.mine.length===1)+'">'+e(name(k))+'</button>';}).join("");
  var ws=D.works.filter(function(w){return !only||w.courses.indexOf(only)>=0;});
  el("cl-works").innerHTML=ws.length?ws.map(card).join(""):'<li class="cl-empty">The school\'s book list names no texts for this class.</li>';
}
var STATE={text:["Full text","cl-text"],outline:["Outline only","cl-outline"],none:["No text yet","cl-none"]};
function card(w){
  var st=STATE[w.state]||STATE.none,act="";
  if(w.state==="text")act='<a class="cl-act" href="/read/'+encodeURIComponent(w.slug)+'">Read it</a>';
  else if(w.state==="outline")act='<button type="button" class="cl-act" data-outline="'+e(w.outline)+'" data-title="'+e(w.title)+'">See its outline</button>';
  return '<li class="cl-work"><span class="cl-state '+st[1]+'">'+st[0]+'</span><span class="cl-t">'+e(w.title)+'</span>'+
    (w.author?'<span class="cl-a">'+e(w.author)+'</span>':"")+'<span class="cl-c">'+e(w.course_names.join(", "))+'</span>'+
    (w.note&&w.state==="none"?'<span class="cl-n">'+e(w.note)+'</span>':"")+act+'</li>';
}
el("cl-courses").addEventListener("click",function(ev){var b=ev.target.closest("[data-c]");if(!b)return;only=b.getAttribute("data-c");render();
  var again=el("cl-courses").querySelector('[data-c="'+only+'"]');if(again)again.focus();});

function openDlg(title,html){el("cl-dlg-title").textContent=title;el("cl-dlg-body").innerHTML=html;opener=document.activeElement;
  if(!dlg.open)dlg.showModal();var f=el("cl-dlg-body").querySelector("input,button,a");if(f)f.focus();}
dlg.addEventListener("click",function(ev){if(ev.target===dlg||ev.target.closest("[data-close]"))dlg.close();});
dlg.addEventListener("close",function(){if(opener&&opener.isConnected)opener.focus();});

el("classes-edit").addEventListener("click",function(){
  var subjects={};D.courses.forEach(function(c){(subjects[c.subject]=subjects[c.subject]||[]).push(c);});
  openDlg("The classes you teach",'<form id="cl-form"><p class="cl-help">Your Living Library opens on these classes\' books. Change them whenever you like.</p>'+
    Object.keys(subjects).map(function(s){return '<fieldset><legend>'+e(s)+'</legend>'+subjects[s].map(function(c){
      return '<label><input type="checkbox" value="'+e(c.key)+'"'+(D.mine.indexOf(c.key)>=0?" checked":"")+'> '+e(c.name)+' <span class="cl-g">grades '+e(c.grades)+'</span></label>';}).join("")+'</fieldset>';}).join("")+
    '<p class="cl-err" role="alert" hidden></p><div class="cl-actions"><button type="button" class="btn-ghost" data-close>Cancel</button><button type="submit" class="cl-save">Save</button></div></form>');
  el("cl-form").onsubmit=function(ev){ev.preventDefault();
    var keys=[].slice.call(el("cl-form").querySelectorAll("input:checked")).map(function(x){return x.value;});
    fetch("/api/library/courses",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({courses:keys})})
      .then(function(r){return r.json().then(function(d){if(!r.ok)throw new Error(d.error||"That didn't save.");return d;});})
      .then(function(d){D.mine=d.mine;D.works=d.works;dlg.close();render();if(window.Shell)Shell.toast("Saved your classes");})
      .catch(function(err){var p=el("cl-form").querySelector(".cl-err");p.textContent=err.message;p.hidden=false;});
  };
});

el("cl-works").addEventListener("click",function(ev){
  var b=ev.target.closest("[data-outline]");if(!b)return;
  openDlg(b.getAttribute("data-title"),'<p class="cl-help">Loading its contents…</p>');
  fetch("/api/library/outline/"+encodeURIComponent(b.getAttribute("data-outline")),{credentials:"same-origin"}).then(function(r){return r.json();}).then(function(d){
    var o=d.outline;if(!o){el("cl-dlg-body").innerHTML='<p class="cl-help">'+e(d.error||"That outline didn't load.")+'</p>';return;}
    function walk(es){return '<ul>'+es.map(function(x){return '<li><span class="cl-ol">'+e([x.label,x.title].filter(Boolean).join(" "))+'</span>'+
      (x.covers?'<span class="cl-cov">'+e(x.covers)+(x.basis==="general"?' <span class="cl-gen" title="Written from general knowledge of the subject, not from the publisher\'s page">general</span>':"")+'</span>':"")+
      (x.children?walk(x.children):"")+'</li>';}).join("")+'</ul>';}
    el("cl-dlg-body").innerHTML='<p class="cl-help">'+e([(o.authors||[]).join(", "),o.publisher,o.edition].filter(Boolean).join(" · "))+'</p>'+
      '<p class="cl-help">Exegetica doesn\'t have this book\'s text. Drafts get these contents and what each part covers; a description marked “general” was written from knowledge of the subject, the rest from the publisher\'s or a school\'s page.'+
      (o.match&&o.match!=="exact edition"?" These contents come from "+e(o.match)+", so numbering may differ from the class copies.":"")+'</p>'+
      (o.summary?'<p class="cl-sum">'+e(o.summary)+'</p>':"")+(o.toc&&o.toc.length?walk(o.toc):"")+
      ((o.sources||[]).length?'<p class="cl-src">From: '+o.sources.map(function(s){return '<a href="'+e(s.url)+'" target="_blank" rel="noopener">'+e(s.what||"source")+'</a>';}).join(", ")+'</p>':"");
  }).catch(function(){el("cl-dlg-body").innerHTML='<p class="cl-help">That outline didn\'t load. Try again.</p>';});
});

load();
})();
