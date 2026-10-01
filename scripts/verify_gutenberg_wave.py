"""Verify the Gutenberg-sourceable Reformed/historic works against Gutenberg's catalog and
write the confirmed wave to docs/reformed-gutenberg-wave.md.

Matches against the full downloadable catalog (pg_catalog.csv.gz) LOCALLY — no per-work
gutendex calls, so no throttling/hangs. Uses the same normalize + author-token matching as the
live adapter (accent-folded token overlap), so a hit here means ingestion will find it too.
The catalog is cached in .seed_cache/. Runnable plain:

    .venv\\Scripts\\python.exe scripts\\verify_gutenberg_wave.py [--refresh]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import gzip
import io
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402

from webapp.sources.matching import author_tokens, normalize  # noqa: E402

_CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv.gz"

# author -> works, transcribed from the Gb-tagged entries of docs/reformed-pd-ingestion.md
CANDIDATES = [
    ("Augustine of Hippo", ["Confessions", "The City of God", "On Christian Doctrine", "The Enchiridion", "On the Trinity"]),
    ("Eusebius", ["The Church History of Eusebius"]),
    ("Anselm", ["Cur Deus Homo", "Proslogium", "Monologium"]),
    ("Thomas Aquinas", ["Summa Theologica", "Catena Aurea"]),
    ("Thomas a Kempis", ["The Imitation of Christ"]),
    ("Martin Luther", ["The Bondage of the Will", "Commentary on Galatians", "Table Talk", "Ninety-Five Theses"]),
    ("John Knox", ["The History of the Reformation of Religion in Scotland"]),
    ("Hugh Latimer", ["Sermons of Hugh Latimer"]),
    ("William Tyndale", ["The Obedience of a Christian Man"]),
    ("Richard Baxter", ["The Saints' Everlasting Rest", "The Reformed Pastor", "A Call to the Unconverted"]),
    ("John Bunyan", ["The Pilgrim's Progress", "The Holy War", "Grace Abounding to the Chief of Sinners"]),
    ("Joseph Alleine", ["An Alarm to the Unconverted"]),
    ("Samuel Rutherford", ["Letters of Samuel Rutherford", "Lex Rex"]),
    ("Andrew Bonar", ["Memoir and Remains of Robert Murray McCheyne"]),
    ("Horatius Bonar", ["God's Way of Holiness", "God's Way of Peace", "The Everlasting Righteousness"]),
    ("George Muller", ["The Life of Trust"]),
    ("Jonathan Edwards", ["The Religious Affections", "Freedom of the Will", "Sinners in the Hands of an Angry God", "The Life of David Brainerd"]),
    ("George Whitefield", ["Selected Sermons of George Whitefield", "George Whitefield's Journals"]),
    ("John Newton", ["Cardiphonia", "The Life of John Newton"]),
    ("John Wesley", ["Explanatory Notes upon the New Testament", "A Plain Account of Christian Perfection", "Sermons on Several Occasions"]),
    ("Philip Doddridge", ["The Rise and Progress of Religion in the Soul"]),
    ("Isaac Watts", ["Hymns and Spiritual Songs", "The Psalms of David Imitated", "Logic"]),
    ("William Law", ["A Serious Call to a Devout and Holy Life"]),
    ("Henry Scougal", ["The Life of God in the Soul of Man"]),
    ("Charles Spurgeon", ["The Treasury of David", "All of Grace", "John Ploughman's Talk"]),
    ("J. C. Ryle", ["Expository Thoughts on the Gospels", "Holiness"]),
    ("Richard Chenevix Trench", ["Notes on the Parables of Our Lord", "Synonyms of the New Testament"]),
    ("F. W. Krummacher", ["Elijah the Tishbite", "The Suffering Saviour"]),
    ("William Smith", ["A Dictionary of the Bible"]),
    ("Alexander Cruden", ["A Complete Concordance to the Holy Scriptures"]),
    ("William Cowper", ["Olney Hymns"]),
    ("Brother Lawrence", ["The Practice of the Presence of God"]),
    ("J. H. Merle d'Aubigne", ["History of the Reformation in the Sixteenth Century"]),
    ("John Foxe", ["Foxe's Book of Martyrs"]),
    ("Alfred Edersheim", ["The Life and Times of Jesus the Messiah", "The Temple", "Sketches of Jewish Social Life", "Bible History"]),
]


def load_catalog(refresh: bool) -> list[dict]:
    cache = _ROOT / ".seed_cache" / "pg_catalog.csv.gz"
    cache.parent.mkdir(exist_ok=True)
    if refresh or not cache.exists():
        print("downloading Gutenberg catalog…", flush=True)
        r = httpx.get(_CATALOG_URL, timeout=90, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        cache.write_bytes(r.content)
    data = gzip.decompress(cache.read_bytes()).decode("utf-8", "replace")
    return list(csv.DictReader(io.StringIO(data)))


def build_index(rows: list[dict]) -> list[tuple]:
    """English text rows, pre-normalized: (id, orig_title, norm_title, author_token_set)."""
    idx = []
    for row in rows:
        if row.get("Type") != "Text" or row.get("Language") != "en":
            continue
        nt = normalize(row.get("Title"))
        if not nt:
            continue
        idx.append((row.get("Text#"), row.get("Title"), nt, author_tokens(row.get("Authors"))))
    return idx


def best_match(title: str, author: str, index: list[tuple]):
    wt = normalize(title)
    want = author_tokens(author)
    best, best_score = None, None
    for gid, otitle, nt, atoks in index:
        if not ((wt in nt or nt in wt) and min(len(nt), len(wt)) >= 3):
            continue
        if want and not (want & atoks):
            continue
        score = (2 if nt == wt else 0) - abs(len(nt) - len(wt)) / 100.0
        if best_score is None or score > best_score:
            best, best_score = (gid, otitle), score
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download the catalog instead of using the cache")
    args = ap.parse_args()

    index = build_index(load_catalog(args.refresh))
    print(f"catalog: {len(index):,} English text works indexed\n", flush=True)

    results = []
    for author, works in CANDIDATES:
        print(author, flush=True)
        for title in works:
            m = best_match(title, author, index)
            results.append((author, title, m))
            print(f"  {'OK #' + m[0] if m else '-- (not found)':16} {title}"
                  + (f"   [{m[1][:44]}]" if m else ""), flush=True)

    ok = [r for r in results if r[2]]
    today = datetime.date.today().isoformat()
    lines = [
        "# Gutenberg wave — verified sourceable works",
        "",
        f"Generated by `scripts/verify_gutenberg_wave.py` on {today}, matched against Gutenberg's full "
        "catalog with the same accent-folded title + author-token logic the ingestion adapter uses. "
        "The Gutenberg-reachable subset of [reformed-pd-ingestion.md](reformed-pd-ingestion.md).",
        "",
        f"**Confirmed {len(ok)} / {len(results)} works on Gutenberg.**",
        "",
        "## Confirmed — ready to ingest",
        "",
    ]
    cur = None
    for author, title, m in results:
        if not m:
            continue
        if author != cur:
            lines.append(f"### {author}")
            cur = author
        lines.append(f"- {title} — Gutenberg #{m[0]} · `https://www.gutenberg.org/ebooks/{m[0]}.txt.utf-8`  \n  _catalog title: {m[1]}_")
    lines += ["", "## Not found on Gutenberg — fall through to the CCEL pass, then archive.org", ""]
    cur = None
    for author, title, m in results:
        if m:
            continue
        if author != cur:
            lines.append(f"### {author}")
            cur = author
        lines.append(f"- {title}")
    out = _ROOT / "docs" / "reformed-gutenberg-wave.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nCONFIRMED {len(ok)} / {len(results)} | wrote {out.relative_to(_ROOT)}", flush=True)


if __name__ == "__main__":
    main()
