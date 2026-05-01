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

### 3a. Single-letter Schrödinger pairs

Each `<a>/<b>` cell is genuinely ambiguous — it can be read as either letter `<a>` or letter `<b>` in any direction. The puzzle is constructed so that every clue that crosses a rebus cell yields a valid word with either choice. The themed slot itself typically has **two** valid answers (one per letter set), and both answer the same clue.

**Example: [`gxd/newyorker/2023/tny2023-07-14.xd`](../gxd/newyorker/2023/tny2023-07-14.xd)** — "A Freudian Puzzle":

```
Rebus: 1=C/P 2=I/E 3=G/N 4=A/I 5=R/S

LEIS#12345#SOUR
ART#ARCED#FUMED

A37. Cigar, to a Freudian ~ C/PI/EG/NA/IR/S
D9.  RadioShack feature   ~ CAPITALR/S
```

- A37 (across, 5 rebus cells `12345`) has two valid readings: **CIGAR** (using left halves `C-I-G-A-R`, the literal reading) and **PENIS** (using right halves `P-E-N-I-S`, Freud's punchline). Both answer the clue.
- Every down clue that crosses A37 must work with **either** letter at the rebus cell — that's the structural condition that lets the across Schrödinger resolve either way.
- D9 ends at cell `5` (`R/S`) and is one of those crossings; its declared `CAPITALR/S` similarly embeds both halves, and the answer reads either way at the rebus cell.
- A37's declared answer `C/PI/EG/NA/IR/S` is the **inline form**: each rebus cell appears as its full `<a>/<b>` literally, and the reader extracts whichever reading they're after.

### 3b. Directional multi-letter pairs (traditional quantum)

The traditional quantum pattern: an `<a>/<b>` cell reads as multi-letter `<a>` going one way and multi-letter `<b>` going the other. The convention puts the across half first (`<across>/<down>`); the orderings can flip cell-by-cell so each direction's word works out. **Each clue has a single fixed answer** — only one half yields a real word in each direction. Unlike §3a, the cell is *not* ambiguous: across and down each pin down their own reading. The two halves are themed (a name, a candy bar, an antonym pair).

**Example: [`gxd/nytimes/2024/nyt2024-01-18.xd`](../gxd/nytimes/2024/nyt2024-01-18.xd)** — Vivien Leigh:

```
Rebus: 1=IE/EI 2=EI/IE 3=EI/IE 4=IE/EI 5=EI/IE 6=IE/EI 7=EI/IE 8=IE/EI

VIV1NL2GH#TWINS
...

A17. Actress who portrayed Scarlett O'Hara and Blanche DuBois ~ VIVIE/EINLEI/IEGH
D4.  What Columbus thought he'd reached in 1492          ~ THIE/EINDEI/IES
```

- A17 (across, 9 cells `VIV1NL2GH`) is **VIVIENLEIGH**: cell `1` contributes `IE` (left half of `IE/EI`), cell `2` contributes `EI` (left half of `EI/IE`).
- D4 (down, 7 cells `T-H-1-N-D-3-S`) crosses A17 at cell `1` and is **THEINDIES**: cell `1` contributes `EI` (right half of `IE/EI`), cell `3` contributes `IE` (right half of `EI/IE`).
- The same grid cell is read `IE` across (the IE in `VIVIEN`) and `EI` down (the EI in `THEINDIES`). The slash-pair encodes direction, not choice.
- The half-orderings flip cell-by-cell (`1=IE/EI` but `2=EI/IE`) precisely so the across word works in every across slot and the down word works in every down slot.
- The declared answers `VIVIE/EINLEI/IEGH` and `THIE/EINDEI/IES` are inline forms — they embed both halves at every rebus cell; the reader extracts the directional letters. The actual answers are `VIVIENLEIGH` and `THEINDIES`, each fixed for its direction.

**Example: [`gxd/nytimes/2025/nyt2025-09-21.xd`](../gxd/nytimes/2025/nyt2025-09-21.xd)** — "Gimme a Break!":

```
Rebus: 1=KIT/KAT 2=KIT/KAT 3=KIT/KAT 4=KIT/KAT 5=KIT/KAT

A23. Traditional form of Japanese drama                    ~ KABUKIT/KATHEATER
D18. Regular at a park with half-pipes, informally         ~ SKIT/KATERAT
```

Every rebus cell is `KIT` across and `KAT` down. A23 = **KABUKITHEATER** (kabuki theater); D18 (which crosses A23 at cell `1`) = **SKATERAT** (skate rat). The other across rebus answers — `WRECKITRALPH`, `TIKITORCHES`, `TESTKITCHEN`, `FOSTERKITTEN` — all use `KIT`; the other down rebus answers — `TONKATSU`, `LOOKATMENOW`, `MEERKATS`, `SNEAKATTACK` — all use `KAT`. Each clue has one answer.

**Example: [`gxd/nytimes/2025/nyt2025-08-27.xd`](../gxd/nytimes/2025/nyt2025-08-27.xd)** — UP/DOWN theme:

```
Rebus: 1=UP/DOWN 2=UP/DOWN 3=UP/DOWN 4=UP/DOWN

A18. "Anything sounds good to me"  ~ IMUP/DOWNFORWHATEVER
D3.  One end of the day            ~ SUNUP/DOWN
```

Across reading uses `UP`, down reading uses `DOWN`. A18 = **IMUPFORWHATEVER**; D3 (crossing A18 at cell `1`) = **SUNDOWN**. Several across answers (`BUTTONUP`, `GOBBLEUP`, `GOINGUPINFLAMES`) and down answers (`SUNDOWN`, etc.) are real phrases on both their themed halves, but each clue still has a single fixed answer determined by direction.

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

### 3d. Directional length-asymmetric pairs

A directional pattern (like §3b) where the two halves have **different lengths**. The across reading uses one expansion and the down reading uses the other; each clue has one fixed answer. The "wit" is typically that the two halves sound the same or otherwise relate phonetically.

**Example: [`gxd/nytimes/2025/nyt2025-01-02.xd`](../gxd/nytimes/2025/nyt2025-01-02.xd)** — "PH/F" phonetic theme:

```
Rebus: 1=PH/F

A1. First in a series ~ ALPH/FA
D3. Worn at the edges ~ PH/FRAYED
```

Every rebus cell is `PH` across and `F` down. A1 = **ALPHA** (`AL` + `PH` + `A`, 5 letters in 4 cells); D3, which crosses A1 at cell `1`, = **FRAYED** (`F` + `RAYED`, 6 letters in 6 cells). The puzzle's quip — `WHYISNTTHEWORD … PHONETICALLY … SPELLEDWITHANF` — is the giveaway: across answers are "spelled with PH," down answers with F, and the two are phonetically interchangeable. Other across rebus answers all use `PH` (`IPHONE`, `PHOTO`, `PHONETICALLY`); other down rebus answers all use `F` (`FELTS`, `FUTON`, `FILIPINO`, `AFRAIDSO`, `DWARF`, `HALF`, `ELF`).

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

| Puzzle | Rebus | Declared answer | Intended reading |
|---|---|---|---|
| Vivien Leigh | `1=IE/EI`       | `VIVIE/EINLEI/IEGH` (A17)        | `VIVIENLEIGH` (across) |
| Vivien Leigh | `1=IE/EI`       | `THIE/EINDEI/IES`   (D4)         | `THEINDIES`   (down)   |
| Freudian     | `1=C/P 2=I/E …` | `C/PI/EG/NA/IR/S`   (A37)        | `CIGAR` or `PENIS` (Schrödinger across — both readings answer the clue) |
| Freudian     | `1=C/P`         | `C/PRIMPING`        (D37)        | `CRIMPING` or `PRIMPING` (Schrödinger down — both spellings work at the rebus cell) |
| KIT/KAT      | `1=KIT/KAT`     | `KABUKIT/KATHEATER` (A23)        | `KABUKITHEATER` (across) |
| KIT/KAT      | `1=KIT/KAT`     | `SKIT/KATERAT`      (D18)        | `SKATERAT`    (down)   |
| UP/DOWN      | `1=UP/DOWN`     | `IMUP/DOWNFORWHATEVER` (A18)     | `IMUPFORWHATEVER` (across) |
| UP/DOWN      | `1=UP/DOWN`     | `SUNUP/DOWN`        (D3)         | `SUNDOWN`     (down)   |
| T/W          | `1=T/W`         | `T/WEENSY`, `NEW/T`              | `TEENSY`/`WEENSY` (Schrödinger across), and `NEWT` (multi-letter down) |

The reader is expected to extract a reading by taking the appropriate half of each `<a>/<b>` chunk. Whether *both* halves are valid readings of the same clue depends on the puzzle's pattern: §3a (Freudian) and §4 (the `|`-disambiguated puzzle) are genuinely Schrödinger — each cell is ambiguous, and both readings answer the clue. §3b (VIVIEN, KIT/KAT, UP/DOWN) is directional — each clue has just one valid answer, and the inline form is purely a notational quirk that writes both halves anyway.

### Problems with the inline form

The inline convention has two serious problems and one minor one:

1. **It mangles the actual words.** `C/PI/EG/NA/IR/S` is just unreadable to a human and to any tooling that wants to operate on words. The puzzle's actual answers — `CIGAR` and `PENIS` — appear nowhere in the file as searchable strings.
2. **It defeats text-based corpus analysis.** Word-frequency studies, search-by-answer, "what's the most common 5-letter answer at A37?", etc. all break because the actual words have been spliced together with `/`s and adjacent fragments. Looking for `CRIMPING` in the corpus will not find `C/PRIMPING`.
3. **It's ambiguous w.r.t. literal slashes.** The literal-`/` rebus puzzles (§2) put `/` in answers as data; this inline convention puts `/` in answers as syntax. A parser can't tell them apart without consulting the `Rebus:` header.

### A clearer alternative

Each clue's declared answer should hold the *answer* — a whole, recognizable word. For directional puzzles (§3b) that's just one word per clue:

```
A17. Actress who portrayed Scarlett O'Hara… ~ VIVIENLEIGH
D4.  What Columbus thought he'd reached in 1492 ~ THEINDIES
A23. Traditional form of Japanese drama       ~ KABUKITHEATER
D18. Regular at a park with half-pipes…       ~ SKATERAT
```

For genuine Schrödinger clues (§3a, §4 — two valid answers in the same slot) the natural form lists both with an explicit operator:

```
A37. Cigar, to a Freudian    ~ CIGAR / PENIS
D37. Styling one's hair, say ~ CRIMPING / PRIMPING
A17. Only Monopoly railroad… ~ SHORTLINE / CHORTLING
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
| `<a>/<b>` Schrödinger or directional (§3a–§3d)          | 19       | `tny2023-07-14` (Schrödinger), `nyt2024-01-18` / `nyt2025-09-21` / `nyt2025-08-27` (directional multi-letter), `nyt2025-09-11` (asymmetric), `nyt2025-01-02` (directional length-asymmetric), etc. |
| `<a>/<b\|c>` explicit asymmetric (uses `\|`)            | 1        | `nyt2021-11-04` |
| Multiple clues at same position                         | 1        | `nyt2021-11-04` |

---

## 7. Open questions for the spec

1. **What does `/` mean in a `Rebus:` value?** The corpus uses it for at least four overlapping things — single-letter Schrödinger (§3a), directional multi-letter pairs (§3b), asymmetric Schrödinger/rebus combos (§3c), and directional length-asymmetric pairs (§3d). A formal spec needs to either:
   - pick one and require puzzles to conform; or
   - define a richer notation that makes the differences explicit (e.g. `|` vs `/` cleanly separated; perhaps `()` for grouping).

2. **What does `|` mean?** It appears in only one puzzle (`nyt2021-11-04`) as an explicit Schrödinger marker. If formalized, it would distinguish "either letter" (`S|E`) from "both letters concatenated" (`SE`).

3. **How does empty-half escape work?** `1=/` is the literal slash character in three corpus puzzles. The simplest rule — *a single `/` with non-empty halves is an operator; otherwise it's literal* — handles this without breaking existing files.

4. **Are inline answer forms sanctioned?** Declared answers like `VIVIE/EINLEI/IEGH` are common but undocumented. They make text-based corpus analysis effectively impossible — the actual words don't appear as searchable strings. Strong recommendation: deprecate the inline form in favor of `~ READING` for directional puzzles (one fixed answer per clue) and `~ READING_A / READING_B` (or `~ READING_A | READING_B`) only for genuine Schrödinger clues, where each side is a real word. See [§5](#5-inline-answer-forms-and-why-they-should-probably-go-away).

5. **Are multiple clues at the same position legal?** Only one puzzle uses this and only with the explicit `|`-disambiguated convention. If allowed, it should probably be limited to puzzles with at least one Schrödinger cell in the slot (otherwise there's no semantic basis for two different answers).

6. **Direction-asymmetric semantics** (§3c): if the spec keeps the asymmetric pattern, it needs a way to indicate which direction is multi-letter and which is Schrödinger — the `|` convention from §4 is one option, but it would need to be applied consistently.

---

## 8. Suggested rule (one possible formalization)

For discussion, not a recommendation:

> A `Rebus:` value is parsed as follows:
>
> - If the value contains `/` with non-empty halves, the halves are alternative readings. When *both* halves are single letters, the corpus treats them as Schrödinger letter-alternatives valid in either direction (§3a). When *either* half is multi-letter, the corpus treats them as `<across>/<down>` directional expansions with one fixed answer per direction (§3b, §3d). The syntax does not disambiguate these — tooling must rely on the half-length pattern (and on slot length and clue count for the §3c asymmetric case).
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
