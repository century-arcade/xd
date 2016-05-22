#!/usr/bin/env python3

from xdfile.utils import open_output, log, find_files, get_args
from xdfile.metadatabase import xd_sources_header, xd_sources_row

import email
import mimetypes

def parse_date(datestr):
    import timestring
    dt = timestring.Date(datestr)
    return "%d-%02d-%02d" % (dt.year, dt.month, dt.day)


def xd_send_email(destaddr, subject='', body=''):
    import boto3
    client = boto3.client('ses')
    log("sending email to %s (subject '%s')" % (destaddr, subject))
    try:
        response = client.send_email(
                Source='sys@xd.saul.pw',
                Destination= {'ToAddresses': [ destaddr ] },
                Message={ 'Subject': { 'Data': subject },
                'Body': { 'Text': { 'Data': body } } })
        return response
    except Exception as e:
        log(str(e))
        return None


def generate_files(msg):
    counter = 1
    for part in msg.walk():
        # multipart/* are just containers
        if part.get_content_maintype() == 'multipart':
            continue
        # Applications should really sanitize the given filename so that an
        # email message can't be used to overwrite important files
        filename = part.get_filename()
        if not filename:
            ext = mimetypes.guess_extension(part.get_content_type())
            if not ext:
                # Use a generic bag-of-bits extension
                ext = '.bin'
            filename = 'part-%03d%s' % (counter, ext)
        counter += 1

        yield filename, part.get_payload(decode=True)

def main():
    args = get_args('parse downloaded emails')
    outf = open_output()

    sources_tsv = ''
    for emailfn, emailcontents in find_files(*args.inputs):
        msg = email.message_from_bytes(emailcontents)
        upload_date = parse_date(msg["Date"])
        upload_src = msg["From"]

        email_sources_tsv = []
        for puzfn, puzdata in generate_files(msg):
            # a basic sanity check of filesize
            # accommodate small puzzles and .pdf
            log("%s: %s from %s" % (puzfn, upload_date, upload_src))

            if len(puzdata) > 1000 and len(puzdata) < 100000:
                email_sources_tsv.append(xd_sources_row(puzfn, upload_src, upload_date))

                outf.write_file(puzfn, puzdata)

                
            # generate receipt row, send receipt email with ReceiptId/URL?
            # save file to `date`-email.zip

        if email_sources_tsv:
            xd_send_email(upload_src, subject='%d files received' % len(email_sources_tsv), body='Check this out')
            sources_tsv += "".join(email_sources_tsv)
        else:
            xd_send_email(upload_src, subject='nothing uploaded', body='failed due to error')

    outf.write_file("sources.tsv", xd_sources_header + sources_tsv)

main()
