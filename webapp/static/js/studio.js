/* The Media Studio · Exegetica page (templates/studio.html). The rail, theme and Need help now? come from static/js/shell.js. */
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
let CFG = null, images = [], current = null, busy = false, pollTimer = null, QUOTE = null, quoteTimer = null, quoteSeq = 0;
let folders = [], view = "root", anchor = null, renaming = false;
const picked = new Set();
const state = {mode: "create", model: {}, service: "", shape: {image: "square", video: "wide"}, seconds: null, source: null,
               end: null, refs: [], pins: [], extend: null,
               task: {}, auto: {create: true, edit: true}};   // what is being made, and whether Auto picks the model
const VERB = {create: "Make image", edit: "Edit image", video: "Make video"};

function money(x){ return x < 0.01 ? "under 1¢" : "about $" + x.toFixed(x < 0.1 ? 3 : 2); }
function models(mode){ return CFG ? CFG.models.filter(m => m.does.includes(mode)) : []; }
function model(){ return CFG && CFG.models.find(m => m.id === state.model[state.mode]); }
function ready(m){ return !!(m && m.services.some(s => CFG.services[s].ready)); }
function serviceLabel(s){ return CFG && CFG.services[s] ? CFG.services[s].label : s; }
function price(){ return QUOTE && QUOTE.choice ? QUOTE.choice.usd : null; }

function settings(){
  const video = state.mode === "video";
  const m = model();
  return {mode: state.mode, model: state.model[state.mode], service: state.service,
          shape: video ? state.shape.video : state.shape.image, steps: Number($("steps").value),
          seconds: state.seconds, audio: $("audio").checked, framed: video && !!state.source && !extending(),
          ending: video && !!state.end && !!m && m.end_image && !extending(), extending: extending()};
}
function extending(){
  // carrying on an earlier H3 clip: only in video mode, on a model that can
  const m = model();
  return state.mode === "video" && !!state.extend && !!m && !!m.extends;
}
function picture(p){ return p.id ? {id: p.id} : {data_url: p.data_url}; }
function requote(){
  // today's price for these settings on each service, from the server's price book
  clearTimeout(quoteTimer);
  quoteTimer = setTimeout(async () => {
    const seq = ++quoteSeq;
    try {
      const r = await fetch("/api/studio/quote", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(settings())});
      const d = await r.json();
      if (seq !== quoteSeq || !r.ok) return;
      QUOTE = d;
      fillServices();
      sync();
    } catch (e) { /* the next change asks again */ }
  }, 120);
}
function fillServices(){
  const sel = $("service");
  sel.innerHTML = "";
  const opts = (QUOTE && QUOTE.services) || [];
  const cheapest = opts.find(o => o.usable && o.auto);
  const first = document.createElement("option");
  first.value = "";
  first.textContent = "Cheapest today" + (cheapest ? " · " + cheapest.label : "");
  sel.appendChild(first);
  opts.forEach(o => {
    const el = document.createElement("option");
    el.value = o.service;
    el.disabled = !o.usable;
    el.textContent = o.label + " · " + (o.usable ? money(o.usd)
      : o.reason === "not set up" ? "needs " + CFG.services[o.service].env : o.reason);
    sel.appendChild(el);
  });
  sel.value = opts.some(o => o.service === state.service && o.usable) ? state.service : "";
  const p = QUOTE && QUOTE.prices;
  $("prices-when").textContent = !p || !p.checked ? "Prices are the listed ones until the first daily check."
    : "Prices checked " + new Date(p.checked).toLocaleString() + "." + (p.kept && p.kept.length ? " " + p.kept.length + " could not be read and use the last good price." : "");
}
function pressed(id, v){ $(id).querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === String(v)))); }
function chips(id, values, labelOf, current, onPick){
  $(id).innerHTML = "";
  values.forEach(v => {
    const b = document.createElement("button");
    b.type = "button"; b.dataset.v = v; b.textContent = labelOf(v);
    b.setAttribute("aria-pressed", String(String(v) === String(current)));
    b.onclick = () => { onPick(v); pressed(id, v); sync(); requote(); };
    $(id).appendChild(b);
  });
}

function fillModels(){
  const sel = $("model");
  sel.innerHTML = "";
  const auto = tasks(state.mode).length ? autoModel(state.mode) : null;
  if (auto) {
    const o = document.createElement("option");
    o.value = "auto";
    o.textContent = "Auto: " + CFG.models.find(m => m.id === auto).label;   // the task chips above say what it is best for
    sel.appendChild(o);
  }
  models(state.mode).forEach(m => {
    const o = document.createElement("option");
    o.value = m.id;
    o.textContent = m.label + (ready(m) ? "" : " · needs a key for " + m.services.map(serviceLabel).join(" or "));
    o.disabled = !ready(m);
    sel.appendChild(o);
  });
  sel.value = auto && state.auto[state.mode] ? "auto" : state.model[state.mode];
}
function fitModel(){
  // Auto's pick for what is being made, or the chosen model, or the mode's default, or the first set up
  if (state.auto[state.mode] && autoModel(state.mode)) { state.model[state.mode] = autoModel(state.mode); return; }
  const list = models(state.mode);
  let m = list.find(x => x.id === state.model[state.mode]);
  if (!ready(m)) m = list.find(x => x.id === CFG.defaults[state.mode] && ready(x)) || list.find(ready) || list[0];
  state.model[state.mode] = m ? m.id : null;
}
function layout(){
  // the controls that depend on the mode and the model
  fitModel();
  const m = model(), video = state.mode === "video";
  renderTasks();
  fillModels();
  renderCard();
  $("model-note").textContent = m ? m.note : "";
  $("steps-fld").hidden = video || !m || !m.max_steps;
  if (m && m.max_steps) {
    $("steps").max = m.max_steps;
    if (Number($("steps").value) > m.max_steps) $("steps").value = m.steps;
    $("steps-n").textContent = $("steps").value;
  }
  if (video && m) {
    if (!m.sizes.includes(state.shape.video)) state.shape.video = m.sizes[0];
    chips("shape", m.sizes, k => CFG.shapes[k].label, state.shape.video, v => state.shape.video = v);
    if (!m.seconds.includes(state.seconds)) state.seconds = m.seconds[0];
    chips("seconds", m.seconds, s => s + " seconds", state.seconds, v => state.seconds = v);
    $("audio").checked = !!m.audio;
  } else if (CFG) {
    chips("shape", Object.keys(CFG.shapes), k => CFG.shapes[k].label, state.shape.image, v => state.shape.image = v);
  }
  $("seconds-fld").hidden = !video;
  $("audio-fld").hidden = !video || !m || m.audio === null;
  renderPictures();   // picture numbers start at 2 in an edit
  sync();
  requote();
}
function sync(){
  const editing = state.mode === "edit", video = state.mode === "video", m = model();
  const ext = extending();
  $("extend-fld").hidden = !ext;
  if (ext && $("extend-video").dataset.src !== state.extend.preview) {
    $("extend-video").src = state.extend.preview + "#t=0.5";
    $("extend-video").dataset.src = state.extend.preview;
  }
  $("source-fld").hidden = !(editing || video) || ext;
  $("source-lab").textContent = video ? "First frame (optional)" : "Image to edit";
  $("source-none").textContent = video ? "Leave empty to make the video from words alone, or upload an image or pick one below and choose Animate this."
                                       : "Upload an image, or pick one below and choose Edit this.";
  $("clear-source").hidden = !state.source;
  $("source-img").hidden = !state.source;
  $("source-none").hidden = !!state.source;
  if (state.source) $("source-img").src = state.source.preview;
  $("end-fld").hidden = !(video && m && m.end_image) || ext;
  $("end-img").hidden = !state.end;
  $("end-none").hidden = !!state.end;
  $("clear-end").hidden = !state.end;
  if (state.end) $("end-img").src = state.end.preview;
  $("refs-fld").hidden = !((video || editing) && m && m.refs) || ext;
  $("refs-hint").textContent = editing ? "More pictures the edit can use. The image to edit is Picture 1, so name these Picture 2, Picture 3 and on."
                                       : "People, things or places to show. Name them in your description as Picture 1, Picture 2 and on.";
  $("pins-fld").hidden = !(video && m && m.pins) || ext;
  $("refs-btn").disabled = !m || state.refs.length >= (m.refs || 0);
  $("pins-btn").disabled = !m || state.pins.length >= (m.pins || 0);
  $("prompt-lab").textContent = video ? "Describe the video" : editing ? "Describe the change" : "Describe the image";
  $("prompt").placeholder = video ? (state.source ? "The steam rises and the camera slowly pushes in" : "Waves rolling onto a rocky shore at dawn")
                         : editing ? "Make the apple green" : "An apple on a wooden table in morning light";
  const choice = QUOTE && QUOTE.model === state.model[state.mode] ? QUOTE.choice : null;
  const framed = video && !!state.source && !!choice && choice.frame_sets_shape;
  $("shape").hidden = framed || ext;
  $("shape-note").hidden = !(framed || ext);
  $("shape-note").textContent = ext ? "The clip being extended sets the shape." : "The first frame sets the video's shape.";
  const noFrame = video && !!state.source && m && !m.start_image;
  const why = noFrame ? m.label + " starts from a description only. Remove the first frame or pick another model."
            : (QUOTE && !QUOTE.choice ? QUOTE.why : null);
  $("model-note").textContent = why || (m ? m.note : "");
  $("model-note").classList.toggle("warn", !!why);
  const p = choice ? choice.usd : null;
  $("make").textContent = VERB[state.mode] + (p != null ? " · " + money(p) + " on " + choice.label : "");
  $("make").disabled = busy || !CFG || !CFG.storage || !choice || noFrame || !$("prompt").value.trim() || (editing && !state.source);
}

