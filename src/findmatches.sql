.load src/gridcmp

CREATE TABLE IF NOT EXISTS gridmatches (
    xdid1 TEXT,
    xdid2 TEXT,
    matchpct INT
);

-- grab 100 crosswords that we have not processed
CREATE TEMP TABLE unchecked_puzzles AS
SELECT b.xdid, b.grid, b.date, b.size
FROM puzzles b
WHERE b.xdid NOT IN (SELECT xdid2 FROM gridmatches)
LIMIT 100;

-- check if those crosswords have any matches
INSERT INTO gridmatches (xdid1, xdid2, matchpct)
  SELECT a.xdid as xdid1, b.xdid as xdid2, gridcmp(a.grid, b.grid) AS matchpct
        FROM puzzles a
        CROSS JOIN unchecked_puzzles b
        WHERE a.date < b.date
        AND a.size = b.size
        AND ABS(matchpct) > 30
        ;

-- log crosswords with no matches that we have processed
INSERT INTO gridmatches (xdid1, xdid2, matchpct)
    SELECT NULL as xdid1, b.xdid as xdid2, NULL as matchpct
    FROM unchecked_puzzles b
    WHERE b.xdid NOT IN (SELECT xdid2 FROM gridmatches)
