
## Download crossword data

All public data from xd is available in three .zip archives:

- [xd-metadata.zip](/xd-metadata.zip)  (2MB), metadata and similarity for all puzzles in the corpus, public and private

- [xd-puzzles.zip](https://github.com/century-arcade/xd/releases/download/puzzles-pre1965/xd-puzzles.zip)  (12MB), all 5,688 puzzles in the corpus published before 1965, in [.xd format](https://github.com/century-arcade/xd): 5,633 from the New York Times (1942-1964), 50 from the first Simon & Schuster crossword books (1924), and a handful of early newspaper puzzles

- [xd-clues.zip](/xd-clues.zip)  (67MB), over 6,000,000 answer/clue usages, grouped by publication-year

The clues and the metadata are also published as versioned snapshots, in Parquet, on Hugging Face and Kaggle (links to come once they are up).
Each snapshot is fixed, so a result can name the version it used, and the clue snapshots apply a minimum cell size: a publication-year with fewer than 5 puzzles is coarsened to its decade or left out.
What is published, and the terms we ask people to honor, are in [DATASETS.md](https://centuryarcade.org/xd/datasets/).

## Source code

- Browse the entire source code at [github.com/century-arcade/xd](https://github.com/century-arcade/xd).

## Submit puzzles

Email crosswords for comparison or inclusion to [submitxd@saul.pw](mailto:submitxd@saul.pw) as attachments of .puz, .ipuz, .xd, or a .zip of any of these.
Each filename should include the date (in YYYYMMDD format), or a three digit number (NNN) if they are published sequentially.

If you have more than a few puzzles, please email me at [xd@saul.pw](mailto:xd@saul.pw) to discuss the best way to import and organize them.