function renderPictures(){
  // the reference pictures, named as the prompt names them, and the pictures pinned at a second
  $("refs").innerHTML = "";
  const first = state.mode === "edit" ? 2 : 1;   // in an edit, Picture 1 is the image being edited
  state.refs.forEach((p, n) => {
    const d = document.createElement("div");
    d.className = "thumb";
    d.innerHTML = `<img src="${esc(p.preview)}" alt="Picture ${n + first}"><span>Picture ${n + first}</span><button class="linkbtn" type="button">Remove</button>`;
    d.querySelector("button").onclick = () => { state.refs.splice(n, 1); renderPictures(); sync(); };
    $("refs").appendChild(d);
  });
  $("pins").innerHTML = "";
  state.pins.forEach((p, n) => {
    const d = document.createElement("div");
    d.className = "thumb";
    d.innerHTML = `<img src="${esc(p.preview)}" alt="Picture at ${esc(p.at)} seconds">
      <label>at <input type="number" min="0.5" step="0.5" value="${esc(p.at)}" aria-label="Second for this picture"> s</label>
      <button class="linkbtn" type="button">Remove</button>`;
    d.querySelector("input").onchange = e => { p.at = Number(e.target.value); };
    d.querySelector("button").onclick = () => { state.pins.splice(n, 1); renderPictures(); sync(); };
    $("pins").appendChild(d);
  });
}
function shrink(file){
  // a picture for the GPU is scaled down in the browser to 2048 pixels on its long side, since
  // H3 uses no more, and a dozen full-size photos would make a very large request
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file), img = new Image();
    img.onload = () => {
      const s = Math.min(1, 2048 / Math.max(img.naturalWidth, img.naturalHeight));
      const c = document.createElement("canvas");
      c.width = Math.round(img.naturalWidth * s); c.height = Math.round(img.naturalHeight * s);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      const data_url = c.toDataURL("image/jpeg", 0.92);
      resolve({data_url, preview: data_url});
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("unreadable")); };
    img.src = url;
  });
}
async function addPictures(files, list, limit, extra){
  for (const f of files) {
    if (list.length >= limit) break;
    try { list.push(Object.assign(await shrink(f), extra ? extra() : {})); }
    catch (e) { say("That picture could not be read.", true); }
  }
  renderPictures(); sync(); requote();
}
function sizeText(img){
  const size = img.width && img.height ? img.width + "×" + img.height : (CFG && CFG.shapes[img.shape] ? CFG.shapes[img.shape].label : "");
  if (img.kind === "video") return [size, img.seconds ? img.seconds + " seconds" : "", img.audio ? "with sound" : ""].filter(Boolean).join(", ");
  return size;
}
function showImage(img){
  current = img;
  const when = new Date(img.created * 1000).toLocaleString();
  const words = (img.rewritten ? `<details><summary>Your words</summary>${esc(img.prompt)}</details>` : "")
    + (img.service_prompt ? `<details><summary>The prompt ${esc(img.engine)} used</summary>${esc(img.service_prompt)}</details>` : "");
  const what = [esc(img.engine) + " on " + esc(serviceLabel(img.service)) + (img.steps ? ", " + img.steps + " steps" : ""),
                esc(sizeText(img)), money(img.est_usd || 0), esc(when)].filter(Boolean).join(" · ");
  let body;
  const thing = img.kind === "video" ? "video" : "image";
  if (img.status === "pending") {
    const pct = typeof img.progress === "number" ? img.progress : null;
    body = `<div class="waiting"><h2>Making the ${thing}</h2>
      <p>${img.service === "baseten" ? "Your GPU takes a minute or two to wake if it was asleep, then "
            + (img.rewrite_on_gpu ? "it rewrites your words and " : "") + esc(img.engine) + " starts."
          : esc(img.engine) + " usually takes a few minutes."} You can leave this page and come back.</p>
      <div class="bar"${pct == null ? "" : ` role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"`}><span style="width:${pct == null ? 8 : Math.max(8, pct)}%"></span></div></div>`;
  } else if (img.status === "failed") {
    body = `<div class="waiting failed"><h2>This ${thing} was not made</h2><p>${esc(img.error || "The service gave no reason.")}</p></div>`;
  } else if (img.kind === "video") {
    body = `<video src="${esc(img.url)}" controls playsinline preload="metadata" width="${img.width || ""}" height="${img.height || ""}"></video>`;
  } else {
    body = `<img src="${esc(img.url)}" alt="${esc(img.prompt)}" width="${img.width || ""}" height="${img.height || ""}">`;
  }
  const done = img.status === "ready", still = done && img.kind !== "video";
  $("stage").innerHTML = `${body}
     <div class="meta"><p class="used">${esc(img.prompt_used)}</p>${words}<div>${what}</div></div>
     <div class="actions">
       ${done ? `<a class="btn" href="${esc(img.url)}" download="studio-${esc(img.id.slice(0, 8))}.${esc(img.ext || (img.kind === "video" ? "mp4" : "jpg"))}">Download</a>` : ""}
       ${still ? `<button class="btn" type="button" id="edit-this">Edit this</button><button class="btn" type="button" id="animate-this">Animate this</button>` : ""}
       ${still && refModel() ? `<button class="btn" type="button" id="picture-this">Use as a picture</button>` : ""}
       ${done && img.kind === "video" && extender(img) ? `<button class="btn" type="button" id="extend-this">Extend this</button>` : ""}
       <button class="btn" type="button" id="delete-this">Delete</button>
     </div>`;
  if (done && img.kind === "video" && extender(img)) $("extend-this").onclick = () => extendClip(img);
  if (still) {
    $("edit-this").onclick = () => useAsSource(img, "edit");
    $("animate-this").onclick = () => useAsSource(img, "video");
  }
  if (still && refModel()) $("picture-this").onclick = () => useAsPicture(img);
  $("delete-this").onclick = () => remove(img);
  renderGrid();
}
function useAsSource(img, mode){
  state.source = {id: img.id, preview: img.url};
  setMode(mode);
  $("prompt").focus();
}
function refModel(){ return CFG && CFG.models.find(m => m.refs && m.does.includes("video") && ready(m)); }
function extender(img){
  // a clip H3 made can be carried on by the model that extends clips, on the GPU
  return String(img.model_id || "").startsWith("h3") && CFG && CFG.models.find(m => m.extends && ready(m));
}
function extendClip(img){
  const m = extender(img);
  state.extend = {id: img.id, preview: img.url};
  state.model.video = m.id;
  setMode("video");
  state.service = "baseten";   // only the GPU extends a clip
  requote();
  say("Describe what happens next. The new clip starts from this one's last second.");
  $("prompt").focus();
}
function useAsPicture(img){
  // a studio image becomes the next reference picture for the video model that takes them
  const m = refModel();
  if (state.refs.length >= m.refs) { say(m.label + " takes up to " + m.refs + " pictures.", true); return; }
  if (!state.refs.some(p => p.id === img.id)) state.refs.push({id: img.id, preview: img.url});
  state.model.video = m.id;
  setMode("video");
  renderPictures();
  say("Added as Picture " + state.refs.length + ".");
}
// ---------------------------------------------------------------- the library
// Folders work like Finder: the Library shows the folders, then the work in no folder, and a
// folder shows its own work. Selecting is direct (the tick on each tile, shift for a range,
// ctrl or cmd to add one), the header turns into the selection's action bar, and work can be
// dragged onto a folder card, or onto "Library" to take it out of a folder.
const ICON = {
  lock: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>',
  folder: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/></svg>',
  newFolder: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/><path d="M12 11v5M9.5 13.5h5"/></svg>',
  more: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5.5" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="18.5" cy="12" r="1.4" fill="currentColor"/></svg>',
  x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  tick: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  pencil: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>',
  key: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="15" r="4"/><path d="M11 12l8-8M16 7l2.5 2.5"/></svg>',
  unlock: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.5-2"/></svg>',
  trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13"/></svg>',
  out: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V6M6.5 11.5L12 6l5.5 5.5"/><path d="M5 20h14"/></svg>',
  move: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/><path d="M9.5 13.5h5M12.5 11l2.5 2.5-2.5 2.5"/></svg>',
  eye: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  palette: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.2 0 1.8-.8 1.8-1.7 0-1.3-1-1.6-1-2.6 0-1 .8-1.7 1.8-1.7h2.2a3.7 3.7 0 0 0 3.7-3.7C20.5 6.9 16.7 3.5 12 3.5z"/><circle cx="7.6" cy="11" r="1.1" fill="currentColor"/><circle cx="10.5" cy="7.4" r="1.1" fill="currentColor"/><circle cx="15" cy="7.6" r="1.1" fill="currentColor"/></svg>',
};
const plural = (n, one) => n + " " + (n === 1 ? one : one + "s");
function folderOf(id){ return folders.find(f => f.id === id); }
function coverSrc(f, mode, theme){
  // the server draws the lock as this session has it; the name and theme in the address fetch a new
  // cover after a rename or a new color, and `theme` previews one before it is saved
  const state = !f.protected ? "plain" : f.open ? "open" : "locked";
  return `/api/studio/folders/${f.id}/cover?mode=${mode}&state=${state}&name=${encodeURIComponent(f.name)}`
    + (theme ? `&theme=${encodeURIComponent(theme)}` : `&look=${encodeURIComponent((f.themes || {})[mode] || "")}`);
}
function darkPage(){
  const t = document.documentElement.getAttribute("data-theme");
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}
// the folder covers come in the light or the dark cloth, so a change of theme redraws them
new MutationObserver(() => renderLibrary()).observe(document.documentElement, {attributes: true, attributeFilter: ["data-theme"]});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => renderLibrary());
function visible(img){ return view === "root" ? !img.folder_id || !folderOf(img.folder_id) : img.folder_id === view; }
function viewed(){ return images.filter(visible); }
function inFolder(f){ return images.filter(i => i.folder_id === f.id); }
function renderGrid(){ renderLibrary(); }
function renderFolders(){ renderLibrary(); }

