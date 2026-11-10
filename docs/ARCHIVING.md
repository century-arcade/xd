# Archiving crosswords

*For anyone who makes, publishes or collects crosswords. Draft, November 2026.*

## Why

Crosswords get lost. A venue closes, a website lapses, a hard drive dies, and a run of puzzles thousands of people solved is gone. This page says how to keep puzzles readable for a century with a folder and a spreadsheet.

It starts from Laura Braunstein's talk "Future-Proof Your Puzzle Archive" at Crossword Con in April 2025 **[check: link Laura and the slides]**. She quoted Thomas Hyry **[check: link Hyry and the source of the quote]**: archives are less about saving records than about acknowledging and managing loss. You will not save everything, and you don't have to. Collecting everything is a habit. Deciding what to keep is a plan, and a plan is what lasts.

Her five steps are right: make a plan, organize, use durable formats, keep copies in more than one place, and build in accountability. We differ on one point. She says never to archive `.puz` files. We say keep the file you were given, whatever it is, and make a readable copy beside it. A `.puz` file isn't the problem. Converting a puzzle through `.puz`, and throwing away the original, is.

We thank Laura for the talk, and for publishing her slides under CC BY-NC so others can build on them.

## The guidelines

### 1. Decide what you keep

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

### 4. Make a readable copy

Beside each original, keep a copy a person can read with no software. We recommend [`.xd`](https://github.com/century-arcade/xdformat/blob/master/doc/xd-format.md): one plain-text file per puzzle, with the headers, the grid as rows of letters, every clue with its answer, and the notes. It holds rebus squares, circles and shading, odd shapes, accented letters and the full byline. Any text editor opens it, and the 160,000 puzzles of the xd Crossword Corpus are in it. The converters are in [this repository](https://github.com/century-arcade/xd).

XML and PDF are also fine. XML is a durable text format, and a PDF shows the puzzle as solvers saw it.

Make it from the original, not from a `.puz` made from the original. A `.puz` has no way to mark squares outside a puzzle's shape, keeps one author field where the byline had two constructors and an editor, holds only Latin-1 characters, and stores rebus squares and notes in extensions that many tools drop **[check: .puz limits]**. Once the original is gone, that loss is permanent.

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

A second copy on your own laptop is not a second copy. Put one where it fails for different reasons: a friend's drive, a cloud account that isn't the one you use every day, a library, the corpus. Copy the whole folder, receipts and all, and check the fingerprints.

### 7. Say what you hold, and to whom

An archive no one knows about dies with its keeper. Tell someone what you have and where: a friend, your editor, a library, us. The crossword world doesn't need one place that holds the only copy. It needs one place that knows what exists, and many places that keep it: centralized collection and curation, distributed preservation.

### 8. Look at it once a year

Check every fingerprint against the record, open a few files in each format, add the year's new puzzles, and confirm the second copy is still there and current. Braunstein suggests an archive buddy who does the same, so you remind each other.

## Metadata

Here is where each column of Braunstein's metadata template goes in an `.xd` file or the record in step 3.

| Template column | Where it goes |
|---|---|
| Filename | the record's `file` |
| Puzzle Title | `Title:` |
| Puzzle Type | an extra header, which the spec allows, or the notes **[check: should the corpus name one?]** |
| Collaborator | `Author:`, constructors joined with "and"; `Editor:` for the editor |
| Theme | the notes; a contest's prompt and answer go in `Meta:` |
| Dimensions | the grid itself |
| Published (YYYY-MM-DD) | `Date:` |
| Venue Name | the publication, which the corpus records in each puzzle's identifier |
| Venue URL | the record's `source` |
| Fee | not recorded |
| Rights | not recorded; `Copyright:` holds the printed rights line |
| Notes | the notes |

The corpus doesn't record Fee or Rights. A fee is private between constructor and venue. Rights change after publication: they revert, or are sold or licensed again. The corpus records what was printed, not the contract. A constructor should keep both anyway. The fee is your history of what the work paid. The rights tell you what you can republish, and when.

## Giving your archive to the corpus

Send us the originals, the record and the readable copies, and we will check the copies, add the puzzles to the corpus, and keep your originals unchanged with their fingerprints. [CONTRIBUTING.md](CONTRIBUTING.md) says what happens to puzzles we are given, who can see them, and what you can ask of us.

xdfetch, a puzzle downloader we are writing, is a reference implementation of the record-keeping in steps 2 and 3 **[check: link once public]**.
