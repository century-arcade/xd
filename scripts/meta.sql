CREATE TABLE "receipts" (
    "CaptureTime" TEXT,
    "ReceivedTime" TEXT,
    "ExternalSource" TEXT,
    "InternalSource" TEXT,
    "SourceFilename" TEXT,
    "xdid" TEXT
);

CREATE INDEX "XDID" on receipts (xdid ASC);

