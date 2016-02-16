# .xd futureproof crossword format

.xd is a corpus-oriented format, modeled after the simplicity and intuitiveness of the markdown format.  It supports 99.99% of published crosswords, and is intended to be convenient for bulk analysis of crosswords by both humans and machines, from the present and into the future.

## xdfile.py

  * `xdfile.py` has a simple parser for .xd files with example code that
answers some simple queries, like "what is the most used grid in this .zip of .xd files?"

  * `puz2xd.py` will convert Across-Lite .puz format to .xd.  Scripts to
convert other formats would be welcome.

## Full Example

This is the oldest rebus crossword from the New York Times (found by `grep -r Rebus crosswords/nytimes | sort`), available thanks to the huge effort of the [Pre-Shortzian Puzzle Project](http://www.preshortzianpuzzleproject.com/):

    Title: New York Times, Saturday, January 1, 1955
    Creator: Anthony Morse
    Contributor: Margaret Farrar (Editor)
    Rebus: 1=HEART,2=DIAMOND,3=SPADE,4=CLUB

    Publisher: New York Times
    Date: 1955-01-01
    Type: Crossword Puzzle
    Language: en-US

    Source: http://www.xwordinfo.com/PS?date=1/1/1955
    Source: http://www.nytimes.com/svc/crosswords/v2/puzzle/daily-19550101.puz


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
    A14. Ultramarine plus. ~ BLUER
    A15. Sea bird. ~ GULL
    A16. ___ Hari. ~ MATA
    A17. Stay home for dinner. ~ EATIN
    A18. Peak. ~ APEX
    A19. Deep freeze. ~ ICER
    A20. Ralph Rackstraw, for instance. ~ ATAR
    A21. Scrabble adjunct. ~ TILE
    A22. A lead from a singleton. ~ SNEAK
    A23. Lowest honor. ~ TEN
    A24. Peanut: Spanish. ~ MANI
    A25. Native of: Suffix. ~ ITE
    A26. Administer a sound defeat. ~ DRUB
    A28. Card games and Spanish baskets. ~ CANASTAS
    A33. Matched the bet. ~ FADED
    A35. Unpressed. ~ BAGGY
    A36. Product of 35 Down. ~ OIL
    A37. Aces. ~ ONES
    A38. Greenaway and Hardcastle. ~ KATES
    A39. Bluefin. ~ TUNA
    A40. Greek letter. ~ ETA
    A41. High card in euchre. ~ JOKER
    A42. Large drinking bowl. ~ JORUM
    A43. Frothy mixture of wine and cream. ~ SILLABUB
    A45. Before long. ~ SOON
    A46. Handy card to have. ~ ACE
    A47. Down, vulnerable, doubled and redoubled. ~ RUIN
    A49. Where Orval Fabus is Governor: Abbr. ~ ARK
    A52. Preliminary labor. ~ SPADEWORK
    A55. The Indian sign. ~ JINX
    A56. Gentleman about town. ~ CLUBMAN
    A57. Quetzal. ~ BIRD
    A58. Plugs. ~ WADS
    A59. Embarrassing argument. ~ SCENE
    A60. Sark or Man. ~ ISLE
    A61. Slight advantage. ~ EDGE
    A62. Popular type of TV show. ~ PANEL
    A63. Mouse ___, a chevrotain. ~ DEER
    A64. Borsch ingredient. ~ BEET
    A65. Russian cooperative. ~ ARTEL

    D1. Vital throb. ~ HEARTBEAT
    D2. Having wings. ~ ALATE
    D3. Start the card game. ~ CUTANDDEAL
    D4. Eldest son. ~ HEIR
    D5. Sea bird. ~ ERN
    D6. On the other hand. ~ AGAIN
    D7. When North and South battle East and West. ~ DUPLICATEBRIDGE
    D8. Sheltered. ~ ALEE
    D9. Six years before the Battle of Hastings. ~ MLX
    D10. Kimberley works. ~ DIAMONDMINES
    D11. Rose point. ~ LACE
    D12. Virginia willow. ~ ITEA
    D13. A gay old time. ~ LARK
    D21. The score. ~ TAB
    D22. Time spent in a place. ~ STAY
    D24. Child's pie mix. ~ MUD
    D25. Noun suffixes. ~ INGS
    D27. Legal matter. ~ RES
    D29. Teen-___. ~ AGER
    D30. Masters' contest. ~ TOURNAMENT
    D31. Hokkaido inhabitant. ~ AINU
    D32. Bridge triumph. ~ SLAM
    D33. Hatfields to the McCoys. ~ FOES
    D34. Against. ~ ANTI
    D35. Azerbaijan port. ~ BAKU
    D38. Honshu port. ~ KOBE
    D39. Very. ~ TOO
    D41. High, low, ___ and the game. ~ JACK
    D42. Short for a man's name. ~ JON
    D44. Food supply. ~ LARDER
    D45. Number of tricks in a book. ~ SIX
    D48. Loose. ~ UNSET
    D50. Indian princess. ~ RANEE
    D51. Mournful sound. ~ KNELL
    D52. Highest suit call in bridge. ~ SPADEBID
    D53. Prudent. ~ WISE
    D54. Border of an escutcheon. ~ ORLE
    D55. Green. ~ JADE
    D56. Commuters' card room. ~ CLUBCAR
    D58. Entanglement. ~ WEB
    D59. Resort. ~ SPA

## Format specification

The .xd format is a simple UTF-8 text file, and can often be 7-bit ASCII clean.

Sections are delineated by two or more consecutive newlines (0x0A).  Subsections are delineated by one blank line.

### Headers (Section 1)

The first section is a set of key:value pairs, one per line.  Standard metadata
descriptors from the [Dublin Core](http://dublincore.org/documents/dces/) are
preferred.

Multiple entries with the same key are allowed.

Additional subsections indicate lesser exposed metadata.  The first level is Public, the
second level is Machine, the third level is Internal.

### Grid (Section 2)

Optional leading whitespace and trailing whitespace on each line.  Never any
whitespace between characters in a grid line.

One line per row.  One UTF-8 character per cell.

Uppercase A-Z refer to that letter in the solution; a '#' is a block.  In a few
puzzles, '\_' is a non-existing block (on the edges), and '.' would be used for
an empty cell (e.g. a partial solution).

Lowercase a-z indicate Special cells. The 'Special' header indicates whether
those cells are "shaded" or have a "circle".

    Special: shaded

Digits, most symbols, and printable unicode characters (if needed) can be used
to indicate rebus cells.  The 'Rebus' header provides the translation:

    Rebus: 1=ONE,2=TWO,3=THREE

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

The full answer should be provided, including rebus expansion.

The backslash ('\\') is used as a line separator in the rare case of a multi-line clue.

### Notes (Section 4)

The free-format final section can contain any amount of notes.


