# Editorial conventions

What goes in a `.xd` file and how its fields are used.

Companion documents:

- [COLLECTION.md](COLLECTION.md): which puzzles we collect.
- The import guide (CONTRIBUTING.md in the private corpus repository): how to submit
  puzzles, how they are named and shelved, and source archives.
- REVIEWING.md (in the private corpus repository): what to check in an import MR.
- In the xdformat repo: [xd-format.md](https://github.com/century-arcade/xdformat/blob/master/doc/xd-format.md) (the format).
- On this site: [character-encoding.md](character-encoding.md) (decoding and
  typography), [rebus-conventions.md](rebus-conventions.md) (rebus and
  quantum cells).

Each convention below is marked:

- **[established]**: written down and agreed, as defined in
  [GOVERNANCE.md](GOVERNANCE.md); editorial rules are written in the spec,
  the lint rules or REVIEWING.md.
- **[practice]**: what merged imports already do, but not written down until
  now. Confirm or change.
- **[proposed]**: under discussion (October 2026), not yet a rule.

## Principles

1. **A `.xd` file holds the puzzle and nothing else.** **[established]** The same
   puzzle from any source should yield the same grid, clues and headers,
   byte for byte (see
   CONTRIBUTING.md, "Versions of a puzzle"
   for what to do when they don't). The notes are the exception
   **[practice]**: they carry
   what a reader needs to know about the puzzle (text published with it,
   errata, corrections to what was published), so two otherwise identical
   files can differ there. Where a puzzle came from and how it was made
   (sources, OCR, who reviewed it) go in `receipts.tsv` and
   the source archive's `NOTES.md`. They
   don't go in the `.xd`.
2. **The puzzle as the publisher meant it.** **[practice]** The clues, grid
   and headings are the publisher's. Obvious mistakes (a typo, a misprinted
   answer letter, damage in transfer) are corrected to what was meant;
   anything the publisher did on purpose (wordplay, a gimmick) stays.
   The corpus favors intent: where it's clear what was meant, correct to
   that, whoever made the mistake.
3. **Corrections that change what was published are noted; bookkeeping is
   not.** **[practice]** When the `.xd` corrects an answer or grid letter the
   publisher got wrong, or applies published errata, the notes say what was
   published and what it became. Fixes to our own copy (transfer damage, a
   better scan, markup) and typo fixes in clue text are recorded only in the
   commit that makes them (see CONTRIBUTING.md, "Editing puzzles already in
   the corpus").
4. **The originals are never edited.** **[established]** Fixes go in the `.xd`
   files (or `overrides.tsv`). Files in a source archive stay exactly as they were
   received.

## Characters and typography

- **UTF-8, ASCII where the original is only typography.** **[established]**
  Curly quotes become straight quotes, an ellipsis becomes `...`, and a
  no-break space becomes a space (puz2xd's decode, lint rule XD208).
- **Runs of spaces inside text stay as published.** **[established]** Some
  are the puzzle: spaced-out letters (`S         L        O        T ~
  EXPANSIONSLOT`) or a blank pattern with wider gaps between words
  (`R O C _   A _ D   R _ _ _`). Most are slips, and many mark something
  lost, such as a dropped `à` (`Cancel,   la`) or lost italics
  (`M*A*S*H    meal`). Converters keep them; tabs and line breaks become one
  space. xdlint's XD210 (info) lists them; fix each one after checking the
  source (`xdlint --fix --unsafe-fixes --enable-only XD210` collapses them).
  Runs where the format puts one space, such as after `A1.` or around
  ` ~ `, are XD209's and `xdlint --fix` collapses them.
- **Real letters keep their accents**: `Almodóvar`, not `Almodovar`.
  **[established]**
- **The em dash (U+2014) is kept** as Unicode. Publishers use it both as
  typography and as a fill-in-the-blank marker (`Persona non — ~ GRATA`).
  **[established]** Don't flatten em dashes across the corpus, because some are
  Mac Roman `ó` mojibake that still need review ([character-encoding.md](character-encoding.md)
  §7).
- **Fill-in-the-blank keeps the publisher's form**: `___` or `—`, whichever the
  source used. **[practice]**
- **Whitespace is collapsed.** **[established]** The rare clue where spacing is
  the point (a SPACES meta-clue) is handled in `overrides.tsv`.
- **Markup only in clues**: `{/italic/}`, `{*bold*}`, `{_underline_}`,
  `{-strike-}`. Headers and notes are plain text. **[established]**
  Superscript `{^x^}` and subscript `{~x~}` (from the v4 draft) are in use
  in 14 files. **[practice]**

## Headers

- **`Title:`** is the puzzle's own name. **[practice]**
  - If the heading has both a series label and a name ("Crossword Puzzle #2:
    Flights of Fancy"), the title is the name ("Flights of Fancy") and the
    series number goes in `Number:`.
  - A subtitle or tagline goes in the notes.
  - When the puzzle has no name, the series heading is the title ("Judge's
    Crossword Puzzle No. 67").
  - When the puzzle has no name and the outlet prints no series heading, the
    title is the date, without the outlet's name (the publication is already
    recorded in the pubid and `publications.tsv`). **[proposed]** Form:
    weekday, full month, no zero padding: `Tuesday, October 6, 2026`. The corpus
    has all three of `Tuesday, October 6, 2026`, `October 6, 2026` and
    `October 06, 2026`. Whether to rewrite titles an outlet printed with its
    name and a date in some other form (`LA Times, Mon, Jan 6, 2020`) is an
    open question (see below); existing files are not changed.
- **`Author:`** is the constructor, in a normalized form. **[established]**
  - Not the editor, not a banner, no "By " prefix.
  - Two constructors are joined with "and" ("Brooke Husic and Ada Nicolle").
    **[proposed]** for new imports. The corpus has both (about 3,200 files
    with "and", 3,300 with "&"), and existing files are not changed.
  - Each person is named the way the names tables spell them, not
    necessarily as printed. **[proposed]** See "People's names" below for
    what is rewritten and what stays.
- **`Byline:`** is the author credit exactly as published. **[practice]** for
  Judge, **[proposed]** everywhere: it is present whenever `Author:` differs
  from what was printed, beyond the formatting above ("By ", "&" for "and", an
  editor credit moved to `Editor:`). Examples: `B. E. Quigley`,
  `www.brendanemmettquigley.com`, `brooke` (Puzzmo), `Submitted by W. T.
  Litson, Jr., Oceanside, L. I.`, `Puzzle by John Doe, clues by Mary Jane`.
  It holds only what was printed: where an outlet prints the editor as a
  credit of its own, a normalized `Editor:` doesn't add it to `Byline:`, because
  that would mean writing a byline the outlet never printed. It is an extra
  header, which the spec allows; adding it to the spec is
  [xdformat issue 11](https://github.com/century-arcade/xdformat/issues/11).
- **`Editor:`** has a header of its own, never folded into `Copyright:` or
  `Author:`. **[established]** Some older shelves use the form `Author: X / Ed.
  Y`. New imports use `Editor:`. Names in it follow "People's names", like
  `Author:`. When `Editor:` is normalized, its printed form is the names table
  row that rewrote it (Puzzmo's `Ann` is Ann Hagerty in `puzzmo/names.tsv`).
- **`Copyright:`** holds only the rights or syndication line. **[established]**
- **`Date:`** is the date this publication printed or posted the puzzle, in
  `YYYY-MM-DD` form, and must match the file name. **[established]** For a
  syndicated puzzle, use the date this publication ran it, not the date the
  feed carried it (precedent: the Boston Globe re-dating, 2026-10).
  **[practice]**
  - **A rerun** (the outlet ran the same puzzle again) is shelved on both
    dates. **[proposed]**
  - **A reprint** labeled "originally published ..." keeps that line in its
    notes and is not filed a second time under the original date.
    **[proposed]**
- **`Number:`** is required for any numbered series: a newspaper, magazine or
  book number, "No. 67". **[practice]**
  - It's required even when the puzzle also has a name: "Crossword Puzzle #2:
    Flights of Fancy" is `Title: Flights of Fancy` with `Number: 2`.
  - It's also required when the series heading is the title: "Judge's Crossword
    Puzzle No. 67" also gets `Number: 67`.
  - `Number:` is the puzzle's place in a numbered series, not just any number
    in its title. A puzzle titled "Chanel #5" is probably not part of a
    numbered series and gets no `Number:`.
  - A numbered sub-series inside another series (say, a "Christmas Puzzle #4"
    in the Boston Globe's daily) is treated one of two ways, never both:
    - **As its own numbered series**, e.g. "the Boston Globe Christmas
      Puzzle", with its own pubid and `Number: 4`.
    - **As part of its parent's dated series**, with no `Number:`. The title
      keeps the number ("Christmas Puzzle #4"), so it still shows the puzzle
      belongs to a sub-series.
- **`Meta:`** holds the prompt and answer of a contest or meta puzzle, as
  `Meta: <prompt> ~ <answer>` (148 files). **[practice]** It is an extra
  header, which the spec allows. The prompt is also given in the notes. The
  answer never goes in the notes, because solving software shows the notes
  before the solve.
- **`Special:`** and **`Rebus:`** follow the [spec](https://github.com/century-arcade/xdformat/blob/master/doc/xd-format.md) and
  [rebus-conventions.md](rebus-conventions.md).
  Circles and shading are preserved. **[established]**

## People's names

**[proposed]** throughout. `Author:` and `Editor:` name people; `Byline:`
keeps what was printed. So `Author:` can use one spelling per person without
losing anything, but only where we're sure it's the same person. Who is the
same person is decided once, in the names tables, not by each importer.

The files fix spellings; the tables link names. A spelling of a name (initials,
a typo, a handle) means the same person forever, so it's corrected in the file
once. A different name (a pen name, a house name, a maiden or married name) is
a fact about the person that can change over time, so the file keeps the name
the puzzle was published under and the names tables say who it is. A name
change is a new table row and rewrites no files. The one exception is a name
the person has left behind (below).

- **Rewritten to the person's name** (the printed form goes in `Byline:`):
  - initials, a middle name or initial, a nickname: `B. E. Quigley`,
    `Brendan Quigley`, `Liz Gorski`;
  - a misspelling with no possible intent: `Bremdan Emmett Quigley`, `Will
    Shorts`;
  - a website or handle printed as the whole credit:
    `www.brendanemmettquigley.com`. A site that credits people by the name
    they choose there prints handles, even ones that look like first names:
    Puzzmo's `brooke`, `rafa` and `Ann`;
  - a publication's own way of crediting someone: Newsday's `S.N.` for
    Stanley Newman;
  - a joke byline, when it's clear who made the puzzle: a person playing on
    their own name for a puzzle or two (`Past Quiara Vasquez`, `Quiara
    Vasquezzzzz` on her own site). `Byline:` keeps the joke, so it still
    shows, and `Author:` puts the puzzle with the rest of the person's work.
    A one-off joke is a hand fix like any other and needs no names table
    row; a joke name the person keeps using gets one, like a handle.
- **A name the person has left behind** is corrected by hand, not by a table.
  We follow the Trans Metadata Collective's
  [Metadata Best Practices for Trans and Gender Diverse Resources](https://doi.org/10.5281/zenodo.6686841)
  (v2.6, 2025, sections 3.2.4 and 3.2.6): their work is found under the name
  they use now, and the old name is used as little as possible and never shown
  beside the new one.
  - Write the current name in `Author:` or `Editor:`. No `Byline:` (or the
    current name in brackets, `Byline: [Current Name]`, to show it was
    supplied, not printed).
  - The old name goes nowhere we publish: not `Byline:`, not a names table,
    not a commit message, MR or issue. The source archive keeps what was
    printed.
  - Where we can ask the person, we do, and do what they say.
  - When it isn't clear whether an earlier name is one the person still uses
    or one they've left behind, treat it as left behind.
- **Kept as printed** (no `Byline:` needed unless the byline says more):
  - a pen name or house name: `Anna Gram`, `Thomas Joseph`. It's a name used
    across many puzzles, not a one-off joke: the credit the person or
    publisher chose. The names tables say who is behind it;
  - an earlier name the person published under and doesn't disown, such as a
    maiden name: `Margaret Petherbridge`, not rewritten to Margaret Farrar. A
    `former` row in the names tables links the two. A spelling of the earlier
    name is rewritten to that name, not to the later one (`M. Petherbridge` is
    `Margaret Petherbridge`). When a constructor changes their name, their
    earlier puzzles keep the old one and nothing is rewritten;
  - anything we aren't sure of: an attribution a table marks "likely", a
    surname or first name alone (unless the publication's table says it is
    that publication's handle or initials for someone, as above), a byline
    that may be a joke on the theme but with no sure maker (`Peter O'Gordon`
    on an Irish theme);
  - a name no table has yet. That's normal for a new constructor.
- **Removed, and not kept in `Byline:`**: things that were never part of the
  byline. A date stamp (`Rich Norris010201`), conversion leftovers (`Fred
  Piscop?ACROSS`, `s Brendan Emmett Quigley`), an email or website a feed
  added in parentheses, a date and title lead-in (`June 27, 2004 - Don't Take
  My Advice by ...`). Text the publisher printed with the name (a hometown, an
  address, "clues by") stays in `Byline:`.
- **The wrong person credited** (not a spelling) is corrected in `Author:`
  and the commit says how it's known. `Byline:` keeps what was printed.
- **The names tables** are `names.tsv` files at two levels, one row per
  printed form that isn't the person's own name. A name is looked up in its
  shelf's table first, then the corpus's.
  - **A shelf's table** (`<shelf>/names.tsv`, beside its `ABOUT.md`) holds
    how that publication credits people: Puzzmo's handles, Newsday's `S.N.`,
    Newsday's editor credited as `Stanley`, a misspelling the outlet repeats,
    a house name (`Thomas Joseph`) and who made its puzzles when. It covers
    every series on the shelf (`puzzmo/` is pzmo, pzmomini and pzmobig), so
    most rows need no scope. Whoever imports or reviews the shelf sees it
    there.
  - **The corpus's table** (`names.tsv` at the root) holds facts about a
    person that hold wherever they're printed: their own variants (`Louis
    Sabin` for Lou Sabin, `B. E. Quigley`), an earlier name they published
    under (`Margaret Petherbridge`), a pen name (`Anna Gram`). A row belongs here when its printed form turns up on more
    than one shelf, or could.
  - Each row has the byline as printed, the person, the kind (`variant`,
    `misspelling`, `former`, `pen`, `house`), a status (`confirmed` or
    `likely`), an optional scope (series, role, dates) for a name that would
    be wrong more widely, an optional Wikidata QID, and a source. Variants and
    misspellings need no source; pen, house and former names, and a handle
    resolved from anything but the outlet's own data, do. `variant` and
    `misspelling` rows rewrite `Author:` and `Editor:`; `former`, `pen` and
    `house` rows only link a name to the person and rewrite nothing. A
    `former` row is only for an earlier name the person doesn't disown, and
    its source shows that; a name they've left behind never gets a row (see
    above).
  - A one-off typo in one file needs no row: correct the name, and `Byline:`
    keeps what was printed. Add a row when the same slip recurs.
  - Names are compared after folding case, accents and punctuation, so
    `erik agard` and `Erik Agard` need no row.
  - The spelling a variant is rewritten to is the one the person uses for
    that name, where they've said; otherwise the fullest form they're most
    often printed with. A `former`, `pen` or `house` row's person is the
    name they use now. Every person a shelf's table names is spelled the way
    the corpus spells them.
  - **When a table changes**: a new or corrected `variant` or `misspelling`
    row and the files it rewrites go in the same MR, and touch only the files
    with that spelling. A `former`, `pen` or `house` row changes no files.
  - Guesses ("may be") stay out. A "likely" row links the names but never
    rewrites `Author:`.
- **What contributors do**: type the byline as printed in `Author:` (or
  `Byline:`), split out the editor, and fix nothing else. Fetching and
  converting never resolve names, so a converter run again over an old source
  archive still gives what was printed.
- **Where names are normalized**: a step of every import, after converting
  and before committing. A fixer applies the tables: it writes the person's
  name in `Author:` and `Editor:`, and puts the printed author credit in
  `Byline:` (a file that already has `Byline:` keeps it). The nightly runs it,
  and so does a contributor's import. Because it runs on files, not sources,
  adding a row later fixes the files already on the shelf too. The MR check
  flags a name a table resolves that a file still has as printed, and lists
  each name no table knows, with any near match ("one letter from Brendan
  Emmett Quigley"), so a typo or a new variant is caught while the source is
  open; add a row, or say so in the MR.

## Identifiers and file names

How a puzzle's xdid, file name and shelf are chosen is defined in
CONTRIBUTING.md, "xdids" and
"Shelving".

## Clues and grid

- **Clues are the publisher's text**, with obvious typos corrected and no
  "[sic]" or other annotations in the clue. **[practice]**
- **Standard numbering.** Clues are numbered by the xd format's rules. If the
  publisher numbered differently, the notes say how, whether by an older
  numbering style or by an editorial error (a number in the wrong square, a
  clue for a number the grid doesn't have, or the reverse). These can
  always be worked out from the grid. **[practice]**
- **A clue with no entry, or an entry with no clue,** is recorded in the notes.
  **[practice]**
- **A clue published blank stays blank.** **[practice]** Some puzzles leave
  clues empty on purpose: the theme entries of a "CLUELESS" or "Beats Me!"
  puzzle, Erik Agard's "DOWNS ONLY" with no Across clues. A note isn't
  needed when the title or theme explains the blanks; text the publisher
  printed about them goes in the notes like any other (see "Notes"). A blank
  clue means the publisher printed none. A clue we don't have is `[XXX]`
  (see "Incomplete puzzles").
  - **Form:** the number, then one space, then the separator:
    `A21. ~ GAMBLERSCARDGAME`. **[proposed]** The 68 blank clues in the corpus (11
    files) are written with two spaces (`A21.  ~ GAMBLERSCARDGAME`), which
    is what `xdfile` writes for an empty clue. xdlint's XD209 flags the two
    spaces, and `xdlint --fix` turns them into the one-space form.
  - **A clue that is a single character** the publisher printed, such as
    `~` or `-`, keeps that character: `A21. ~ ~ GAMBLERSCARDGAME`,
    `A21. - ~ GAMBLERSCARDGAME`. **[practice]** The answer is what follows
    the last ` ~ `, so these don't clash with the blank form (22 files
    have a tilde clue, `A36. ~ ~ TILDE`).
- **More than one set of clues for one grid** (easy and hard, a hint for
  each clue): the second set goes on `^Label:` lines under each clue, as the
  xd v4 spec allows (`A1 ^Hard: ...`). **[practice]**
- **A deliberately asymmetric grid** stays as published. **[practice]**
- **The answers are the solution the puzzle implies, not a copy of an answer
  key.** **[practice]** A published key, even one printed beside the puzzle,
  is one source for the answers, not part of the puzzle. Answers can also
  come from solvers, or from solving the puzzle, and are no less correct for
  it; where they came from goes in receipts, or in the commit message and
  the source archive's `NOTES.md` (for a grid we solved, there's no answer
  file), not in the notes.
  A key letter that its clue and crossings rule out (HOUST for HOUSE) is
  corrected, with a note (see "Notes"): otherwise the answer is lost to
  anyone searching for it, and so is its link to its clue.
- **A square nothing decides.** When both crossing clues allow more than one
  letter and nothing in the puzzle settles it, the square can hold both, as
  a Schrödinger rebus cell (see
  [rebus-conventions.md](rebus-conventions.md)),
  whatever the key says. Recording just one possible answer is also
  acceptable. **[practice]**

## Notes

The spec's free-form final section (Section 4) holds the notes. Some imports
use a `Notes:` header instead. **[practice]** Section 4 is preferred, and is an
open question for the corpus.

- **A one-line editorial note goes in a `Notes:` header:** a sentence from
  the contributor saying why a header differs from the page, such as a
  corrected number or date ("Printed as No. 155, a misprint: this is No.
  156."), or a number given to a puzzle printed without one. Text printed
  with the puzzle, and longer notes, go in Section 4. **[proposed]**

What goes in the notes: **[practice]**

- Text published with the puzzle: instructions, the theme or meta
  explanation, an introduction, a subtitle, a clue with no entry, a blank clue
  that is the joke.
- A correction to an answer or grid letter the publisher got wrong: what
  was published, when, and what it became. For example: "The answer key for
  this puzzle, printed in the December 25, 1926 issue, gave 17 Across as RE
  (and so 2 Down as EMEERS), presumably in error."
- Errata the outlet or author published for the puzzle, quoted, with their
  date, and whether they have been made in this file, including errata that
  say the puzzle can't be solved as published. Errata that only fix a clue
  typo can instead be applied quietly, like any typo fix (see
  CONTRIBUTING.md, "Editing puzzles already in
  the corpus").
- How something the format can't express was represented: renumbered clues,
  marked squares turned into blocks or rebus cells.
- For a picture clue, what the picture showed. This can also go in the clue
  text.

What does not go in the notes:

- Where the puzzle came from and how it was made: download details, OCR
  caveats, who found the answers, review history, credit for whoever typed
  or converted the puzzle ("Litzed by ..."). These go in receipts and
  the source archive's `NOTES.md`.
- Fixes to our own copy (transfer damage, a better scan, a redownload,
  markup), typo fixes in clue text, and a bare notice that the puzzle was
  updated, with no errata. These are recorded in git (see "Principles").
- Things published near the puzzle that aren't part of it: prize and payment
  notices, advertisements.

## Incomplete puzzles

- **No answers.** Unknown answer squares are `.`. **[established]** Puzzles
  without answers are welcome; a missing answer key doesn't stop an import.
- **A missing clue** is filed as our `[XXX]` placeholder, not held back
  (30 files). **[practice]** Say in the notes what is missing. Never leave
  it blank: a blank clue means the publisher printed none (see "Clues and
  grid").
- **A puzzle known to exist but not found** is a stub (see
  CONTRIBUTING.md, "Stubs"). **[proposed]**
- **Placeholder answers are filled in.** A contest puzzle released with its
  answers withheld (WSJ's contest grids since about 2023 are redacted to a
  single letter) gets its real answers as soon as they're known: from the
  outlet's answer release, a later copy of the puzzle, or solving it (see
  "Clues and grid"). A placeholder is never the intended final state. If
  the answers are already known when the puzzle is imported, file the
  solved grid directly. **[practice]**

## Scope

Which puzzles we collect is in [COLLECTION.md](COLLECTION.md).

## Open questions

- **Feature and sub-series names.** A recurring feature's name that is
  distinct from the puzzle's title (GAMES's "World's Most Ornery Crossword")
  has no home yet. `Category:` is the nearest existing header (about 4,300
  files use it). **[proposed]**
- **Date titles from the outlet.** Many shelves arrive titled with the
  outlet's name and a date: about 23,000 `nytimes/` files (`NY Times, ...`)
  and about 5,000 `latimes/` files. Should the outlet's name be taken out
  and the date put in the form above? Under principle 2 the headings are
  the publisher's, so this is right only where the outlet's name was added
  by a downloader rather than printed with the puzzle; until that is
  checked shelf by shelf, it is not a rule yet.
- **`Notes:` header or Section 4.** About 2,600 files use a `Notes:` header,
  because `puz2xd` writes a `.puz` file's notes there and `xdfile.py` lists
  `notes` as a known header. Section 4 is preferred, except for a one-line
  editorial note (see "Notes"). If Section 4 is standard, the
  converters change for new files, and existing files get a header sweep in a
  separate MR.
- **Puzzles revised in place.** An outlet whose archive serves only the
  rewritten text under the original date (for example Daily Pop). The
  proposed `Text-As-Of:` header is xdformat issue 16. "Versions of a puzzle"
  covers a revision only when both captures exist.
- **Backfilling people's names.** Applying "People's names" to existing files
  changes `Author:` or `Editor:` in a few thousand files (by crossref's
  2026-09 count), adding `Byline:` where `Author:` changes. It goes shelf by
  shelf, each shelf's table and files in one MR, starting with Puzzmo (gxd
  !417). crossref's alias list (about 630 rows: 494 seen on one shelf only,
  129 on several) is the starting point for the rest; its one-shelf rows go
  to shelf tables, and its others to the corpus's table. Its married and
  maiden name rows become `former` rows, which rewrite nothing.
- **Related xdformat issues** (the format's open design questions; check them
  for the latest): [16, `Text-As-Of:`](https://github.com/century-arcade/xdformat/issues/16),
  [11, a `Byline:` field](https://github.com/century-arcade/xdformat/issues/11),
  [12, rebus and quantum cells](https://github.com/century-arcade/xdformat/issues/12),
  [13, cells whose correct answer is empty](https://github.com/century-arcade/xdformat/issues/13).
