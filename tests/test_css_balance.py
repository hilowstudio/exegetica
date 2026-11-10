"""Every stylesheet's braces balance. A stray "}" at the top level silently swallows the rule after it (one hid the
chat page's no-break rule for references, 2026-11-10), and nothing else would notice."""
import pathlib
import re

import pytest

STATIC = pathlib.Path(__file__).resolve().parent.parent / "webapp" / "static"
SHEETS = sorted(p for p in STATIC.rglob("*.css") if "vendor" not in p.parts)


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda p: p.relative_to(STATIC).as_posix())
def test_braces_balance(sheet):
    css = re.sub(r"/\*.*?\*/", "", sheet.read_text(encoding="utf-8"), flags=re.S)
    css = re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", "", css)      # braces inside strings don't count
    depth = 0
    for i, ch in enumerate(css):
        depth += (ch == "{") - (ch == "}")
        assert depth >= 0, f"a stray closing brace near: {css[max(0, i - 80):i + 1]!r}"
    assert depth == 0, "a block is never closed"
