"""Date arithmetic with a bound parameter must say what the parameter is. Postgres reads an uncast `$n` subtracted
from a date as another date, and date minus date is a number of days, so `day > date - $2` compared a date with a
number and broke /ops in production (2026-11-25). The free checks run with no database, so this reads the source."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

UNCAST = re.compile(r"(::date|current_date)\s*[-+]\s*\$\d+(?!\s*::)")


def test_a_parameter_added_to_or_taken_from_a_date_is_cast():
    found = []
    for path in sorted((ROOT / "webapp").rglob("*.py")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if UNCAST.search(line):
                found.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
    assert not found, "cast the parameter (for example `- $2::int`):\n" + "\n".join(found)


def test_the_check_catches_the_bug_it_was_written_for():
    assert UNCAST.search("day > (now() at time zone 'UTC')::date - $2")
    assert not UNCAST.search("day > (now() at time zone 'UTC')::date - $2::int")
