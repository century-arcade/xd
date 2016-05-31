
#scripts/30-clean-metadata.py -o $PRIV/puzzles.tsv $GXD

# 3x: statistics and cacheable metadata
# 4x: individual puzzle/grid/clue/answer analyses
# 5x: fun facts (one-off interesting queries)

scripts/30-clean-metadata.py -o $PRIV/puzzles.tsv $GXD
scripts/41-pubyears.py -o $PUB

scripts/50-analyze-puzzle -o $WWW -c $GXD.zip recents.tsv  # XXX: this takes input files not .tsvs
#scripts/51-clues-tsv.py ${CORPUS} -o pub
