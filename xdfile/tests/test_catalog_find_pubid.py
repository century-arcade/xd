"""find_pubid's implicit stage: pubids that contain digits."""
import pytest

from xdfile import catalog
from xdfile import metadatabase as metadb


@pytest.fixture
def pubs(monkeypatch):
    def use(*pubids):
        monkeypatch.setattr(metadb, "xd_publications", lambda: dict.fromkeys(pubids))
        monkeypatch.setattr(catalog, "_load_pubregex", lambda: [])
    return use


def test_letters_only_pubid(pubs):
    pubs("nyt", "nytmini", "usun")
    assert catalog.find_pubid("x|nyt2015-03-22.puz") == "nyt"
    assert catalog.find_pubid("x|usun230101-data.xml") == "usun"
    assert catalog.find_pubid("x|nytmini-123.json") == "nytmini"


def test_pubid_with_digits(pubs):
    pubs("club72", "7xw")
    assert catalog.find_pubid("x|club72-0001.puz") == "club72"
    assert catalog.find_pubid("x|club72-2020-01-01.puz") == "club72"
    assert catalog.find_pubid("x|club722020-01-01.puz") == "club72"    # older form, no hyphen
    assert catalog.find_pubid("x|7xw2021-01-01.puz") == "7xw"


def test_series_pubid_extends_parent_with_digit(pubs):
    pubs("tpfa", "tpfa4", "tpfat")
    assert catalog.find_pubid("x|tpfa4-001.puz") == "tpfa4"
    assert catalog.find_pubid("x|tpfat-001.puz") == "tpfat"
    # the parent's own dated puzzle is not the series'
    assert catalog.find_pubid("x|tpfa4024-03-01.puz") == "tpfa"
    assert catalog.find_pubid("x|tpfa-012.puz") == "tpfa"


def test_unrelated_matches_stay_ambiguous(pubs):
    pubs("nyt", "lat")
    assert catalog.find_pubid("nyt2015-03-22|lat2015-03-22") is None
