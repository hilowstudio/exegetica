/* An upload or a saved link in the Living Library (templates/doc.html, decision 0029, phase 3). The way back names
   where the reader came from; a teacher can save it to a unit or a class shelf. The passage panel links the text. */
(function(){
  "use strict";
  var back = document.getElementById("back"), from = "";
  try{ from = new URL(document.referrer).pathname; }catch(e){}
  if(from === "/read" || from.indexOf("/read/") === 0){ back.href = "/read"; back.textContent = "‹ Reading Room"; }
  // a Prep Room resource: drawn by the Prep Room's own renderer, so the Student copy here is its Student view
  var src = document.getElementById("hdoc"), paper = document.getElementById("hpaper");
  if(src && paper && window.md){
    var text = JSON.parse(src.textContent), seg = document.getElementById("docAud");
    var draw = function(student){
      paper.innerHTML = md(student ? studentCopy(text) : text);
      if(window.Passage) Passage.linkRefs(paper);
    };
    draw(false);
    if(seg) seg.addEventListener("click", function(e){
      var t = e.target.closest("button"); if(!t) return;
      Array.prototype.forEach.call(seg.children, function(x){ x.setAttribute("aria-pressed", String(x === t)); });
      draw(t.dataset.v === "student");
    });
  }
  var b = document.getElementById("docSave");
  if(b && window.Passage){
    b.onclick = function(){
      // a class copy is known by the teacher's copy it came from, so a unit or a shelf that holds either shows it held
      var id = b.dataset.id, origin = b.dataset.origin || id, kind = b.dataset.kind, title = b.dataset.title;
      Passage.addToUnit({kind: "shelf", ref: {item_id: id}, label: title}, b, null, {
        place: {kind: kind, ref: {item_id: id, origin: origin}, label: title},
        hold: kind === "link" ? {kind: "link", key: b.dataset.url} : {kind: "upload", key: origin},
        // a class's copy shares itself; a teacher's own goes to the class shelf first (decision 0030)
        share: b.dataset.classCopy ? {url: location.origin + location.pathname, title: title} : {shelf: true, title: title}
      });
    };
  }
})();
