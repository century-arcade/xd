DROP TABLE IF EXISTS gridmatches;
CREATE TABLE gridmatches (
    xdid1 TEXT,
    xdid2 TEXT,
    matchpct INT
);
.mode tabs
.import '| tail -n +2 gxd/similar.tsv' gridmatches