function renderLibrary(){
  if (view !== "root" && !folderOf(view)) view = "root";
  const f = folderOf(view), shown = viewed();
  $("gallery").hidden = !images.length && !folders.length;
  renderHead(f);
  renderCards();
  renderTiles(shown);
  const atRoot = view === "root";
  $("loose-lab").hidden = !atRoot || !folders.length || !shown.length;
  $("empty-folder").hidden = !!shown.length;
  $("empty-folder").textContent = atRoot
    ? (folders.length ? "Everything is in a folder." : "")
    : "This folder is empty. Drag work onto it in the Library, or make something while it is open.";
  $("saving-to").hidden = atRoot;
  if (f) $("saving-to").innerHTML = (f.protected ? ICON.lock : ICON.folder) + "<span>New work goes into " + esc(f.name) + "</span>";
}

function renderHead(f){
  const n = picked.size;
  $("lib-title").hidden = $("lib-actions").hidden = !!n;
  $("selbar").hidden = !n;
  if (n) {
    const all = viewed().every(i => picked.has(i.id));
    $("sel-count").textContent = plural(n, "item") + " selected";
    $("sel-all").textContent = all ? "Clear" : "Select all";
    return;
  }
  const t = $("lib-title");
  if (!f) t.innerHTML = "<h2>Library</h2>";
  else {
    t.innerHTML = `<button class="crumb" type="button" id="crumb" title="Back to the Library. Drop work here to take it out of the folder.">Library</button>
      <span class="slash" aria-hidden="true">/</span>`
      + (renaming ? `<input class="rename" id="rename" value="${esc(f.name)}" maxlength="60" aria-label="Folder name">`
                  : `<h2>${esc(f.name)}</h2>`)
      + (f.protected ? `<span class="lockmark" title="Protected by a password">${ICON.lock}</span>` : "");
    $("crumb").onclick = () => goTo("root");
    dropTarget($("crumb"), null);
    if (renaming) startRename(f);
  }
  $("new-folder").hidden = !!f;
  $("folder-menu").hidden = !f;
}

function renderCards(){
  const box = $("folders");
  box.hidden = view !== "root" || !folders.length;
  box.innerHTML = "";
  if (box.hidden) return;
  const mode = darkPage() ? "dark" : "light";
  folders.forEach(f => {
    // each folder is a house cloth cover with its name for the title, never a preview of its work,
    // so a protected folder's face shows nothing but its name and a lock
    const shut = !f.open, guarded = f.protected;
    const card = document.createElement("div");
    card.className = "fcard";
    card.setAttribute("role", "listitem");
    const count = shut ? "Locked" : plural(inFolder(f).length, "item") + (guarded ? " · unlocked" : "");
    card.innerHTML = `<button class="fopen" type="button" aria-label="${esc(f.name + ", " + count + (guarded ? ", protected by a password" : ""))}">
        <span class="fcover"><img src="${esc(coverSrc(f, mode))}" alt="" onload="this.classList.add('in')"></span>
        <span class="meta">${count}</span></button>
      <button class="fmore" type="button" aria-haspopup="menu" aria-expanded="false" aria-label="Options for ${esc(f.name)}">${ICON.more}</button>`;
    card.querySelector(".fopen").onclick = () => openFolder(f);
    const more = card.querySelector(".fmore");
    more.onclick = () => folderMenu(f, more);
    card.oncontextmenu = e => { e.preventDefault(); folderMenu(f, more); };
    dropTarget(card, f.id);
    box.appendChild(card);
  });
}

