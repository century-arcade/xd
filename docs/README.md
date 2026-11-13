# The xd Crossword Corpus

Home of the corpus: https://centuryarcade.org/xd/

The xd Crossword Corpus is the world's largest collection of crossword puzzles, with more than 160,000 published crosswords
from over 160 publications (as of November 2026), from 1913 to today, kept in a plain-text format for
research and preservation. Every puzzle is stored as one [`.xd` file](https://github.com/century-arcade/xdformat/blob/master/doc/xd-format.md)
holding its grid, clues, answers and publication details, together with a record
of where it came from for nearly every puzzle.

The corpus was created by [Saul Pwanson](https://saul.pw/) in 2016 and is currently maintained by [Alex DeJarnatt](https://alexdej.com/) as a volunteer
project of [Century Arcade](https://github.com/century-arcade), with technical help from [Anja Kefala](https://github.com/anjakefala/).

## Sites using the corpus

- [The Cross(word) Reference](https://crosswordreference.com): browse and search puzzles, clues, and answers across the corpus.
- [xd.saul.pw](https://xd.saul.pw): Saul's original plagiarism analysis, plus statistics and reports. 
- [Spread the Word(list)](https://www.spreadthewordlist.com/): clue database build on the xd Crossword Corpus.
- [Puzzmo Crossword Data](https://data.puzzmo.com/xwd): search clues and answers in the corpus.

## Use the corpus

Most of the puzzles in the corpus are still under copyright by their publishers and constructors, so the raw corpus
itself is not public. It is available for research, in forms ranging from
aggregate statistics to derived datasets to the full collection. See
[ACCESS.md](ACCESS.md) for what data is available, how to ask, and the terms of use.

## Contribute puzzles

We welcome puzzles from any publication that meets the collection scope in
[COLLECTION.md](COLLECTION.md): American-style crosswords, made by a person,
part of a published series. If you edit, construct or publish crosswords,
[CONTRIBUTING.md](CONTRIBUTING.md) says what we do with puzzles we are given,
who can see them, and what to send. Send puzzles, or questions, to
xd@centuryarcade.org. Volunteers who want to convert and submit puzzles themselves
are welcome too; see the end of that page.

## Policies

- [CONTRIBUTING.md](CONTRIBUTING.md): what happens to puzzles you give us,
  and what to send.
- [COLLECTION.md](COLLECTION.md): what the corpus collects.
- [EDITORIAL.md](EDITORIAL.md): what a corpus puzzle contains and how it is
  represented.
- [ACCESS.md](ACCESS.md): who may use the corpus, how, and on what terms.
- [DATASETS.md](DATASETS.md): what datasets the corpus publishes, where,
  and the rules they follow.
- [AI.md](AI.md): the corpus's statement on AI, and the terms on using its
  data to train models.
- [PRESERVATION.md](PRESERVATION.md): how the corpus is kept, and what we
  commit to.
- [ARCHIVING.md](ARCHIVING.md): guidelines for anyone archiving crosswords
  of their own.
- [GOVERNANCE.md](GOVERNANCE.md): who maintains the corpus and how decisions are
  made.
- [DECISIONS.md](DECISIONS.md): a dated log of decisions.
- [HISTORY.md](HISTORY.md): where the corpus came from, 2016 to today.
- [assessments/](assessments/): yearly self-assessments of the project's
  preservation capability.

## The parts

| | |
|---|---|
| [xdformat](https://github.com/century-arcade/xdformat) | The `.xd` file format specification, and converters from `.puz` and `.ipuz`. |
| [xd](https://github.com/century-arcade/xd) | The project's home: this site and its policy documents, and the pipeline that imports, checks and analyzes the corpus and builds xd.saul.pw. |
| The corpus | The corpus itself: a private repository, with the provenance of nearly every puzzle. Access on request. |
| [The Cross(word) Reference](https://crosswordreference.com) | Browsing and search. |
| [Every Puzzle Project](https://github.com/EveryPuzzleProject) | A sister project digitizing historical crosswords from scans, which feeds the corpus. |

## Citing

If you publish research or results that use the corpus, please cite it:

> Pwanson, Saul and DeJarnatt, Alex. (2026). *The xd Crossword Corpus.*
> Century Arcade. https://centuryarcade.org/xd/

Use the year the corpus was accessed. Earlier work cited it as
"Pwanson, Saul. (2019). xd Crossword Corpus. http://xd.saul.pw"; that is the
same corpus.

A DOI for the corpus is being registered with Zenodo; until then cite the address above.

## Contact

Open an issue in [this repository](https://github.com/century-arcade/xd), or find us on [Discord](https://saul.pw/chat).


## Acknowledgments

We thank the following individuals for their contributions to the xd Crossword Corpus:

- Barry Haldiman
- Quiara Vasquez
- Ben Zimmer
- Evan Birnholz
- David Steinberg
- Ben Tausig
- [Roy Leban](https://royleban.com/)
- [Alex Boisvert](https://alexboisvert.com/)
- [Mike Selinker](https://www.selinker.com/)
- [Enrique Henestroza Anguiano](https://datalexic.com/)
- Alex Bajcz
- Daniel Kirkdorffer
- [jmviz](https://github.com/jmviz)
- [Jim Horne](https://xwordinfo.com/)

Additionally we'd like to think the whole team behind [Pre-Shortzian Puzzle Project](http://www.preshortzianpuzzleproject.com/) for inspiring our project.
