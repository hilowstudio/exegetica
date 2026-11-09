"""Transcribe a scanned maths textbook page by page into Markdown with TeX (rendered by the reader's KaTeX), with
Claude Haiku 5.5 reading each page image. For school reference copies whose equations OCR can't read (2026-11-09,
Adam approved after a 10-page pilot: Haiku matched the pages exactly; Sonnet 5.5 declined to transcribe).

    python scripts/vision_transcribe.py <slug> [--first N] [--last N] [--workers 6]

Reads the PDF named in .seed_cache/school/<slug>/extract.json, writes .seed_cache/school/<slug>/vision/pNNNN.md (one
per page, skipped when present, so a run resumes), and appends usage to vision/usage.jsonl. A page the API's content
filter blocks, or that the model declines, gets pNNNN.blocked instead; the build falls back to the page's OCR text.
Costs real money: about $0.0008 a page at Haiku 5.5 prices ($0.10 / $0.50 per million tokens)."""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import io
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".seed_cache" / "school"
MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50          # dollars per million tokens (prompts under 100K tokens)

SYSTEM = """You transcribe one scanned page of a school textbook into Markdown, exactly as printed, for a reading app \
that renders TeX with KaTeX.

- Transcribe every word of the page's teaching content in reading order: headings, body text, examples and their \
solutions, definitions, key-concept boxes, exercises with their numbers and answer choices, tables.
- Write all mathematics in TeX: inline as \\( ... \\), displayed equations as \\[ ... \\] on their own line. This \
includes single variables, numbers with exponents, units with symbols, angles, fractions, roots, vectors, matrices \
and chemical formulas. Use only KaTeX-supported commands.
- Headings: ## for a lesson or section title, ### for a sub-heading, **bold** only where the page sets a term in bold.
- Tables as Markdown tables. Lists as Markdown lists, keeping the book's own numbering and letters.
- A figure, photo or diagram: write [Figure: a short plain description, then its caption or labels if printed]. \
Do not describe decoration.
- Leave out running heads (the book or chapter title and page number at the top or bottom edge), page numbers, \
website plugs, and margin icons.
- Transcribe only what was printed. These are used copies: leave out everything a reader added by hand, such as \
handwriting, names, notes, doodles, answers written into blanks or margins, circled or crossed-out choices, \
highlighting and library stamps. Do not mention that anything was added. A blank the book prints for the student to \
fill in stays a blank: write it as ________.
- Never add explanations, answers or anything the page does not print. If a spot is unreadable, write [illegible].
- A blank page, or one with only a picture: output [Figure: ...] or nothing.
Output only the transcription."""

DECLINED = re.compile(r"^(I can[’']t|I cannot|I'm not able|I am not able|Sorry)", re.I)


def _key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    for line in open(ROOT / ".env", encoding="utf-8"):
        if line.startswith("ANTHROPIC_API_KEY="):
            os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug"); ap.add_argument("--first", type=int, default=1); ap.add_argument("--last", type=int)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--pdf", help="the PDF, when extract has not run yet")
    a = ap.parse_args()
    import anthropic
    import pypdfium2 as pdfium
    _key()
    client = anthropic.Anthropic(max_retries=6)
    d = CACHE / a.slug
    out = d / "vision"
    out.mkdir(parents=True, exist_ok=True)
    pdf_path = a.pdf or json.loads((d / "extract.json").read_text(encoding="utf-8"))["pdf"]
    n_pages = len(pdfium.PdfDocument(pdf_path))
    last = min(a.last or n_pages, n_pages)
    todo = [n for n in range(a.first, last + 1)
            if not (out / f"p{n:04d}.md").exists() and not (out / f"p{n:04d}.blocked").exists()]
    print(f"{a.slug}: {len(todo)} pages to read ({a.first}-{last}), {MODEL}", flush=True)
    lock = threading.Lock()
    local = threading.local()
    spent = {"cost": 0.0, "done": 0, "blocked": 0}

    def doc():
        if not hasattr(local, "pdf"):
            local.pdf = pdfium.PdfDocument(pdf_path)
        return local.pdf

    def one(n):
        with lock:                                   # pdfium is not thread-safe: render one page at a time
            pg = doc()[n - 1]
            w, h = pg.get_size()
            im = pg.render(scale=1568 / max(w, h)).to_pil().convert("RGB")
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=88)
        b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
        try:
            r = client.messages.create(
                model=MODEL, max_tokens=16000, system=SYSTEM, output_config={"effort": "low"},
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                    {"type": "text", "text": "Transcribe this page."}]}])
        except anthropic.BadRequestError as e:          # the content filter answers 400; record it, never retry around it
            (out / f"p{n:04d}.blocked").write_text(str(e.message), encoding="utf-8")
            with lock:
                spent["blocked"] += 1
            return
        text = "".join(b.text for b in r.content if b.type == "text").strip()
        cost = r.usage.input_tokens * PRICE_IN / 1e6 + r.usage.output_tokens * PRICE_OUT / 1e6
        if r.stop_reason == "refusal" or DECLINED.match(text):
            (out / f"p{n:04d}.blocked").write_text(text or "refusal", encoding="utf-8")
        else:
            (out / f"p{n:04d}.md").write_text(text, encoding="utf-8")
        with lock:
            spent["cost"] += cost; spent["done"] += 1
            with open(out / "usage.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"p": n, "in": r.usage.input_tokens, "out": r.usage.output_tokens,
                                    "cost": round(cost, 6), "stop": r.stop_reason}) + "\n")
            if spent["done"] % 25 == 0:
                print(f"  {spent['done']}/{len(todo)} pages, ${spent['cost']:.3f}, {spent['blocked']} blocked", flush=True)

    t0 = time.time()
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for f in cf.as_completed([ex.submit(one, n) for n in todo]):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001  a connection failure or similar: the page stays to do on a rerun
                print("  page failed:", repr(e)[:200], flush=True)
    print(f"{a.slug}: {spent['done']} pages read, {spent['blocked']} blocked, ${spent['cost']:.3f}, "
          f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
