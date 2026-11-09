# Preservation

*Draft, November 2026, for a corpus begun in 2016 (see [HISTORY.md](HISTORY.md)).*

## Purpose and scope

The xd Crossword Corpus exists to keep published crosswords readable, findable
and studiable for as long as anyone wants them, which we take to mean a
century or more. This document says what we do to keep the corpus safe, what
we promise, and where the limits are.

The corpus is run by two volunteers, funded from their own pockets, with no
institution behind it. What we can promise is scaled to that. We do not claim
to be a certified repository. We do claim that the choices below make the
corpus unusually easy to keep, and that we are honest about where it is at
risk.

## What preservation means here

Two things, in order of importance:

1. **The bits survive.** Every puzzle, and the original file it was made
   from, exists in more than one copy in more than one place, and we can tell
   when a copy has been damaged.
2. **The content stays readable.** A puzzle is stored as plain UTF-8 text in
   the `.xd` format, whose specification is public. A `.xd` file can be read
   with no software at all, and the whole corpus can be processed with a few
   lines of code in any language. There is no database, no binary format and
   no proprietary dependency between a reader and a puzzle.

## How the corpus is kept

- **Version control.** The corpus is a git repository. Every change to every
  file is recorded with who made it, when and why. History is never rewritten.
- **Copies.** The repository is hosted on a commercial git service, mirrored
  to a second service, and cloned on the maintainers' machines and by other
  contributors. Any complete clone is the whole corpus.
- **Originals.** The file each puzzle was converted from is kept, unchanged,
  in a checksummed archive in cloud storage, and a receipts table links nearly
  every puzzle to its original and its source. A few early bulk imports have
  no receipts, and some source archives from before 2025 were lost (see
  "Limits and known risks"). Fixes are made to the `.xd` file,
  never to the original.
- **Checks.** Every contribution is checked by continuous integration before
  it is merged: format validity, identifiers, shelving, dates and receipts.
  A scheduled job checks that every registered source archive is still
  present and unchanged.
- **Format.** The `.xd` format is specified publicly and versioned
  conservatively. When the format changes, existing files remain valid or are
  migrated in a recorded, reviewable change.

## What we commit to

- Every puzzle accepted into the corpus is kept indefinitely, with its
  provenance, unless removed under the rule below.
- The original source files are kept as received.
- Changes to puzzles are recorded in history and, where they change an
  answer or apply errata, explained in the puzzle's notes (see [EDITORIAL.md](EDITORIAL.md)).
- The corpus can be handed over whole at any time: a clone of the repository
  and a copy of the source archives are everything there is.
- We assess our own preservation capability once a year, publish the result in
  [assessments/](assessments/), and act on what it finds.

## Limits and known risks

- **Two people.** Continuity depends on the maintainers. See
  [GOVERNANCE.md](GOVERNANCE.md), "Continuity", for what happens if one or
  both stop.
- **Source archives have one copy.** As of November 2026 the original source
  files live in a single cloud bucket. Some early source archives, from before
  2025, were lost when an earlier bucket was retired, although the puzzles
  converted from them are intact. A second copy is the first item on our
  preservation plan.
- **No tested restore.** We have never rebuilt the corpus from a mirror as an
  exercise. We intend to, yearly.
- **Hosting is personal.** The services the corpus lives on are paid for and
  administered by the maintainers as individuals.

## Removing puzzles

Puzzles are removed from the corpus only deliberately: at the request of a
rights holder, because they turn out to be outside the collection scope, or
because they are duplicates. A removal is a recorded change with its reason in
the commit, and the puzzle's identifier is never reused. Removed puzzles stay in
history; a removal that must also purge history is treated as an exceptional
decision and logged in [DECISIONS.md](DECISIONS.md).

## Review

Reviewed once a year with the preservation assessment. Last reviewed:
November 2026 (first version).
