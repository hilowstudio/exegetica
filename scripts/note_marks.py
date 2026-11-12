"""Find where each footnote mark sits on a page, for books whose OCR can't read the tiny raised numbers.

Claude Haiku 5.5 sees the page image and reports only each mark and the few words printed just before it (never
the page's text otherwise), as JSON. scripts/seed_pd_scan.py then finds those words in the OCR text and links the
mark to the page's note. Approved by Adam 2026-11-11 for the John commentaries (~7,250 pages, about $1.50-3 total).

    python scripts/note_marks.py <work> [--pages 117,121] [--workers 6]

Writes .seed_cache/school/<cache>/marks/pNNNN.json ({"marks": [{"mark": "1", "before": "..."}]}), skipping pages
already done, and appends usage to marks/usage.jsonl. A page the API declines gets pNNNN.blocked.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import io
import json
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import seed_pd_scan as sps  # noqa: E402
from vision_transcribe import MODEL, PRICE_IN, PRICE_OUT, _key  # noqa: E402

SYSTEM = """You locate footnote reference marks on one scanned book page. A footnote reference mark is a small \
raised number or symbol (1, 2, 208, *, †) in the main text that points to a footnote printed at the foot of the \
page.

For each mark in the main text, in reading order, give the mark and the last 4 words printed just before it, \
exactly as printed (with their punctuation). Do not list the numbers that begin the footnotes themselves. Do not \
transcribe anything else.

Output only JSON: {"marks": [{"mark": "1", "before": "four words before it"}]}. If the main text has no footnote \
marks, output {"marks": []}."""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work"); ap.add_argument("--pages"); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    import anthropic
    import pypdfium2 as pdfium
    _key()
    client = anthropic.Anthropic(max_retries=6)
    s = sps.spec(a.work)
    out = s["dir"] / "marks"
    out.mkdir(parents=True, exist_ok=True)
    skip = sps.dropped(s)
    n_pages = sps.n_pages(s)
    wanted = [int(x) for x in a.pages.split(",")] if a.pages else range(1, n_pages + 1)
    todo = [n for n in wanted if n not in skip and not (out / f"p{n:04d}.json").exists()
            and not (out / f"p{n:04d}.blocked").exists()]
    print(f"{a.work}: {len(todo)} pages to read for footnote marks, {MODEL}", flush=True)
    lock, local = threading.Lock(), threading.local()
    spent = {"cost": 0.0, "done": 0}

    def one(n):
        with lock:
            if not hasattr(local, "pdf"):
                local.pdf = pdfium.PdfDocument(str(sps.pdf_path(s)))
            pg = local.pdf[n - 1]
            w, h = pg.get_size()
            im = pg.render(scale=1568 / max(w, h)).to_pil().convert("L")
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=85)
        b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
        try:
            r = client.messages.create(
                model=MODEL, max_tokens=2000, system=SYSTEM, output_config={"effort": "low"},
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                    {"type": "text", "text": "List this page's footnote reference marks."}]}])
        except anthropic.BadRequestError as e:
            (out / f"p{n:04d}.blocked").write_text(str(e.message), encoding="utf-8")
            return
        text = "".join(b.text for b in r.content if b.type == "text").strip()
        data = {"marks": [], "unparsed": text[:500]}
        for i in reversed([m.start() for m in re.finditer(r'\{\s*"marks"', text)]):   # the last answer it gave
            try:
                data = json.JSONDecoder().raw_decode(text[i:])[0]
                break
            except json.JSONDecodeError:
                continue
        (out / f"p{n:04d}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cost = r.usage.input_tokens * PRICE_IN / 1e6 + r.usage.output_tokens * PRICE_OUT / 1e6
        with lock:
            spent["cost"] += cost; spent["done"] += 1
            with open(out / "usage.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"p": n, "in": r.usage.input_tokens, "out": r.usage.output_tokens,
                                    "cost": round(cost, 6)}) + "\n")
            if spent["done"] % 50 == 0:
                print(f"  {spent['done']}/{len(todo)} pages, ${spent['cost']:.3f}", flush=True)

    with cf.ThreadPoolExecutor(a.workers) as ex:
        for f in cf.as_completed([ex.submit(one, n) for n in todo]):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001  the page stays to do on a rerun
                print("  page failed:", repr(e)[:200], flush=True)
    print(f"{a.work}: {spent['done']} pages read, ${spent['cost']:.3f}", flush=True)


if __name__ == "__main__":
    main()
