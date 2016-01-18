#!/usr/bin/python

import os
import argparse

from utils import DateUtils
from utils import ZipUtils
from errors import *



DEFAULT_CONTENT_TYPE = 'html'

def parse_args():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--download-raw', action='store_true')
    group.add_argument('--raw-to-xd', action='store_true')
    group.add_argument('--download-xd', action='store_true')
    parser.add_argument('-s', '--scraper', required=True)
    parser.add_argument('-o', '--outfile', required=True)
    parser.add_argument('-i', '--infile')
    parser.add_argument('-f', '--from-date', help='Format "YYYY-MM-DD"')
    parser.add_argument('-t', '--to-date', help='Format "YYYY-MM-DD"')
    args = parser.parse_args()

    # additional validations
    try:
        module = __import__("scrapers", fromlist=[args.scraper])
        scraper = getattr(module, args.scraper)()
    except (ImportError, AttributeError):
        parser.error('unknown scraper "%s"' %args.scraper)

    if os.path.exists(args.outfile):
        parser.error('outfile "%s" already exists' %args.outfile)
    elif args.raw_to_xd and not args.infile:
        parser.error('infile is mandatory for raw_to_xd')
    elif args.infile and not os.path.exists(args.infile):
        parser.error('infile "%s" does not exist' %args.infile)
    elif not args.raw_to_xd \
    and not (args.from_date and args.to_date):
        parser.error('both from_date and to_date are required '
                     'for download_raw or download_xd')
    elif args.from_date and args.to_date:
        if not DateUtils.is_valid(args.from_date):
            parser.error('from_date "%s" is invalid' %args.from_date)
        elif not DateUtils.is_valid(args.to_date):
            parser.error('to_date "%s" is invalid' %args.to_date)
        elif DateUtils.from_string(args.from_date) > DateUtils.from_string(args.to_date):
            parser.error('from_date should be equal or less than to_date')
        elif DateUtils.from_string(args.from_date) > DateUtils.today():
            parser.error('from_date should be equal or less than today')
        elif DateUtils.from_string(args.to_date) > DateUtils.today():
            parser.error('to_date should be equal or less than today')

    return args, scraper

if __name__ ==  '__main__':
    args, scraper = parse_args()

    if args.raw_to_xd:
        format = scraper.RAW_CONTENT_TYPE or DEFAULT_CONTENT_TYPE

        for filename, content in ZipUtils.read(args.infile):
            print 'Processing Raw Crossword - %s' %filename
            crossword = scraper.build_crossword(content)
            content = str(crossword)
            filename = filename.replace(format, 'xd')

            if content:
                # append to zip archive
                ZipUtils.append(content, filename, args.outfile)
    else:
        for date in DateUtils.get_dates_between(args.from_date, args.to_date):
            print 'Processing Crossword for date - %s' %DateUtils.to_string(date)

            try:
                content = scraper.get_content(date)
            except ContentDownloadError:
                print '\tERR: Content Download Error'
            except NoCrosswordError:
                print '\tERR: No Crossword for date'
                continue

            format = scraper.RAW_CONTENT_TYPE or DEFAULT_CONTENT_TYPE
            prefix = scraper.FILENAME_PREFIX or scraper.__name__.replace('Scraper', '').lower()

            if args.download_xd:
                crossword = scraper.build_crossword(content)
                content = str(crossword)
                format = 'xd'

            if content:
                # append to zip archive
                filename = '%s-%s.%s' %(prefix, DateUtils.to_string(date), format)
                filename = os.path.join('crosswords-%s' %prefix, str(date.year), filename)
                ZipUtils.append(content, filename, args.outfile)
