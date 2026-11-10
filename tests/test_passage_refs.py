"""The shared passage panel's reference finder (static/js/passage.js), run under node against the forms the
Reading Room's books and the app's own pages actually use. Skipped where node isn't installed."""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PASSAGE = ROOT / "webapp" / "static" / "js" / "passage.js"

# just enough of a page for the module to load: a panel with no teacher, nothing marked data-scripture
HARNESS = r"""
const fs = require("fs");
const el = () => ({hasAttribute: () => false, addEventListener() {}, classList: {toggle() {}, contains: () => false},
                   set onclick(f) {}, style: {}});
global.window = global;
global.document = {getElementById: el, querySelectorAll: () => [], addEventListener() {}, body: {children: [], classList: {toggle() {}}}};
global.matchMedia = () => ({matches: false, addEventListener() {}});
eval(fs.readFileSync(process.env.PASSAGE_JS, "utf8"));
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const out = {};
for (const c of cases.normalize) out["n:" + c] = Passage.normalize(c);
for (const c of cases.html) out["h:" + c] = Passage.linkHtml(c);
for (const c of cases.chapter) out["c:" + c] = Passage.chapter(c);
console.log(JSON.stringify(out));
"""

NORMALIZE = {
    "John 3:16": "John 3:16",
    "Rom. 8:28": "Romans 8:28",
    "1 Cor. 13:4-7": "1 Corinthians 13:4-7",
    "John 7:53-8:11": "John 7:53-8:11",
    "Psalm 23:1": "Psalm 23:1",              # one psalm, as the ESV and Scripture Memory write it
    "Psalms 23:1": "Psalm 23:1",
    "Rom. viii. 28": "Romans 8:28",          # how most of the Reading Room's older books write it
    "Ps. li. 10-12": "Psalm 51:10-12",
    "Psalm cxix. 105": "Psalm 119:105",
    "Deut. xxx. 11": "Deuteronomy 30:11",
    "John xiii. 4": "John 13:4",
    "Luke VIII. 1": "Luke 8:1",
    "I Cor. xiii. 13": "1 Corinthians 13:13",
    "II Kings 2:11": "2 Kings 2:11",
    "Song of Songs 2:4": "Song of Solomon 2:4",
    "Mark 13: 20-22": "Mark 13:20-22",       # a space after the colon, as Boyce writes it
    # never references
    "Numbers c. 1": None,                    # Numbers has 36 chapters
    "John 22:1": None,
    "Rom. ic. 3": None,                      # not a Roman numeral
    "Jude 2:1": None,
    "Mark 12": None,
    "Ex 3:14": None,                         # ambiguous short form, left out on purpose
}

HTML = {
    "See John 3:16 and Rom. viii. 28.":
        'See <a class="ref" href="/?passage=John%203%3A16" data-ref="John 3:16">John 3:16</a> and '
        '<a class="ref" href="/?passage=Romans%208%3A28" data-ref="Romans 8:28">Rom. viii. 28</a>.',
    "<code>John 3:16</code> stays code": "<code>John 3:16</code> stays code",
    '<a href="/x">John 3:16</a> is already a link': '<a href="/x">John 3:16</a> is already a link',
    "The train left at 3:16 on Tuesday": "The train left at 3:16 on Tuesday",
    "Johnson 3:16": "Johnson 3:16",
}


# a whole chapter, as teachers type a passage source in the Prep Room
CHAPTER = {"John 7": "John 7", "Ps. 23": "Psalm 23", "1 Cor 13": "1 Corinthians 13", "John 22": None, "Johnson 3": None}


@pytest.mark.skipif(not shutil.which("node"), reason="node isn't installed")
def test_the_reference_finder_reads_old_and_new_forms():
    cases = json.dumps({"normalize": list(NORMALIZE), "html": list(HTML), "chapter": list(CHAPTER)})
    env = {**os.environ, "PASSAGE_JS": str(PASSAGE)}
    run = subprocess.run(["node", "-e", HARNESS], input=cases, capture_output=True, text=True, encoding="utf-8",
                         env=env, timeout=60)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)
    for ref, want in NORMALIZE.items():
        assert out["n:" + ref] == want, ref
    for html, want in HTML.items():
        assert out["h:" + html] == want, html
    for ref, want in CHAPTER.items():
        assert out["c:" + ref] == want, ref
