/* The Media Studio's player, with Loop or Bounce (forward, then backward, on repeat). Browsers can't play video backward,
   so for Bounce the page reads the clip's MP4 itself, decodes every frame (WebCodecs), encodes each frame on its own so
   any frame decodes alone, and writes a looping WebM: the frames forward, then the same frames backward. It stays in this
   page (nothing is uploaded), and it has no sound. Used by studio.js. */
"use strict";
const Bounce = (() => {
  const KEY = "studio-playback", KEEP = 3;
  const built = new Map();   // item id -> {url, end}: its bounce, the last few only
  const able = typeof VideoDecoder === "function" && typeof VideoEncoder === "function";
  let mode = "loop", stop = () => {};
  try { if (localStorage.getItem(KEY) === "bounce" && able) mode = "bounce"; } catch (e) { /* the default */ }

  function mount(box, img, seg, note){
    stop();
    let v = null, gone = false, making = null, failed = false;
    const say = text => { note.textContent = text; };
    const tell = () => say(mode !== "bounce" ? "" : failed ? "This clip can't bounce here, so it loops."
                           : making ? "Making the bounce…" : img.audio ? "Bounce plays without sound." : "");
    const make = (src, bounce) => {
      const el = document.createElement("video");
      el.src = src; el.controls = true; el.playsInline = true; el.preload = "metadata"; el.loop = true;
      if (img.width) el.width = img.width;
      if (img.height) el.height = img.height;
      if (bounce) { el.muted = true; el.dataset.bounce = "1"; }
      return el;
    };
    function swap(el, at){
      // the new player takes the old one's place, time and play state
      const playing = !!v && !v.paused && !v.ended;
      const go = () => { if (gone) return; v.replaceWith(el); v = el; if (playing) el.play().catch(() => {}); };
      if (!at) { go(); return; }
      el.preload = "auto";
      el.addEventListener("loadedmetadata", () => { el.currentTime = at; }, {once: true});
      el.addEventListener("seeked", go, {once: true});
    }
    async function bounce(){
      const have = built.get(img.id);
      if (have) { swap(make(have.url, true), v.currentTime); return; }
      if (making || failed) return;
      making = true;
      tell();
      try {
        const got = await build(img.url, () => gone);
        if (!got) return;   // left the page
        remember(img.id, got);
        if (!gone && mode === "bounce") swap(make(got.url, true), Math.min(v.currentTime, got.end));
      } catch (e) {
        failed = true;
      } finally {
        making = false;
        if (!gone) tell();
      }
    }
    function pick(m){
      if (m === mode) return;
      mode = m;
      try { localStorage.setItem(KEY, mode); } catch (e) { /* kept for this visit only */ }
      seg.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === mode)));
      if (mode === "bounce") bounce();
      else if (v.dataset.bounce) {
        const end = built.get(img.id)?.end || 0, t = v.currentTime;
        swap(make(img.url, false), t <= end ? t : Math.max(0, 2 * end - t));   // the same frame, going forward
      }
      tell();
    }

    seg.innerHTML = "";
    [["loop", "Loop"], ["bounce", "Bounce"]].forEach(([value, label]) => {
      const b = document.createElement("button");
      b.type = "button"; b.dataset.v = value; b.textContent = label;
      b.setAttribute("aria-pressed", String(value === mode));
      b.onclick = () => pick(value);
      seg.appendChild(b);
    });
    seg.hidden = !able;
    const have = mode === "bounce" && built.get(img.id);
    v = make(have ? have.url : img.url, !!have);
    box.appendChild(v);
    if (mode === "bounce" && !have) bounce();
    tell();
    stop = () => { gone = true; };
  }

  function remember(id, got){
    const old = built.get(id);
    if (old) URL.revokeObjectURL(old.url);
    built.delete(id);
    built.set(id, got);
    while (built.size > KEEP) {
      const [first, item] = built.entries().next().value;
      built.delete(first);
      URL.revokeObjectURL(item.url);
    }
  }

  /* Decode every frame of the MP4 and encode each as a VP8 key frame, then write the WebM. */
  async function build(url, left){
    const file = new Uint8Array(await (await fetch(url)).arrayBuffer());
    const track = mp4(file);
    const chunks = [];
    let broken = null;
    const enc = new VideoEncoder({
      output: chunk => { const b = new Uint8Array(chunk.byteLength); chunk.copyTo(b); chunks.push({t: chunk.timestamp, b}); },
      error: e => { broken = e; },
    });
    enc.configure({codec: "vp8", width: track.width, height: track.height, framerate: track.fps,
                   bitrate: Math.round(track.width * track.height * 0.35 * track.fps)});   // key frames run about twice this
    const dec = new VideoDecoder({
      output: frame => { if (enc.state === "configured") enc.encode(frame, {keyFrame: true}); frame.close(); },
      error: e => { broken = e; },
    });
    dec.configure({codec: track.codec, description: track.description, codedWidth: track.width, codedHeight: track.height});
    try {
      for (const s of track.samples) {
        while (dec.decodeQueueSize > 8 || enc.encodeQueueSize > 8) await new Promise(r => setTimeout(r, 2));
        if (broken) throw broken;
        if (left()) return null;
        dec.decode(new EncodedVideoChunk({type: s.key ? "key" : "delta", timestamp: s.pts, duration: s.dur,
                                          data: file.subarray(s.offset, s.offset + s.size)}));
      }
      await dec.flush();
      await enc.flush();
      if (broken) throw broken;
    } finally {
      if (dec.state !== "closed") dec.close();
      if (enc.state !== "closed") enc.close();
    }
    if (chunks.length < 3) throw new Error("too few frames");
    return webm(chunks, track.width, track.height);
  }

  /* The video track of an MP4: its codec, size and samples (offset, size, time, key frame), in decoding order. */
  function mp4(buf){
    const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
    const u32 = p => dv.getUint32(p), type = p => String.fromCharCode(buf[p], buf[p + 1], buf[p + 2], buf[p + 3]);
    function boxes(start, end){
      const out = {};
      for (let p = start; p + 8 <= end;) {
        let size = u32(p), head = 8;
        if (size === 1) { size = Number(dv.getBigUint64(p + 8)); head = 16; }
        else if (size === 0) size = end - p;
        (out[type(p + 4)] ||= []).push({at: p + head, end: p + size});
        p += size;
      }
      return out;
    }
    const inside = (b, name) => (boxes(b.at, b.end)[name] || [])[0];
    const moov = (boxes(0, buf.length).moov || [])[0];
    if (!moov) throw new Error("no moov");
    const trak = (boxes(moov.at, moov.end).trak || []).find(t => {
      const hdlr = inside(inside(t, "mdia"), "hdlr");
      return hdlr && type(hdlr.at + 8) === "vide";
    });
    if (!trak) throw new Error("no video");
    const mdia = inside(trak, "mdia"), stbl = inside(inside(mdia, "minf"), "stbl"), mdhd = inside(mdia, "mdhd");
    const scale = buf[mdhd.at] === 1 ? u32(mdhd.at + 20) : u32(mdhd.at + 12);
    const stsd = inside(stbl, "stsd"), entry = stsd.at + 8, kind = type(entry + 4);
    if (kind !== "avc1" && kind !== "avc3") throw new Error("codec " + kind);
    const avcC = inside({at: entry + 86, end: entry + u32(entry)}, "avcC");
    const description = buf.slice(avcC.at, avcC.end);
    const hex = n => n.toString(16).padStart(2, "0");
    const codec = "avc1." + hex(description[1]) + hex(description[2]) + hex(description[3]);
    const width = dv.getUint16(entry + 32), height = dv.getUint16(entry + 34);
    const table = (name, cols) => {
      const b = inside(stbl, name);
      if (!b) return null;
      const n = u32(b.at + 4), rows = [];
      for (let i = 0; i < n; i++) rows.push(cols.map((_, c) => u32(b.at + 8 + (i * cols.length + c) * 4)));
      return {rows, version: buf[b.at]};
    };
    const stsz = inside(stbl, "stsz"), fixed = u32(stsz.at + 4), count = u32(stsz.at + 8);
    const sizes = Array.from({length: count}, (_, i) => fixed || u32(stsz.at + 12 + i * 4));
    const stco = inside(stbl, "stco"), co64 = inside(stbl, "co64");
    const chunkAt = stco ? Array.from({length: u32(stco.at + 4)}, (_, i) => u32(stco.at + 8 + i * 4))
                         : Array.from({length: u32(co64.at + 4)}, (_, i) => Number(dv.getBigUint64(co64.at + 8 + i * 8)));
    const stsc = table("stsc", [1, 2, 3]).rows, stts = table("stts", [1, 2]).rows;
    const ctts = table("ctts", [1, 2]), stss = table("stss", [1]);
    const keys = stss ? new Set(stss.rows.map(r => r[0] - 1)) : null;
    const offsets = [];
    stsc.forEach(([first, per], i) => {
      const last = i + 1 < stsc.length ? stsc[i + 1][0] - 1 : chunkAt.length;
      for (let c = first; c <= last; c++) {
        let p = chunkAt[c - 1];
        for (let k = 0; k < per && offsets.length < count; k++) { offsets.push(p); p += sizes[offsets.length - 1]; }
      }
    });
    const shift = [];
    if (ctts) ctts.rows.forEach(([n, off]) => { for (let i = 0; i < n; i++) shift.push(ctts.version === 1 ? off | 0 : off); });
    const samples = [];
    let dts = 0, i = 0;
    stts.forEach(([n, delta]) => {
      for (let k = 0; k < n && i < count; k++, i++) {
        samples.push({offset: offsets[i], size: sizes[i], key: !keys || keys.has(i),
                      pts: Math.round((dts + (shift[i] || 0)) * 1e6 / scale), dur: Math.round(delta * 1e6 / scale)});
        dts += delta;
      }
    });
    const fps = Math.max(1, Math.round(count * scale / Math.max(1, dts)));
    return {codec, description, width, height, samples, fps};
  }

  /* A WebM file in memory: EBML elements, one VP8 track, a cluster every five seconds. Frames go forward, then back
     again without repeating the end frames, and the loop returns to the first. */
  function webm(chunks, w, h){
    const frames = chunks.sort((a, b) => a.t - b.t);
    const t0 = frames[0].t, ms = f => Math.round((f.t - t0) / 1000);
    const n = frames.length, end = ms(frames[n - 1]);
    const seq = frames.map(f => [ms(f), f.b]).concat(frames.slice(1, n - 1).reverse().map(f => [2 * end - ms(f), f.b]));
    const clusters = [];
    let start = -1, blocks = [];
    const close = () => { if (blocks.length) clusters.push(el(0x1F43B675, uint(0xE7, start), ...blocks)); blocks = []; };
    seq.forEach(([t, data]) => {
      if (start < 0 || t - start >= 5000) { close(); start = t; }
      const head = new Uint8Array(4);
      head[0] = 0x81;                                   // track 1
      new DataView(head.buffer).setInt16(1, t - start); // time within the cluster
      head[3] = 0x80;                                   // a key frame
      blocks.push(el(0xA3, head, data));
    });
    close();
    const ebml = el(0x1A45DFA3, uint(0x4286, 1), uint(0x42F7, 1), uint(0x42F2, 4), uint(0x42F3, 8),
                    str(0x4282, "webm"), uint(0x4287, 2), uint(0x4285, 2));
    const info = el(0x1549A966, uint(0x2AD7B1, 1000000), str(0x4D80, "Exegetica"), str(0x5741, "Exegetica"),
                    f64(0x4489, 2 * end));
    const tracks = el(0x1654AE6B, el(0xAE, uint(0xD7, 1), uint(0x73C5, 1), uint(0x83, 1), uint(0x9C, 0), str(0x86, "V_VP8"),
                                     el(0xE0, uint(0xB0, w), uint(0xBA, h))));
    const segment = el(0x18538067, info, tracks, ...clusters);
    return {url: URL.createObjectURL(new Blob([...ebml.parts, ...segment.parts], {type: "video/webm"})), end: end / 1000};
  }
  function bytes(n, width){
    const out = [];
    do { out.unshift(n % 256); n = Math.floor(n / 256); } while (n > 0 || out.length < (width || 1));
    return out;
  }
  function vint(len){
    for (let w = 1; w <= 8; w++) {
      if (len < 2 ** (7 * w) - 1) { const b = bytes(len, w); b[0] |= 1 << (8 - w); return b; }
    }
    throw new Error("too large");
  }
  function el(id, ...kids){
    const parts = [];
    let len = 0;
    kids.forEach(k => {
      if (k instanceof Uint8Array) { parts.push(k); len += k.length; }
      else { parts.push(...k.parts); len += k.len; }
    });
    const top = new Uint8Array([...bytes(id), ...vint(len)]);
    return {parts: [top, ...parts], len: top.length + len};
  }
  const uint = (id, n) => el(id, new Uint8Array(bytes(n)));
  const str = (id, s) => el(id, new TextEncoder().encode(s));
  function f64(id, x){ const b = new Uint8Array(8); new DataView(b.buffer).setFloat64(0, x); return el(id, b); }

  return {mount, stop: () => stop()};
})();
