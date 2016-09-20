-- xd

CREATE TABLE receipts (
    CaptureTime TEXT,
    ReceivedTime TEXT,
    ExternalSource TEXT,
    InternalSource TEXT,
    SourceFilename TEXT,
    xdid CHAR(16),
    PRIMARY KEY (ExternalSource, SourceFilename)
);

CREATE INDEX XDID on receipts (xdid ASC);


CREATE TABLE similar_grids (
    xdid CHAR(16),
    xdidMatch CHAR(16),
    GridMatchPct INTEGER
);


CREATE TABLE similar_clues (
    xdid CHAR(16),
    reused_clues INTEGER,
    reused_answers INTEGER,
    total_clues INTEGER
);


CREATE TABLE publications (
    PublicationAbbr CHAR(8),
    PublisherAbbr CHAR(8),
    PublicationName TEXT,
    PublisherName TEXT,
    FirstIssueDate CHAR(10),
    LastIssueDate CHAR(10),
    NumberIssued INTEGER,
    Contact TEXT,
    Sources TEXT
);


CREATE TABLE puzzles (
    xdid CHAR(16),  -- "eltana-001"
    Date CHAR(10),  -- "2016-07-18"
    Size CHAR(8),   -- "15x15RS" (Rebus/Special)
    Title TEXT,
    Author TEXT,
    Editor TEXT,
    Copyright TEXT,
    A1_D1 TEXT
);


-- grouped by pub-year-weekday
CREATE TABLE stats (
    pubid CHAR(6),   -- "nyt"
    year CHAR(4),    -- "2006"
    weekday CHAR(3), -- "Mon"
    Size TEXT, -- most common entry
    Editor TEXT, -- most common entry
    Copyright TEXT, -- most common, after removing Date/Author
    NumExisting INTEGER, -- known or assumed to be in existence (0 means unknown)
    NumXd INTEGER,       -- total number in xd
    NumPublic INTEGER,   -- available for public download
    -- duplicate grids, same author
    NumReprints INTEGER, -- 100% grid match
    NumTouchups INTEGER, -- 75-99% grid match
    NumRedone INTEGER,   -- 30-75% grid match
    -- duplicate grids, different author
    NumSuspicious INTEGER, -- >50% similar grid
    NumThemeCopies INTEGER -- 30-50% similar grid
);

