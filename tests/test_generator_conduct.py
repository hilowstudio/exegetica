"""The Generator carries its conduct floor, withholds worship formats, and the pastors' Theologian
reads the same doctrine file as the student chat (docs/decisions/0006, 0010). No network."""
import importlib

from webapp import generator


def test_every_format_prompt_carries_the_floor():
    for format_id in generator.FORMATS:
        system = generator.build_system(format_id, "secondary")
        assert "## Conduct (every resource)" in system, format_id
        assert "[Prayer: led by the teacher]" in system, format_id


def test_revision_prompt_carries_the_floor():
    system, _task = generator.build_revision("# Doc", "make it shorter")
    assert "## Conduct (every resource)" in system


def test_worship_formats_are_withheld_everywhere():
    assert "devotional_guide" not in generator.FORMATS
    assert all(f["id"] != "devotional_guide" for f in generator.format_list())


def test_pastors_theologian_includes_the_shared_doctrine():
    assert "# The Theologian" in generator._THEOLOGIAN
    assert "# The tradition this library follows" in generator._THEOLOGIAN
    server = importlib.import_module("studybible_mcp.server")
    persona = server._load_persona()
    assert "# The Theologian" in persona and "# The tradition this library follows" in persona
