# xd

The xd project includes a [text format for crossword puzzles](docs/xd-format.md) and a pipeline for downloading, parsing, analyzing puzzles, and producing the website and released data at [xd.saul.pw](https://xd.saul.pw).

## Requirements

- python 3.7+
- git
- markdown (to build website)
- sqlite (for grid comparison)
- gcc (to build sqlite plugin)
- aws-cli (to deploy)

# Running the pipeline

1. Checkout the gxd repo (private; join [#crosswords on the Discord](https://saul.pw/chat) to discuss getting access).

    make setup

2. Download new puzzles from known sources, convert to .xd, shelve, and commit to gxd repo.

    make import

Raw puz/etc files saved to .zip in /tmp, and .xd files saved to `gxd` directory.

3. Analyze puzzles

    make analyze

Output in `pub` directory.

4. Build website

    make website

Output in `wwwroot` directory.

5. Generate `gxd.sqlite` database (400MB)

    make gxd.sqlite

6. Find similar grids (takes ~12 hours)

    make gridmatches

Similarity scores saved to `gridmatches` table in gxd.sqlite.
