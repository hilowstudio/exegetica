"""Train the crisis check's local classifier (webapp/safety.py, docs/decisions/0018-crisis-check.md).

A logistic regression over two kinds of feature: the model2vec embedding the libraries already use
(potion-retrieval-32M, baked into the image) and the message's words and word pairs. Together they
beat either alone in cross-validation. It runs on the server in under a millisecond with no network,
and it sits beside the word list: either one opens the help window.

Trained on:
- scripts/crisis_train.json, 600 messages written for training by an agent that never saw the
  evaluation sets (label 1 opens the window, 0 must not)
- evals/crisis/heldout.json, the first evaluation set, already spent on the word list (its
  "ambiguous" messages are left out)
- 3,000 random verses of the BSB and the KJV as messages that must not open it, since students paste
  verses, then the 2,000 verses a first model scores most like a crisis. The lament psalms and Job
  sound like distress in the first person, so the classifier must learn Scripture's voice. The WEB is
  left out, to measure how often a pasted verse still opens the window.

The threshold is chosen by five-fold cross-validation on the messages (not the verses): the highest
one that still catches TARGET_RECALL of the crisis messages. evals/crisis/heldout2.json is never
read here; score it afterward with evals/crisis/run.py.

    .venv/Scripts/python.exe scripts/train_crisis_check.py      # writes webapp/crisis_classifier.json
"""
from __future__ import annotations

import datetime as dt
import json
import random
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from webapp import safety  # noqa: E402

OUT = ROOT / "webapp" / "crisis_classifier.json"
VERSE_TRANSLATIONS = ("BSB", "KJV")
RANDOM_VERSES = 3000   # drawn at random from those translations
HARD_VERSES = 2000     # then the ones a first model scores most like a crisis
TARGET_RECALL = 0.90
L2 = 1e-4
MIN_COUNT = 2      # a word or pair joins the vocabulary when this many training messages use it
SEED = 7


def _fit(x: np.ndarray, y: np.ndarray, weight: np.ndarray, steps: int = 3000, lr: float = 0.5):
    """Weighted logistic regression by gradient descent. Returns (w, b)."""
    w = np.zeros(x.shape[1])
    b = 0.0
    total = weight.sum()
    for _ in range(steps):
        p = 1 / (1 + np.exp(-(x @ w + b)))
        g = weight * (p - y)
        w -= lr * (x.T @ g / total + L2 * w)
        b -= lr * g.sum() / total
    return w, b


def _weights(y: np.ndarray, verse: np.ndarray) -> np.ndarray:
    """Each class weighs the same in total, and the verses together weigh as much as the written
    messages that must not open the window."""
    out = np.ones(len(y))
    pos, neg_msg, neg_verse = (y == 1), (y == 0) & ~verse, verse
    half = pos.sum() / 2
    out[neg_msg] = half / max(neg_msg.sum(), 1)
    out[neg_verse] = half / max(neg_verse.sum(), 1)
    return out


def main() -> None:
    rows = json.loads((ROOT / "scripts" / "crisis_train.json").read_text(encoding="utf-8"))
    msgs = [(r["text"], int(r["label"])) for r in rows]
    for c in json.loads((ROOT / "evals" / "crisis" / "heldout.json").read_text(encoding="utf-8")):
        if c["expect"] in ("fire", "quiet"):
            msgs.append((c["text"], int(c["expect"] == "fire")))
    con = sqlite3.connect(f"file:{ROOT / 'db' / 'study_bible.db'}?mode=ro", uri=True)
    every_verse = [t for (t,) in con.execute(
        f"select text from translations where translation in ({','.join('?' * len(VERSE_TRANSLATIONS))}) "
        "and text != ''", VERSE_TRANSLATIONS)]
    random.Random(SEED).shuffle(every_verse)
    verses = every_verse[:RANDOM_VERSES]

    counts: dict[str, int] = {}
    for t, _ in msgs:
        for g in safety._grams(t):
            counts[g] = counts.get(g, 0) + 1
    vocab_list = sorted(g for g, n in counts.items() if n >= MIN_COUNT)
    vocab = {g: i for i, g in enumerate(vocab_list)}
    embed = safety._embedder()
    xm = safety._features(embed, vocab, [t for t, _ in msgs])
    ym = np.array([y for _, y in msgs], dtype=float)

    # A first model on the random verses finds the verses most like a crisis (the lament psalms,
    # Job), which join the training as verses that must not open the window.
    xv = safety._features(embed, vocab, verses)
    y = np.concatenate([ym, np.zeros(len(verses))])
    verse = np.concatenate([np.zeros(len(msgs), bool), np.ones(len(verses), bool)])
    w, b = _fit(np.vstack([xm, xv]), y, _weights(y, verse))
    rest = every_verse[RANDOM_VERSES:]
    rest_scores = np.concatenate([safety._features(embed, vocab, rest[i:i + 4000]) @ w
                                  for i in range(0, len(rest), 4000)])
    verses += [rest[i] for i in np.argsort(-rest_scores)[:HARD_VERSES]]
    xv = safety._features(embed, vocab, verses)

    # Five folds over the written messages; the verses train every fold and are scored apart.
    order = np.random.default_rng(SEED).permutation(len(msgs))
    folds = np.array_split(order, 5)
    scores = np.zeros(len(msgs))
    verse_scores = []
    for k, test in enumerate(folds):
        train = np.concatenate([f for j, f in enumerate(folds) if j != k])
        vt = np.arange(len(verses)) % 5 != k
        x = np.vstack([xm[train], xv[vt]])
        y = np.concatenate([ym[train], np.zeros(vt.sum())])
        verse = np.concatenate([np.zeros(len(train), bool), np.ones(vt.sum(), bool)])
        w, b = _fit(x, y, _weights(y, verse))
        scores[test] = 1 / (1 + np.exp(-(xm[test] @ w + b)))
        verse_scores.append(1 / (1 + np.exp(-(xv[~vt] @ w + b))))
    verse_scores = np.concatenate(verse_scores)
    pos = np.sort(scores[ym == 1])
    threshold = float(pos[int((1 - TARGET_RECALL) * len(pos))])
    caught = (scores[ym == 1] >= threshold).mean()
    wrong = (scores[ym == 0] >= threshold).mean()
    verse_wrong = (verse_scores >= threshold).mean()
    print(f"cross-validated at threshold {threshold:.3f}: crisis caught {caught:.1%}, "
          f"quiet messages opened {wrong:.1%}, verses opened {verse_wrong:.2%}")

    x = np.vstack([xm, xv])
    y = np.concatenate([ym, np.zeros(len(verses))])
    verse = np.concatenate([np.zeros(len(msgs), bool), np.ones(len(verses), bool)])
    w, b = _fit(x, y, _weights(y, verse))
    OUT.write_text(json.dumps({
        "model": safety.EMBED_MODEL, "trained": dt.date.today().isoformat(),
        "examples": {"messages": len(msgs), "verses": len(verses)},
        "cross_validated": {"crisis_caught": round(float(caught), 3), "quiet_opened": round(float(wrong), 3),
                            "verses_opened": round(float(verse_wrong), 4)},
        "threshold": round(threshold, 4), "bias": round(float(b), 6), "vocab": vocab_list,
        "weights": [round(float(v), 6) for v in w],
    }) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
