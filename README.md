# .xd futureproof crossword format

.xd is a corpus-oriented format, modeled after the simplicity and intuitiveness of the markdown format.  It supports 99.99% of published crosswords, and is intended to be convenient for bulk analysis of crosswords by both humans and machines, from the present and into the future.

## xdfile.py

  * `xdfile.py` has a simple parser for .xd files with example code that
answers some simple queries, like "what is the most used grid in this .zip of .xd files?"

  * `puz2xd.py` will convert Across-Lite .puz format to .xd.  Scripts to convert other formats are also in `src/`.

## Full Example

This is the oldest rebus crossword from the New York Times (found by `grep -r Rebus crosswords/nytimes | sort`), available thanks to the huge effort of the [Pre-Shortzian Puzzle Project](http://www.preshortzianpuzzleproject.com/):

    Title: New York Times, Saturday, January 1, 1955
    Author: Anthony Morse
    Editor: Margaret Farrar
    Rebus: 1=HEART 2=DIAMOND 3=SPADE 4=CLUB
    Date: 1955-01-01


    1ACHE#ADAM#2LIL
    BLUER#GULL#MATA
    EATIN#APEX#ICER
    ATAR#TILE#SNEAK
    TEN#MANI#ITE###
    ##DRUB#CANASTAS
    FADED#BAGGY#OIL
    ONES#KATES#TUNA
    ETA#JOKER#JORUM
    SILLABUB#SOON##
    ###ACE#RUIN#ARK
    3WORK#JINX#4MAN
    BIRD#WADS#SCENE
    ISLE#EDGE#PANEL
    DEER#BEET#ARTEL


    A1. Sadness. ~ HEARTACHE
    A6. Progenitor. ~ ADAM
    A10. Mae West stand-by. ~ DIAMONDLIL
    [...]

    D1. Vital throb. ~ HEARTBEAT
    D2. Having wings. ~ ALATE
    D3. Start the card game. ~ CUTANDDEAL
    [...]

## Format specification

The .xd format is a simple UTF-8 text file, and can often be 7-bit ASCII clean.

Sections are delineated by two or more blank lines (3 consecutive newlines
(0x0A)).  Subsections are delineated by a single blank line.

### Headers (Section 1)

The first section is a set of key:value pairs, one per line.  Title, Author,
Editor, Copyright, and Date are the standard headers.  Other headers describing
the puzzle semantics are given below.  Additional headers are allowed but will
be ignored.  Multiple entries with the same key are not allowed.

### Grid (Section 2)

Optional leading whitespace and trailing whitespace on each line.  Never any
whitespace between characters in a grid line.

One line per row.  One UTF-8 character per cell.

Uppercase A-Z refer to that letter in the solution; a '#' is a block.  In a few
puzzles, '\_' means a space or non-existing block (usually on the edges), and '.' would
be used for an empty cell (e.g. a partial solution).

Lowercase a-z indicate Special cells. The 'Special' header indicates whether
those cells are "shaded" or have a "circle".

    Special: shaded

Digits, most symbols, and printable unicode characters (if needed) can be used
to indicate rebus cells.  The 'Rebus' header provides the translation:

    Rebus: 1=ONE 2=TWO 3=THREE

Lowercase letters always indicate Special cells if there is a Special header.
If a puzzle has cells that are both Special and Rebus, a lowercase letter
should be used, and set to its value in the Rebus header.

### Clues (Section 3)

A leading uppercase letter indicates the group the clue is in. 'A' or 'D'
indicate Across or Down; the full heading for other letters would be specified
in the 'Cluegroup' header.  For uniclues, the cluegroup letter is omitted.

The clues should be sorted, with a single newline separating clue groups (Across and Down).

Minimal markup is available.  An example clue line:

    A51. {/Italic/}, {*bold*}, {_underscore_}, or {-strike-thru-} ~ MARKUP

The clue is separated from the answer by a tilde with spaces on both sides (' ~ ').

The full answer should be provided, including rebus expansion.  [This makes clue/answer lines independently useful.]

The backslash ('\\') is used as a line separator in the rare case of a multi-line clue.

### Notes (Section 4)

The free-format final section can contain any amount of notes.


