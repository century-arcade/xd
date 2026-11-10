# Archiving crosswords

*For anyone who makes, publishes or collects crosswords. Draft, November 2026.*

## Why

Crosswords get lost. A venue closes, a website lapses, a hard drive dies, and a run of puzzles thousands of people solved is gone. This page says how to keep puzzles readable for a century with a folder and a spreadsheet.

This proposal was inspired by Laura Braunstein's talk "Future-Proof Your Puzzle Archive" at Crossword Con in April 2025 ([video](https://www.youtube.com/watch?v=xxZpUFBzdj8), [slides](https://docs.google.com/presentation/d/14VD5loMkncWrag8M0T7wZcqlRTEv4PwFRrt2KphDXHk/edit?usp=sharing)). She quoted librarian Thomas Hyry: archives are less about saving records than about acknowledging and managing loss. You will not save everything, and you don't have to. Collecting everything is a habit. Deciding what to keep is a plan, and a plan is what lasts. We thank Laura for the talk, and for publishing her slides under CC BY-NC so others can build on them.

Here at Century Arcade we have a decade's experience collecting and saving crosswords. What follows are our recommendations for keeping your own.

## The guidelines

### 1. Decide what to keep

Write it down in one sentence. "Every puzzle I published, as published." "Every puzzle my venue ran, with the constructor's notes." Drafts and test-solve notes are yours to keep or not. Decide once, not for every file.

### 2. Keep the original file, never edited

Keep each puzzle in the file the source produced: the `.puz` the website served, the `.jpz` from the editor, the Crossword Compiler file, the PDF, the scan. Don't fix it or resave it. Fix errors in the readable copy and say so there. The original is your evidence of what was published.

### 3. Record where and when you got it

For every original, keep one row in a spreadsheet saved as plain text (`.tsv` or `.csv`), next to the files. The minimal record is five fields:

| file | sha256 | received | source | notes |
|---|---|---|---|---|
| `originals/2026/2026-03-14-pi-day.puz` | `9f2c…e41a` | 2026-03-14 | `https://example.com/puzzles/pi-day.puz` | downloaded from the venue's site |

- **file**: where it is in your archive.
- **sha256**: a fingerprint of the file's exact bytes, all 64 characters (shortened here). If one byte changes, the fingerprint changes. On a Mac or Linux, `shasum -a 256 FILE`; on Windows, `certutil -hashfile FILE SHA256`.
- **received**: the date you got it, as `YYYY-MM-DD`.
- **source**: the address you downloaded it from, or the person who sent it.
- **notes**: anything else, in plain words.

Never change a row. If a file moves or is replaced, add a new row. The corpus keeps the same record in its `receipts.tsv` and `source-archives.tsv`.

[xdfetch](https://github.com/century-arcade/xdfetch), our puzzle downloader, keeps this record for you: it saves the original file as served and writes a receipt row for each one.

### 4. Make a readable copy

Beside each original, keep a copy a person can read without special software.

`.puz` has two big problems as an archival format: first, it's a proprietary binary format, requiring software to read and make sense of it. Second, that it's been frozen in time for almost 20 years; it lacks new features that are becoming common in crosswords, such that important information is lost when puzzles are written solely as `.puz` files.

`.xml` and `.json` are better, when written directly from a crossword program, but can introduce a serious problem when defined on an ad hoc basis, which is that modern puzzles manifest a surprising number of difficult edge cases: character encoding, rebus entries, "Schrödinger" squares, odd shapes, unusual clue numbering, and so on.

We recommend [`.xd`](https://github.com/century-arcade/xdformat/blob/master/doc/xd-format.md): one plain-text file per puzzle, headers, grid, clues with answers, notes. Any text editor opens it. The 160,000 puzzles in the xd Crossword Corpus are in it, converters exist for all major crossword formats, and a robust linter is available to check syntax. The conventions for rebus squares, circles and shading, Schrödinger squares, odd shapes and multi-author bylines were all worked out by key stakeholders over months. That work is done, and it's what you get for free.

Including a pdf or jpg of the puzzle as it appeared in print or on a web site is not a bad idea as well.

### 5. Name and arrange files so a stranger can find them

Put the date first, as `YYYY-MM-DD`, so files sort in order. Add a short venue name and title. Use lowercase letters, digits and hyphens; no spaces. One folder per year is enough for most people. Keep originals and readable copies apart, with matching names:

```
crosswords/
  receipts.tsv
  originals/2026/2026-03-14-pi-day.puz
  xd/2026/2026-03-14-pi-day.xd
```

Add a `README.txt` at the top saying whose archive it is, what it holds, and how to reach you.

### 6. Keep a second copy you don't control

A second copy on your own laptop is not a second copy. Put one where it fails for different reasons: a friend's drive, a cloud account that isn't the one you use every day, a library. Copy the whole folder, receipts and all, and check the fingerprints.

### 7. Say what you hold

An archive no one knows about dies with its keeper. Tell someone what you have and where: a friend, your editor, a library.

Better, [send it to us](CONTRIBUTING.md). The corpus is one collection, kept in many copies, and a puzzle in it is as safe as we know how to make it. Your originals are stored exactly as received, with their fingerprints, and never shared; the readable copies join the corpus. That page says what we do with what you send and what you can ask of us.

### 8. Look at it once a year

Check every fingerprint against the record, open a few files in each format, add the year's new puzzles, and confirm the second copy is still there and current. Laura suggests an archive buddy who does the same, so you remind each other.

## Metadata

Two records hold everything a stranger needs to know about a puzzle: the receipt row from step 3, which says where the file came from, and the headers of its readable copy, which say what the puzzle is.

The receipt, one row per original:

| field | required | what it is |
|---|---|---|
| file | yes | the path in your archive |
| sha256 | yes | the fingerprint of the file's bytes |
| received | yes | the date you got it, `YYYY-MM-DD` |
| source | yes | the address you downloaded it from, or the person who sent it |
| notes | no | anything else, in plain words |

The headers, at the top of each `.xd` file:

| header | required | what it is |
|---|---|---|
| Title | yes | as published; omit it if the puzzle had none |
| Author | yes | the byline as printed, constructors and all |
| Editor | no | the editor, if credited |
| Copyright | if printed | the rights line as printed |
| Date | yes | the date published, `YYYY-MM-DD` |
| Number | no | the puzzle's number in its series |

The notes section at the end of the file takes the rest: the theme, the venue, a contest's answer, anything the file doesn't show. Everything else a template might ask for is already there: the dimensions are the grid, the venue is in the filename and the source. If you keep more, keep it in the receipt's notes or the `.xd` notes rather than in a column no one else will read.

Laura's metadata template, published with her talk, is a good checklist for a constructor's own records and covers some things we don't ask for.