function renderTiles(shown){
  const grid = $("grid"), focused = document.activeElement && document.activeElement.dataset.id;
  grid.classList.toggle("selecting", picked.size > 0);
  grid.innerHTML = "";
  shown.forEach((img, n) => {
    const b = document.createElement("button");
    const on = picked.has(img.id);
    b.type = "button"; b.title = img.prompt; b.dataset.id = img.id;
    b.setAttribute("aria-label", (img.kind === "video" ? "Video: " : "Image: ") + img.prompt);
    if (picked.size) b.setAttribute("aria-pressed", String(on));
    else if (current && current.id === img.id) b.setAttribute("aria-current", "true");
    if (img.status === "pending") b.innerHTML = `<span class="word">Making the ${img.kind === "video" ? "video" : "image"}…</span>`;
    else if (img.status === "failed") b.innerHTML = `<span class="word">Not made</span>`;
    else if (img.kind === "video") b.innerHTML = `<video src="${esc(img.url)}#t=0.5" muted preload="metadata"></video><span class="tag">Video</span>`;
    else b.innerHTML = `<img src="${esc(img.url)}" alt="" loading="lazy">`;
    b.insertAdjacentHTML("beforeend", `<span class="tick" title="Select">${ICON.tick}</span>`);
    b.onclick = e => {
      if (b.dataset.held) { delete b.dataset.held; return; }   // a long press already selected it
      if (e.shiftKey && anchor) return pickRange(shown, img.id);
      if (picked.size || e.ctrlKey || e.metaKey || e.target.closest(".tick")) return toggle(img.id);
      showImage(img);
    };
    b.onkeydown = e => { if (e.key === " ") { e.preventDefault(); toggle(img.id); } };
    b.draggable = true;
    b.ondragstart = e => {
      const ids = picked.has(img.id) ? [...picked] : [img.id];
      e.dataTransfer.setData("application/x-studio-items", JSON.stringify(ids));
      e.dataTransfer.effectAllowed = "move";
      ids.forEach(id => { const t = grid.querySelector(`[data-id="${id}"]`); if (t) t.classList.add("dragging"); });
    };
    b.ondragend = () => grid.querySelectorAll(".dragging").forEach(t => t.classList.remove("dragging"));
    b.onpointerdown = e => {   // a long press on a touch screen starts selecting
      if (e.pointerType !== "touch") return;
      const timer = setTimeout(() => { b.dataset.held = "1"; toggle(img.id); }, 450);
      const stop = () => { clearTimeout(timer); b.removeEventListener("pointerup", stop); b.removeEventListener("pointermove", stop); };
      b.addEventListener("pointerup", stop); b.addEventListener("pointermove", stop);
    };
    grid.appendChild(b);
    if (img.id === focused) b.focus();
  });
}

function toggle(id){
  picked.has(id) ? picked.delete(id) : picked.add(id);
  anchor = id;
  renderLibrary();
}
function pickRange(shown, id){
  const ids = shown.map(i => i.id), a = ids.indexOf(anchor), b = ids.indexOf(id);
  ids.slice(Math.min(a, b), Math.max(a, b) + 1).forEach(x => picked.add(x));
  renderLibrary();
}
function clearPicked(){ picked.clear(); anchor = null; renderLibrary(); }

function dropTarget(el, folderId){
  el.ondragover = e => {
    if (!e.dataTransfer.types.includes("application/x-studio-items")) return;
    e.preventDefault(); e.dataTransfer.dropEffect = "move"; el.classList.add("drop");
  };
  el.ondragleave = () => el.classList.remove("drop");
  el.ondrop = e => {
    e.preventDefault(); el.classList.remove("drop");
    const ids = JSON.parse(e.dataTransfer.getData("application/x-studio-items") || "[]");
    if (ids.length) moveTo(folderId, ids);
  };
}

function showFirst(){
  const first = viewed()[0];
  if (first) showImage(first);
  else { current = null; $("stage").innerHTML = '<div class="empty"><h2>Nothing here yet</h2></div>'; renderLibrary(); }
}
function goTo(id){
  view = id; renaming = false; picked.clear(); anchor = null;
  renderLibrary();
  if (!current || !visible(current)) showFirst();
  $("gallery").scrollIntoView({block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});
}
async function reload(){
  // the server leaves out what sits in a closed folder, so opening or locking one asks again
  const d = await (await fetch("/api/studio/images")).json();
  images = d.images || [];
  folders = d.folders || [];
  for (const id of [...picked]) if (!images.some(i => i.id === id)) picked.delete(id);
  if (current) current = images.find(i => i.id === current.id) || null;   // the fresh copy, or gone
}

