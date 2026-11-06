#!/usr/bin/env python3

# Usage: $0 --snapshot 2026.11 -o <outroot> xd-clues.zip xd-metadata.zip
#
# Builds the versioned dataset snapshots published on Hugging Face and Kaggle
# (tier (b) in https://centuryarcade.org/xdcorpus/DATASETS.html) from the two
# public zips that `make analyze` writes. Reads nothing from gxd/.
#
#   <outroot>/xd-clues/     data/pubid=<pubid>/clues.parquet, README.md,
#                           dataset-metadata.json
#   <outroot>/xd-answers/   answers.parquet, answers_total.parquet, README.md,
#                           dataset-metadata.json (counted from the xd-clues rows)
#   <outroot>/xd-metadata/  puzzles.parquet, stats.parquet, similar.parquet,
#                           README.md, dataset-metadata.json
#
# README.md is the Hugging Face dataset card; dataset-metadata.json is for
# `kaggle datasets create`. Both are published under OWNER on Hugging Face
# and Kaggle.
#
# Minimum cell size: a publication-year with fewer than MIN_CELL puzzles
# (counted in stats.tsv) keeps its decade but loses its year. The rows nulled
# that way form one cell per publication-decade; if that cell still has fewer
# than MIN_CELL puzzles, its rows are dropped. Rows with no year at all are
# dropped too, since they have no decade.

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import zipfile

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


MIN_CELL = 5

OWNER = 'century-arcade'  # Hugging Face organization and Kaggle owner

CORPUS_URL = 'https://centuryarcade.org/xdcorpus/'
DATASETS_URL = CORPUS_URL + 'DATASETS.html'
ACCESS_URL = CORPUS_URL + 'ACCESS.html'
AI_URL = CORPUS_URL + 'AI.html'
CITING_URL = CORPUS_URL + '#citing'

TAGS = ['crossword', 'crosswords', 'puzzles', 'clues', 'corpus']
KAGGLE_KEYWORDS = ['crossword', 'puzzles', 'games', 'text data', 'nlp']

TERMS = f"""\
These data are for research, analysis, building tools for crossword
constructors and solvers, and solving. Please do not use them to build
systems that generate crosswords or crossword clues for publication. If you
publish work that uses them, cite the corpus (below). These are terms we ask
people to honor, not a license we can enforce; the full policy is in
[DATASETS.md]({DATASETS_URL}), with [ACCESS.md]({ACCESS_URL}) for access to
the corpus itself and [AI.md]({AI_URL}) for using the data to train models."""

CITATION = """\
> Pwanson, Saul and DeJarnatt, Alex. (2026). *The xd Crossword Corpus.*
> Century Arcade. https://centuryarcade.org/xdcorpus/

Use the year the corpus was accessed. Earlier work cited it as
"Pwanson, Saul. (2019). xd Crossword Corpus. http://xd.saul.pw"; that is the
same corpus."""


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def read_tsv(zf, name):
    'all columns as non-null strings; no quoting, since clues contain quotes'
    with zf.open(name) as fp:
        header = fp.readline().decode('utf-8').rstrip('\n').split('\t')
    with zf.open(name) as fp:
        t = pacsv.read_csv(fp,
            read_options=pacsv.ReadOptions(block_size=64 << 20),
            parse_options=pacsv.ParseOptions(delimiter='\t', quote_char=False),
            convert_options=pacsv.ConvertOptions(
                column_types={c: pa.string() for c in header},
                strings_can_be_null=False,
                quoted_strings_can_be_null=False))
    return t.to_pandas()


