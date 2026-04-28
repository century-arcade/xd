# Rebus, Quantum, and Schrödinger Conventions in .xd

## Status

The current spec ([doc/xd-format.md](xd-format.md), v3.0) defines a `Rebus:` header for cells that hold a multi-character or non-standard string:

> Digits, most symbols, and printable unicode characters (if needed) can be used to indicate rebus cells. The 'Rebus' header provides the translation:
>
>     Rebus: 1=ONE 2=TWO 3=THREE

That is the entirety of the spec's coverage. In practice, the gxd corpus (94k+ puzzles) uses the `Rebus:` header with several conventions that go well beyond this — most prominently with `/` and `|` operators that have no defined meaning in the spec, and with declared answers that embed alternate readings inline.

This document catalogues the patterns observed in the corpus, with concrete examples. It is intended as starting material for a spec discussion.

The validator at the project root (`xdlint.py`) currently accepts all of these patterns under a permissive *structural* check; see [§9](#9-what-the-linter-currently-validates).

---

## 1. Standard plain rebus (spec-compliant)

A rebus key expands to a single string, used the same way in both directions.

**Example: [`gxd/nytimes/1955/nyt1955-01-01.xd`](../gxd/nytimes/1955/nyt1955-01-01.xd) — quoted in the spec itself**

```
Rebus: 1=HEART 2=DIAMOND 3=SPADE 4=CLUB

1ACHE#ADAM#2LIL
...

A1. Sadness. ~ HEARTACHE
A10. Mae West stand-by. ~ DIAMONDLIL
D1. Vital throb. ~ HEARTBEAT
```

Cell `1` expands to `HEART` whether the slot is read across or down. The declared answer embeds the expansion inline (`HEARTACHE` = `HEART` + `ACHE`).

**Frequency:** the dominant pattern in the corpus.

---

## 2. Single-character punctuation rebus

Rebus key expands to a single non-letter character (often punctuation or a math symbol). Doesn't conflict with the spec — it's just an unusual choice of expansion.

**Example: [`gxd/avclub/2017/avc2017-11-01.xd`](../gxd/avclub/2017/avc2017-11-01.xd)** — themed "Let's Roll":

```
Rebus: 1=/

TOM#WITHTIMETO1
...

A52. Low-quality ~ CRUMMY
```

Cell `1` is a literal `/` character. The puzzle theme uses literal slashes inside answers.

**Example: [`gxd/nysun/2005/nys2005-12-30.xd`](../gxd/nysun/2005/nys2005-12-30.xd)** — math operators:

```
Rebus: 1=/ 2=* 3=+ 4=-
```

**Spec-implication:** under any rule that makes `/` an operator, `1=/` becomes ambiguous. One way to resolve: treat empty-half cases (`1=/`, `1=|`) as literal characters, with operators only kicking in when both halves are non-empty.

---

## 3. Quantum rebus with `/` — the central undocumented convention

In ~19 corpus puzzles, the rebus value contains a non-trivial `/` (both halves non-empty). This is consistently used to mean "two readings" — but *which* dimension splits the readings varies by puzzle. There are at least four sub-patterns.

### 3a. Directional single-letter

Each `<a>/<b>` cell is read as one letter — `<a>` when traversed across, `<b>` when traversed down. Used when both halves are themed words/phrases that interlock.

**Example: [`gxd/newyorker/2023/tny2023-07-14.xd`](../gxd/newyorker/2023/tny2023-07-14.xd)** — "A Freudian Puzzle":

```
Rebus: 1=C/P 2=I/E 3=G/N 4=A/I 5=R/S

LEIS#12345#SOUR
ART#ARCED#FUMED

A37. Cigar, to a Freudian ~ C/PI/EG/NA/IR/S
D9.  RadioShack feature  ~ CAPITALR/S
```

- The five cells, read across, spell **C-I-G-A-R**.
- The five cells, each in its respective down column, spell **P-E-N-I-S** (Freud's punchline).
- A37's declared answer `C/PI/EG/NA/IR/S` is the **inline form**: each rebus cell appears as its full `<a>/<b>` literally, and the reader extracts one direction's letters.
- D9's declared `CAPITALR/S` shows `R/S` for the rebus cell at the bottom of that column; the down reading takes the right half.

### 3b. Themed multi-letter pairs (both readings yield valid words)

Each `<a>/<b>` cell expands to multiple letters in both directions, but the puzzle is constructed so that *both* the across and down readings of a slot yield real English. The convention is essentially: each cell = `<a>` or `<b>`, both readings valid.

**Example: [`gxd/nytimes/2024/nyt2024-01-18.xd`](../gxd/nytimes/2024/nyt2024-01-18.xd)** — Vivien Leigh:

```
Rebus: 1=IE/EI 2=EI/IE 3=EI/IE 4=IE/EI 5=EI/IE 6=IE/EI 7=EI/IE 8=IE/EI

VIV1NL2GH#TWINS
...

A17. Actress who portrayed Scarlett O'Hara and Blanche DuBois ~ VIVIE/EINLEI/IEGH
D23. Ratfink ~ STOOLEI/IE
```

- A17's slot is 9 cells: `VIV1NL2GH`. Substituting cell `1`=IE and cell `2`=EI gives **VIV-IE-NL-EI-GH** = `VIVIENLEIGH` (Vivien Leigh, 11 letters).
- D23's slot ends at cell `1`. Substituting cell `1`=IE gives `STOOLIE`, =EI gives `STOOLEI`. The clue "Ratfink" matches **STOOLIE** (down reading = right half = IE).
- Both A17's declared `VIVIE/EINLEI/IEGH` (16 chars) and D23's `STOOLEI/IE` (10 chars) are inline forms — they document both possible readings literally; the reader extracts the chosen direction's letters.

**Example: [`gxd/nytimes/2025/nyt2025-09-21.xd`](../gxd/nytimes/2025/nyt2025-09-21.xd)** — "Gimme a Break!":

```
Rebus: 1=KIT/KAT 2=KIT/KAT 3=KIT/KAT 4=KIT/KAT 5=KIT/KAT

A23. Traditional form of Japanese drama ~ KABUKIT/KATHEATER
D21. Breaded, fried Japanese pork cutlet ~ TONKIT/KATSU
```

A23's slot reads as either `KABUKIT-HEATER` (kabuki theater) or `KABUKAT-HEATER`; the across reading uses left half = KIT → KABUKIT-HEATER... actually `KABUKI THEATER`, so KIT is correct. D21 takes the right half KAT → TONKATSU.

**Example: [`gxd/nytimes/2025/nyt2025-08-27.xd`](../gxd/nytimes/2025/nyt2025-08-27.xd)** — UP/DOWN theme:

```
Rebus: 1=UP/DOWN 2=UP/DOWN 3=UP/DOWN 4=UP/DOWN

A18. "Anything sounds good to me" ~ IMUP/DOWNFORWHATEVER
A23. Basic couturier offering ~ BUTTONUP/DOWN
```

Both `IMUPFORWHATEVER` and `IMDOWNFORWHATEVER` are colloquial; `BUTTONUP` and `BUTTONDOWN` both refer to shirts. The puzzle's wit is that **both** readings are valid English in every slot.

### 3c. Asymmetric implicit (one direction Schrödinger, other multi-letter)

This is the trickiest pattern: `<a>/<b>` means "either single letter `a` or single letter `b`" in one direction (Schrödinger choice), and "the multi-letter rebus `ab`" in the other direction. **The choice of which direction is which is theme-driven and not encoded in the syntax.**

**Example: [`gxd/nytimes/2025/nyt2025-09-11.xd`](../gxd/nytimes/2025/nyt2025-09-11.xd)**:

```
Rebus: 1=T/W 2=W/T 3=H/D 4=R/D

NAPLES###1EENSY
ELAINE##WENTAPE
2ALKIE#NEEDANAP
##IEDS#ALDA####
BIND#TEST#SUMTO
...

A7.  Minuscule, in cutesy lingo  ~ T/WEENSY
A15. Hand-held communication device ~ W/TALKIE
D1.  Semiaquatic amphibian ~ NEW/T
D7.  Material with a coarse weave ~ T/WEED
```

**A7** (across, slot `1EENSY` = 6 cells): the answer is **TEENSY** *or* **WEENSY** (both fit "minuscule"). Cell `1` reads as a single letter — the across direction is Schrödinger T-or-W.

**D1** (down, slot N-E-`2` = 3 cells): the answer is **NEWT**. For a 4-letter answer to fit a 3-cell slot, cell `2` must contribute *both* letters in the down direction, reading as **WT** (the rebus key `2=W/T` concatenated). The down direction is multi-letter.

**D7** (down, slot `1`-E-E-D = 4 cells): the answer is **TWEED**. Cell `1` reads as **TW** (multi-letter) in the down direction, even though the same cell read as a single letter in across (A7).

**A15** (across, slot `2ALKIE` = 6 cells): the answer is **WALKIE** or **TALKIE** (single-letter Schrödinger across).

So in the *same puzzle*, `<a>/<b>` means one thing across and another thing down, and the difference is detectable only by counting cells against word-length. The `/` syntax doesn't encode which direction is which.

### 3d. Length-asymmetric pairs

`<a>/<b>` where `a` and `b` have different lengths. Each reading uses one (different-length) expansion.

**Example: [`gxd/nytimes/2025/nyt2025-01-02.xd`](../gxd/nytimes/2025/nyt2025-01-02.xd)** — "PH/F" phonetic theme:

```
Rebus: 1=PH/F

A1.  First in a series ~ ALPH/FA
A5.  Pixel rival ~ IPH/FONE
A10. Snap ~ PH/FOTO
A35. Middle of the quip ... and a hint to eight squares in this puzzle ~ PH/FONETICALLY
```

A1's reading is **ALPHA** (using `PH`, 2 letters) *or* **ALFA** (using `F`, 1 letter), and the slot accommodates whichever was chosen. Each cell expands to either `PH` or `F` — Schrödinger between two different-length rebuses, valid in any direction.

---

## 4. Combined `/` and `|` (asymmetric explicit)

Exactly **one** corpus puzzle uses `|` in a Rebus value, and it does so to disambiguate the asymmetric pattern of §3c.

**Example: [`gxd/nytimes/2021/nyt2021-11-04.xd`](../gxd/nytimes/2021/nyt2021-11-04.xd)**:

```
Rebus: 1=SE/S|E 2=S|C/SC 3=E|G/EG 4=GH/G|H 5=A|B/AB 6=A|P/AP 7=NL/N|L 8=TN/T|N
Notes: Each rebus is two letters in one direction, and a quantum letter in the other direction, yielding separate answers with different clues.
```

- The half **without** `|` is the multi-letter rebus reading (e.g. `SE`, `SC`, `EG` …).
- The half **with** `|` is the Schrödinger reading — either letter is valid (e.g. `S|E` means either `S` or `E`).
- The `Notes:` header explicitly explains the convention.

This puzzle is also the only one in the corpus with **multiple clues at the same position**:

```
A17. Only Monopoly railroad whose name doesn't contain "Railroad" ~ SHORTLINE
A17. Laughing gleefully ~ CHORTLING
A40. Setting for "The Sound of Music" ~ AUSTRIA
A40. Greyhound journey ~ BUSTRIP
D11. Web master? ~ SPIDERMAN
D11. Of the outer skin layer ~ EPIDERMAL
```

Both A17 answers are 9-letter words that fit the same across slot, differing where the slot crosses Schrödinger cells (cell `2` reads `S` for SHORTLINE, `C` for CHORTLING; cell `3` reads `E` for SHORTLINE, `G` for CHORTLING). Each clue documents *one* valid reading; the puzzle author lists clues for the readings that form recognized words.

This is the cleanest convention in the corpus, but it's a single puzzle — not enough to call it "the standard."

---

## 5. Inline answer forms (and why they should probably go away)

A recurring auxiliary convention: declared answers **embed the full rebus expansion inline** at each rebus cell, displaying both possible readings. Examples:

| Puzzle | Rebus | Declared answer | Intended reading(s) |
|---|---|---|---|
| Vivien Leigh | `1=IE/EI` | `VIVIE/EINLEI/IEGH`              | `VIVIENLEIGH` |
| Freudian     | `1=C/P 2=I/E …` | `C/PI/EG/NA/IR/S`           | `CIGAR` (across) — letters in the columns spell `PENIS` (down) |
| Freudian     | `1=C/P` | `C/PRIMPING` (D37)               | `CRIMPING` or `PRIMPING` |
| KIT/KAT      | `1=KIT/KAT` | `KABUKIT/KATHEATER`          | `KABUKITHEATER` and `KABUKATHEATER` |
| UP/DOWN      | `1=UP/DOWN` | `IMUP/DOWNFORWHATEVER`       | `IMUPFORWHATEVER` and `IMDOWNFORWHATEVER` |
| T/W          | `1=T/W` | `T/WEENSY`, `NEW/T`              | `TEENSY`/`WEENSY`, and `NEWT` (one direction multi-letter) |

The reader is expected to extract a directional reading by taking the appropriate half of each `<a>/<b>` chunk.

### Problems with the inline form

The inline convention has two serious problems and one minor one:

1. **It mangles the actual words.** `C/PI/EG/NA/IR/S` is just unreadable to a human and to any tooling that wants to operate on words. The puzzle's actual answers — `CIGAR` and `PENIS` — appear nowhere in the file as searchable strings.
2. **It defeats text-based corpus analysis.** Word-frequency studies, search-by-answer, "what's the most common 5-letter answer at A37?", etc. all break because the actual words have been spliced together with `/`s and adjacent fragments. Looking for `CRIMPING` in the corpus will not find `C/PRIMPING`.
3. **It's ambiguous w.r.t. literal slashes.** The literal-`/` rebus puzzles (§2) put `/` in answers as data; this inline convention puts `/` in answers as syntax. A parser can't tell them apart without consulting the `Rebus:` header.

### A clearer alternative

Each clue's declared answer should hold the *answer* — one or more whole, recognizable words separated by an explicit operator. The two natural choices:

```
A37. Cigar, to a Freudian ~ CIGAR / PENIS
D37. Styling one's hair, say ~ CRIMPING / PRIMPING
A17. Actress who portrayed Scarlett O'Hara… ~ VIVIENLEIGH
A23. Traditional form of Japanese drama ~ KABUKITHEATER / KABUKATHEATER
```

…where `~ X / Y` (or `~ X | Y`) means "this clue's slot has reading X *or* reading Y" and each side is a real word. The reader and any downstream tool can then index, grep, count, and compare answers without any rebus-aware parsing.

For asymmetric puzzles (§3c) this is also strictly clearer:

```
A7.  Minuscule, in cutesy lingo  ~ TEENSY / WEENSY
D1.  Semiaquatic amphibian       ~ NEWT
D7.  Material with a coarse weave ~ TWEED
```

The down-direction multi-letter case (`NEWT`, `TWEED`) becomes just an answer; the across-direction Schrödinger case (`TEENSY` / `WEENSY`) shows both alternatives without surgically inserting `/` mid-word.

This convention makes the inline form completely unnecessary, and it removes any conflict between rebus syntax and answer text.

---

## 6. Frequency in the corpus

| Convention | File count | Examples |
|------------|-----------:|----------|
| Plain rebus (`1=ONE`)                                   | hundreds | spec example `nyt1955-01-01` |
| Single-char punctuation rebus (`1=/`, `1=*`, etc.)      | 3        | `avc2017-11-01`, `nys2005-12-30` |
| `<a>/<b>` directional or themed                         | 19       | `tny2023-07-14`, `nyt2024-01-18`, `nyt2025-09-11`, `nyt2025-09-21`, `nyt2025-08-27`, `nyt2025-01-02`, etc. |
| `<a>/<b\|c>` explicit asymmetric (uses `\|`)            | 1        | `nyt2021-11-04` |
| Multiple clues at same position                         | 1        | `nyt2021-11-04` |

---

## 7. Open questions for the spec

1. **What does `/` mean in a `Rebus:` value?** The corpus uses it for at least four overlapping things — directional single-letter, themed multi-letter pairs, asymmetric Schrödinger/rebus combos, and length-asymmetric Schrödinger. A formal spec needs to either:
   - pick one and require puzzles to conform; or
   - define a richer notation that makes the differences explicit (e.g. `|` vs `/` cleanly separated; perhaps `()` for grouping).

2. **What does `|` mean?** It appears in only one puzzle (`nyt2021-11-04`) as an explicit Schrödinger marker. If formalized, it would distinguish "either letter" (`S|E`) from "both letters concatenated" (`SE`).

3. **How does empty-half escape work?** `1=/` is the literal slash character in three corpus puzzles. The simplest rule — *a single `/` with non-empty halves is an operator; otherwise it's literal* — handles this without breaking existing files.

4. **Are inline answer forms sanctioned?** Declared answers like `VIVIE/EINLEI/IEGH` are common but undocumented. They make text-based corpus analysis effectively impossible — the actual words don't appear as searchable strings. Strong recommendation: deprecate the inline form in favor of `~ READING_A / READING_B` (or `~ READING_A | READING_B`), where each side is a real word. See [§5](#5-inline-answer-forms-and-why-they-should-probably-go-away).

5. **Are multiple clues at the same position legal?** Only one puzzle uses this and only with the explicit `|`-disambiguated convention. If allowed, it should probably be limited to puzzles with at least one Schrödinger cell in the slot (otherwise there's no semantic basis for two different answers).

6. **Direction-asymmetric semantics** (§3c): if the spec keeps the asymmetric pattern, it needs a way to indicate which direction is multi-letter and which is Schrödinger — the `|` convention from §4 is one option, but it would need to be applied consistently.

---

## 8. Suggested rule (one possible formalization)

For discussion, not a recommendation:

> A `Rebus:` value is parsed as follows:
>
> - If the value contains `/` with non-empty halves, the halves are read as `<across>/<down>` directional expansions.
> - Within each half (or in a value with no `/`), if `|` separates non-empty parts, those parts are Schrödinger letter-alternatives — any of them is valid in any direction the slot is read.
> - A value where `/` has empty halves on either side (e.g. `1=/`) is the literal value, not an operator.
> - Multiple clues at the same position are legal only when the slot contains at least one Schrödinger cell in that direction.
> - Declared answers contain whole words. When a slot has multiple valid readings, they are listed `~ A / B` (or `~ A | B`). The inline form (rebus expansion embedded inside an answer at each cell) is deprecated.

This is what `xdlint.py` currently checks. It accommodates §1, §2, §3a, §3b, §3d, §4, §5 cleanly. It does *not* enforce §3c's asymmetric-implicit pattern — those puzzles pass only because the validator is permissive about both flat and inline forms structurally; it doesn't try to reason about whether `1=T/W` means single-letter Schrödinger across versus multi-letter `TW` down.

Open: what about `()` for explicit grouping if the spec eventually wants it? Suggested by the user in early discussion, deferred.

---

## 9. What the linter currently validates

`xdlint.py` (project root) checks declared answers against grid cells using a permissive lockstep walk:

- For a plain cell, the declared character must match the grid character.
- For a rebus cell, the declared substring must be *either* the chosen direction's expansion *or* the inline `<across>/<down>` form (provided both halves are single-distinct strings).
- For a Schrödinger cell (multiple `|`-separated alternatives), any alternative matches.

This passes all 20+ corpus puzzles using these conventions but is **structural only** — it does not verify that the chosen reading produces a real word, nor that "across uses left half" is consistent with "down uses right half." The asymmetric-implicit puzzles of §3c pass because the inline form parses structurally regardless of whether the puzzle's actual semantic interpretation is single-letter-across-multi-letter-down or vice versa.

The linter rules involved:
- `XD002` — unrecognized grid character (rebus key not in `Rebus:` header)
- `XD003` — `Rebus:` key declared but never used in grid
- `XD004` — clue position has no corresponding slot in grid
- `XD005` — clue position count mismatch (counts distinct positions, not total clues, to accommodate Schrödinger duplicates)
- `XD006` — declared answer length mismatch
- `XD007` — declared answer letters disagree with slot
- `XD008` — duplicate clue position (allowed when the slot contains a Schrödinger cell in that direction)

If/when the spec formalizes any of the patterns in this document, the linter should be tightened to enforce it.
