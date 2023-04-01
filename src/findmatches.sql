.load src/gridcmp

DROP TABLE IF EXISTS gridmatches ;
CREATE TABLE IF NOT EXISTS gridmatches AS
  SELECT a.xdid as xdid1, b.xdid as xdid2, gridcmp(a.grid, b.grid) AS matchpct
        FROM puzzles a
        CROSS JOIN puzzles b
        WHERE a.date < b.date
        AND a.size = b.size
        AND ABS(matchpct) > 30
        ;
