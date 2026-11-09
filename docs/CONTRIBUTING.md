---
---
# Contributing puzzles

*For editors, constructors and publishers. Draft, November 2026, for a corpus begun in 2016 (see [HISTORY.md](HISTORY.md)).*

If you edit, construct, publish, or collect crosswords, we would like to add yours to our collection.
This page says what we do with puzzles we are given, who can see them, and
what you can ask of us. The short version: your originals are kept safe and
unchanged, the corpus never offers the puzzles to solvers, and you stay in control of how your work is represented.

## Why we are asking

Crosswords disappear. Newspapers fold, websites go offline, apps change, and a run of puzzles that was solved by thousands of people survives only in a box or on one person's hard drive. The xd Crossword Corpus exists so that published puzzles stay readable and findable for the long term, a century or more, in a plain-text form that needs no particular software to read. The corpus already holds more than 160,000 puzzles from over 160 publications, going back to the very first crossword puzzle in December 1913, and it is used to study how crosswords and their language have changed.

## What happens to what you send

- **The originals are kept exactly as received.** We store the original puzzles in the format you send them, unchanged, in a checksummed and versioned private archive. This archive is not made available to anyone outside the project.
- **Each puzzle is converted to one plain-text file** holding its grid, clues, answers, title, constructor, editor, date and copyright line. Headers are normalized as described in [EDITORIAL.md](EDITORIAL.md).
- **The corpus is private.** It lives in a repository that is not public, with more than one copy in more than one place. How it is kept is described in
  [PRESERVATION.md](PRESERVATION.md).

## Who can see it

Researchers can ask for access for a stated non-commercial purpose and must agree to terms that forbid publishing puzzles or passing them on. Most research needs only derived data, such as clue and
answer pairs or statistics, and that is what most people get. The forms of access and the terms are in [ACCESS.md](ACCESS.md).

Aggregate statistics and analyses are published at [xd.saul.pw](https://xd.saul.pw). They describe the corpus as a whole and do not reproduce puzzles.

**The Cross(word) Reference.** Puzzles in the corpus appear on
[The Cross(word) Reference](https://crosswordreference.com), a site for
looking up clues, answers and constructors across crossword history. A puzzle
is shown there as a reference, with its answers filled in, not as something
to solve. If you would rather your puzzles, or your whole series, you may opt out.

## What you can ask of us

At any time:

- what we hold from your publication;
- corrections to anything we got wrong;
- that a constructor be named as they wish to be named;
- that specific puzzles, or all of yours, be removed. Removals are honored and
  recorded, and anyone who has a copy is asked to delete it.

## What to send

Anything. Puzzle files in any format (`.puz`, `.ipuz`, `.jpz`, Crossword
Compiler, Across Lite, spreadsheets), PDFs, page scans, photographs of
clippings, or a link to an online archive. Complete runs are ideal, but
partial ones are welcome; gaps can be filled later. If you are not sure what
you have, send a sample and we will tell you what we can do with it.

Send it, or ask us anything, at xd@centuryarcade.org. Large archives can be shared however is convenient for you.

## What you get back

A clean, checked copy of your own archive in a durable plain-text format, with
the errors we found listed, which for most publications is a better copy than
the one they started with. If it is useful to you, we can also provide
statistics about your run: constructors, word counts, grid sizes, how your
puzzles compare with the rest of the corpus.

## Doing the conversion yourself

Some contributors prefer to convert their puzzles and submit them directly.
That is welcome. The converters are in
[xdformat](https://github.com/century-arcade/xdformat), and the import guide,
with the rules for naming, filing and provenance, lives in the private corpus
repository; ask for access (see [ACCESS.md](ACCESS.md)) and we will set you
up.
