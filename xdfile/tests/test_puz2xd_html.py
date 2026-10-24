"""html_to_markup(): HTML formatting tags in .puz text -> xd markup.

xword-dl with preserve_html leaves the publisher's tags in the .puz
(Atlantic clues have <i>Bring It On</i>); without it, html2text writes them
as Markdown (_Bring It On_), which the .xd format doesn't read.
"""
from xdfile.puz2xd import decode, html_to_markup


def test_formatting_tags_become_markup():
    assert html_to_markup("Kirsten in <i>Bring It On</i>") == "Kirsten in {/Bring It On/}"
    assert html_to_markup("<em>Sex Education</em> star") == "{/Sex Education/} star"
    assert html_to_markup("<b>Bold</b> and <strong>strong</strong>") == "{*Bold*} and {*strong*}"
    assert html_to_markup("<u>under</u> <s>gone</s> <strike>x</strike> <del>y</del>") == \
        "{_under_} {-gone-} {-x-} {-y-}"
    assert html_to_markup("H<sub>2</sub>O, E = mc<sup>2</sup>") == "H{~2~}O, E = mc{^2^}"
    assert html_to_markup('<I CLASS="x">Caps</I>') == "{/Caps/}"


def test_spaces_moved_outside_markup_and_empty_markup_dropped():
    assert html_to_markup("I'm not <i>arguing </i>— I'm") == "I'm not {/arguing/} — I'm"
    assert html_to_markup("a <i></i>b") == "a b"


def test_other_tags_dropped_and_non_tags_kept():
    assert html_to_markup('<span class="c">See</span> <a href="/x">this</a>') == "See this"
    assert html_to_markup("Line one<br/>line two") == "Line one line two"
    assert html_to_markup("I <3 NY") == "I <3 NY"
    assert html_to_markup("x < y > z") == "x < y > z"


def test_headers_get_plain_text():
    assert html_to_markup("Słoń <i>Test</i>", markup=False) == "Słoń Test"


def test_runs_before_decode_so_escaped_tags_stay_text():
    assert decode(html_to_markup("Tag &lt;i&gt; in HTML")) == "Tag <i> in HTML"
    assert decode(html_to_markup("<i>B&amp;O</i> Railroad")) == "{/B&O/} Railroad"
