# Datasets

*Draft, November 2026, for a corpus begun in 2016 (see [HISTORY.md](HISTORY.md)). Marked **[practice]** where it describes what we
already publish, **[proposed]** where it is new.*

## Purpose

Most puzzles in the corpus are under copyright, and we do not publish them
(see [ACCESS.md](ACCESS.md)). But much work with crosswords does not need
whole puzzles: it needs the words, the clues, who edited what and when. The
public data is for anyone who wants to study crosswords or build something
with crossword data: researchers, and just as much hobbyist programmers,
since the corpus and most of the crossword world are hobby projects. We
publish it so that this can happen without anyone having to ask, and
without redistributing anyone's puzzles.

The principle behind every public dataset: **nothing we publish lets a
copyrighted puzzle be rebuilt**.

The data is offered as it is, without warranty, and it carries the corpus's
errors; what we can and cannot promise about rights and accuracy is in
[ACCESS.md](ACCESS.md#what-we-can-and-cannot-promise).

## Three tiers

### (a) Public full content

Complete puzzles that are out of copyright:

- **Before 1931**: public domain in the United States outright. The
  corpus holds 459: *Judge* magazine 1924 to 1930 (304, digitized by the
  [Every Puzzle Project](https://github.com/EveryPuzzleProject)), the 1924
  Simon & Schuster book (150), and 5 single puzzles. **[proposed]**
- ***Judge*, 1931 to 1939**: 227 puzzles. US copyright in works
  published 1931 to 1963 lasted only if renewed in the 28th year, and a
  check of the renewal records
  ([assessments/copyright-renewal-2026.md](assessments/copyright-renewal-2026.md))
  found no renewal of any *Judge* issue. **[proposed]**
- **New York Times, 1942 to 1963**: not public domain. A check of the
  renewal records ([assessments/copyright-renewal-2026.md](assessments/copyright-renewal-2026.md))
  found that the Times renewed the copyright in every issue of those years,
  so these 5,267 puzzles stay under copyright until 2037 to 2058. They
  belong to tier (c), the gated tier, not here. The `puzzles-pre1965`
  release of [century-arcade/xd](https://github.com/century-arcade/xd/releases)
  published them on the belief that the Times had not renewed; the
  maintainers are deciding what to do with that release. **[proposed]**

Anyone can download them, from GitHub releases and Hugging Face.

### (b) Public derived data

- **Clues and answers** (`clues.tsv` in `xd-clues.zip`): one row per clue,
  with publication, year, answer and clue. **[practice]**
- **Puzzle metadata** (`xd-metadata.zip`): `puzzles.tsv` (identifier, date,
  size, title, constructor, editor, copyright line), `stats.tsv` (puzzle
  counts by publication, year and weekday) and `similar.tsv` (for each
  puzzle, how much of its grid and clues match earlier puzzles).
  **[practice]**
- **Answer lexicon by year**: each answer with its number of uses per
  publication-year. **[proposed]**
- **Grid statistics**: size, block count, word count and word lengths,
  without the grid itself. **[proposed]**

Anyone can download them, today from [xd.saul.pw/data](https://xd.saul.pw/data),
and from Hugging Face and Kaggle once they are set up.

### (c) Gated

Samples of full modern puzzles (see "Samples" in [ACCESS.md](ACCESS.md)).

- **A random sample of 1,000 puzzles**, drawn across the whole corpus, with
  full `.xd` content. It is fixed and versioned: the same puzzles every
  time, so results can be compared. A researcher building a crossword
  solver already has it.
  **[practice]**
- Variations can follow on request: a sample stratified by decade or by
  publication, a date-split benchmark (older puzzles for training, recent
  ones for testing), and larger samples. **[proposed]**

These are published on Hugging Face as gated datasets: each person asks, a
maintainer approves them by name, and the [ACCESS.md](ACCESS.md) terms
apply, including the rule against delivering puzzles to solvers. This is
the same process as a request by email, with a form, and hobbyists apply the
same way as researchers. **[proposed]**

The full corpus is not a dataset. It stays available only by direct
arrangement under [ACCESS.md](ACCESS.md).

## Rules for derived data

Tier (b) follows these rules, **[proposed]** unless marked.

- **No grids, no clue numbers.** A clue row does not say where its answer
  sits in a grid, or which clue it was. **[practice]**
- **Year, not date.** Clue rows carry the year of publication and nothing
  finer. **[practice]**
- **Rows are reordered within each publication-year.** The order of a
  puzzle's clues does not survive; today the rows of each publication-year
  are sorted by answer and clue. **[practice]**
- **Contest puzzles with redacted grids are left out.** Their clues are not
  published, so a contest is not spoiled before its answers are. **[practice]**
- **A minimum cell size.** A publication-year with fewer than 5 puzzles is
  too small to hide which clue came from which puzzle. Its rows are merged
  into a coarser cell (the publication's decade) or dropped.
- **A coverage table.** Coverage is very uneven, so every dataset card
  carries a table of puzzle counts by publication and decade.

`puzzles.tsv` is per puzzle and carries full dates, but no clues, and no
answers beyond the first across and down, used as a grid hash. **[practice]**

## Where and how

- **Hugging Face**, under the
  [`century-arcade`](https://huggingface.co/century-arcade) organization,
  holds tiers (a), (b) and the gated tier (c). **[proposed]**
- **Kaggle**, equally, holds tier (b): the same snapshots with the same card
  text, published at the same time as on Hugging Face. **[proposed]**
- **Snapshots, not streams.** Datasets are versioned snapshots, published
  quarterly, not rebuilt nightly, so that a result can name the version it
  used. **[proposed]**
- **Zenodo** holds one record for the corpus as a whole, with a DOI for
  citing it, pointing at the corpus page. **[proposed]**
- **GitHub releases** keep the public-domain puzzle sets, as they do now.
  **[practice]**

Every dataset card states the terms in one paragraph, links to this document,
to [ACCESS.md](ACCESS.md), and to [AI.md](AI.md), the corpus's statement on
AI, which sets the terms on using the data to train models; says how to cite
the corpus (see [README.md](README.md#citing)); and carries the coverage
table. **[proposed]**

## Publishers and constructors

Publishers and constructors can ask for their puzzles to be removed from
tier (a) or tier (c), as described in [CONTRIBUTING.md](CONTRIBUTING.md).
The puzzles are removed from the next snapshot, and gated users are asked to
delete their copies.

A tier (b) row cannot be traced to one puzzle, but a publication can ask
to be left out of future snapshots, and we will do so. **[proposed]**

## Review

This policy is reviewed once a year with the other policies and the
preservation assessment. Changes are logged in [DECISIONS.md](DECISIONS.md).
