"""Build a shareable reference page listing every title the study-Bible MCP can serve.
Reads the cleaned father roster JSON and emits a self-contained HTML artifact."""
import json
import os
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
fathers = data["fathers"]
fathers_json = json.dumps(fathers, ensure_ascii=False)

HTML = r"""<title>Study Bible Corpus</title>
<meta name="description" content="Every source the study-Bible MCP connector can serve — translations, lexicons, commentaries, the church-fathers catena, creeds and confessions.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,500&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root{
    --paper:#f0e8dc; --surface:#f8f2ea; --surface-2:#e9e0d1; --sunk:#e2d7c6; --ink:#1e2026;
    --ink-soft:#54596a; --ink-faint:#8b8f9b; --rule:#ddd3c1; --rule-strong:#c9bda6;
    --accent:#c05a64; --accent-soft:#a84a55; --iron:#42718a; --brass:#9a7c3d;
    --serif:"Spectral",Georgia,serif; --sans:"Public Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    --shadow:0 14px 40px -22px rgba(40,32,22,.55);
  }
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
    --paper:#14151a; --surface:#1b1d23; --surface-2:#23252c; --sunk:#101116; --ink:#e9e7e0;
    --ink-soft:#a9aeb9; --ink-faint:#787d88; --rule:#2c2f37; --rule-strong:#3b3f49;
    --accent:#dd8089; --accent-soft:#b0555f; --iron:#7fb0c2; --brass:#c7a45f;
    --shadow:0 16px 44px -22px rgba(0,0,0,.7);
  }}
  :root[data-theme="dark"]{
    --paper:#14151a; --surface:#1b1d23; --surface-2:#23252c; --sunk:#101116; --ink:#e9e7e0;
    --ink-soft:#a9aeb9; --ink-faint:#787d88; --rule:#2c2f37; --rule-strong:#3b3f49;
    --accent:#dd8089; --accent-soft:#b0555f; --iron:#7fb0c2; --brass:#c7a45f;
    --shadow:0 16px 44px -22px rgba(0,0,0,.7);
  }
  *{box-sizing:border-box}
  body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6;
    -webkit-font-smoothing:antialiased}
  .page{max-width:940px;margin:0 auto;padding:48px 24px 90px}
  h1,h2,h3{text-wrap:balance}
  a{color:var(--iron)}

  /* header */
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:500}
  h1{font-family:var(--serif);font-weight:600;font-size:clamp(2rem,5vw,3rem);line-height:1.08;margin:.35em 0 .18em;letter-spacing:-.01em}
  .lead{font-size:1.06rem;color:var(--ink-soft);max-width:64ch;margin:0 0 26px}
  .lead b{color:var(--ink);font-weight:600}
  .stats{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 8px}
  .stat{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:11px 15px;min-width:96px}
  .stat .n{font-family:var(--serif);font-weight:600;font-size:1.5rem;line-height:1;color:var(--ink);font-variant-numeric:tabular-nums}
  .stat .l{font-family:var(--mono);font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-faint);margin-top:5px}

  /* sections */
  section{margin-top:44px}
  .sec-h{display:flex;align-items:baseline;gap:12px;border-bottom:2px solid var(--rule-strong);padding-bottom:9px;margin-bottom:18px}
  .sec-h h2{font-family:var(--serif);font-weight:600;font-size:1.42rem;margin:0;color:var(--ink)}
  .sec-h .k{font-family:var(--mono);font-size:11px;color:var(--iron);font-weight:500;margin-left:auto;flex:none}
  .sec-note{font-size:13.5px;color:var(--ink-soft);margin:-8px 0 18px;max-width:62ch}

  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:12px}
  .item{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:13px 15px}
  .item .t{font-family:var(--serif);font-weight:600;font-size:1.04rem;color:var(--ink);line-height:1.25}
  .item .t .abbr{font-family:var(--mono);font-size:12px;color:var(--accent);font-weight:500;margin-right:7px}
  .item .d{font-size:12.5px;color:var(--ink-soft);margin-top:3px;line-height:1.45}

  /* compact pill rows for creeds */
  .pillrow{display:flex;flex-wrap:wrap;gap:8px}
  .pill{background:var(--surface);border:1px solid var(--rule);border-radius:999px;padding:6px 13px;font-size:13.5px;color:var(--ink)}
  .pill b{font-weight:600}

  /* fathers */
  .fbar{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-bottom:16px}
  .search{flex:1;min-width:220px;display:flex;align-items:center;gap:9px;background:var(--surface);border:1px solid var(--rule-strong);border-radius:10px;padding:9px 13px}
  .search svg{width:16px;height:16px;stroke:var(--ink-faint);fill:none;stroke-width:2;flex:none}
  .search input{flex:1;border:0;background:none;font-family:var(--sans);font-size:14.5px;color:var(--ink);outline:none}
  .fcount{font-family:var(--mono);font-size:12px;color:var(--ink-faint);flex:none}
  .fathers{columns:3 210px;column-gap:26px}
  .fentry{break-inside:avoid;display:flex;align-items:baseline;gap:8px;padding:4px 0;border-bottom:1px solid var(--rule);line-height:1.35}
  .fentry .fn{font-size:13.7px;color:var(--ink);flex:1}
  .fentry .fc{font-family:var(--mono);font-size:11px;color:var(--ink-faint);flex:none;font-variant-numeric:tabular-nums}
  .fnone{color:var(--ink-soft);font-size:14px;padding:14px 0}
  mark{background:color-mix(in srgb,var(--accent) 30%,transparent);color:inherit;border-radius:3px;padding:0 1px}

  .foot{margin-top:52px;padding-top:18px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--ink-faint);line-height:1.6}
  .foot b{color:var(--ink-soft)}
  @media(max-width:560px){ .fathers{columns:1} .page{padding:34px 16px 70px} }
</style>

<div class="page">
  <header>
    <div class="eyebrow">Study-Bible MCP &middot; source corpus</div>
    <h1>Everything the connector can cite</h1>
    <p class="lead">The complete inventory of texts the study-Bible MCP serves from owned data &mdash; translations, tagged original languages, lexicons, public-domain commentaries, a <b>~300-author church-fathers catena</b>, and the historic creeds, confessions, and catechisms. This is the connector's built-in library, distinct from the teacher-facing Living Library catalog.</p>
    <div class="stats" id="stats"></div>
  </header>

  <section>
    <div class="sec-h"><h2>Bible translations</h2><span class="k">5 texts</span></div>
    <div class="grid">
      <div class="item"><div class="t"><span class="abbr">BSB</span>Berean Standard Bible</div><div class="d">Default modern readable text; public domain, Strong's-mapped.</div></div>
      <div class="item"><div class="t"><span class="abbr">WEB</span>World English Bible</div><div class="d">Public-domain modern English base text.</div></div>
      <div class="item"><div class="t"><span class="abbr">KJV</span>King James Version</div><div class="d">The 1769 Authorized Version.</div></div>
      <div class="item"><div class="t"><span class="abbr">ASV</span>American Standard Version</div><div class="d">1901 formal-equivalent revision.</div></div>
      <div class="item"><div class="t"><span class="abbr">YLT</span>Young's Literal Translation</div><div class="d">Hyper-literal rendering for word study.</div></div>
    </div>
  </section>

  <section>
    <div class="sec-h"><h2>Original languages &amp; morphology</h2><span class="k">tagged</span></div>
    <div class="grid">
      <div class="item"><div class="t"><span class="abbr">TAHOT</span>Hebrew Old Testament</div><div class="d">STEPBible amalgamated, tagged text with Strong's + morphology.</div></div>
      <div class="item"><div class="t"><span class="abbr">TAGNT</span>Greek New Testament</div><div class="d">STEPBible amalgamated, tagged Greek NT.</div></div>
      <div class="item"><div class="t"><span class="abbr">TEHMC</span>Hebrew morphology codes</div><div class="d">Parsing tables for every tagged Hebrew word.</div></div>
      <div class="item"><div class="t"><span class="abbr">TEGMC</span>Greek morphology codes</div><div class="d">Parsing tables for every tagged Greek word.</div></div>
    </div>
  </section>

  <section>
    <div class="sec-h"><h2>Lexicons</h2><span class="k">5 works</span></div>
    <div class="grid">
      <div class="item"><div class="t"><span class="abbr">TBESH</span>Extended Strong's Hebrew</div><div class="d">Tyndale brief extended Hebrew lexicon.</div></div>
      <div class="item"><div class="t"><span class="abbr">TBESG</span>Extended Strong's Greek</div><div class="d">Tyndale brief extended Greek lexicon.</div></div>
      <div class="item"><div class="t"><span class="abbr">TFLSJ</span>Liddell-Scott-Jones</div><div class="d">LSJ classical Greek lexicon subset.</div></div>
      <div class="item"><div class="t"><span class="abbr">BDB</span>Brown-Driver-Briggs</div><div class="d">The standard Hebrew &amp; Aramaic lexicon.</div></div>
      <div class="item"><div class="t">Abbott-Smith</div><div class="d">Manual Greek Lexicon of the New Testament.</div></div>
    </div>
  </section>

  <section>
    <div class="sec-h"><h2>Commentaries</h2><span class="k">7 works &middot; public domain</span></div>
    <div class="grid">
      <div class="item"><div class="t">Matthew Henry</div><div class="d">Complete devotional commentary on the whole Bible.</div></div>
      <div class="item"><div class="t">Jamieson-Fausset-Brown</div><div class="d">One-volume critical &amp; explanatory (JFB).</div></div>
      <div class="item"><div class="t">John Gill</div><div class="d">Exposition of the Old &amp; New Testaments.</div></div>
      <div class="item"><div class="t">John Calvin</div><div class="d">Calvin's Commentaries.</div></div>
      <div class="item"><div class="t">Adam Clarke</div><div class="d">Clarke's Commentary on the whole Bible.</div></div>
      <div class="item"><div class="t">Keil &amp; Delitzsch</div><div class="d">Commentary on the Old Testament.</div></div>
      <div class="item"><div class="t">Barnes' Notes</div><div class="d">Albert Barnes, via SWORD module.</div></div>
    </div>
  </section>

  <section>
    <div class="sec-h"><h2>Creeds, confessions &amp; catechisms</h2><span class="k">21 documents</span></div>
    <div class="pillrow">
      <span class="pill">Apostles' Creed</span>
      <span class="pill">Nicene Creed</span>
      <span class="pill">Athanasian Creed</span>
      <span class="pill">Chalcedonian Definition</span>
      <span class="pill">Belgic Confession</span>
      <span class="pill">Heidelberg Catechism</span>
      <span class="pill">Canons of Dort</span>
      <span class="pill">Second Helvetic Confession</span>
      <span class="pill">Scots Confession</span>
      <span class="pill"><b>Westminster</b> Confession</span>
      <span class="pill"><b>Westminster</b> Larger Catechism</span>
      <span class="pill"><b>Westminster</b> Shorter Catechism</span>
      <span class="pill">WSC &mdash; PCA edition</span>
      <span class="pill">Sum of Saving Knowledge</span>
      <span class="pill">Savoy Declaration</span>
      <span class="pill"><b>1689</b> Baptist Confession</span>
      <span class="pill">Keach's Catechism</span>
      <span class="pill">1858 Abstract of Principles</span>
      <span class="pill">Catechism for Young Children</span>
      <span class="pill">Thirty-Nine Articles</span>
      <span class="pill">Luther's 95 Theses</span>
    </div>
  </section>

  <section>
    <div class="sec-h"><h2>Reference &amp; study aids</h2></div>
    <div class="grid">
      <div class="item"><div class="t">Easton's Bible Dictionary</div><div class="d">Classic single-volume dictionary.</div></div>
      <div class="item"><div class="t">Morning &amp; Evening</div><div class="d">Spurgeon's daily devotional.</div></div>
      <div class="item"><div class="t">Septuagint</div><div class="d">Brenton (English), Swete (Greek), Copenhagen (LXX + English).</div></div>
      <div class="item"><div class="t">Cross-references</div><div class="d">Treasury of Scripture Knowledge / OpenBible.</div></div>
      <div class="item"><div class="t">Parallel passages</div><div class="d">Gospel &amp; synoptic parallels (TheologAI).</div></div>
      <div class="item"><div class="t">People, places &amp; events</div><div class="d">ACAI + Theographic + TIPNR proper-names spine.</div></div>
      <div class="item"><div class="t">unfoldingWord notes</div><div class="d">Translation notes, key terms, study notes, dictionary.</div></div>
    </div>
  </section>

  <section>
    <div class="sec-h"><h2>Church-fathers catena</h2><span class="k" id="fkey"></span></div>
    <p class="sec-note">A verse-linked catena spanning the Apostolic Fathers, the Nicene and post-Nicene doctors, the Syriac and Desert traditions, the medieval schoolmen, the Reformers, and a few moderns. Every author below is searchable and citable by passage.</p>
    <div class="fbar">
      <label class="search">
        <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        <input id="fsearch" type="text" placeholder="Filter authors — e.g. Augustine, Syrian, Chrysostom" aria-label="Filter church fathers">
      </label>
      <span class="fcount" id="fcount"></span>
    </div>
    <div class="fathers" id="fathers"></div>
    <div class="fnone" id="fnone" hidden>No author matches that filter.</div>
  </section>

  <div class="foot">
    <b>Provenance.</b> All titles are served from owned data (public-domain texts and openly-licensed scholarly resources) &mdash; the connector makes no runtime call to a third-party API to answer. Counts reflect the built database. This corpus is separate from the <b>Living Library</b>, the teacher-facing catalog of full-length works.
  </div>
</div>

<script id="fathers-data" type="application/json">__FATHERS_JSON__</script>
<script>
  var FATHERS = JSON.parse(document.getElementById("fathers-data").textContent);
  var TOTAL_ENTRIES = FATHERS.reduce(function(s,f){return s+f.count;},0);

  // stat strip
  var STATS = [
    [FATHERS.length, "Church fathers"],
    [TOTAL_ENTRIES.toLocaleString(), "Catena entries"],
    [5, "Translations"],
    [7, "Commentaries"],
    [21, "Creeds & confessions"],
    [5, "Lexicons"]
  ];
  document.getElementById("stats").innerHTML = STATS.map(function(s){
    return '<div class="stat"><div class="n">'+s[0]+'</div><div class="l">'+s[1]+'</div></div>';
  }).join("");
  document.getElementById("fkey").textContent = FATHERS.length + " authors · " + TOTAL_ENTRIES.toLocaleString() + " entries";

  function esc(s){return (s||"").replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}
  var host = document.getElementById("fathers"), countEl = document.getElementById("fcount"), noneEl = document.getElementById("fnone");

  function render(q){
    q = (q||"").trim().toLowerCase();
    var shown = FATHERS.filter(function(f){ return !q || f.name.toLowerCase().indexOf(q)>=0; });
    countEl.textContent = shown.length===FATHERS.length ? (FATHERS.length+" shown") : (shown.length+" of "+FATHERS.length);
    noneEl.hidden = shown.length>0;
    host.hidden = shown.length===0;
    host.innerHTML = shown.map(function(f){
      var name = esc(f.name);
      if(q){ var i=f.name.toLowerCase().indexOf(q); if(i>=0){ name = esc(f.name.slice(0,i))+"<mark>"+esc(f.name.slice(i,i+q.length))+"</mark>"+esc(f.name.slice(i+q.length)); } }
      return '<div class="fentry"><span class="fn">'+name+'</span><span class="fc">'+f.count+'</span></div>';
    }).join("");
  }
  render("");
  document.getElementById("fsearch").addEventListener("input", function(e){ render(e.target.value); });
</script>
"""

out = sys.argv[2]
open(out, "w", encoding="utf-8").write(HTML.replace("__FATHERS_JSON__", fathers_json))
print("wrote", out, "chars:", os.path.getsize(out))
