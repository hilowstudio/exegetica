#!/usr/bin/env python3
"""
Apply scripts/schema.sql to the database in DATABASE_URL (loaded from .env).

Safe to re-run: tables, columns and constraints are added only when missing. The schema
also changes data. It drops eight retired tables (DROP TABLE IF EXISTS: memory_verses,
memory_folders, chats and five library_* objective tables, CASCADE for those five) and
clears every stored profile photo (UPDATE users SET picture = null). Read schema.sql's
DROP and UPDATE lines before running it against a database that holds anything new.
The connection string is read from the environment and never printed.

    .venv/Scripts/python.exe scripts/db_migrate.py
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from webapp import db  # noqa: E402


async def main() -> int:
    if not db.dsn():
        print("DATABASE_URL is not set (checked .env). Nothing to migrate.")
        return 1
    await db.init_pool()
    schema = (ROOT / "scripts" / "schema.sql").read_text(encoding="utf-8")
    await db.apply_schema(schema)
    rows = await db.fetch(
        "select table_name from information_schema.tables "
        "where table_schema='public' order by table_name"
    )
    print("Schema applied. Public tables:", ", ".join(r["table_name"] for r in rows) or "(none)")
    await db.close_pool()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
