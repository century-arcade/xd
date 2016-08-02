CREATE TABLE "receipts" (
    "ReceiptId" INTEGER PRIMARY KEY NOT NULL,
    "CaptureTime" TEXT,
    "ReceivedTime" TEXT,
    "ExternalSource" TEXT,
    "InternalSource" TEXT,
    "SourceFilename" TEXT,
    "xdid" TEXT
);
CREATE UNIQUE INDEX "ReceiptID" on receipts (ReceiptId ASC);

