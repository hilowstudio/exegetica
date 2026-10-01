"""
Resource generator: assembles standards-aligned generation prompts.

Loads the format catalog (resource-generators.yaml), the format-recommendation
bridge, and the distilled standards index. Given a chosen format + learning
objective(s) + grade band, it builds the (system, task) prompt pair that the
provider layer streams into a finished, downloadable resource.
"""

import hashlib
import json
import re
from pathlib import Path

import yaml

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
_STD = _HERE / "standards"

_catalog = yaml.safe_load((_ROOT / "resource-generators.yaml").read_text(encoding="utf-8"))
_rec = yaml.safe_load((_STD / "format-recommendations.yaml").read_text(encoding="utf-8"))
TREE = json.loads((_STD / "standards-tree.json").read_text(encoding="utf-8"))
_OBJECTIVES = json.loads((_STD / "standards-objectives.json").read_text(encoding="utf-8"))

GLOBAL = _catalog.get("global_conventions", {})
FORMATS = {f["id"]: f for f in _catalog.get("formats", [])}
GRADE_BANDS = GLOBAL.get("grade_bands", {})

_PROMPTS = _ROOT / "src" / "studybible_mcp" / "prompts"


def _read_prompt(name: str) -> str:
    try:
        return (_PROMPTS / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


_THEOLOGIAN = _read_prompt("theologian.md")
_FAITH_INTEGRATION = _read_prompt("faith-integration.md")
_VOICE = _read_prompt("voice.md")


def _with_voice(system: str) -> str:
    """Append the shared voice rules to any generation system prompt."""
    return f"{system}\n\n---\n\n{_VOICE}" if _VOICE else system

_CONVENTION_KEYS = ["identity", "output_format", "sourcing", "differentiation",
                    "answer_keys", "quantity_and_length", "accessibility"]


def format_list() -> list[dict]:
    """Compact list for the format picker."""
    return [
        {"id": f["id"], "name": f["name"],
         "definition": (f.get("definition") or "").strip(),
         "use_when": (f.get("use_when") or "").strip()}
        for f in _catalog.get("formats", [])
    ]


def grade_bands() -> dict:
    return GRADE_BANDS


def objectives_for(sub_topic_id: str) -> list[dict]:
    return _OBJECTIVES.get(sub_topic_id, [])


# ---------------------------------------------------------------------------
# Fuzzy standards search (owned data, no external service)
# ---------------------------------------------------------------------------
_WORD = re.compile(r"[a-z0-9]+")
_SEARCH: list[dict] = []
_VOCAB: set[str] = set()
_LEVEL_PRIOR = {"objective": 0.6, "sub-topic": 0.9, "topic": 0.3, "strand": 0.2, "subject": 0.1}
_STOPWORDS = {"the", "of", "a", "an", "and", "or", "to", "in", "for", "on", "with",
              "is", "are", "be", "by", "at", "as", "how", "what"}


def _idx_add(level: str, label: str, ids: dict, path: list[str], grade=None) -> None:
    words = set(_WORD.findall(label.lower()))
    _SEARCH.append({
        "level": level, "label": label, "grade": grade, "ids": ids, "path": path,
        "_norm": label.lower(), "_words": words, "_pnorm": " ".join(path).lower(),
    })
    _VOCAB.update(w for w in words if len(w) >= 3)


def _build_search_index() -> None:
    by_sub: dict[str, tuple] = {}
    for s in TREE.get("subjects", []):
        sid, sname = s["id"], s["name"]
        _idx_add("subject", sname, {"subject": sid}, [])
        for ss in s.get("sub_subjects", []):
            ssid, ssname = ss["id"], ss["name"]
            _idx_add("strand", ssname, {"subject": sid, "sub_subject": ssid}, [sname])
            for t in ss.get("topics", []):
                tid, tname = t["id"], t["name"]
                _idx_add("topic", tname,
                         {"subject": sid, "sub_subject": ssid, "topic": tid}, [sname, ssname])
                for st in t.get("sub_topics", []):
                    stid, stname = st["id"], st["name"]
                    ids = {"subject": sid, "sub_subject": ssid, "topic": tid, "sub_topic": stid}
                    _idx_add("sub-topic", stname, ids, [sname, ssname, tname])
                    by_sub[stid] = (ids, [sname, ssname, tname, stname])
    for stid, objs in _OBJECTIVES.items():
        loc = by_sub.get(stid)
        if not loc:
            continue
        base_ids, path = loc
        for o in objs:
            oid, text = o.get("id"), (o.get("t") or o.get("text") or "")
            if not oid or not text:
                continue
            ids = dict(base_ids)
            ids["objective"] = oid
            _idx_add("objective", text, ids, path, grade=o.get("g"))


_build_search_index()


def _lev_le(a: str, b: str, maxd: int = 1) -> bool:
    """True if the Levenshtein distance between a and b is at most maxd (bounded)."""
    la, lb = len(a), len(b)
    if abs(la - lb) > maxd:
        return False
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        best = cur[0]
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if cur[j] < best:
                best = cur[j]
        if best > maxd:
            return False
        prev = cur
    return prev[lb] <= maxd


def _expand(tok: str) -> set[str]:
    """A query token plus close-spelled vocabulary words, for typo tolerance."""
    out = {tok}
    if len(tok) >= 4:
        for v in _VOCAB:
            if v != tok and abs(len(v) - len(tok)) <= 1 and _lev_le(tok, v, 1):
                out.add(v)
                if len(out) >= 6:
                    break
    return out


def _lexical_score(rec: dict, q: str, variants: list, ntok: int) -> tuple[float, int]:
    """Fuzzy lexical score (excluding the level prior) and how many query
    tokens matched, against a node's own text and, more weakly, its path."""
    norm, words, pnorm = rec["_norm"], rec["_words"], rec["_pnorm"]
    lex = 0.0
    matched = 0
    if q in norm:
        lex += 5.0 + max(0.0, 2.0 - len(norm) / 40.0)
    elif q in pnorm:
        lex += 1.5
    for variant in variants:
        hit = 0.0
        for v in variant:
            if v in words:
                hit = 1.0
                break
            if v in norm:
                hit = max(hit, 0.6)
        if hit == 0.0:
            for v in variant:
                if v in pnorm:
                    hit = 0.4
                    break
        if hit > 0.0:
            matched += 1
            lex += 2.0 * hit
    if matched:
        lex += 3.0 * (matched / ntok)
        if matched < ntok and q not in norm and q not in pnorm:
            lex -= 1.5 * (ntok - matched)
    return lex, matched


# ---- semantic layer (precomputed static embeddings, loaded lazily) ----
_EMB = None
_EMB_MODEL = None
_SEM_READY: bool | None = None
_EMB_NPY = _STD / "standards-embeddings.npy"
_EMB_MANIFEST = _STD / "standards-embeddings.json"
_SEM_W, _LEX_W, _SEM_MIN, _SEM_KEEP = 4.0, 0.55, 0.30, 0.9


def _signature() -> str:
    joined = "\n".join(json.dumps(r["ids"], sort_keys=True) for r in _SEARCH)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _ensure_semantic() -> bool:
    """Load the precomputed matrix + query model once. Falls back silently
    (returns False) if the files are missing, stale, or the deps are absent."""
    global _EMB, _EMB_MODEL, _SEM_READY
    if _SEM_READY is not None:
        return _SEM_READY
    _SEM_READY = False
    try:
        if not (_EMB_NPY.exists() and _EMB_MANIFEST.exists()):
            return False
        man = json.loads(_EMB_MANIFEST.read_text(encoding="utf-8"))
        if man.get("count") != len(_SEARCH) or man.get("sig") != _signature():
            return False
        import numpy as np
        emb = np.load(_EMB_NPY)
        if emb.shape[0] != len(_SEARCH):
            return False
        _EMB = emb
        if _EMB_MODEL is None:
            _EMB_MODEL = _load_model()
        _SEM_READY = True
    except Exception:
        _SEM_READY = False
    return _SEM_READY


def _load_model():
    from model2vec import StaticModel
    return StaticModel.from_pretrained("minishlab/potion-retrieval-32M")


def embed(texts):
    """Embed short texts with the shared static model (L2-normalized rows). None on failure."""
    global _EMB_MODEL
    try:
        if _EMB_MODEL is None:
            _EMB_MODEL = _load_model()
        import numpy as np
        v = np.asarray(_EMB_MODEL.encode(list(texts)), dtype="float32")
        n = np.linalg.norm(v, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return v / n
    except Exception:
        return None


def semantic_available() -> bool:
    return _ensure_semantic()


def _semantic_sims(q: str):
    """Cosine similarity of the query against every node, or None if unavailable."""
    if not _ensure_semantic():
        return None
    try:
        import numpy as np
        qv = np.asarray(_EMB_MODEL.encode([q])[0], dtype=np.float32)
        n = float(np.linalg.norm(qv))
        if n == 0.0:
            return None
        return _EMB @ (qv / n)
    except Exception:
        return None


def search_standards(query: str, limit: int = 25) -> list[dict]:
    """Hybrid ranked search across every level of the standards spine.

    Blends semantic similarity (precomputed static embeddings) with a fuzzy
    lexical score that handles whole words, prefixes/substrings, and typos.
    When the embedding matrix is absent or stale, degrades to fuzzy-only.
    Returns ranked hits carrying the ids needed to navigate straight to them.
    """
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    tokens = [t for t in _WORD.findall(q) if len(t) >= 2]
    tokens = [t for t in tokens if t not in _STOPWORDS] or tokens
    if not tokens:
        return []
    variants = [_expand(t) for t in tokens]
    sims = _semantic_sims(q)
    scored: list[tuple] = []
    for i, rec in enumerate(_SEARCH):
        lex, matched = _lexical_score(rec, q, variants, len(tokens))
        prior = _LEVEL_PRIOR.get(rec["level"], 0.0)
        if sims is not None:
            sim = float(sims[i])
            if matched == 0 and sim < _SEM_MIN:
                continue
            final = _SEM_W * max(0.0, sim) + _LEX_W * lex + prior
            if final <= _SEM_KEEP:
                continue
        else:
            if matched == 0:
                continue
            final = lex + prior
            if final <= 0.5:
                continue
        scored.append((final, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{
        "level": rec["level"], "label": rec["label"], "grade": rec["grade"],
        "path": rec["path"], "ids": rec["ids"],
    } for final, rec in scored[:limit]]


def recommend(sub_subject_id: str) -> list[str]:
    """Ordered format ids for a sub_subject: specific palette, then universal."""
    subject = (sub_subject_id or "").split(".")[0]
    specific = _rec["by_sub_subject"].get(sub_subject_id) or _rec["by_subject"].get(subject, [])
    out = list(specific)
    for u in _rec.get("universal", []):
        if u not in out:
            out.append(u)
    out = [i for i in out if i in FORMATS]
    # The school asks that faith integration be considered for every lesson, so surface it first.
    if "faith_integration" in out:
        out = ["faith_integration"] + [i for i in out if i != "faith_integration"]
    return out


def _render_conventions() -> str:
    parts: list[str] = []
    for key in _CONVENTION_KEYS:
        v = GLOBAL.get(key)
        if isinstance(v, str):
            parts.append(v.strip())
        elif isinstance(v, dict):
            parts += [vv.strip() for vv in v.values() if isinstance(vv, str)]
    return "\n".join(f"- {p}" for p in parts if p)


def _build_faith_integration_system(fmt: dict, grade_band: str) -> str:
    """Faith-integration is driven by the Theologian voice + integration framework,
    not the generic curriculum-designer prompt."""
    band_desc = GRADE_BANDS.get(grade_band, "")
    adapt = (fmt.get("grade_band_adaptations") or {}).get(grade_band)
    lines = []
    if _THEOLOGIAN:
        lines += [_THEOLOGIAN, "", "---", ""]
    if _FAITH_INTEGRATION:
        lines += [_FAITH_INTEGRATION, "", "---", ""]
    lines += [
        "## Your task now",
        "A teacher at a Christian classical school is working on the curricular location and "
        "learning objective(s) given below. Produce a Faith & Bible Integration Guide that helps "
        "this teacher integrate Christian perspective and devotion to Jesus into exactly this "
        "material, following the framework above. Honor 'without forcing it' above all: name only "
        "the modes the material genuinely supports, and where a content link would be strained, "
        "say so and point to the honest posture instead.",
        "The output IS the guide, addressed to the teacher, in Markdown.",
        "Required structure — include every component, in this order:",
    ]
    for s in (fmt.get("structure") or []):
        lines.append(f"  - {s}")
    if fmt.get("formatting"):
        lines.append(f"Formatting: {fmt['formatting']}")
    if fmt.get("sourcing_note"):
        lines.append(f"Sourcing: {fmt['sourcing_note']}")
    lines += ["", f"## Grade band: {grade_band} — {band_desc}"]
    if adapt:
        lines.append(f"Adaptation at this band: {adapt}")
    return "\n".join(lines)


def build_system(format_id: str, grade_band: str) -> str:
    """The generator system prompt: conventions + the chosen format's schema."""
    fmt = FORMATS[format_id]
    if format_id == "faith_integration":
        return _with_voice(_build_faith_integration_system(fmt, grade_band))
    band_desc = GRADE_BANDS.get(grade_band, "")
    adapt = (fmt.get("grade_band_adaptations") or {}).get(grade_band)
    lines = [
        "You are an expert Christian classical-education curriculum designer. You "
        "produce finished, standards-aligned classroom resources an instructor can "
        "download and use as-is. The output IS the document.",
        "",
        "## Non-negotiable conventions",
        _render_conventions(),
        "",
        f"## Format to produce: {fmt['name']}",
        f"Definition: {(fmt.get('definition') or '').strip()}",
        f"Use when: {(fmt.get('use_when') or '').strip()}",
        "Required structure — include every component, in this order:",
    ]
    for s in (fmt.get("structure") or []):
        lines.append(f"  - {s}")
    if fmt.get("formatting"):
        lines.append(f"Formatting: {fmt['formatting']}")
    if fmt.get("defaults"):
        lines.append(f"Default scope: {fmt['defaults']}")
    if fmt.get("sourcing_note"):
        lines.append(f"Sourcing for this format: {fmt['sourcing_note']}")
    lines.append("")
    lines.append(f"## Grade band: {grade_band} — {band_desc}")
    if adapt:
        lines.append(f"Adaptation for this format at this band: {adapt}")
    return _with_voice("\n".join(lines))


_GEN_WORD_BUDGET = 90000   # ~120k tokens of book text; above this a book needs the Phase-2 comprehension layer


def _ch_label(c: dict | None, n: int) -> str:
    t = (c or {}).get("title")
    return f'section {n} ("{t}")' if t else f"section {n}"


def _coverage(coverage: dict, chapters: list[dict]) -> tuple[set, str, int]:
    """Normalize a coverage spec to (covered section numbers, human description, last covered n)."""
    nmap = {c["n"]: c for c in chapters}
    if coverage.get("through"):
        n = int(coverage["through"])
        return {c["n"] for c in chapters if c["n"] <= n}, f"through {_ch_label(nmap.get(n), n)}", n
    if coverage.get("range"):
        a, b = int(coverage["range"][0]), int(coverage["range"][1])
        return ({c["n"] for c in chapters if a <= c["n"] <= b},
                f"{_ch_label(nmap.get(a), a)} through {_ch_label(nmap.get(b), b)}", b)
    if coverage.get("chapters"):
        cs = [int(x) for x in coverage["chapters"]]
        return {c["n"] for c in chapters if c["n"] in cs}, "sections " + ", ".join(map(str, cs)), max(cs)
    return {c["n"] for c in chapters}, "the whole work", (chapters[-1]["n"] if chapters else 0)


def build_book_task(format_id: str, book: dict, coverage: dict, grade_band: str, brief: str) -> str:
    """The user turn for BOOK-based generation (the Living Library redesign): read the real text,
    understand the whole work, but calibrate the artifact to the student's position in it."""
    fmt = FORMATS[format_id]
    chapters = book.get("chapters") or []
    covered, cov_desc, last = _coverage(coverage, chapters)
    total = book.get("word_count") or sum(c.get("words", 0) for c in chapters)

    if total <= _GEN_WORD_BUDGET:              # fits: feed the whole work (omniscient comprehension)
        included, omitted = chapters, ""
    else:                                      # too big for Phase 1: keep covered + recent prior, up to budget
        budget, keep = _GEN_WORD_BUDGET, []
        for c in reversed([c for c in chapters if c["n"] <= last]):
            if c["n"] in covered or budget - c.get("words", 0) > 0:
                keep.append(c); budget -= c.get("words", 0)
        included = sorted(keep, key=lambda c: c["n"])
        omitted = ("\n(Note: earlier chapters were omitted for length — a whole-work comprehension "
                   "layer is pending. Work only from the text provided.)")

    blocks = [f"\n[{_ch_label(c, c['n'])}]" + (" »»» COVERED »»»" if c["n"] in covered else "")
              + f"\n{c['text']}" for c in included]

    lines = [
        f'Generate the {fmt["name"]} now, for a class reading of "{book["title"]}"'
        + (f' by {book["author"]}' if book.get("author") else "") + ".",
        "",
        f"ASSIGNMENT COVERAGE: {cov_desc}.",
        f"The students have read {cov_desc} and NOT beyond. Calibrate every student-facing item to that vantage:",
        "  - Ask only about what is knowable from the covered sections.",
        "  - Honor the reader's current understanding — an appearance is only an appearance, not a "
        "later revelation (keep dramatic irony intact).",
        "  - Reveal nothing from beyond the covered sections anywhere in student-facing content.",
        "",
        "Use your understanding of the WHOLE work (below) to judge what is significant in the covered "
        "sections and to develop their themes deliberately — but the artifact must land exactly where "
        "the students are in their reading.",
        "",
        f"Grade band: {grade_band}.",
    ]
    if brief and brief.strip():
        lines += ["", f"Instructor's additional instructions: {brief.strip()}"]
    lines += [
        "",
        "Do any study-bible tool lookups you need BEFORE writing; emit no progress notes. Produce only "
        "the finished resource in Markdown, beginning with the metadata header (book title, author, and "
        f"coverage: {cov_desc}). End the student-facing resource with a line `Coverage: {cov_desc}`.",
        "If this resource has answers or model responses, put them ALL after a `---` rule in a final "
        "section headed EXACTLY `## Answer Key`, revealing no answers before it.",
        "You MAY add one final `## Teaching Notes` section (teacher-only); there, and only there, you "
        "may reference later developments in the work to help the teacher steer discussion." + omitted,
        "",
        f'=== FULL TEXT of "{book["title"]}" (covered sections marked »»» COVERED »»») ===',
        "".join(blocks),
    ]
    return "\n".join(lines)


def build_book_task_large(format_id: str, book: dict, coverage: dict, grade_band: str, brief: str,
                          comprehension: dict, covered: list, recap: str, retrieved: bool = False) -> str:
    """Book-based generation for a LARGE work: a pre-built whole-work understanding (so the model is
    'omniscient') + the covered text (verbatim, or the most-relevant passages when the range is huge)
    + the story-so-far for ranges that don't start at the beginning. Output stays positioned."""
    fmt = FORMATS[format_id]
    _, cov_desc, _ = _coverage(coverage, book.get("chapters") or [])
    comp = comprehension or {}
    arc = "; ".join(f'{a.get("title", "")} ({a.get("span", "")}): {a.get("what_happens", "")}'
                    for a in comp.get("arc", []))
    themes = "; ".join(f'{t.get("name", "")} — {t.get("arc", "")}' for t in comp.get("themes", []))
    sig = "; ".join(f'{s.get("element", "")}: {s.get("why_matters", "")}' for s in comp.get("significance", []))
    covered_block = "".join(f'\n[{_ch_label({"title": t}, n)}]\n{txt}' for n, t, txt in covered)

    lines = [
        f'Generate the {fmt["name"]} now, for a class reading of "{book["title"]}"'
        + (f' by {book["author"]}' if book.get("author") else "") + ".",
        "",
        f"ASSIGNMENT COVERAGE: {cov_desc}.",
        f"The students have read {cov_desc} and NOT beyond. Calibrate every student-facing item to that vantage:",
        "  - Ask only about what is knowable from the covered sections.",
        "  - Honor the reader's current understanding — an appearance is only an appearance, not a "
        "later revelation (keep dramatic irony intact).",
        "  - Reveal nothing from beyond the covered sections anywhere in student-facing content.",
        "",
        "This is a large work. You are given a WHOLE-WORK UNDERSTANDING (so you know what is significant "
        "and how the themes develop) and the COVERED TEXT itself. Use the understanding to judge "
        "significance and shape strong items — but never leak anything past the covered sections into "
        "student-facing content.",
        f"Grade band: {grade_band}.",
    ]
    if brief and brief.strip():
        lines += ["", f"Instructor's additional instructions: {brief.strip()}"]
    lines += [
        "",
        "Do any study-bible tool lookups you need BEFORE writing; emit no progress notes. Produce only "
        "the finished resource in Markdown, beginning with the metadata header (book title, author, and "
        f"coverage: {cov_desc}). End the student-facing resource with a line `Coverage: {cov_desc}`.",
        "If this resource has answers, put them ALL after a `---` rule in a final section headed EXACTLY "
        "`## Answer Key`, revealing none before it.",
        "You MAY add one final `## Teaching Notes` section (teacher-only); there, and only there, you may "
        "reference later developments in the work to help the teacher steer discussion.",
        "",
        f'=== WHOLE-WORK UNDERSTANDING of "{book["title"]}" (for significance & theme development) ===',
        "Summary: " + (comp.get("summary", "") or ""),
    ]
    if arc:
        lines.append("Arc: " + arc)
    if themes:
        lines.append("Themes: " + themes)
    if sig:
        lines.append("Significant elements: " + sig)
    if recap:
        lines += ["", "=== THE STORY SO FAR (up to the start of the covered range) ===", recap]
    lines += [
        "",
        f'=== COVERED TEXT ({"selected relevant passages" if retrieved else "full text"}; {cov_desc}) ===',
        covered_block,
    ]
    return "\n".join(lines)


def build_task(format_id: str, objectives: list[dict], grade_band: str,
               context: dict | None, brief: str) -> str:
    """The user turn for standards-mode generation: what to make, for which
    academic-spine objectives, where. (Book-mode generation uses build_book_task /
    build_book_task_large instead.)"""
    fmt = FORMATS[format_id]
    ctx = context or {}
    path = " > ".join(x for x in [
        ctx.get("subject_name"), ctx.get("sub_subject_name"),
        ctx.get("topic_name"), ctx.get("sub_topic_name")] if x)
    lines = [f"Generate the {fmt['name']} now.", "", f"Grade band: {grade_band}."]
    if path:
        lines.append(f"Curricular location: {path}.")
    lines += ["", "Target learning objective(s) — teach or assess exactly these, "
                  "matching each verb and cognitive level:"]
    ids: list[str] = []
    for o in objectives:
        oid = o.get("id")
        if oid:
            ids.append(oid)
        text = o.get("t") or o.get("text") or ""
        meta = ""
        if o.get("g") is not None:
            meta = f" (grade {o.get('g')}, complexity {o.get('c')})"
        lines.append(f"  - [{oid}] {text}{meta}")
        anc = o.get("a") or o.get("anchors") or {}
        parts = []
        if anc.get("scripture"):
            parts.append("Scripture " + "; ".join(anc["scripture"]))
        if anc.get("confessions"):
            parts.append("Confession " + "; ".join(anc["confessions"]))
        if anc.get("greek"):
            parts.append("Original-language " + "; ".join(anc["greek"]))
        if anc.get("standards"):
            parts.append("Aligned standard " + "; ".join(anc["standards"]))
        if parts:
            lines.append(f"      · Ground in: {' | '.join(parts)}")
    _biblical = any((o.get("a") or o.get("anchors") or {}).get(k)
                    for o in objectives for k in ("scripture", "confessions", "greek"))
    _standards = any((o.get("a") or o.get("anchors") or {}).get("standards") for o in objectives)
    if _biblical:
        lines += ["", "For each Scripture/confession anchor above, use the study-bible tools "
                      "to quote the passage accurately and cite the confession/creed; do not "
                      "rely on memory for wording or references."]
    if _standards:
        lines += ["", "Each objective is aligned to the academic standard(s) shown; keep the "
                      "resource faithful to that standard's content and grade level."]
    if brief and brief.strip():
        lines += ["", f"Instructor's additional instructions: {brief.strip()}"]
    if format_id == "faith_integration":
        lines += [
            "",
            "Produce the Faith & Bible Integration Guide now, in Markdown, addressed to the "
            "teacher, beginning with the metadata header. Ground any Scripture or confession in "
            "the study-bible tools and cite it; where none genuinely fits this material, use none "
            "rather than reaching. Do not force a doxological ending.",
        ]
        return "\n".join(lines)
    standards = ", ".join(i for i in ids if i)
    lines += [
        "",
        "Do any Scripture or study-bible tool lookups you need BEFORE you start "
        "writing. Between tool calls, emit no progress notes, plans, or commentary; "
        "your visible output must be the finished document and nothing else.",
        "Produce only the finished resource in Markdown, beginning with the metadata "
        f"header. End the main resource with a line `Standards: {standards}`.",
        "If (and only if) this resource has answers, solutions, or model responses, "
        "put them ALL in a single final section — after a `---` rule and headed "
        "EXACTLY `## Answer Key` — and reveal no answers anywhere before it.",
    ]
    return "\n".join(lines)


def build_revision(document: str, instruction: str) -> tuple[str, str]:
    """System + task for editing an existing resource in place (no full regen)."""
    system = (
        "You revise existing classroom resources. Apply the requested change and "
        "return the COMPLETE updated resource in Markdown. Preserve the metadata "
        "header, the overall structure and formatting, the `Standards:` line, and "
        "the final `## Answer Key` section (keep answers consistent with any edited "
        "items). Change only what the instruction asks; leave everything else "
        "untouched. Output the document only — no commentary. For any biblical, "
        "original-language, commentary, confessional, or church-father content, "
        "ground it in the Study Bible tools and never fabricate a reference."
    )
    system = _with_voice(system)
    task = (
        "Here is the current resource:\n\n" + document.strip() +
        "\n\n---\n\nRequested change: " + instruction.strip() +
        "\n\nReturn the complete updated resource in Markdown, only."
    )
    return system, task
