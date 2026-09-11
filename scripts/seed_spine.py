#!/usr/bin/env python3
"""
Seed spine_nodes (Postgres) from the canonical JSON spine in webapp/standards/.

Postgres is now the source of truth for the academic spine's *structure*; the
JSON + .npy embeddings remain a generated read-cache the in-memory search loads.
This importer is idempotent (upsert on id) — safe to re-run whenever the JSON is
regenerated. Rows are inserted parent-first so the self-referential FK holds.

    .venv/Scripts/python.exe scripts/seed_spine.py
"""
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from webapp import db  # noqa: E402

STD = ROOT / "webapp" / "standards"


def _rows() -> list[tuple]:
    tree = json.loads((STD / "standards-tree.json").read_text(encoding="utf-8"))
    objs = json.loads((STD / "standards-objectives.json").read_text(encoding="utf-8"))

    rows: list[tuple] = []          # (id, level, parent_id, position, name, grade)
    sub_topic_ids: set[str] = set()

    for si, s in enumerate(tree.get("subjects", [])):
        rows.append((s["id"], "subject", None, si, s.get("name"), None))
        for ssi, ss in enumerate(s.get("sub_subjects", [])):
            rows.append((ss["id"], "sub_subject", s["id"], ssi, ss.get("name"), None))
            for ti, t in enumerate(ss.get("topics", [])):
                rows.append((t["id"], "topic", ss["id"], ti, t.get("name"), None))
                for sti, st in enumerate(t.get("sub_topics", [])):
                    rows.append((st["id"], "sub_topic", t["id"], sti, st.get("name"), None))
                    sub_topic_ids.add(st["id"])

    orphans = 0
    for stid, olist in objs.items():
        if stid not in sub_topic_ids:      # objective whose sub-topic isn't in the tree
            orphans += len(olist)
            continue
        for oi, o in enumerate(olist):
            oid = o.get("id")
            text = o.get("t") or o.get("text") or ""
            if not oid or not text:
                continue
            rows.append((oid, "objective", stid, oi, text, o.get("g")))
    if orphans:
        print(f"note: skipped {orphans} objective(s) under sub-topics not in the tree")
    return rows


async def main() -> int:
    if not db.dsn():
        print("DATABASE_URL is not set (checked .env). Nothing to seed.")
        return 1
    rows = _rows()
    await db.init_pool()
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                """insert into spine_nodes (id, level, parent_id, position, name, grade, source)
                   values ($1, $2, $3, $4, $5, $6, 'seed')
                   on conflict (id) do update
                     set level=excluded.level, parent_id=excluded.parent_id,
                         position=excluded.position, name=excluded.name,
                         grade=excluded.grade, updated_at=now()""",
                rows,
            )
    counts = await db.fetch(
        "select level, count(*) n from spine_nodes group by level order by min(position), level"
    )
    total = await db.fetchval("select count(*) from spine_nodes")
    print("Seeded spine_nodes:", ", ".join(f"{r['level']}={r['n']}" for r in counts), f"(total {total})")
    # integrity: every non-subject must have an existing parent
    dangling = await db.fetchval(
        "select count(*) from spine_nodes c where c.parent_id is not null "
        "and not exists (select 1 from spine_nodes p where p.id = c.parent_id)"
    )
    print("dangling parents:", dangling)
    await db.close_pool()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