// ---------------------------------------------------------------- talking to the server
async function send(url, method, body){
  try {
    const r = await fetch(url, {method, headers: {"Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined});
    const d = await r.json().catch(() => ({}));
    return r.ok ? d : {error: d.error || "That did not work."};
  } catch (e) { return {error: "The connection dropped. Try again."}; }
}
function toast(text, undo){ Shell.toast(text, undo ? {undo} : {}); }   // the shell's toast

// ---------------------------------------------------------------- dialogs and menus
function ask({title, note, fields = [], ok = "OK", danger = false, extra = null, submit, body = null, setup = null, wide = false}){
  // a small form in a dialog; resolves with what submit returned, or null when cancelled. `body`
  // replaces the fields with custom content, which `setup` wires up once it is on the page.
  return new Promise(resolve => {
    const dlg = $("dlg"), form = $("dlg-form");
    dlg.classList.toggle("wide", wide);
    $("dlg-title").textContent = title;
    $("dlg-note").textContent = note || "";
    $("dlg-error").textContent = "";
    $("dlg-ok").textContent = ok;
    $("dlg-ok").className = "btn primary" + (danger ? " warn" : "");
    $("dlg-fields").innerHTML = body != null ? body : fields.map((f, n) => {
      const id = "dlg-" + n, hide = f.shownBy ? " hidden" : "";
      if (f.type === "checkbox") return `<div class="field"><label class="check"><input type="checkbox" name="${f.name}" data-shows="${f.shows || ""}"><span>${esc(f.label)}</span></label></div>`;
      const input = `<input id="${id}" name="${f.name}" type="${f.type || "text"}" value="${esc(f.value || "")}"
                      maxlength="${f.type === "password" ? 200 : 60}" autocomplete="${f.autocomplete || "off"}">`;
      return `<div class="field" data-field="${f.name}"${hide}><label for="${id}">${esc(f.label)}</label>`
        + (f.type === "password" ? `<div class="pw">${input}<button class="iconbtn" type="button" data-reveal="${id}" aria-label="Show the password" aria-pressed="false">${ICON.eye}</button></div>` : input)
        + "</div>";
    }).join("");
    $("dlg-fields").querySelectorAll("[data-reveal]").forEach(b => b.onclick = () => {
      const i = $(b.dataset.reveal), show = i.type === "password";
      i.type = show ? "text" : "password";
      b.setAttribute("aria-pressed", String(show));
      b.setAttribute("aria-label", show ? "Hide the password" : "Show the password");
    });
    $("dlg-fields").querySelectorAll("[data-shows]").forEach(c => c.onchange = () => {
      const target = $("dlg-fields").querySelector(`[data-field="${c.dataset.shows}"]`);
      if (target) { target.hidden = !c.checked; if (c.checked) target.querySelector("input").focus(); }
    });
    if (setup) setup($("dlg-fields"));
    const ex = $("dlg-extra");
    ex.hidden = !extra;
    if (extra) ex.textContent = extra.label;
    const done = v => { form.onsubmit = null; dlg.oncancel = null; $("dlg-cancel").onclick = null; ex.onclick = null; dlg.close(); resolve(v); };
    const attempt = async run => {
      const values = {};
      fields.forEach(f => { const el = form.elements[f.name]; values[f.name] = f.type === "checkbox" ? el.checked : el.value; });
      $("dlg-ok").disabled = ex.disabled = true;
      try {
        const r = await run(values);
        if (r && r.error) { $("dlg-error").textContent = r.error; return; }
        done(r || {});
      } finally { $("dlg-ok").disabled = ex.disabled = false; }
    };
    $("dlg-cancel").onclick = () => done(null);
    dlg.oncancel = e => { e.preventDefault(); done(null); };
    form.onsubmit = e => { e.preventDefault(); attempt(submit); };
    if (extra) ex.onclick = () => attempt(extra.run);
    dlg.showModal();
    // a field first; with none, Cancel when the button would destroy something, so Enter is safe
    const first = $("dlg-fields").querySelector("input:not([type=checkbox])") || (danger ? $("dlg-cancel") : $("dlg-ok"));
    first.focus();
  });
}
const confirmAsk = (title, note, ok) => ask({title, note, ok, danger: true, submit: async () => ({})});

let menuAnchor = null;
function openMenu(anchor, entries){
  const menu = $("menu");
  if (menuAnchor === anchor) return closeMenu();
  closeMenu();
  menu.innerHTML = "";
  entries.forEach(e => {
    if (e === "-") { menu.appendChild(document.createElement("hr")); return; }
    if (!e.run) { const l = document.createElement("div"); l.className = "label"; l.textContent = e.text; menu.appendChild(l); return; }
    const b = document.createElement("button");
    b.type = "button"; b.setAttribute("role", "menuitem");
    if (e.danger) b.className = "danger";
    b.innerHTML = (e.icon || "") + `<span>${esc(e.text)}</span>`;
    b.onclick = () => { closeMenu(); e.run(); };
    menu.appendChild(b);
  });
  menu.hidden = false;
  const r = anchor.getBoundingClientRect(), w = menu.offsetWidth, h = menu.offsetHeight;
  menu.style.left = Math.max(8, Math.min(r.right - w, innerWidth - w - 8)) + "px";
  menu.style.top = (r.bottom + 6 + h > innerHeight - 8 ? Math.max(8, r.top - h - 6) : r.bottom + 6) + "px";
  menuAnchor = anchor;
  anchor.setAttribute("aria-expanded", "true");
  const first = menu.querySelector("button");
  if (first) first.focus();
}
function closeMenu(){
  if (!menuAnchor) return;
  $("menu").hidden = true;
  menuAnchor.setAttribute("aria-expanded", "false");
  menuAnchor = null;
}
document.addEventListener("pointerdown", e => { if (menuAnchor && !$("menu").contains(e.target) && !menuAnchor.contains(e.target)) closeMenu(); });
$("menu").addEventListener("keydown", e => {
  const items = [...$("menu").querySelectorAll("button")], at = items.indexOf(document.activeElement);
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    items[(at + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length].focus();
  } else if (e.key === "Escape" || e.key === "Tab") { const a = menuAnchor; closeMenu(); if (a && e.key === "Escape") a.focus(); }
});

// ---------------------------------------------------------------- folder actions
async function unlock(f){
  const got = await ask({title: f.name + " is locked", note: "Enter its password. It stays open in this browser for 30 minutes, or until you lock it.",
    fields: [{name: "password", label: "Password", type: "password", autocomplete: "current-password"}], ok: "Unlock",
    submit: v => send("/api/studio/folders/" + f.id + "/unlock", "POST", v)});
  if (!got) return false;
  await reload();
  return true;
}
async function openFolder(f){
  if (!f.open && !(await unlock(f))) return;
  goTo(f.id);
}
async function newFolder(){
  const got = await ask({title: "New folder", fields: [
      {name: "name", label: "Name"},
      {name: "protect", label: "Protect it with a password", type: "checkbox", shows: "password"},
      {name: "password", label: "Password", type: "password", autocomplete: "new-password", shownBy: "protect"}],
    ok: "Create", submit: v => send("/api/studio/folders", "POST", {name: v.name, password: v.protect ? v.password : null})});
  if (!got) return null;
  folders = got.folders;
  return got.created;
}
$("new-folder").innerHTML = ICON.newFolder + "<span>New folder</span>";
$("new-folder").onclick = async () => { if (await newFolder()) { renderLibrary(); toast("Folder created. Drag work onto it, or open it and make something."); } };
$("folder-menu").innerHTML = ICON.more;
$("folder-menu").onclick = () => folderMenu(folderOf(view), $("folder-menu"), true);
function folderMenu(f, anchor, inHeader = false){
  // the same choices on a folder's card (its ⋯ button or a right-click) and in an open folder's header
  openMenu(anchor, [
    ...(inHeader ? [] : [{text: f.open ? "Open" : "Unlock and open", icon: f.open ? ICON.folder : ICON.lock, run: () => openFolder(f)}]),
    {text: "Rename", icon: ICON.pencil, run: () => withOpen(f, g => { if (inHeader) { renaming = true; renderLibrary(); } else renameFolder(g); })},
    {text: "Cover color…", icon: ICON.palette, run: () => withOpen(f, coverColors)},
    {text: f.protected ? "Change password" : "Add a password", icon: ICON.key, run: () => withOpen(f, setPassword)},
    ...(f.protected && f.open ? [{text: "Lock now", icon: ICON.lock, run: () => lockFolder(f)}] : []),
    "-",
    {text: "Delete folder", icon: ICON.trash, danger: true, run: () => withOpen(f, deleteFolder)},
  ]);
}
async function withOpen(f, act){
  // a protected folder is changed only while it is open, so a locked one asks for its password first
  if (!f.open) {
    if (!(await unlock(f))) return;
    renderLibrary();
  }
  act(folderOf(f.id) || f);
}
async function renameFolder(f){
  const got = await ask({title: "Rename folder", fields: [{name: "name", label: "Name", value: f.name}], ok: "Rename",
    submit: v => send("/api/studio/folders/" + f.id, "PATCH", {name: v.name})});
  if (!got) return;
  folders = got.folders;
  renderLibrary();
  toast("Renamed.");
}
let HOUSE_THEMES = null;
async function houseThemes(){
  if (!HOUSE_THEMES) HOUSE_THEMES = (await (await fetch("/api/house-cover/options")).json()).themes || [];
  return HOUSE_THEMES;
}
async function coverColors(f){
  // one house cloth for light pages and one for dark, each previewed as this folder's real cover
  const themes = await houseThemes();
  const pick = {light: f.themes.light, dark: f.themes.dark}, changed = {};
  const column = mode => `<section>
      <h3>${mode === "light" ? "On light pages" : "On dark pages"}<button class="linkbtn" type="button" data-auto="${mode}">Let the folder choose</button></h3>
      <img class="prev" data-prev="${mode}" alt="${esc(f.name)} as it looks on ${mode} pages">
      <div class="swatches" role="radiogroup" aria-label="Cover color on ${mode} pages">${themes.filter(t => t.mode === mode).map(t =>
        `<button type="button" class="sw" role="radio" data-mode="${mode}" data-key="${esc(t.key)}" title="${esc(t.name)}" aria-label="${esc(t.name)}"
           style="--c:${esc(t.cloth)};--f:${esc(t.foil)};--f2:${esc(t.foil2 || t.foil)}"></button>`).join("")}</div>
    </section>`;
  const got = await ask({title: "Cover color", wide: true, ok: "Save",
    note: "Choose the cloth " + f.name + " is bound in. It has one for light pages and one for dark.",
    body: `<div class="palette">${column("light")}${column("dark")}</div>`,
    setup: root => {
      const show = mode => {
        const all = [...root.querySelectorAll(`.sw[data-mode="${mode}"]`)];
        all.forEach(b => { const on = b.dataset.key === pick[mode]; b.setAttribute("aria-checked", String(on)); b.tabIndex = on ? 0 : -1; });
        if (!all.some(b => b.tabIndex === 0)) all[0].tabIndex = 0;
        root.querySelector(`[data-prev="${mode}"]`).src = coverSrc(f, mode, pick[mode] || "auto");
      };
      root.querySelectorAll(".sw").forEach(b => {
        b.onclick = () => { pick[b.dataset.mode] = changed[b.dataset.mode] = b.dataset.key; show(b.dataset.mode); };
        b.onkeydown = e => {   // arrow keys move through one row of swatches, like any radio group
          const step = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1}[e.key];
          if (!step) return;
          e.preventDefault();
          const all = [...root.querySelectorAll(`.sw[data-mode="${b.dataset.mode}"]`)];
          const next = all[(all.indexOf(b) + step + all.length) % all.length];
          next.click(); next.focus();
        };
      });
      root.querySelectorAll("[data-auto]").forEach(b => b.onclick = () => {
        const mode = b.dataset.auto;
        pick[mode] = null; changed[mode] = null; show(mode);
      });
      show("light"); show("dark");
    },
    submit: () => Object.keys(changed).length ? send("/api/studio/folders/" + f.id, "PATCH", {themes: changed}) : Promise.resolve({})});
  if (!got || !got.folders) return;
  folders = got.folders;
  renderLibrary();
  toast("Cover color saved.");
}
function startRename(f){
  const input = $("rename");
  input.focus(); input.select();
  let settled = false;
  const finish = async save => {
    if (settled) return;
    settled = true;
    renaming = false;
    const name = input.value.trim();
    if (save && name && name !== f.name) {
      const d = await send("/api/studio/folders/" + f.id, "PATCH", {name});
      if (d.error) toast(d.error); else folders = d.folders;
    }
    renderLibrary();
  };
  input.onkeydown = e => { if (e.key === "Enter") finish(true); if (e.key === "Escape") finish(false); };
  input.onblur = () => finish(true);
}
async function setPassword(f){
  const got = await ask({title: (f.protected ? "Change the password for " : "Protect ") + f.name,
    note: f.protected ? "" : "Its work then stays hidden, even in the Library, until the folder is opened with the password.",
    fields: [{name: "password", label: f.protected ? "New password" : "Password", type: "password", autocomplete: "new-password"}],
    ok: "Save", submit: v => send("/api/studio/folders/" + f.id, "PATCH", {password: v.password}),
    extra: f.protected ? {label: "Remove password", run: () => send("/api/studio/folders/" + f.id, "PATCH", {remove_password: true})} : null});
  if (!got) return;
  folders = got.folders;
  renderLibrary();
  toast(folderOf(f.id).protected ? "Password saved." : "Password removed.");
}
async function lockFolder(f){
  const d = await send("/api/studio/folders/" + f.id + "/lock", "POST");
  if (d.error) { toast(d.error); return; }
  await reload();
  goTo("root");
  toast(f.name + " is locked.");
}
async function deleteFolder(f){
  const n = inFolder(f).length;
  if (!(await confirmAsk("Delete " + f.name + "?", n ? `Its ${plural(n, "item")} stay, and move to the Library.` : "It is empty.", "Delete folder"))) return;
  const d = await send("/api/studio/folders/" + f.id, "DELETE");
  if (d.error) { toast(d.error); return; }
  await reload();
  goTo("root");
  toast("Folder deleted." + (n ? " Its work is in the Library." : ""));
}

// ---------------------------------------------------------------- acting on the selection
async function moveTo(target, ids){
  const f = target && folderOf(target);
  if (f && !f.open && !(await unlock(f))) return;
  const before = new Map(images.filter(i => ids.includes(i.id)).map(i => [i.id, i.folder_id || null]));
  if ([...before.values()].every(x => x === target)) return;
  const d = await send("/api/studio/items/move", "POST", {ids, folder: target});
  if (d.error) { toast(d.error); return; }
  images.forEach(i => { if (before.has(i.id)) i.folder_id = target; });
  picked.clear(); anchor = null;
  if (!current || !visible(current)) showFirst(); else renderLibrary();
  toast(`Moved ${plural(d.moved, "item")} to ${f ? f.name : "the Library"}`, async () => {
    const back = {};
    before.forEach((folder, id) => (back[folder || ""] ||= []).push(id));
    for (const [folder, list] of Object.entries(back)) await send("/api/studio/items/move", "POST", {ids: list, folder: folder || null});
    images.forEach(i => { if (before.has(i.id)) i.folder_id = before.get(i.id); });
    renderLibrary();
  });
}
$("move-btn").innerHTML = ICON.move + "<span>Move to…</span>";
$("move-btn").onclick = () => {
  const ids = [...picked], here = view === "root" ? null : view;
  const entries = [{text: "Move " + plural(ids.length, "item") + " to"}];
  if (here) entries.push({text: "Library (no folder)", icon: ICON.out, run: () => moveTo(null, ids)});
  folders.filter(f => f.id !== here).forEach(f => entries.push({text: f.name, icon: f.protected ? ICON.lock : ICON.folder, run: () => moveTo(f.id, ids)}));
  entries.push("-", {text: "New folder…", icon: ICON.newFolder, run: async () => { const id = await newFolder(); if (id) moveTo(id, ids); }});
  openMenu($("move-btn"), entries);
};
async function deletePicked(){
  const ids = [...picked];
  if (!(await confirmAsk("Delete " + plural(ids.length, "item") + "?", "They cannot be recovered. Anything still being made stops showing here, though its service may still finish it.", "Delete"))) return;
  const d = await send("/api/studio/items/delete", "POST", {ids});
  if (d.error) { toast(d.error); return; }
  images = images.filter(i => !picked.has(i.id));
  if (state.source && picked.has(state.source.id)) state.source = null;
  picked.clear(); anchor = null;
  if (current && !images.some(i => i.id === current.id)) showFirst(); else renderLibrary();
  toast("Deleted " + plural(d.deleted, "item") + ".");
  sync();
}
$("bulk-delete").innerHTML = ICON.trash + "<span>Delete</span>";
$("bulk-delete").onclick = deletePicked;
$("sel-clear").innerHTML = ICON.x;
$("sel-clear").onclick = clearPicked;
$("sel-all").onclick = () => {
  const shown = viewed();
  if (shown.every(i => picked.has(i.id))) picked.clear(); else shown.forEach(i => picked.add(i.id));
  renderLibrary();
};
$("select-btn").onclick = () => { const first = viewed()[0]; if (first) toggle(first.id); };
document.addEventListener("keydown", e => {
  if ($("dlg").open) return;
  if (e.key === "Escape" && picked.size && !menuAnchor) { clearPicked(); return; }
  if (e.target.closest("input, textarea, select")) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a" && (picked.size || $("gallery").contains(document.activeElement))) {
    e.preventDefault(); viewed().forEach(i => picked.add(i.id)); renderLibrary();
  } else if ((e.key === "Delete" || e.key === "Backspace") && picked.size) {
    e.preventDefault(); deletePicked();
  }
});
async function remove(img){
  const pending = img.status === "pending";
  const ok = await confirmAsk(pending ? "Stop waiting for this?" : "Delete this?",
    pending ? "It leaves the studio. The service may still finish it, and charge for it." : "It cannot be recovered.",
    pending ? "Remove" : "Delete");
  if (!ok) return;
  const r = await fetch("/api/studio/image/" + img.id, {method: "DELETE"});
  if (!r.ok) { toast("That could not be deleted."); return; }
  images = images.filter(i => i.id !== img.id);
  picked.delete(img.id);
  if (state.source && state.source.id === img.id) state.source = null;
  showFirst();
  toast("Deleted.");
  sync();
}
// ---------------------------------------------------------------- choosing a model without guessing
// "What are you making?" picks the model (Auto) from CFG.tasks; the card under the menu says what the
// chosen model is for, from sources, and shows its own pictures from the sample set; the comparison
// shows one request answered by every model.
let SAMPLES = null;
const cmp = {kind: "create", key: null};
function tasks(mode){ return (CFG && CFG.tasks && CFG.tasks[mode]) || []; }
function task(mode){ return tasks(mode).find(t => t.key === state.task[mode]) || tasks(mode)[0]; }
function autoModel(mode){ const t = task(mode); return t && CFG.models.find(m => m.id === t.model && ready(m)) ? t.model : null; }
function renderTasks(){
  const list = tasks(state.mode);
  $("task-fld").hidden = !list.length;
  if (!list.length) return;
  chips("tasks", list.map(t => t.key), k => list.find(t => t.key === k).label, task(state.mode).key, v => {
    state.task[state.mode] = v;
    if (state.auto[state.mode] && autoModel(state.mode)) state.model[state.mode] = autoModel(state.mode);
    layout();
  });
}
function samplesOf(id, kind){
  const r = (SAMPLES && SAMPLES.results && SAMPLES.results[id]) || {};
  const keys = kind === "edit" ? (SAMPLES ? SAMPLES.edits.map(e => "edit-" + e.key) : []) : (SAMPLES ? SAMPLES.prompts.map(p => p.key) : []);
  return keys.filter(k => r[k]).map(k => ({key: k, ...r[k]}));
}
function typical(list){
  const s = list.map(x => x.seconds).sort((a, b) => a - b);
  return s.length ? s[Math.floor(s.length / 2)] : null;
}
function renderCard(){
  const m = model(), box = $("mcard");
  const kind = state.mode === "edit" ? "edit" : "create";
  box.hidden = state.mode === "video" || !m || !m.card;
  if (box.hidden) return;
  const c = m.card, mine = samplesOf(m.id, kind);
  const four = (SAMPLES && SAMPLES.strip) || [];   // the person, words, details and imagination prompts
  const strip = kind === "edit" ? mine : four.map(k => mine.find(x => x.key === k)).filter(Boolean);
  const secs = typical(mine);
  const facts = [secs != null ? "about " + (secs < 10 ? secs.toFixed(0) : Math.round(secs)) + " seconds" : null,
                 m.max_size ? "up to " + m.max_size : null].filter(Boolean);
  const pick = k => kind === "edit" && c[k + "_edit"] ? c[k + "_edit"] : c[k];   // a model that does both has edit points
  box.innerHTML = `<div class="best">${esc(pick("best"))}</div>
    <ul>${(pick("good") || []).map(g => `<li class="good">${esc(g)}</li>`).join("")}${(pick("weak") || []).map(w => `<li class="weak">${esc(w)}</li>`).join("")}</ul>
    <div class="facts">${facts.map(esc).join("<span aria-hidden='true'>·</span>")}</div>
    ${strip.length ? `<div class="strip">${strip.slice(0, 4).map(x => `<button type="button" data-key="${esc(x.key)}" aria-label="See ${esc(m.label)}'s sample next to the other models"><img src="/static/studio-samples/${esc(x.file)}" alt="" loading="lazy"></button>`).join("")}</div>` : ""}
    <div class="foot"><button class="linkbtn" type="button" id="card-compare">Compare every model on the same requests</button></div>
    ${(c.sources || []).length ? `<details><summary>Where this comes from</summary>${c.sources.map(s => `<div><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a></div>`).join("")}</details>` : ""}`;
  box.querySelectorAll(".strip button").forEach(b => b.onclick = () => openCompare(kind, b.dataset.key.replace(/^edit-/, "")));
  $("card-compare").onclick = () => openCompare(kind);
}
function openCompare(kind, key){
  cmp.kind = kind || "create";
  cmp.key = key || null;
  renderCompare();
  if (!$("compare").open) $("compare").showModal();
}
function renderCompare(){
  pressed("cmp-kind", cmp.kind);
  const list = !SAMPLES ? [] : cmp.kind === "edit" ? SAMPLES.edits : SAMPLES.prompts;
  if (!list.some(p => p.key === cmp.key)) cmp.key = list.length ? list[0].key : null;
  chips("cmp-prompts", list.map(p => p.key), k => list.find(p => p.key === k).label, cmp.key, v => { cmp.key = v; renderCompare(); });
  const p = list.find(x => x.key === cmp.key);
  $("cmp-text").textContent = p ? "“" + p.text + "”" : "The sample set has not been made yet.";
  const grid = $("cmp-grid");
  grid.innerHTML = "";
  if (!p) return;
  const sampleKey = cmp.kind === "edit" ? "edit-" + p.key : p.key;
  const cards = [];
  if (cmp.kind === "edit") {
    const base = (SAMPLES.results[SAMPLES.base_model] || {})[p.base];
    if (base) cards.push({base: true, label: "Before the edit", file: base.file, note: "the picture every model was given"});
  }
  CFG.models.filter(m => m.does.includes(cmp.kind)).forEach(m => {
    const s = (SAMPLES.results[m.id] || {})[sampleKey];
    cards.push({id: m.id, label: m.label, file: s && s.file,
                note: s ? (s.seconds < 10 ? s.seconds.toFixed(0) : Math.round(s.seconds)) + " s · " + money(s.usd) : "no sample"});
  });
  cards.forEach(c => {
    const d = document.createElement("div");
    d.className = "cmp-card" + (c.base ? " base" : "");
    d.innerHTML = (c.file ? `<button class="pic" type="button" aria-label="Enlarge ${esc(c.label)}"><img src="/static/studio-samples/${esc(c.file)}" alt="" loading="lazy"></button>`
                          : `<div class="gap">The service refused or failed this one.</div>`)
      + `<div class="who"><b>${esc(c.label)}</b><span>${esc(c.note)}</span></div>`
      + (c.id ? `<button class="linkbtn use" type="button" aria-label="Use ${esc(c.label)}">Use this model</button>` : "");
    if (c.file) d.querySelector(".pic").onclick = () => {
      $("lightbox-img").src = "/static/studio-samples/" + c.file;
      $("lightbox-img").alt = c.label;
      $("lightbox-cap").textContent = c.label + " · " + c.note;
      $("lightbox").hidden = false;
      $("lightbox-close").focus();
    };
    if (c.id) d.querySelector(".use").onclick = () => {
      $("compare").close();
      setMode(cmp.kind);
      state.auto[cmp.kind] = false;
      state.model[cmp.kind] = c.id;
      layout();
      say("Switched to " + c.label + ".");
    };
    grid.appendChild(d);
  });
  $("cmp-foot").textContent = SAMPLES ? "Each model was given exactly these words" + (cmp.kind === "edit" ? " and the same picture" : "")
    + ", once, on " + SAMPLES.made + ". Times and prices are what that one run took." : "";
}
$("cmp-kind").querySelectorAll("button").forEach(b => b.onclick = () => { cmp.kind = b.dataset.v; cmp.key = null; renderCompare(); });
$("compare-close").innerHTML = ICON.x;
$("compare-close").onclick = () => $("compare").close();
$("lightbox-close").onclick = () => { $("lightbox").hidden = true; };
$("lightbox").onclick = e => { if (e.target === $("lightbox")) $("lightbox").hidden = true; };
$("compare").addEventListener("cancel", e => { if (!$("lightbox").hidden) { e.preventDefault(); $("lightbox").hidden = true; } });

function say(text, err){ $("status").textContent = text; $("status").classList.toggle("err", !!err); }

function replace(img){
  const at = images.findIndex(i => i.id === img.id);
  if (at >= 0) images[at] = img;
  if (current && current.id === img.id) showImage(img); else renderGrid();
}
function watch(){
  // ask about each pending video until none is left
  clearTimeout(pollTimer);
  if (!images.some(i => i.status === "pending")) return;
  pollTimer = setTimeout(async () => {
    for (const img of images.filter(i => i.status === "pending")) {
      try {
        const r = await fetch("/api/studio/image/" + img.id + "/check");
        const d = await r.json().catch(() => ({}));
        if (r.status === 404) { images = images.filter(i => i.id !== img.id); renderGrid(); continue; }
        const thing = img.kind === "video" ? "video" : "image";
        if (!r.ok) { if (current && current.id === img.id) say(d.error || "Still waiting on the " + thing + ".", true); continue; }
        if (d.image.status !== "pending" || d.image.progress !== img.progress) replace(d.image);
        if (d.image.status === "ready" && current && current.id === img.id) say("The " + thing + " is ready.");
        if (d.image.status === "failed" && current && current.id === img.id) say("The " + thing + " was not made.", true);
      } catch (e) { /* the next round tries again */ }
    }
    watch();
  }, 8000);
}

async function make(){
  if (busy) return;
  const m = model(), p = price();
  if (p != null && p >= 1 && !(await ask({title: "This will cost " + money(p), note: "Anything a dollar or more asks first.",
                                          ok: "Make it", submit: async () => ({})}))) return;
  busy = true; sync();
  const video = state.mode === "video";
  say(video ? "Starting the video…" : state.mode === "edit" ? "Editing the image…" : "Making the image…");
  const body = Object.assign(settings(), {prompt: $("prompt").value, model: m.id, rewrite: $("rewrite").checked,
                                          folder: view === "root" ? null : view});
  if (extending()) {
    body.extend = {id: state.extend.id};
  } else {
    if (state.source && state.mode !== "create") body.source = picture(state.source);
    if (video && m.end_image && state.end) body.end = picture(state.end);
    if ((video || state.mode === "edit") && m.refs && state.refs.length) body.refs = state.refs.map(picture);
    if (video && m.pins && state.pins.length) body.pins = state.pins.map(p => ({source: picture(p), at: p.at}));
  }
  try {
    const r = await fetch("/api/studio/generate", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { say(d.error || "That could not be made.", true); return; }
    images.unshift(d.image);
    showImage(d.image);
    say(d.image.status === "pending" ? "The " + (video ? "video" : "image") + " has started on " + d.image.service_label + ". It shows here when it is done."
                                     : "Done on " + d.image.service_label + ".");
    watch();
  } catch (e) {
    say("The connection dropped. Try again.", true);
  } finally { busy = false; sync(); requote(); }
}

function setMode(mode){
  state.mode = mode;
  state.service = "";
  pressed("mode", mode);
  fitModel();
  layout();
}
$("mode").querySelectorAll("button").forEach(b => b.onclick = () => setMode(b.dataset.v));
$("model").onchange = () => {
  const v = $("model").value;
  state.auto[state.mode] = v === "auto";   // a model picked by hand stays until Auto is picked again
  if (v !== "auto") state.model[state.mode] = v;
  state.service = "";
  layout();
};
$("service").onchange = () => { state.service = $("service").value; requote(); };
$("check-prices").onclick = async () => {
  $("check-prices").disabled = true;
  $("prices-when").textContent = "Checking every service's price…";
  try {
    const r = await fetch("/api/studio/prices", {method: "POST"});
    if (!r.ok) say("The prices could not be checked.", true);
  } catch (e) { say("The prices could not be checked.", true); }
  finally { $("check-prices").disabled = false; requote(); }
};
$("upload-btn").onclick = () => $("upload").click();
$("clear-source").onclick = () => { state.source = null; $("upload").value = ""; sync(); requote(); };
$("upload").onchange = () => {
  const f = $("upload").files[0];
  if (!f) return;
  if (f.size > 8 * 1024 * 1024) { say("Upload an image under 8 MB.", true); return; }
  const reader = new FileReader();
  reader.onload = () => { state.source = {data_url: reader.result, preview: reader.result}; say(""); sync(); requote(); };
  reader.readAsDataURL(f);
};
$("clear-extend").onclick = () => { state.extend = null; state.service = ""; sync(); requote(); };
$("end-btn").onclick = () => $("end-upload").click();
$("clear-end").onclick = () => { state.end = null; $("end-upload").value = ""; sync(); requote(); };
$("end-upload").onchange = async () => {
  const f = $("end-upload").files[0];
  if (!f) return;
  try { state.end = await shrink(f); say(""); } catch (e) { say("That picture could not be read.", true); }
  sync(); requote();
};
$("refs-btn").onclick = () => $("refs-upload").click();
$("refs-upload").onchange = () => { const m = model(); addPictures([...$("refs-upload").files], state.refs, m ? m.refs : 0); $("refs-upload").value = ""; };
$("pins-btn").onclick = () => $("pins-upload").click();
$("pins-upload").onchange = () => {
  const m = model();
  addPictures([...$("pins-upload").files], state.pins, m ? m.pins : 0, () => ({at: Math.max(0.5, Math.round((state.seconds || 5) / 2 * 2) / 2)}));
  $("pins-upload").value = "";
};
$("prompt").addEventListener("input", sync);
$("audio").addEventListener("change", () => { sync(); requote(); });
$("steps").addEventListener("input", () => { $("steps-n").textContent = $("steps").value; requote(); });
$("make").onclick = make;
$("prompt").addEventListener("keydown", e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) make(); });

