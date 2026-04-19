## How to process big puzzle archive (like bwh.zip)

        # 90-split-archive.py reads files from the positional input path (bwh/).
        # --source is only a metadata label written into sources.tsv; it is not an input file path.
        rm -rf bwh/ bwh-zips/ && mkdir bwh/ bwh-zips/
        tar -xzf ~/Downloads/bwh-2015.tgz -C bwh/
        ./scripts/90-split-archive.py -o bwh-zips/ --source bwh-2015.tgz bwh/
        ./scripts/18-convert2xd.py -o gxd/ bwh-zips/up.zip


## How to manually process puzzles from appropriate publisher with different sources

        ./scripts/10-manual.sh <branch_name> <source_a.zip> "<source_a_name>"
        [ example: ./scripts/10-manual.sh latime_02 latimes-2015-raw.zip "LA Times" ]
        cd gxd && git checkout <branch_name> && git add .
        [ example: cd gxd && git checkout latime_01 && git add . ]
        # Check for quality before commit
        ../scripts/55-lint.sh
        git commit -m 'message about source_a'
        cd ..
        ./scripts/18-convert2xd.py -o gxd/ <source_b.zip> --extsrc "<ext_src_b>" --intsrc "<int_src_b>"
        [ example: ./scripts/18-convert2xd.py -o gxd/ bwh_zips/la.zip --extsrc "bwh" --intsrc "bwh-2015.tgz" ]
        cd gxd && ../scripts/git-diff-clues.sh <branch_a_gitcode> <branch_b_gitcode> <outdir>
        [ example: cd gxd && ../scripts/git-diff-clues.sh xml bwh latimes/ ]
        # outdir - where output of prev scripts goes - usually named by publisher
        # Check for quality before commit
        ../scripts/55-lint.sh
        cd .. && ./scripts/19b-receipts-tsv.sh
        ./scripts/48-stats.sh

## publications.tsv maintenance

`gxd/publications.tsv` is maintained manually (or by a separate curated process).
Import scripts such as `scripts/18-convert2xd.py` and `scripts/19-reshelve.py` do not automatically add/update publication rows.

When introducing a new publication/pubid, add the row to `gxd/publications.tsv` before running imports for that pubid.

## How to check receipts.tsv for duplicate values

### filter out duplicates based on InternalSource & Filename

        awk 'BEGIN {FS="\t"} {c[$5$6]++} {if (c[$5$6] == 1) print $0}' receipts.tsv

### number of receipts

        cat receipts.tsv | wc -l

### enumerate ExternalSources with amount of receipts

        cat receipts.tsv | cut -f 4 | sort | uniq -c | sort -n

### enumerate InternalSources with amount of receipts

        cat receipts.tsv | cut -f 5 | sort | uniq -c | sort -n

### print duplicate receipts based on InternalSource & Filename

        cat receipts.tsv | cut -f 5,6 | sort | uniq -d -c

### print duplicate receipts based on receiptid

        cat receipts.tsv | cut -f 1 | sort -n | uniq -c -d

### check for puzzle duplicates and generate diffs

        cd gxd/
        ../scripts/git-diff-clues.sh <origin> <input> -R <dir to process>

### check from meda.db for receipts with empty xdid

        select * from receipts where xdid=='';

### check from meta.db for receipts amount with duplicate xdid

       select count(*) from (select xdid, count(*) as c from receipts group by xdid having c>=2 order by c);

