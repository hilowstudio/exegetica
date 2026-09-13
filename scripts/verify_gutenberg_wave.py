"""Verify the Gutenberg-sourceable Reformed/historic works against gutendex and write the
confirmed wave to docs/reformed-gutenberg-wave.md.

Runs serially with per-work retries so a slow/throttling gutendex doesn't cause false misses
(the study-Bible sandbox throttles; a normal network handles this fine). Uses the SAME
gutenberg adapter that does the real fetch, so a confirmation here means ingestion will find
it too. Runnable plain:

    .venv\\Scripts\\python.exe scripts\\verify_gutenberg_wave.py [--delay 1.5] [--tries 4]
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from webapp.sources import gutenberg as G  # noqa: E402

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


async def resolve(author: str, title: str, tries: int, delay: float):
    """discover() with an outer retry so a transient gutendex timeout isn't a false miss."""
    for attempt in range(tries):
        try:
            hit = await G.discover({"title": title, "authors": [author]})
        except Exception:  # noqa: BLE001
            hit = None
        if hit:
            return hit
        await asyncio.sleep(delay * (attempt + 1))
    return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=1.5, help="base pause between lookups (grows on retry)")
    ap.add_argument("--tries", type=int, default=4, help="outer attempts per work before calling it a miss")
    args = ap.parse_args()

    results = []
    for author, works in CANDIDATES:
        print(author, flush=True)
        for title in works:
            hit = await resolve(author, title, args.tries, args.delay)
            results.append((author, title, hit))
            print(f"  {'OK #' + hit['source_id'] if hit else '-- (not found)':14} {title}", flush=True)
            await asyncio.sleep(args.delay)

    ok = [r for r in results if r[2]]
    miss = [r for r in results if not r[2]]
    today = datetime.date.today().isoformat()
    lines = [
        "# Gutenberg wave — verified sourceable works",
        "",
        f"Generated by `scripts/verify_gutenberg_wave.py` on {today}. The Gutenberg-reachable subset of "
        "[reformed-pd-ingestion.md](reformed-pd-ingestion.md), confirmed against gutendex with the same "
        "adapter that performs ingestion (a hit here = ingestion will find it).",
        "",
        f"**Confirmed {len(ok)} / {len(results)} works.**",
        "",
        "## Confirmed on Gutenberg (ready to ingest)",
        "",
    ]
    cur = None
    for author, title, hit in results:
        if not hit:
            continue
        if author != cur:
            lines.append(f"### {author}")
            cur = author
        lines.append(f"- {title} — Gutenberg #{hit['source_id']} · `{hit['text_url']}`")
    lines += ["", "## Not found on Gutenberg (fall through to the CCEL pass, then archive.org)", ""]
    cur = None
    for author, title, hit in results:
        if hit:
            continue
        if author != cur:
            lines.append(f"### {author}")
            cur = author
        lines.append(f"- {title}")
    out = _ROOT / "docs" / "reformed-gutenberg-wave.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nCONFIRMED {len(ok)} / {len(results)} | wrote {out.relative_to(_ROOT)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
