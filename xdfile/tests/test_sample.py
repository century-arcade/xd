"""Unit tests for xdfile/sample.py (reproducible stratified sampling)."""
from xdfile import sample
from xdfile.sample import Candidate


def _pub(pubid, years_counts):
    out = []
    for year, n in years_counts.items():
        for i in range(n):
            out.append(Candidate('%s%d-%02d-%02d' % (pubid, year, i // 28 % 12 + 1, i % 28 + 1),
                                 pubid, '%d-01-01' % year))
    return out


def test_quota_floor_and_cap():
    assert sample.quota(5000, 1000, 1) == 5
    assert sample.quota(300, 1000, 1) == 1     # small outlet still represented
    assert sample.quota(0, 1000, 1) == 0
    assert sample.quota(2, 1, 1) == 2           # never more than available


def test_split_by_decade_sums_and_prefers_modern_on_tie():
    alloc = sample.split_by_decade(3, {1990: 100, 2000: 100, 2010: 100})
    assert sum(alloc.values()) == 3
    alloc = sample.split_by_decade(1, {1990: 100, 2010: 100})
    assert alloc == {1990: 0, 2010: 1}


def test_draw_is_deterministic_and_seed_sensitive():
    cands = _pub('aaa', {1995: 300, 2005: 300}) + _pub('bbb', {2012: 2500})
    a, _ = sample.draw(cands, 'seed1')
    b, _ = sample.draw(list(reversed(cands)), 'seed1')
    c, _ = sample.draw(cands, 'seed2')
    assert a == b
    assert a != c
    assert len(a) == 1 + 3


def test_adding_puzzles_to_one_pub_does_not_change_another():
    base = _pub('aaa', {2001: 1500}) + _pub('bbb', {2011: 1500})
    more = base + _pub('aaa', {2002: 50})
    sel_base, _ = sample.draw(base, 's')
    sel_more, _ = sample.draw(more, 's')
    assert [x for x in sel_base if x.startswith('bbb')] == [x for x in sel_more if x.startswith('bbb')]


def test_near_duplicates_and_excludes_blocked():
    cands = [Candidate('aaa2001-01-01', 'aaa', '2001-01-01'),
             Candidate('bbb2001-01-08', 'bbb', '2001-01-08')]
    sim = sample.similarity_graph([('aaa2001-01-01', 'bbb2001-01-08', '98')], 50)
    sel, report = sample.draw(cands, 's', similar=sim)
    assert len(sel) == 1                         # syndicated copy not drawn twice
    sel, _ = sample.draw(cands, 's', similar=sim, excluded={'aaa2001-01-01'})
    assert sel == []                             # excluded, and its copy too


def test_in_window():
    assert sample.in_window('1999-12-31', '1965-01-01', '2020-01-01')
    assert not sample.in_window('2020-01-01', '1965-01-01', '2020-01-01')
    assert not sample.in_window('1964-12-31', '1965-01-01', None)
    assert not sample.in_window('', '1965-01-01', None)


def test_transposed_match_counts_as_similar():
    sim = sample.similarity_graph([('a', 'b', '-97'), ('c', 'd', '-20')], 50)
    assert sim['a'] == {'b'} and 'c' not in sim
