/* Moments in a Living Library video or podcast episode (decision 0026, webapp/excerpts.py): the published
   transcript when one exists, and the teacher's saved excerpts, each a time range with the words spoken there
   (or the teacher's own) and a note. Units draw on them through the Prep Room. */
(function(){
"use strict";
var e=function(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");};
function stamp(t){t=Math.max(0,Math.floor(t));var h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=t%60;
  return (h?h+":"+String(m).padStart(2,"0"):m)+":"+String(s).padStart(2,"0");}
function api(method,url,body){
  return fetch(url,{method:method,credentials:"same-origin",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined})
    .then(function(r){return r.json().catch(function(){return {};}).then(function(d){if(!r.ok)throw new Error(d.error||"That didn't work. Try again.");return d;});});
}
function lines(segs){   // about one line every 30 seconds, as the drafts see it
  var out=[],cur=[],start=null;
  segs.forEach(function(s){if(start===null)start=s.start;cur.push(s.text);if(s.end-start>=30){out.push({t:start,text:cur.join(" ")});cur=[];start=null;}});
  if(cur.length)out.push({t:start||0,text:cur.join(" ")});return out;
}

var M={item:null,box:null,episode:"",episodeTitle:"",data:null,mark:0};
var pending={};   // deletions still inside their Undo time, sent at once if the page closes
window.addEventListener("pagehide",function(){Object.keys(pending).forEach(function(k){clearTimeout(pending[k].t);fetch(pending[k].url,{method:"DELETE",credentials:"same-origin",keepalive:true});});pending={};});

function q(sel){return M.box?M.box.querySelector(sel):null;}
function mount(item,box){
  [].forEach.call(document.querySelectorAll(".moments"),function(other){if(other!==box)other.innerHTML="";});   // one panel at a time
  M.item=item;M.box=box;M.episode="";M.episodeTitle="";M.data=null;
  box.innerHTML='<h3 class="m-h">Moments</h3><p class="m-help">Save the parts of this '+(item.type==="video"?"video":"show")+
    ' you\'ll teach from. A unit in the Prep Room can draw on them.</p>'+
    (item.type==="podcast"?'<label class="m-lab" for="m-ep">Episode</label><select id="m-ep" class="m-in"><option value="">Loading the episodes…</option></select>':"")+
    '<div id="m-body"></div>';
  if(item.type==="podcast"){
    api("GET","/api/library/item/"+encodeURIComponent(item.id)+"/episodes").then(function(d){
      var sel=q("#m-ep");if(!sel)return;
      sel.innerHTML='<option value="">Choose an episode</option>'+d.episodes.map(function(x){
        return '<option value="'+e(x.guid)+'">'+e(x.title)+(x.date?" ("+e(x.date.slice(0,16))+")":"")+(x.has_transcript?" · transcript":"")+'</option>';}).join("");
      sel.onchange=function(){M.episode=sel.value;M.episodeTitle=sel.value?sel.options[sel.selectedIndex].text.replace(/ \(.*$/,""):"";load(true);};
      load(false);
    }).catch(function(err){q("#m-ep").innerHTML='<option value="">'+e(err.message)+'</option>';load(false);});
  }else load(true);
}

function load(lookUp){
  var url="/api/library/item/"+encodeURIComponent(M.item.id)+"/moments"+(M.episode?"?episode="+encodeURIComponent(M.episode):"");
  api("GET",url).then(function(d){M.data=d;
    if(!d.transcript&&!d.job&&lookUp&&(M.item.type==="video"||M.episode))return look(true);
    draw();watch();}).catch(function(err){q("#m-body").innerHTML='<p class="m-help">'+e(err.message)+'</p>';});
}
// First a free check for a published transcript; "Make a transcript" asks Gemini (decision 0028), and while it
// works the panel asks again every few seconds until the transcript is there or the job says why not.
function look(quiet,make){
  var body=q("#m-body"),btn=body&&body.querySelector(".m-make");if(make&&btn){btn.disabled=true;btn.textContent="Starting…";}
  api("POST","/api/library/item/"+encodeURIComponent(M.item.id)+"/transcript",{episode:M.episode||null,make:!!make}).then(function(d){
    if(d.transcript)M.data.transcript=d.transcript;else{if(d.missing)M.data.missing=d.missing;M.data.job=d.job||null;}
    draw();watch();
  }).catch(function(err){if(make){M.data.job={status:"failed",error:err.message};}draw();});
}
var watching=null;
function watch(){
  clearTimeout(watching);
  if(!M.data||M.data.transcript||!M.data.job||M.data.job.status!=="running")return;
  var box=M.box,item=M.item,episode=M.episode;
  watching=setTimeout(function(){
    if(!box.isConnected||M.box!==box||M.item!==item||M.episode!==episode)return;   // the panel moved on
    var url="/api/library/item/"+encodeURIComponent(item.id)+"/moments"+(episode?"?episode="+encodeURIComponent(episode):"");
    api("GET",url).then(function(d){M.data=d;draw();watch();
      if(d.transcript&&window.Shell)Shell.toast("The transcript is ready");}).catch(function(){watch();});
  },5000);
}

function draw(){
  var d=M.data,body=q("#m-body");if(!body||!d)return;
  var mine=d.excerpts.filter(function(x){return M.item.type==="video"||x.episode_key===M.episode;});
  var html="";
  if(M.item.type==="podcast"&&!M.episode){
    html+='<p class="m-help">Choose an episode to see its transcript, if the show publishes one, and to save its moments.</p>';
  }else{
    if(d.transcript){
      html+='<p class="m-help">Transcript ('+e(d.transcript.source)+'). Pick a line\'s time to set where a moment starts, then another to set where it ends.</p>'+
        '<ol class="m-tx">'+lines(d.transcript.segments).map(function(l){return '<li><button type="button" class="m-t" data-t="'+l.t+'">'+stamp(l.t)+'</button> '+e(l.text)+'</li>';}).join("")+'</ol>';
    }else if(d.job&&d.job.status==="running"){
      html+='<p class="m-help m-status" role="status">Gemini is writing the transcript. It takes a minute or two, and you can close this and come back.</p>';
    }else{
      var failed=d.job&&d.job.status==="failed";
      html+='<p class="m-help">'+e(failed?d.job.error:(d.missing||""))+(d.make&&!failed?" "+e(d.make):"")+'</p>'+
        '<button type="button" class="m-make">'+(failed?"Try again":"Make a transcript")+'</button>';
    }
    html+='<form class="m-form" id="m-form"><div class="m-row"><label>Starts <input id="m-s" class="m-in" inputmode="numeric" placeholder="2:14" autocomplete="off"></label>'+
      '<label>Ends <input id="m-e" class="m-in" inputmode="numeric" placeholder="3:05" autocomplete="off"></label></div>'+
      (d.transcript?"":'<label class="m-lab" for="m-q">The words (optional)</label><textarea id="m-q" class="m-in" rows="2" maxlength="2000" placeholder="What is said there, if you want it kept"></textarea>')+
      '<label class="m-lab" for="m-n">Note (optional)</label><input id="m-n" class="m-in" maxlength="1000" placeholder="Why it matters for your class" autocomplete="off">'+
      '<p class="m-err" role="alert" hidden></p><button type="submit" class="m-save">Save moment</button></form>';
  }
  html+='<h4 class="m-h4">Saved'+(mine.length?" ("+mine.length+")":"")+'</h4>'+(mine.length?'<ul class="m-list">'+mine.map(function(x){
    var when=stamp(x.start)+"–"+stamp(x.end);
    return '<li><span class="m-when">'+(x.link?'<a href="'+e(x.link)+'" target="_blank" rel="noopener">'+when+'</a>':when)+'</span>'+
      (x.quote?'<span class="m-q">“'+e(x.quote.length>280?x.quote.slice(0,278)+"…":x.quote)+'”</span>':"")+(x.note?'<span class="m-note">'+e(x.note)+'</span>':"")+
      '<span class="m-acts">'+(window.Passage&&Passage.teacher?'<button type="button" class="shell-tool sm m-unit" data-unit-moment="'+x.id+'" data-when="'+when+'" aria-haspopup="true" aria-expanded="false" aria-label="Add the moment at '+when+' to a unit">'+Passage.icons.prep+'Add to a unit</button>':"")+
      '<button type="button" class="m-del" data-del="'+x.id+'" aria-label="Delete the moment at '+when+'">Delete</button></span></li>';}).join("")+'</ul>':'<p class="m-help">None yet.</p>');
  body.innerHTML=html;
  var make=body.querySelector(".m-make");if(make)make.onclick=function(){look(false,true);};
  var form=q("#m-form");if(form)form.onsubmit=save;
  body.querySelectorAll("[data-t]").forEach(function(b){b.onclick=function(){var s=q("#m-s"),en=q("#m-e");
    if(!s.value||M.mark===2){s.value=b.textContent;en.value="";M.mark=1;}else{en.value=b.textContent;M.mark=2;}
    (M.mark===1?en:q("#m-n")).focus();};});
  body.querySelectorAll("[data-del]").forEach(function(b){b.onclick=function(){remove(b.getAttribute("data-del"));};});
  body.querySelectorAll("[data-unit-moment]").forEach(function(b){b.onclick=function(){
    Passage.addToUnit({kind:"library",ref:{item_id:M.item.id,excerpts:[b.getAttribute("data-unit-moment")]},label:M.item.title},b,
      "the moment at "+b.getAttribute("data-when"));};});
}
function save(ev){
  ev.preventDefault();
  var err=q("#m-form .m-err"),said=q("#m-q");   // the words box, when there's no transcript
  api("POST","/api/library/item/"+encodeURIComponent(M.item.id)+"/excerpts",{start:q("#m-s").value,end:q("#m-e").value,
      note:q("#m-n").value,quote:said?said.value:"",episode:M.episode||null,episode_title:M.episodeTitle||null})
    .then(function(d){M.data.excerpts.push(d.excerpt);M.data.excerpts.sort(function(a,b){return a.start-b.start;});M.mark=0;draw();
      if(window.Shell)Shell.toast("Saved the moment at "+stamp(d.excerpt.start));})
    .catch(function(x){err.textContent=x.message;err.hidden=false;});
}
function remove(id){
  var list=M.data.excerpts,i=list.findIndex(function(x){return x.id===id;});if(i<0)return;
  var gone=list.splice(i,1)[0];draw();
  var url="/api/library/excerpts/"+encodeURIComponent(id);
  var t=setTimeout(function(){delete pending[id];api("DELETE",url).catch(function(err){list.splice(i,0,gone);draw();if(window.Shell)Shell.toast(err.message);});},6500);
  pending[id]={t:t,url:url};
  if(window.Shell)Shell.toast("Deleted the moment at "+stamp(gone.start),{undo:function(){clearTimeout(t);delete pending[id];list.splice(i,0,gone);draw();}});
}

window.Moments={mount:mount};
})();
