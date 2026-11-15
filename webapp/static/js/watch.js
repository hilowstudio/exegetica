/* Exegetica's video page (decision 0034). Exegetica's own copy plays in the browser's video player: a clip starts at its
   second and stops at its end, with a way to keep watching. A video Exegetica can't host waits behind a play button and
   loads YouTube's privacy-enhanced player only when pressed, so opening the page sends nothing to YouTube. Nothing about
   what anyone watched leaves the browser. */
(function(){
"use strict";
var box = document.getElementById("wv");
if (!box) return;
function stamp(t){t=Math.max(0,Math.floor(t||0));var h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=t%60;
  return (h?h+":"+String(m).padStart(2,"0"):m)+":"+String(s).padStart(2,"0");}
var num = function(x){return x==null||x===""?null:+x;};

if (box.dataset.embed) {                        // YouTube's player, on demand
  var go = box.querySelector(".wv-go");
  go.addEventListener("click", function(){
    var f = document.createElement("iframe");
    f.className = "wv-frame"; f.src = box.dataset.embed; f.title = box.dataset.title || "Video";
    f.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture; fullscreen");
    f.setAttribute("allowfullscreen", ""); f.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
    box.innerHTML = ""; box.classList.add("is-on"); box.appendChild(f); f.focus();
  });
  return;
}

var v = box.querySelector("video"), status = box.querySelector(".wv-status");
var start = num(box.dataset.start), end = num(box.dataset.end);
var clip = start != null && end != null && end > start, inClip = clip, started = false;
function say(html){ status.innerHTML = html || ""; }
v.addEventListener("loadedmetadata", function(){
  if (start != null) v.currentTime = start;
  if (clip) say("This clip runs " + stamp(start) + "–" + stamp(end) + ".");
});
v.addEventListener("play", function(){
  if (!started) { started = true; if (clip && (v.currentTime < start - 1 || v.currentTime > end)) v.currentTime = start; }
});
v.addEventListener("seeked", function(){ if (clip && (v.currentTime < start - 1 || v.currentTime > end)) inClip = false; });
v.addEventListener("timeupdate", function(){
  if (inClip && v.currentTime >= end) {
    v.pause(); inClip = false;
    if (document.fullscreenElement) document.exitFullscreen().catch(function(){});
    say('That\'s the end of the clip. <button type="button" class="lp-link wv-more">Keep watching</button>');
    var b = status.querySelector(".wv-more");
    if (b) b.onclick = function(){ say(""); v.play(); };
  }
});
v.addEventListener("error", function(){ say("The video couldn't be loaded. Try again in a few minutes."); }, true);
})();
