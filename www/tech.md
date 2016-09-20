# Technical Notes

## how to manually convert/shelve a collection

        $ aws s3 cp eltana-20160529.zip s3://xd-private/src/

        $ scripts/20-convert2xd.py -o gxd --source '"Mike Selinker" <mike@lonesharkgames.com>' --copyright Eltana --pubid eltana eltana-20160529.zip

    [convert2xd --no-earlier should not output earlier editions]
        $ rm *[a-d].xd

## filesystem queries (or, why I used the text .xd format)

0. setup

        $  unzip nytimes-1992.zip
        crosswords/nytimes/1992/nyt1992-01-01.xd
        crosswords/nytimes/1992/nyt1992-01-02.xd
        ...

1. How many crosswords are in the corpus?

        $  find crosswords/ -name '*.xd' | wc -l
        24759

2. How many clues?

        $  grep -r '~' crosswords/ | wc -l
        2141944

3. How many unique words?

        $  grep -r '~' crosswords/ | cut -d'~' -f2 | sort | uniq -c | wc -l
        186896

4. Which answers are most common at 1-Down?

        $ grep -r '~' crosswords/ | grep 'D1\.' | cut -d'~' -f2 | sort | uniq -c | sort -nr

# Serverless Best Practices

## set domain root to A record ([*not* CNAME, which precludes MX records]())

 * `example.com`  redirect to www. (with wwwizer?  or tiny bucket with auto-redirect?)
 * `www.example.com`  CNAME to S3
 * `example.com`  MX record to mailserver

