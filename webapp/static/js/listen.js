/* Exegetica's podcast player (decision 0031): the audio comes through Exegetica's own relay, never from the
   podcast's host. A moment plays from its start and stops at its end, with a way to keep listening. Where a listener
   stopped is kept in this browser only, so nothing about their listening reaches the server.
   Listen.mount(el, {src, title, key, seconds, start, end}) draws one player in el and returns {seek}. */
(function(){
"use strict";
function stamp(t){t=Math.max(0,Math.floor(t||0));var h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=t%60;
  return (h?h+":"+String(m).padStart(2,"0"):m)+":"+String(s).padStart(2,"0");}
var e=function(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");};
function ic(d){return '<svg viewBox="0 0 24 24" aria-hidden="true">'+d+'</svg>';}
var PLAY=ic('<path d="M8.5 5.8v12.4L18.5 12z"/>'), PAUSE=ic('<path d="M9 5.5v13M15 5.5v13"/>');
var BACK=ic('<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/><path d="M4.5 4.5v3.3h3.3"/>');
var FWD=ic('<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v3.3h-3.3"/>');
var RATES=[1,1.25,1.5,1.75,2,0.75];
function store(k,v){try{if(v==null)localStorage.removeItem(k);else localStorage.setItem(k,String(v));}catch(x){}}
function load(k){try{return localStorage.getItem(k);}catch(x){return null;}}

function mount(el,o){
  if(!el)return null;
  var moment=o.start!=null&&o.end!=null&&o.end>o.start, key=o.key?"listen:"+o.key:null;
  el.innerHTML='<div class="lp'+(moment?" has-moment":"")+'" role="group" aria-label="Player for '+e(o.title||"this episode")+'">'+
    '<button type="button" class="lp-play" aria-label="Play">'+PLAY+'</button>'+
    '<div class="lp-mid"><div class="lp-track">'+(moment?'<span class="lp-moment" aria-hidden="true"></span>':"")+
      '<input type="range" class="lp-seek" min="0" max="'+(o.seconds||0)+'" step="1" value="0" aria-label="Position"></div>'+
      '<div class="lp-times"><span class="lp-now">0:00</span><span class="lp-dur">'+(o.seconds?stamp(o.seconds):"")+'</span></div></div>'+
    '<div class="lp-side"><button type="button" class="lp-btn lp-back" aria-label="Back 15 seconds">'+BACK+'<span>15</span></button>'+
      '<button type="button" class="lp-btn lp-fwd" aria-label="Forward 30 seconds">'+FWD+'<span>30</span></button>'+
      '<button type="button" class="lp-btn lp-rate" aria-label="Speed: 1 times">1×</button></div>'+
    '<p class="lp-status" role="status"></p>'+
    '<audio class="lp-audio" preload="metadata" src="'+e(o.src)+'"></audio></div>';
  var a=el.querySelector(".lp-audio"),play=el.querySelector(".lp-play"),seek=el.querySelector(".lp-seek"),
      now=el.querySelector(".lp-now"),dur=el.querySelector(".lp-dur"),status=el.querySelector(".lp-status"),
      rate=el.querySelector(".lp-rate"),mark=el.querySelector(".lp-moment");
  var dragging=false,inMoment=moment,started=false,ri=0,lastSave=0;
  function say(html){status.innerHTML=html||"";}
  function total(){return isFinite(a.duration)&&a.duration>0?a.duration:(o.seconds||0);}
  function paint(){
    var d=total(),t=a.currentTime||0;
    if(d&&+seek.max!==Math.floor(d))seek.max=Math.floor(d);
    if(!dragging)seek.value=Math.floor(t);
    now.textContent=stamp(t);if(d)dur.textContent=stamp(d);
    seek.setAttribute("aria-valuetext",stamp(t)+(d?" of "+stamp(d):""));
    seek.style.setProperty("--p",d?(t/d*100)+"%":"0%");
    if(mark&&d){mark.style.left=(o.start/d*100)+"%";mark.style.width=((o.end-o.start)/d*100)+"%";}
  }
  function setPlaying(on){play.innerHTML=on?PAUSE:PLAY;play.setAttribute("aria-label",on?"Pause":"Play");el.firstChild.classList.toggle("playing",on);}
  function go(){
    if(!started){started=true;if(moment&&(a.currentTime<o.start-1||a.currentTime>o.end))a.currentTime=o.start;}
    var p=a.play();if(p&&p.catch)p.catch(function(){say("The audio couldn't start. Try again in a moment.");});
  }
  play.onclick=function(){a.paused?go():a.pause();};
  el.querySelector(".lp-back").onclick=function(){a.currentTime=Math.max(0,a.currentTime-15);paint();};
  el.querySelector(".lp-fwd").onclick=function(){a.currentTime=Math.min(total()||a.currentTime+30,a.currentTime+30);paint();};
  rate.onclick=function(){ri=(ri+1)%RATES.length;a.playbackRate=RATES[ri];rate.textContent=String(RATES[ri]).replace(/^0/,"")+"×";
    rate.setAttribute("aria-label","Speed: "+RATES[ri]+" times");};
  seek.addEventListener("input",function(){dragging=true;now.textContent=stamp(+seek.value);seek.style.setProperty("--p",total()?(+seek.value/total()*100)+"%":"0%");});
  seek.addEventListener("change",function(){dragging=false;a.currentTime=+seek.value;started=true;paint();});
  a.addEventListener("play",function(){setPlaying(true);say("");});
  a.addEventListener("pause",function(){setPlaying(false);if(key&&!inMoment)store(key,Math.floor(a.currentTime));});
  a.addEventListener("ended",function(){setPlaying(false);if(key)store(key,null);});
  a.addEventListener("loadedmetadata",function(){
    paint();
    if(moment){a.currentTime=o.start;paint();say("This moment runs "+stamp(o.start)+"–"+stamp(o.end)+".");return;}
    var was=key?+load(key):0;
    if(was>5&&was<total()-10){a.currentTime=was;started=true;paint();
      say('Picking up at '+stamp(was)+'. <button type="button" class="lp-link lp-over">Start over</button>');
      var b=status.querySelector(".lp-over");if(b)b.onclick=function(){a.currentTime=0;store(key,null);say("");paint();play.focus();};}
  });
  a.addEventListener("timeupdate",function(){
    paint();
    if(inMoment&&a.currentTime>=o.end){
      a.pause();inMoment=false;
      say('That\'s the end of the moment. <button type="button" class="lp-link lp-more">Keep listening</button>');
      var b=status.querySelector(".lp-more");if(b)b.onclick=function(){say("");go();};
    }
    if(key&&!inMoment&&Date.now()-lastSave>10000){lastSave=Date.now();store(key,Math.floor(a.currentTime));}
  });
  a.addEventListener("error",function(){setPlaying(false);say("The audio couldn't be loaded. Try again in a few minutes.");});
  return {seek:function(t){a.currentTime=Math.max(0,t);started=true;inMoment=moment&&t>=o.start&&t<o.end;paint();go();},el:el};
}
window.Listen={mount:mount,stamp:stamp};
})();