(async function boot(){
  try {
    CFG = await (await fetch("/api/studio/config")).json();
    if (!CFG.ready) {
      const keys = Object.values(CFG.services).map(s => s.env).join(", ");
      $("notready").textContent = CFG.storage ? "Media Studio needs at least one of " + keys + " on this server."
                                              : "Media Studio needs R2 storage on this server.";
      $("notready").hidden = false;
    }
    Object.keys(CFG.defaults).forEach(mode => state.model[mode] = CFG.defaults[mode]);
    Object.entries(CFG.tasks || {}).forEach(([mode, list]) => { if (list.length) state.task[mode] = list[0].key; });
    try { SAMPLES = await (await fetch("/static/studio-samples/samples.json", {cache: "no-cache"})).json(); } catch (e) { SAMPLES = null; }
    ["create", "edit", "video"].forEach(mode => { state.mode = mode; fitModel(); });
    state.mode = "create";
    const q = CFG.models.find(m => m.max_steps);
    if (q) { $("steps").value = q.steps; $("steps-n").textContent = q.steps; }
    await reload();
    // the newest work goes on the stage, wherever it is filed, except in a protected folder
    const newest = images.find(i => { const f = folderOf(i.folder_id); return !f || !f.protected; });
    if (newest) showImage(newest); else renderLibrary();
    watch();
  } catch (e) { say("Media Studio could not load.", true); }
  if (CFG) layout(); else sync();
})();