def zip_date(zf, name):
    return datetime.date(*zf.getinfo(name).date_time[:3])


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fp:
        for block in iter(lambda: fp.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def provenance_section(snapshot, built, name, sources):
    '''sources: [(zip path, member names)]; times are the zip entries' own,
    the local time of the machine that ran `make analyze`'''
    lines = [f'Dataset `{OWNER}/{name}`, snapshot **{snapshot}**, built {built} by',
             '[`scripts/30-mkdatasets.py`](https://github.com/century-arcade/xd/blob/master/scripts/30-mkdatasets.py)',
             'in [century-arcade/xd](https://github.com/century-arcade/xd) from these public',
             'zips, as published at [xd.saul.pw/data](https://xd.saul.pw/data):',
             '',
             '| source | built | SHA-256 |',
             '|:--|:--|:--|']
    for path, members in sources:
        zf = zipfile.ZipFile(path)
        when = max(datetime.datetime(*zf.getinfo(m).date_time) for m in members)
        lines.append(f'| `{os.path.basename(path)}` | {when:%Y-%m-%d %H:%M} | `{sha256(path)}` |')
    lines += ['',
              'The build time is the timestamp of the files inside each zip. The zips do',
              'not yet record which commit of the corpus they were built from; this',
              'section will name it once the zip builders record it.']
    return '\n'.join(lines)


def nullable(s):
    'empty string -> null'
    return s.mask(s == '')


def to_int(s):
    return pd.to_numeric(nullable(s), errors='raise').astype('Int64')


def fmt(n):
    return f'{n:,}'


def human_size(nbytes):
    for unit in ['bytes', 'KB', 'MB', 'GB']:
        if nbytes < 1024 or unit == 'GB':
            return f'{nbytes:.0f} {unit}' if unit == 'bytes' else f'{nbytes:.1f} {unit}'
        nbytes /= 1024


def size_category(n):
    for lo, hi, label in [(1e3, 1e4, '1K<n<10K'), (1e4, 1e5, '10K<n<100K'),
                          (1e5, 1e6, '100K<n<1M'), (1e6, 1e7, '1M<n<10M'),
                          (1e7, 1e8, '10M<n<100M'), (1e8, 1e9, '100M<n<1B')]:
        if n < hi:
            return label if n >= lo else 'n<1K'
    return 'n>1T'


def dir_size(path):
    return sum(os.path.getsize(os.path.join(d, f))
               for d, _, files in os.walk(path) for f in files)


# ---- stats ----------------------------------------------------------------

def load_stats(mzip):
    st = read_tsv(mzip, 'xd/stats.tsv')
    out = pd.DataFrame({
        'pubid': st.pubid,
        'year': to_int(st.year),
        'weekday': nullable(st.weekday),
        'Size': nullable(st.Size),
        'Editor': nullable(st.Editor),
        'Copyright': nullable(st.Copyright),
    })
    for c in st.columns:
        if c.startswith('Num'):
            out[c] = pd.to_numeric(st[c], errors='raise').astype('int64')
    return out


def pubyear_counts(stats):
    'puzzles per (pubid, year) in stats.tsv'
    st = stats.dropna(subset=['year'])
    return st.groupby(['pubid', 'year']).NumXd.sum()


def coverage_table(stats):
    st = stats.dropna(subset=['year']).copy()
    st['decade'] = st.year // 10 * 10
    t = st.groupby(['pubid', 'decade']).NumXd.sum().unstack(fill_value=0)
    t = t.loc[t.sum(axis=1) > 0, t.sum(axis=0) > 0]
    decades = sorted(t.columns)
    lines = ['| pubid | ' + ' | '.join(f'{d}s' for d in decades) + ' | total |',
             '|:--|' + '--:|' * (len(decades) + 1)]
    for pubid, row in t.sort_index().iterrows():
        cells = [fmt(row[d]) if row[d] else '' for d in decades]
        lines.append(f'| {pubid} | ' + ' | '.join(cells) + f' | {fmt(row.sum())} |')
    tot = t.sum(axis=0)
    lines.append('| **total** | ' + ' | '.join(f'**{fmt(tot[d])}**' for d in decades)
                 + f' | **{fmt(tot.sum())}** |')
    return '\n'.join(lines), len(t), int(tot.sum())


COVERAGE_NOTE = """\
Coverage is very uneven. Some publications are nearly complete for decades,
others are a few puzzles, and most of the corpus is from 1990 on. Counts are
puzzles in the corpus (from `stats.tsv`), by publication and decade of
publication, and count only puzzles with a full date of publication."""


# ---- xd-clues -------------------------------------------------------------

def build_clues(czip, counts, outdir):
    log('reading clues.tsv...')
    cl = read_tsv(czip, 'xd/clues.tsv')
    assert list(cl.columns) == ['pubid', 'year', 'answer', 'clue'], cl.columns
    nin = len(cl)
    log(f'{fmt(nin)} clue rows')

    cl['year'] = pd.to_numeric(cl.year, errors='raise').astype('Int64')
    noyear = cl.year.isna() | (cl.year == 0)
    n_noyear = int(noyear.sum())
    cl = cl[~noyear].copy()
    cl['decade'] = (cl.year // 10 * 10).astype('int64')

    # cell sizes, from stats.tsv
    py = cl[['pubid', 'year', 'decade']].drop_duplicates()
    py['npuzzles'] = [int(counts.get((p, y), 0)) for p, y in zip(py.pubid, py.year)]
    small = py[py.npuzzles < MIN_CELL]
    # nulled years merge into one cell per publication-decade
    merged = small.groupby(['pubid', 'decade']).npuzzles.sum()
    drop_cells = set(merged[merged < MIN_CELL].index)
    decade_total = py.groupby(['pubid', 'decade']).npuzzles.sum()

    py['small'] = py.npuzzles < MIN_CELL
    py['drop'] = py.small & pd.Series(list(zip(py.pubid, py.decade)), index=py.index).isin(drop_cells)
    # dropped although the whole publication-decade has MIN_CELL or more
    py['looser'] = py['drop'] & pd.Series(
        [decade_total[(p, d)] >= MIN_CELL for p, d in zip(py.pubid, py.decade)], index=py.index)
    flags = cl[['pubid', 'year']].merge(py[['pubid', 'year', 'small', 'drop', 'looser']],
                                        on=['pubid', 'year'], how='left', validate='m:1')
    assert len(flags) == len(cl)
    is_small = pd.Series(flags.small.to_numpy(bool), index=cl.index)
    is_drop = pd.Series(flags['drop'].to_numpy(bool), index=cl.index)
    looser = pd.Series(flags.looser.to_numpy(bool), index=cl.index)

    nums = {
        'rows_in': nin,
        'rows_noyear_dropped': n_noyear,
        'pubyears': len(py),
        'pubyears_small': len(small),
        'pubdecades_dropped': len(drop_cells),
        'pubdecades_merged': len(merged) - len(drop_cells),
        'rows_nulled': int((is_small & ~is_drop).sum()),
        'rows_small_dropped': int(is_drop.sum()),
        'rows_dropped_despite_decade_total': int(looser.sum()),
    }

    cl = cl[~is_drop].copy()
    cl.loc[is_small[~is_drop], 'year'] = pd.NA
    nums['rows_out'] = len(cl)
    nums['pubids_out'] = cl.pubid.nunique()

    # within each publication: year cells first by year, then the merged
    # null-year cell of each decade; each cell sorted by answer then clue
    cl = cl.sort_values(['pubid', 'decade', 'year', 'answer', 'clue'],
                        na_position='last', kind='stable')
    cl = cl[['pubid', 'year', 'decade', 'answer', 'clue']]

    schema = pa.schema([('pubid', pa.string()), ('year', pa.int16()),
                        ('decade', pa.int16()), ('answer', pa.string()),
                        ('clue', pa.string())])
    log(f'writing {nums["pubids_out"]} partitions...')
    for pubid, part in cl.groupby('pubid', sort=True):
        d = os.path.join(outdir, 'data', f'pubid={pubid}')
        os.makedirs(d, exist_ok=True)
        t = pa.Table.from_pandas(part, schema=schema, preserve_index=False)
        pq.write_table(t, os.path.join(d, 'clues.parquet'), compression='zstd')
    return nums, cl


def cell_rule_table(nums):
    return f"""| | clue rows |
|:--|--:|
| rows in `clues.tsv` | {fmt(nums['rows_in'])} |
| dropped: no year of publication | {fmt(nums['rows_noyear_dropped'])} |
| year set to null ({fmt(nums['pubyears_small'])} of {fmt(nums['pubyears'])} publication-years, merged into {fmt(nums['pubdecades_merged'])} publication-decades) | {fmt(nums['rows_nulled'])} |
| dropped: merged cell under {MIN_CELL} puzzles ({fmt(nums['pubdecades_dropped'])} publication-decades) | {fmt(nums['rows_small_dropped'])} |
| **rows kept** | **{fmt(nums['rows_out'])}** |"""


# ---- xd-answers -----------------------------------------------------------

def build_answers(cl, outdir):
    'answer lexicon from the clue rows kept for xd-clues, so it reveals no more'
    os.makedirs(outdir, exist_ok=True)
    ans = (cl.groupby(['answer', 'pubid', 'decade'], sort=True).size()
             .rename('n').reset_index())
    tot = ans.groupby('answer', sort=True).agg(
        n_total=('n', 'sum'), n_pubs=('pubid', 'nunique'),
        first_decade=('decade', 'min'), last_decade=('decade', 'max')).reset_index()
    aschema = pa.schema([('answer', pa.string()), ('pubid', pa.string()),
                         ('decade', pa.int16()), ('n', pa.int32())])
    tschema = pa.schema([('answer', pa.string()), ('n_total', pa.int32()),
                         ('n_pubs', pa.int16()), ('first_decade', pa.int16()),
                         ('last_decade', pa.int16())])
    pq.write_table(pa.Table.from_pandas(ans, schema=aschema, preserve_index=False),
                   os.path.join(outdir, 'answers.parquet'), compression='zstd')
    pq.write_table(pa.Table.from_pandas(tot, schema=tschema, preserve_index=False),
                   os.path.join(outdir, 'answers_total.parquet'), compression='zstd')
    return {'answers_rows': len(ans), 'answers_total_rows': len(tot),
            'clue_rows': int(ans.n.sum())}


def answers_card(snapshot, built, srcdate, cnums, anums, coverage, sizes, provenance):
    first = (f"The answer lexicon of the xd Crossword Corpus, a collection of published "
             f"crosswords from 1913 to today: {fmt(anums['answers_total_rows'])} distinct "
             f"answers, with how often each was used in each publication and decade. "
             f"It has no clue text, no grids and no dates.")
    yaml = f"""---
pretty_name: xd Crossword Corpus answers
license: other
license_name: xd-corpus-terms
license_link: {DATASETS_URL}
language:
- en
tags:
{chr(10).join('- ' + t for t in TAGS)}
size_categories:
- {size_category(anums['answers_rows'])}
configs:
- config_name: answers
  default: true
  data_files:
  - split: train
    path: answers.parquet
- config_name: answers_total
  data_files:
  - split: train
    path: answers_total.parquet
---
"""
    body = f"""
# xd-answers

{first}

This lexicon is published first; the clue text follows in a later snapshot.

Snapshot **{snapshot}**, built {built} from the `xd-clues.zip` and
`xd-metadata.zip` published at [xd.saul.pw/data](https://xd.saul.pw/data)
on {srcdate} (see Provenance). Snapshots are fixed: cite the version you
used. The same snapshot is published on [Hugging Face](https://huggingface.co/datasets/{OWNER}/xd-answers)
and [Kaggle](https://www.kaggle.com/datasets/{OWNER}/xd-answers). The
[xd Crossword Corpus]({CORPUS_URL}) is maintained by Saul Pwanson and Alex
DeJarnatt.

## Files

### `answers.parquet` ({fmt(anums['answers_rows'])} rows, {human_size(sizes['answers'])})

One row per answer, publication and decade, sorted by answer.

| column | type | |
|:--|:--|:--|
| `answer` | string | the answer, upper case, as entered in the grid |
| `pubid` | string | publication identifier, as in the corpus (`nyt`, `lat`, `wsj`, ...) |
| `decade` | int | decade of publication, e.g. `1990` |
| `n` | int | number of clues with this answer in this publication and decade |

### `answers_total.parquet` ({fmt(anums['answers_total_rows'])} rows, {human_size(sizes['answers_total'])})

One row per answer, sorted by answer.

| column | type | |
|:--|:--|:--|
| `answer` | string | |
| `n_total` | int | number of clues with this answer, in all publications |
| `n_pubs` | int | number of publications that used it |
| `first_decade`, `last_decade` | int | first and last decade it was used |

A count is of clue rows: an answer used twice in one puzzle counts twice.

## How it was built

The counts are made from exactly the clue rows that the `xd-clues` snapshot
of the same version keeps, so this dataset never reveals more than that one.
Those rows follow the rules for public derived data in
[DATASETS.md]({DATASETS_URL}): no grids or clue numbers; year, not date;
contest puzzles with redacted grids left out; and a minimum cell size of
{MIN_CELL} puzzles. A publication-year with fewer than {MIN_CELL} puzzles in
the corpus keeps only its decade; the rows so coarsened in one
publication-decade form one cell, and where that cell still has fewer than
{MIN_CELL} puzzles, its rows are dropped. Puzzle counts come from
`stats.tsv`, which counts only puzzles with a full date, so the rule errs
toward coarsening. Counts here are by decade only.

In this snapshot:

{cell_rule_table(cnums)}

The {fmt(anums['clue_rows'])} rows kept are counted into
{fmt(anums['answers_rows'])} answer-publication-decade rows and
{fmt(anums['answers_total_rows'])} distinct answers.

## Coverage

{COVERAGE_NOTE}

{coverage}

## Provenance

{provenance}

## Terms

{TERMS}

A publication can ask to be left out of future snapshots; see
[DATASETS.md]({DATASETS_URL}).

## Citing

{CITATION}
"""
    return yaml + body, first


def clues_card(snapshot, built, srcdate, nums, coverage, npubs, npuzzles, nbytes, provenance):
    first = (f"The clues and answers of the xd Crossword Corpus, a collection of "
             f"published crosswords from 1913 to today: {fmt(nums['rows_out'])} rows from "
             f"{nums['pubids_out']} publications, each with the publication and year it "
             f"appeared. There are no grids, no clue numbers and no dates, so the "
             f"puzzles cannot be rebuilt from it.")
    yaml = f"""---
pretty_name: xd Crossword Corpus clues
license: other
license_name: xd-corpus-terms
license_link: {DATASETS_URL}
language:
- en
tags:
{chr(10).join('- ' + t for t in TAGS)}
size_categories:
- {size_category(nums['rows_out'])}
configs:
- config_name: default
  data_files:
  - split: train
    path: data/*/clues.parquet
---
"""
    body = f"""
# xd-clues

{first}

Snapshot **{snapshot}**, built {built} from the `xd-clues.zip` and
`xd-metadata.zip` published at [xd.saul.pw/data](https://xd.saul.pw/data)
on {srcdate} (see Provenance). Snapshots are fixed: cite the version you
used. The same snapshot is published on [Hugging Face](https://huggingface.co/datasets/{OWNER}/xd-clues)
and [Kaggle](https://www.kaggle.com/datasets/{OWNER}/xd-clues). The
[xd Crossword Corpus]({CORPUS_URL}) is maintained by Saul Pwanson and Alex
DeJarnatt.

## Files

`data/pubid=<pubid>/clues.parquet`, one Parquet file per publication
({human_size(nbytes)} in all). Every file has all five columns, including
`pubid`.

| column | type | |
|:--|:--|:--|
| `pubid` | string | publication identifier, as in the corpus (`nyt`, `lat`, `wsj`, ...) |
| `year` | int, nullable | year of publication; null where the year was coarsened to the decade (see below) |
| `decade` | int | decade of publication, e.g. `1990` |
| `answer` | string | the answer, upper case, as entered in the grid |
| `clue` | string | the clue text |

One row is one use of a clue in one puzzle, so the same answer and clue can
appear many times.

## How the rows were prepared

These are the rules for public derived data in [DATASETS.md]({DATASETS_URL}):

- **No grids, no clue numbers.** A row does not say where its answer sat or
  which clue it was.
- **Year, not date.**
- **Rows are reordered.** Within each publication-year the rows are sorted
  by answer, then clue, so the order of a puzzle's clues does not survive.
- **Contest puzzles with redacted grids are left out**, so a contest is not
  spoiled before its answers are.
- **A minimum cell size of {MIN_CELL} puzzles.** A publication-year with fewer
  than {MIN_CELL} puzzles in the corpus is too small to hide which clue came
  from which puzzle. Its rows keep their decade and their year is set to
  null; all such rows of one publication-decade form one cell, sorted by
  answer then clue. Where that cell still has fewer than {MIN_CELL} puzzles,
  its rows are dropped. Puzzle counts come from `stats.tsv` in
  [xd-metadata](https://xd.saul.pw/data), which counts only puzzles with a
  full date, so a cell may hold more puzzles than it was credited with; the
  rule errs toward coarsening.

In this snapshot:

| | rows |
|:--|--:|
| rows in `clues.tsv` | {fmt(nums['rows_in'])} |
| dropped: no year of publication | {fmt(nums['rows_noyear_dropped'])} |
| year set to null ({fmt(nums['pubyears_small'])} of {fmt(nums['pubyears'])} publication-years, merged into {fmt(nums['pubdecades_merged'])} publication-decades) | {fmt(nums['rows_nulled'])} |
| dropped: merged cell under {MIN_CELL} puzzles ({fmt(nums['pubdecades_dropped'])} publication-decades) | {fmt(nums['rows_small_dropped'])} |
| **rows published** | **{fmt(nums['rows_out'])}** |

## Coverage

{COVERAGE_NOTE}

{coverage}

## Provenance

{provenance}

## Terms

{TERMS}

A publication can ask to be left out of future snapshots; see
[DATASETS.md]({DATASETS_URL}).

## Citing

{CITATION}
"""
    return yaml + body, first


# ---- xd-metadata ----------------------------------------------------------

PUZZLES_COLUMNS = ['xdid', 'Date', 'Size', 'Title', 'Author', 'Editor', 'Copyright', 'A1_D1']


def check_puzzles(pz):
    'stop unless puzzles.tsv holds only what DATASETS.md says it holds'
    if list(pz.columns) != PUZZLES_COLUMNS:
        sys.exit(f'puzzles.tsv columns {list(pz.columns)} != {PUZZLES_COLUMNS}; '
                 'check against DATASETS.md before publishing')
    # A1_D1 is two answers joined by '_': no more than that
    parts = pz.A1_D1.str.count('_')
    if (parts > 1).any():
        bad = pz.A1_D1[parts > 1].head().tolist()
        sys.exit(f'puzzles.tsv A1_D1 holds more than two answers: {bad}')


def build_metadata(mzip, stats, outdir):
    os.makedirs(outdir, exist_ok=True)
    nums = {}

    pz = read_tsv(mzip, 'xd/puzzles.tsv')
    check_puzzles(pz)
    date = pd.to_datetime(nullable(pz.Date), format='%Y-%m-%d', errors='coerce')
    year = pd.to_numeric(pz.Date.str.extract(r'^(\d{4})')[0], errors='coerce').astype('Int64')
    wh = pz.Size.str.extract(r'^(\d+)x(\d+)')
    puzzles = pd.DataFrame({
        'xdid': pz.xdid,
        'date': date.dt.date,
        'year': year,
        'Size': nullable(pz.Size),
        'width': pd.to_numeric(wh[0]).astype('Int64'),
        'height': pd.to_numeric(wh[1]).astype('Int64'),
        'Title': nullable(pz.Title),
        'Author': nullable(pz.Author),
        'Editor': nullable(pz.Editor),
        'Copyright': nullable(pz.Copyright),
        'A1_D1': nullable(pz.A1_D1),
    })
    nums['puzzles'] = len(puzzles)
    nums['puzzles_no_full_date'] = int(puzzles.date.isna().sum())
    nums['puzzles_no_year'] = int(puzzles.year.isna().sum())
    pschema = pa.schema([('xdid', pa.string()), ('date', pa.date32()),
                         ('year', pa.int16()), ('Size', pa.string()),
                         ('width', pa.int16()), ('height', pa.int16()),
                         ('Title', pa.string()), ('Author', pa.string()),
                         ('Editor', pa.string()), ('Copyright', pa.string()),
                         ('A1_D1', pa.string())])
    pq.write_table(pa.Table.from_pandas(puzzles, schema=pschema, preserve_index=False),
                   os.path.join(outdir, 'puzzles.parquet'), compression='zstd')

    sschema = pa.schema([('pubid', pa.string()), ('year', pa.int16()),
                         ('weekday', pa.string()), ('Size', pa.string()),
                         ('Editor', pa.string()), ('Copyright', pa.string())] +
                        [(c, pa.int32()) for c in stats.columns if c.startswith('Num')])
    pq.write_table(pa.Table.from_pandas(stats, schema=sschema, preserve_index=False),
                   os.path.join(outdir, 'stats.parquet'), compression='zstd')
    nums['stats'] = len(stats)

    sim = read_tsv(mzip, 'xd/similar.tsv')
    assert list(sim.columns) == ['xdid1', 'xdid2', 'matchpct'], sim.columns
    similar = pd.DataFrame({'xdid1': nullable(sim.xdid1), 'xdid2': nullable(sim.xdid2),
                            'matchpct': to_int(sim.matchpct)})
    nums['similar'] = len(similar)
    mschema = pa.schema([('xdid1', pa.string()), ('xdid2', pa.string()),
                         ('matchpct', pa.int16())])
    pq.write_table(pa.Table.from_pandas(similar, schema=mschema, preserve_index=False),
                   os.path.join(outdir, 'similar.parquet'), compression='zstd')
    return nums


def metadata_card(snapshot, built, srcdate, nums, coverage, npubs, npuzzles, sizes, provenance):
    first = (f"Metadata for the {fmt(nums['puzzles'])} puzzles in the xd Crossword Corpus, "
             f"published crosswords from 1913 to today: date, size, title, constructor, "
             f"editor and copyright line for each puzzle, puzzle counts by publication, "
             f"year and weekday, and which puzzles' grids match earlier ones. It carries "
             f"no clues and no grids, and no answers but the first across and first "
             f"down of each puzzle.")
    yaml = f"""---
pretty_name: xd Crossword Corpus metadata
license: other
license_name: xd-corpus-terms
license_link: {DATASETS_URL}
language:
- en
tags:
{chr(10).join('- ' + t for t in TAGS)}
size_categories:
- {size_category(nums['puzzles'])}
configs:
- config_name: puzzles
  default: true
  data_files:
  - split: train
    path: puzzles.parquet
- config_name: stats
  data_files:
  - split: train
    path: stats.parquet
- config_name: similar
  data_files:
  - split: train
    path: similar.parquet
---
"""
    body = f"""
# xd-metadata

{first}

Snapshot **{snapshot}**, built {built} from the `xd-metadata.zip` published
at [xd.saul.pw/data](https://xd.saul.pw/data) on {srcdate} (see Provenance).
Snapshots are fixed: cite the version you used. The same snapshot is published
on [Hugging Face](https://huggingface.co/datasets/{OWNER}/xd-metadata) and
[Kaggle](https://www.kaggle.com/datasets/{OWNER}/xd-metadata). The
[xd Crossword Corpus]({CORPUS_URL}) is maintained by Saul Pwanson and Alex
DeJarnatt.

The puzzles themselves are not here: most are under copyright. See
[ACCESS.md]({ACCESS_URL}).

## Files

### `puzzles.parquet` ({fmt(nums['puzzles'])} rows, {human_size(sizes['puzzles'])})

One row per puzzle in the corpus, public or not.

| column | type | |
|:--|:--|:--|
| `xdid` | string | puzzle identifier: publication id and date, e.g. `nyt1994-03-27` |
| `date` | date, nullable | date of publication; null for {fmt(nums['puzzles_no_full_date'])} puzzles with only a year or no date |
| `year` | int, nullable | year of publication (null for {fmt(nums['puzzles_no_year'])}) |
| `Size` | string | grid size as given, e.g. `15x15` |
| `width`, `height` | int, nullable | grid size as numbers |
| `Title` | string | |
| `Author` | string | constructor(s) |
| `Editor` | string | |
| `Copyright` | string | copyright line as printed |
| `A1_D1` | string | the first across and first down answers joined by `_`, used to spot the same grid |

Empty fields are null.

### `stats.parquet` ({fmt(nums['stats'])} rows, {human_size(sizes['stats'])})

Puzzle counts by publication, year and weekday.

| column | type | |
|:--|:--|:--|
| `pubid` | string | publication identifier |
| `year` | int, nullable | |
| `weekday` | string | `Mon` ... `Sun` |
| `Size`, `Editor`, `Copyright` | string | the most common value for the cell, with its count in parentheses when not every puzzle has it |
| `NumXd` | int | puzzles in the corpus |
| `NumPublic` | int | puzzles from 1965 or before; the pipeline counts these cumulatively over the weekday rows of a year, so read the `Sun` row |
| `NumReprints`, `NumTouchups`, `NumThemeCopies`, `NumSuspicious` | int | grid matches between a puzzle and an earlier one: identical with the same constructor; 50% or more with the same constructor; 30 to 50%; 50% or more with a different constructor |
| `NumExisting`, `NumRedone` | int | not computed; always 0 |

Only puzzles with a full date are counted.

### `similar.parquet` ({fmt(nums['similar'])} rows, {human_size(sizes['similar'])})

Pairs of puzzles of the same size whose grids match by more than 30%.

| column | type | |
|:--|:--|:--|
| `xdid1` | string | the earlier puzzle |
| `xdid2` | string | the later puzzle |
| `matchpct` | int | share of non-block cells with the same letter; negative when the match is against the transposed grid |

## Coverage

{COVERAGE_NOTE}

{coverage}

## Provenance

{provenance}

## Terms

{TERMS}

## Citing

{CITATION}
"""
    return yaml + body, first


def write_kaggle(outdir, name, title, description):
    meta = {
        'title': title,
        'id': f'{OWNER}/{name}',
        'licenses': [{'name': 'other'}],
        'description': description,
        'keywords': KAGGLE_KEYWORDS,
    }
    with open(os.path.join(outdir, 'dataset-metadata.json'), 'w', encoding='utf-8') as fp:
        json.dump(meta, fp, indent=2, ensure_ascii=False)
        fp.write('\n')


def write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(text)


def main():
    ap = argparse.ArgumentParser(description='build xd-clues, xd-answers and xd-metadata dataset snapshots')
    ap.add_argument('--snapshot', required=True, help='version, e.g. 2026.11')
    ap.add_argument('-o', '--output', required=True, help='output root (one directory per dataset)')
    ap.add_argument('clues_zip')
    ap.add_argument('metadata_zip')
    args = ap.parse_args()

    if not re.match(r'^\d{4}\.\d{2}$', args.snapshot):
        ap.error('--snapshot should be YYYY.MM')

    built = datetime.date.today().isoformat()
    czip = zipfile.ZipFile(args.clues_zip)
    mzip = zipfile.ZipFile(args.metadata_zip)

    stats = load_stats(mzip)
    counts = pubyear_counts(stats)
    coverage, npubs, npuzzles = coverage_table(stats)

    # xd-metadata first: it checks puzzles.tsv before anything is written for clues
    mdir = os.path.join(args.output, 'xd-metadata')
    if any(os.path.exists(os.path.join(args.output, d))
           for d in ['xd-metadata', 'xd-clues', 'xd-answers']):
        sys.exit(f'{args.output} already holds a snapshot; remove it first')
    mnums = build_metadata(mzip, stats, mdir)
    sizes = {k: os.path.getsize(os.path.join(mdir, k + '.parquet'))
             for k in ['puzzles', 'stats', 'similar']}
    msrc = [(args.metadata_zip, ['xd/puzzles.tsv', 'xd/stats.tsv', 'xd/similar.tsv'])]
    csrc = [(args.clues_zip, ['xd/clues.tsv']), (args.metadata_zip, ['xd/stats.tsv'])]
    card, first = metadata_card(args.snapshot, built, zip_date(mzip, 'xd/puzzles.tsv'),
                                mnums, coverage, npubs, npuzzles, sizes,
                                provenance_section(args.snapshot, built, 'xd-metadata', msrc))
    write_text(os.path.join(mdir, 'README.md'), card)
    write_kaggle(mdir, 'xd-metadata', 'xd Crossword Corpus metadata', first)

    cdir = os.path.join(args.output, 'xd-clues')
    cnums, cl = build_clues(czip, counts, cdir)
    card, first = clues_card(args.snapshot, built, zip_date(czip, 'xd/clues.tsv'),
                             cnums, coverage, npubs, npuzzles, dir_size(cdir),
                             provenance_section(args.snapshot, built, 'xd-clues', csrc))
    write_text(os.path.join(cdir, 'README.md'), card)
    write_kaggle(cdir, 'xd-clues', 'xd Crossword Corpus clues', first)

    adir = os.path.join(args.output, 'xd-answers')
    log('writing answers...')
    anums = build_answers(cl, adir)
    asizes = {k: os.path.getsize(os.path.join(adir, k + '.parquet'))
              for k in ['answers', 'answers_total']}
    card, first = answers_card(args.snapshot, built, zip_date(czip, 'xd/clues.tsv'),
                               cnums, anums, coverage, asizes,
                               provenance_section(args.snapshot, built, 'xd-answers', csrc))
    write_text(os.path.join(adir, 'README.md'), card)
    write_kaggle(adir, 'xd-answers', 'xd Crossword Corpus answers', first)

    report = {'snapshot': args.snapshot, 'built': built,
              'xd-clues': cnums, 'xd-answers': anums, 'xd-metadata': mnums,
              'coverage': {'publications': npubs, 'puzzles': npuzzles}}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
