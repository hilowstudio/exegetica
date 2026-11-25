/* A guest sign-in link on its own page (webapp/guest_link.py): Copy puts it on the clipboard; the box selects it whole. */
(function () {
  var box = document.getElementById("link"), btn = document.getElementById("copy-link");
  if (!box || !btn) return;
  box.addEventListener("focus", function () { box.select(); });
  btn.addEventListener("click", function () {
    var say = function (t) { if (window.Shell && Shell.toast) Shell.toast(t); };
    if (!navigator.clipboard) { box.focus(); say("The link is selected. Copy it with your keyboard."); return; }
    navigator.clipboard.writeText(box.value).then(function () { say("Link copied"); },
      function () { box.focus(); say("Copying isn’t allowed here. The link is selected, so copy it yourself."); });
  });
})();
