import importlib
import os
import subprocess
import sys

from xdfile import html


def test_html5_header():
    h = html.html_header(title='T')
    assert h.lstrip().startswith('<!DOCTYPE html>')
    assert '<meta charset="utf-8">' in h
    assert 'ISO-8859-1' not in h
    assert '<title>T</title>' in h


def test_title_defaults_to_site_name():
    assert '<title>%s</title>' % html.SITE_NAME in html.html_header()


def test_footer_uses_config():
    f = html.html_footer()
    assert 'mailto:%s' % html.CONTACT_EMAIL in f
    assert '>%s</a> project' % html.SITE_ATTRIBUTION in f


def test_navbar_paths():
    h = html.html_header()
    for dest in ('/', '/about/', '/data/', '/pub/', '/word/', '/clue/'):
        assert 'href="%s"' % dest in h
    assert '>Most Popular</a>' in h  # dropdown parent needs its anchor


def test_nav_highlight_ignores_trailing_slash():
    assert 'current-menu-item' in html.html_header(current_url='/about')
    assert 'current-menu-item' not in html.html_header(current_url='/nonexistent')


def test_site_config_env_override(monkeypatch):
    monkeypatch.setenv('SITE_NAME', 'The Cross Reference')
    monkeypatch.setenv('CONTACT_EMAIL', 'hello@example.com')
    monkeypatch.setenv('SITE_ATTRIBUTION', 'The Cross Reference')
    try:
        importlib.reload(html)
        assert 'mailto:hello@example.com' in html.html_footer()
        assert '<title>The Cross Reference</title>' in html.html_header()
    finally:
        monkeypatch.undo()
        importlib.reload(html)


def test_template_importable_without_queries():
    # wwwify.py must not need the corpus/queries layer
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    code = "import sys; import xdfile.html; assert 'queries.similarity' not in sys.modules"
    r = subprocess.run([sys.executable, '-c', code], cwd=root,
                       env={**os.environ, 'PYTHONPATH': '.'})
    assert r.returncode == 0


def test_url_from_pathname():
    from xdfile.utils import url_from_pathname
    assert url_from_pathname('index.html') == '/'
    assert url_from_pathname('pub/index.html') == '/pub/'
    assert url_from_pathname('pub/nyt/index.html') == '/pub/nyt/'
