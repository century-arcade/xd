# History

*November 2026. Dates are from the repositories' commit histories and the public record. Items marked **[check]** are waiting on Saul's memory of the early years.*

The documents on this site were written in 2026. The corpus they describe is ten years old, and the collecting that made it possible started before that.

![Puzzles in the corpus, 2016 to 2026](img/corpus-growth.svg)

## 2015–2016: the format and the first collection

[Saul Pwanson](https://saul.pw/) started gathering published crosswords in 2015 **[check]**, from the puzzle files that publications and syndicates put online for their solving apps. To hold them he defined the `.xd` format: one plain-text file per puzzle, with its headers, grid, clues and answers, readable in any text editor and diffable in git. The [xd repository](https://github.com/century-arcade/xd) opened on 17 January 2016 with the format's README and a `.puz` converter, and other programmers were contributing converters and tools within weeks. By the end of February 2016 the collection could be searched from a small web server, and it held about 52,000 puzzles.

## March 2016: the first thing the collection showed

Nobody had been able to compare puzzles across publications before, because nobody had the puzzles in one place. When Saul did, the repeats stood out: dozens of USA Today and Universal crosswords, both edited by Timothy Parker, that reused the theme answers of earlier New York Times puzzles, and others that had been republished under different bylines. He worked through the evidence with the constructor Ben Tausig, and on 4 March 2016 FiveThirtyEight published Oliver Roeder's [A Plagiarism Scandal Is Unfolding In The Crossword World](https://fivethirtyeight.com/features/a-plagiarism-scandal-is-unfolding-in-the-crossword-world/). The publisher [confirmed the findings](https://fivethirtyeight.com/features/a-crossword-publisher-confirms-plagiarism-allegations/) within the week, and the editor [stepped back](https://fivethirtyeight.com/features/usa-todays-embattled-crossword-puzzle-editor-is-stepping-back-for-now/) and later [left USA Today](https://fivethirtyeight.com/features/timothy-parker-accused-of-plagiarism-is-out-as-usa-todays-crossword-puzzle-editor/).

That was the moment the collection became a corpus. A body of puzzles that could be searched and compared had shown something about the field that no one puzzle could, and it became clear that it was worth keeping properly.

## 2016–2025: the corpus

The collection is older than its repository. Saul had been gathering puzzles for months before the March story, and the 52,000 it was built on were already on his disk. In May 2016 he opened gxd, a git repository for the puzzles with a receipts file that records where each one came from, and committed the collection over the summer, publication by publication: Universal and USA Today in July, the New York Times, Newsday and CrosSynergy in August, the Los Angeles Times in September. That is why the chart above begins in May 2016 and climbs so steeply that year. By December 2016 the repository held 71,000 puzzles.

For the next nine years it grew quietly, mostly by a nightly download of the publications that post their puzzles, with occasional archives contributed by constructors and collectors. [Anja Kefala](https://github.com/anjakefala/) helped with the tooling throughout **[check]**, and [xd.saul.pw](https://xd.saul.pw) published statistics from the corpus: puzzles by publication and year, the most common answers, the grids that reuse each other. By the end of 2025 the corpus held 90,000 puzzles.

## 2026: a second maintainer, new sources, and a public home

[Alex DeJarnatt](https://alexdej.com/) joined as co-maintainer in 2026 **[check month]**. [The Cross Reference](https://crosswordreference.com), a browser for the corpus, launched in September. In October the [Every Puzzle Project](https://everypuzzleproject.github.io/) began reading pre-digital puzzles from scanned pages, starting with *Judge* magazine's 1929–30 run, and a round of imports from publications and contributed archives brought the corpus from 90,000 puzzles to 160,000 in a month.

In November 2026 the maintainers wrote down how the corpus is collected, edited, kept and shared, assessed it against the Digital Preservation Coalition's maturity model, published the first derived datasets, and gave the project this site at centuryarcade.org.

## Puzzles in the corpus

| End of | Puzzles |
|---|---|
| 2016 | 71,049 |
| 2019 | 72,593 |
| 2022 | 84,431 |
| 2025 | 89,922 |
| 9 November 2026 | 162,819 |

Counted from the gxd repository's history by `corpus-stats.py`; the chart above is drawn from the same count by [`scripts/history-chart.py`](https://github.com/century-arcade/xd/blob/master/scripts/history-chart.py).
