"""A shelf document's type is named the same way on the server, on the shelf tiles, in the "File as" menu and in the
upload notice, so a type added in one place can't show as "Document" in another."""
import re
from pathlib import Path

from webapp import shelf_docs

JS = Path(__file__).resolve().parents[1] / "webapp" / "static" / "js"


def test_every_type_has_a_word_everywhere():
    shelves, library = (JS / "shelves.js").read_text(encoding="utf-8"), (JS / "library.js").read_text(encoding="utf-8")
    kind_word = re.search(r"var KIND_WORD = \{([^}]*)\}", shelves).group(1)
    menu = re.search(r'Passage\.menu\(anchor, "File " \+ d\.title \+ " as", \[([^\]]*)\]', shelves).group(1)
    toast = re.search(r"var TYPE_WORD=\{([^}]*)\}", library).group(1)
    for t in shelf_docs.TYPES:
        assert t in shelf_docs.TYPE_WORD, t
        assert re.search(rf'\b{t}: "{re.escape(shelf_docs.TYPE_WORD[t])}"', kind_word), t
        assert f'"{t}"' in menu, t
        assert re.search(rf"\b{t}:\"an? ", toast), t


def test_a_sermon_transcript_is_a_type():
    assert "sermon" in shelf_docs.TYPES and shelf_docs.TYPE_WORD["sermon"] == "Sermon Transcript"
