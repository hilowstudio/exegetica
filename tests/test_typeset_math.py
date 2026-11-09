"""The house typesetting pass (webapp/typeset.py) leaves TeX alone: soft hyphens inside \\triangle or bmatrix, or a
fraction's {54} taken for a printed page marker, break the formula KaTeX draws. No network."""
from webapp import typeset

SHY = "­"


def test_formulas_keep_their_commands_and_denominators():
    html = ('<h2>One</h2><p>Since \\( \\triangle ABC \\) has slope \\( \\dfrac{15}{54} \\), write '
            '\\[ \\begin{bmatrix} 1 &amp; 2 \\end{bmatrix} \\] and so the conclusion follows for everything here.</p>')
    out = typeset.typeset(html, "One")[0]
    assert "\\triangle ABC" in out and "\\dfrac{15}{54}" in out and "\\begin{bmatrix}" in out
    assert SHY in out.split("\\]")[-1]        # prose outside the formulas is still hyphenated


def test_a_page_marker_in_prose_still_goes():
    out = typeset.typeset("<h2>One</h2><p>The text runs on {54} and on through the rest of a sentence.</p>", "One")[0]
    assert "{54}" not in out
