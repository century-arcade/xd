#!/usr/bin/env python3

from xdfile.utils import open_output, log, find_files, get_args, parse_pathname, generate_zip_files, iso8601, to_timet
from xdfile.metadatabase import xd_sources_header, xd_sources_row
from xdfile.cloud import xd_send_email


import email.utils
import email
import mimetypes
import time


def generate_email_files(msg):
    counter = 1
    upload_date = time.mktime(email.utils.parsedate(msg["Date"]))
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

        data = part.get_payload(decode=True)
        if parse_pathname(filename).ext == '.zip':
            for zipfn, zipdata, zipdt in generate_zip_files(data):
                yield zipfn, zipdata, zipdt
        else:
            yield filename, data, upload_date

def main():
    args = get_args('parse downloaded emails')
    outf = open_output()

    sources_tsv = ''
    for emailfn, emailcontents in find_files(*args.inputs):
        msg = email.message_from_bytes(emailcontents)
        upload_src = msg["From"]

        if not upload_src:
            continue

        email_sources_tsv = []
        for puzfn, puzdata, puzdt in generate_email_files(msg):
            # a basic sanity check of filesize
            # accommodate small puzzles and .pdf
            log("%s: %s from %s" % (puzfn, iso8601(puzdt), upload_src))

            if len(puzdata) > 1000 and len(puzdata) < 100000:
                email_sources_tsv.append(xd_sources_row(puzfn, upload_src, iso8601(puzdt)))

                outf.write_file(puzfn, puzdata)

        # generate receipt row, send receipt email

        if email_sources_tsv:
            xd_send_email(upload_src,
                    fromaddr='upload+received@xd.saul.pw',
                    subject='Upload successful: %d files received' % len(email_sources_tsv),
                    body="These files were received:\n" + "\n".join(email_sources_tsv))
            sources_tsv += "".join(email_sources_tsv)
        else:
            xd_send_email(upload_src,
                    fromaddr='upload+failed@xd.saul.pw',
                    subject='Upload error',
                    body='No puzzle files received')

    outf.write_file("sources.tsv", xd_sources_header + sources_tsv)

main()
