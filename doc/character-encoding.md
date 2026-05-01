# Character Encoding Oddities in .xd

## Status

The .xd format spec ([doc/xd-format.md](xd-format.md)) declares the file is "a simple UTF-8 text file, and can often be 7-bit ASCII clean." In practice, the gxd corpus (94k+ puzzles, ingested over years from multiple sources) contains a small fraction of files with byte-level artifacts from at least five different upstream encodings. None of them are inherent to .xd itself — they were inherited from the source .puz / .ipuz / PDF files and propagated through legacy converters.

This document catalogues the patterns observed, the diagnostics that distinguish them, and the cleanup pipeline that handles each. It exists because we hit every one of these patterns at least once during a single review pass and had to figure them out from scratch.

The two relevant tools:

- [`xdfile/puz2xd.py`](../xdfile/puz2xd.py) `decode()` — runs at conversion time on every clue/header pulled out of a .puz file. The shared utility lives in [`xdfile/utils.py`](../xdfile/utils.py).
- [`xdlint.py`](../xdlint.py) rules `XD009` (latin-1 misread of UTF-8) and `XD010` (C1 control [mojibake](https://en.wikipedia.org/wiki/Mojibake)) — run at lint time over .xd files already on disk.

Both implementations are kept in lockstep with each other and with the standalone [`puz2xd-standalone.py`](../puz2xd-standalone.py).

---

## 1. The fundamental problem: bytes 0x80–0x9F

`.puz` files declare their string encoding in a version flag: pre-v1.4 puzzles are ISO-8859-1 (latin-1); v1.4+ may be UTF-8. In ISO-8859-1, bytes 0x80–0x9F decode to **C1 control codepoints** (U+0080–U+009F) — a band of unassigned/control characters that have no meaning in printable text.

Publishers, however, regularly used those byte slots for printable characters from whichever 8-bit encoding their tooling actually produced (cp1252 on Windows, Mac Roman on Mac, cp437 on DOS-era systems). When puzpy honors the file's declared latin-1 encoding, those bytes survive the trip into Python as literal U+0080–U+009F characters, which then sit untouched in any .xd produced by a naive converter.

So *every* C1 control codepoint in our corpus is mojibake. The question is just which encoding produced the byte.

---

## 2. The encoding families observed

| Family | Where it appears | Diagnostic |
|---|---|---|
| **cp1252 (Windows-1252)** | Most common — em dashes, smart quotes, š, Š, ž | C1 byte means a typography char (U+2014 em dash, U+201C/D curly quotes, …) |
| **Mac Roman** | Older publisher feeds (NYTimes, Boston Globe, King Syndicate) | C1 byte means an accented vowel — most consistently `0x8E = é` |
| **cp437 (DOS)** | Old Newsday <2002, NYSun 2007, SimonSchuster <2005, NYT 1990s | C1 byte means an accented vowel via DOS code page (0x82 = é, 0x89 = ë) |
| **UTF-8 misread as latin-1** | Various Reagle (Philadelphia), Universal Crossword, NYT 2013+ | Multi-character runs like `Ã©` (= `é`), `Ãª` (= `ê`), `â` (= `"`) |
| **PDF Symbol font** | Boston Globe 2009-2013 math clues | Non-standard: byte 0x80 = `°`, byte 0x98 = `÷` (no encoding maps this) |

---

## 3. cp1252 — the default

The vast majority of C1-control mojibake comes from cp1252. The fixer [`xdlint.py`](../xdlint.py) `XD010` defaults to this mapping; the same logic lives in [`xdfile/utils.py`](../xdfile/utils.py) `clean_c1_controls()`.

Reference table for the C1 range in cp1252 (the slots marked `—` are undefined and pass through unchanged):

| Byte | Char | Notes | Byte | Char | Notes |
|--:|:--|---|--:|:--|---|
| 0x80 | € | euro / often ambiguous | 0x90 | — |   |
| 0x81 | — |   | 0x91 | ' | left single quote |
| 0x82 | ‚ | low single quote | 0x92 | ' | right single quote |
| 0x83 | ƒ |   | 0x93 | " | left double quote |
| 0x84 | „ | low double quote | 0x94 | " | right double quote |
| 0x85 | … | ellipsis | 0x95 | • | bullet |
| 0x86 | † | dagger | 0x96 | – | en dash |
| 0x87 | ‡ | double dagger | 0x97 | — | em dash |
| 0x88 | ˆ |   | 0x98 | ˜ | small tilde |
| 0x89 | ‰ | per mille | 0x99 | ™ | trademark |
| 0x8A | Š |   | 0x9A | š |   |
| 0x8B | ‹ |   | 0x9B | › |   |
| 0x8C | Œ |   | 0x9C | œ |   |
| 0x8D | — |   | 0x9D | — |   |
| 0x8E | Ž | **see §4** | 0x9E | ž |   |
| 0x8F | — |   | 0x9F | Ÿ |   |

For codepoints undefined in cp1252 (0x81, 0x8D, 0x8F, 0x90, 0x9D), the fixer leaves the codepoint intact rather than guessing — `XD010` still emits the finding so the user can review.

---

## 4. Mac Roman: the U+008E exception

cp1252 says `0x8E = Ž` (Latin capital Z with caron, used in Slavic loanwords). Mac Roman says `0x8E = é`. **Every U+008E in our corpus is `é`, not `Ž`** — Cézanne, José, risqué, Gérard, Cité, entrée. Six confirmed cases, zero exceptions.

The fixer hard-codes this as `_CP1252_OVERRIDES[chr(0x8E)] = "é"`. This is the only codepoint where we override cp1252 systematically.

Other Mac Roman vowels (0x87 = á, 0x88 = à, 0x9A = ö, etc.) overlap less catastrophically with cp1252's Slavic letters and special chars (š, Š, ž), and the cp1252 default tends to produce the right answer there. The XD010 finding message lists the Mac Roman candidate alongside cp1252 so the user can spot exceptions.

---

## 5. cp437/DOS: the older publishers

Some older publisher feeds (Newsday late-1990s/early-2000s, NYSun 2007, SimonSchuster 2003-2004, NYT 1990s, NYT 2009 stragglers) came from a DOS-era pipeline where bytes 0x80–0x9F follow code page 437 — accented vowels at slots that cp1252 reserves for typography:

| Byte | cp1252 | cp437 | Likely intent |
|--:|:--|:--|---|
| 0x82 | ‚ | é | **almost always é in this corpus** |
| 0x83 | ƒ | â | â (rare but seen in `grâce`) |
| 0x85 | … | à | à (Pietà) — but also legit ellipsis cases |
| 0x86 | † | å | seen as `á` in `González` (so likely a different mojibake path) |
| 0x87 | ‡ | ç | cases inconsistent — saw a `Pietà` where it should have been à |
| 0x89 | ‰ | ë | ë (Zoë) |
| 0x8A | Š | è | è (meunière) — but Š is also legit (Špilberk) |
| 0x8B | ‹ | ï | rare |
| 0x9B | › | ¢ | rare |

The fixer does **not** auto-handle these — cp1252 is right for most C1 occurrences, and per-publisher detection isn't reliable enough to swap defaults. Instead, the [XD010 finding message](../xdlint.py) shows all three candidates (cp1252, Mac Roman, cp437):

```
C1 control U+0082 at col 12 (cp1252: '‚', Mac Roman: 'Ç', cp437: 'é')
```

The handful of files needing cp437 (~12 files, ~17 character-edits) should be fixed by hand or with a one-off targeted script. They are listed in the project's commit history under the "char encoding cleanup pass" commits.

---

## 6. UTF-8 misread as latin-1

A different kind of mojibake: a UTF-8-encoded byte sequence got read by an upstream tool as ISO-8859-1, producing two- or three-character latin-1 runs. Three sub-patterns:

### 6a. Single-step (`Ãª` → `ê`)

A UTF-8 byte pair `\xc3\xXX` (encoding U+00C0–U+00FF, the Latin supplement) read as latin-1 produces `Ã` (U+00C3) + a continuation byte interpreted as U+0080–U+00BF. Re-encoding the run as latin-1 and decoding as UTF-8 reverses the corruption.

```
'Ãª' → bytes \xc3\xaa → UTF-8 decode → 'ê'
'Ã©' → bytes \xc3\xa9 → UTF-8 decode → 'é'
'Â°' → bytes \xc2\xb0 → UTF-8 decode → '°'
```

This is what `XD009` (`latin1-utf8-mojibake`) catches. 67 instances across 51 files in the corpus.

False-positive risk is low because real latin-1 text rarely has `Ã`/`Â` followed by a U+0080–U+00BF char — French `Âge`, `RÂLE` etc. have ASCII letters after the `Â`, which fall outside the regex range.

### 6b. Two-step smart-quote trailers (`` → `"`)

For UTF-8 codepoints in the U+2000–U+27FF block (smart quotes, dashes), the encoding is `\xe2\x80\xXX`. When the leading `\xe2\x80` was either dropped entirely or replaced by an upstream processor (often with a straight ASCII `"`), what survives is just the trailing byte at U+0080–U+009F:

```
'dont'      → bytes \xe2\x80\x99 → '’' (right curly) → "don't"
'hi' → bytes \xe2\x80\x9c, \xe2\x80\x9d → '"hi"'
```

`XD010`'s UTF-8 trailer pass handles these by prepending `\xe2` before re-decoding. Also handles the variant where `\xe2` survived as latin-1 `â`:

```
'âs' → bytes \xe2\x80\x99 → "'s"
```

### 6c. Orphan trailers (`"` → `"`)

A specific, very common variant of 6b: smart quotes around a phrase like `\xe2\x80\x9c hello \xe2\x80\x9d` had each `\xe2\x80` lead pair replaced with a straight ASCII `"`, but the `\x9c` / `\x9d` trailer byte was left orphaned next to the straight quote. Pattern uniformly observed: every U+009C / U+009D in the corpus appears immediately after a `"` (336/336 occurrences, no exceptions).

`XD010` strips the orphan trailer when adjacent to a straight quote.

### 6d. Triple-encoded mojibake

Universal Crossword 2018 has files with `Ã¢ÂÂ™` patterns — a UTF-8 sequence that was misread, re-encoded, misread again, and re-encoded once more. Currently the XD009 pass + XD010 trailer pass collapses *most* of this correctly (because XD009 turns `Â` into U+0080, which then matches XD010's trailer regex), but stubborn residue remains. Out of scope for the auto-fixers; hand-edit if it bothers you.

---

## 7. Em dash: not just typography

Em dash (U+2014) appears 839 times across 416 corpus files. It serves at least three distinct purposes, only the first two of which are valid:

1. **Real typography** — `"say it again — I'm outta here"`, attribution dashes (`—Woody Allen`).
2. **Fill-in-the-blank marker** — `"— Miniver (1942 film classic) ~ MRS"`, `"Persona non — ~ GRATA"`. This is a publisher convention distinct from the common ascii-form `___` (triple-underscore) FITB. Found extensively in Wapost, Eltana, NYTimes corpora.
3. **Mac Roman 'ó' mojibake** — `"Almod—var ~ PEDROS"` should be `Almodóvar`. Mac Roman `0x97 = ó` (cp1252 `0x97 = —`). The legacy converter applied cp1252 indiscriminately, turning Mac Roman accented `ó` bytes into spurious em dashes.

Because of (3), **don't auto-flatten em dashes to `--` corpus-wide**. Doing so would erase the diagnostic signal for the Mac Roman cases. Em dashes that are clearly typography or FITB can be left alone; the suspicious ones (mid-word in proper nouns) need manual review.

The `XD010` finding message shows `cp1252: '—', Mac Roman: 'ó'` for U+0097 cases that haven't yet been fixed, so future C1-control reviews surface this distinction.

---

## 8. Boston Globe Symbol-font glyphs

Two files (`bg2010-03-28.xd` and `bg2012-04-29.xd`) contain U+0098 in math contexts that wants `÷`:

```
D109. MDLX ÷ X ~ CLVI            (1560 ÷ 10 = 156, in Roman numerals)
D55.  3 ÷ cosine? ~ TRIPLESECANT (3/cosine = 3 × secant = "triple secant")
```

The byte 0x98 → `÷` mapping doesn't match any standard 8-bit encoding (cp1252: ˜, Mac Roman: ò). This appears to be a Boston Globe internal Symbol-font convention that bled through the .puz pipeline. With only two corpus instances, hand-edit was the right answer; no rule was added.

Similar artifacts appeared at byte 0x80 in BG 2009-2011 files for `°` (`90° on a compass`), where neither cp1252 (`€`) nor Mac Roman (`Ä`) matches. The `XD010` skip-list refuses to auto-fix U+0080 and U+0098 single-character occurrences for exactly this reason.

---

## 9. The decode pipeline (puz2xd.decode)

[`xdfile/puz2xd.py`](../xdfile/puz2xd.py) `decode()` runs at conversion time on every clue, header, and metadata field pulled from a .puz. Order of operations:

1. **Strip orphan `Â`** before a C1 control: `\xc2\xXX` UTF-8 misread as latin-1 produces `Â + control`. Drop the `Â` so `clean_c1_controls` handles the trailer.
2. **NBSP collapse**: `\xc2\xa0` (UTF-8 NBSP read as latin-1) and standalone `\xa0` → space.
3. **Targeted UTF-8 fix**: `\xc3\xa8` (`Ã¨`) → `è`. (Subsumed by `clean_latin1_utf8_mojibake` but kept explicit for clarity / backward-compat with old test cases.)
4. **Mac Roman curly quotes**: `\xd3` → `"`, `\xd4` → `"`.
5. **`clean_latin1_utf8_mojibake`**: §6a — `Ã/Â + cont byte` → re-decoded UTF-8 char.
6. **`clean_c1_controls`**: §3, §4 — UTF-8 trailer reconstruction → U+008E override → cp1252 default with U+0080/U+0098 skipped.
7. **ASCII typography flattening**: curly quotes → ASCII, ellipsis → `...`. Em dash kept as Unicode (matches existing corpus convention).
8. **URL unquote, HTML entity unescape, whitespace collapse** — pre-existing legacy steps.

The two lossy bulk replacements that the legacy decode used to do — `\xc3\x82 → ""` and `\xc2 → " "` — are dropped. They corrupted legitimate French text (real `Â`, `Ã` in proper nouns) trying to clean up a small class of UTF-8 leftovers. The new pipeline only touches `Â` / `Ã` when followed by a continuation byte (a clear UTF-8 mojibake signal).

---

## 10. The lint rules

| Code | Severity | Catches | Auto-fix |
|---|---|---|---|
| `XD009` | error | latin-1 misread of UTF-8 (`Ãª`, `Ã©`, `Ã³`, etc.) | yes |
| `XD010` | error | C1 control codepoints (U+0080–U+009F) | partial |

`XD010`'s fixer runs four passes:

1. UTF-8 trailer reconstruction (§6b)
2. Orphan smart-quote trailer strip (§6c)
3. Per-codepoint overrides (currently just U+008E → é, §4)
4. cp1252 default, with U+0080 and U+0098 skipped (§5, §8) and undefined cp1252 slots passed through (§3)

The finding messages list candidates from cp1252, Mac Roman, and cp437 so a reviewer can pick the right answer when an auto-fix can't.

`XD009` runs **before** `XD010` in the fix order — see [`FIX_ORDER`](../xdlint.py). This matters for triple-mojibake cases (§6d): `Â` collapses to `` after XD009, which XD010's trailer pass then reconstructs to `"`.

---

## 11. Frequency in the corpus

| Pattern | File count | Character count |
|---|---:|---:|
| C1 control mojibake (XD010 catches) | ~150 | ~564 |
| of which: U+0097 (em dash + Mac Roman ó) | ~50 | 98 |
| of which: U+009D (orphan smart quote close) | ~150 | 364 |
| of which: U+008E (Mac Roman é override) | 6 | 6 |
| of which: U+0080 / U+0098 (skipped, manual) | 2 | 2 |
| latin-1 misread of UTF-8 (XD009 catches) | 51 | 67 |
| cp437 typography residue (manual hand-edit) | 12 | 17 |
| Triple-encoded mojibake (Universal 2018) | ~5 | varied |

After running `--fix` with both rules enabled and applying the 17 hand-edits (see [§12](#12-the-residue-list)), the corpus is clean of C1 controls and latin-1-misread-UTF-8 mojibake.

---

## 12. The residue list

Cases where auto-fix doesn't help and hand-editing is the right answer:

| File | Char | Should be | Why |
|---|---|---|---|
| `bg2010-03-28.xd:166` | `` (math context) | `÷` | PDF Symbol font, no encoding match (§8) |
| `bg2012-04-29.xd:138` | `` (math context) | `÷` | PDF Symbol font (§8) |
| `bg2009-06-07.xd:32`  | `` (compass) | `°` | PDF Symbol artifact, neither encoding matches |
| `bg2011-05-15.xd:73`  | `` (Réaumur) | `°` | Same as above |
| `nw1999-03-01.xd:88`  | `‚` (Soufflé) | `é` | cp437 0x82 (§5) — fixed |
| `nys2007-04-02.xd:27` | `‚` (También) | `é` | cp437 0x82 — fixed |
| `nys2007-04-12.xd:29` | `‚` (Kertész) | `é` | cp437 0x82 — fixed |
| `ss2003-12-08.xd:46`  | `‚` (Café) | `é` | cp437 0x82 — fixed |
| `ss2004-03-01.xd:81`  | `‚` (entrées) | `é` | cp437 0x82 — fixed |
| `ss2004-08-30.xd:46`  | `‚` (Café) | `é` | cp437 0x82 — fixed |
| `nyt1997-06-29.xd:57` | `‚` (grâce) | `â` | cp437 0x82, but context wants `â` not `é` |
| `nys2007-04-06.xd:88` | `‰` (Zoë) | `ë` | cp437 0x89 — fixed |
| `nyt2009-01-12.xd:45` | `Ž` (Risqué) | `é` | Mac Roman 0x8E that survived (the override only kicks in pre-fix) — fixed |
| `pk2015-02-08.xd:92`  | `‡` (Pietà) | `à` | OCR/encoding error, not standard — fixed |
| `nw2001-02-13.xd:65`  | `†` (González) | `á` | OCR/encoding error — fixed |
| `pk2005-05-01.xd:123` | `Œ` (`Œteam"`) | `"` (open) | Mojibake of left curly quote — fixed |
| `bg2009-03-15.xd:153` | `‚` (`suppose‚...`) | (delete) | Stray char, not a real letter — fixed |
| `ss2004-02-16.xd:53`  | `Š` (meunière) | `è` | cp437 0x8A (Mac Roman 0x8A is also è) — fixed |
| `nyt2005-01-30a.xd:1` | `†` (`2005† SMOOTH MOVE`) | `:` | Title separator — fixed |

The `Š` characters in `gxd/indie/bequigley/beq-0424.xd:44` and `beq-1390.xd:61` (`Špilberk Castle`) are **legitimate** cp1252 — leave alone.

---

## 13. Recommendations for new ingestion

1. **Use the shared `clean_c1_controls()` and `clean_latin1_utf8_mojibake()` from `xdfile.utils`.** Don't recreate per-byte hand-coded lists.
2. **Don't blanket-strip `Â` (U+00C2) or `Ã` (U+00C3).** They appear in real French/Portuguese text. Only strip when followed by a continuation byte (a UTF-8 mojibake signal).
3. **Don't auto-fix U+0080 or U+0098 single-character occurrences.** Their cp1252 mappings (`€`, `˜`) are usually wrong in this corpus (PDF Symbol artifacts for `°`, `÷`).
4. **Audit `xdfile/ccxml2xd.py`, `xdfile/xwordinfo2xd.py`, `xdfile/ujson2xd.py`** if a new source format starts producing mojibake. They currently hard-assume UTF-8 and skip the cleanup pipeline.
5. **Run XD009 + XD010 routinely.** Both are in the default `--fix` order. They catch mojibake from any source format, not just .puz.
6. **Keep `puz2xd.py` and `puz2xd-standalone.py` in lockstep.** The standalone script duplicates `clean_c1_controls`/`clean_latin1_utf8_mojibake` so it can run without the `xdfile` package installed; both must be updated together.
