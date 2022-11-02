#!/usr/bin/env python3

# Usage:
#  $0 -o <output-zip> -r <recent-downloads.tsv>
#
#  Examines <input> filenames for each source and most recent date; downloads more recent puzzles and saves them to <output-zip>.
#

import urllib.request, urllib.error, urllib.parse
import datetime
import time
import re
import json
import base64

def construct_xdid(pubabbr, dt):
    return pubabbr + dt.strftime("%Y-%m-%d")


puzsrc = {'pubid': 'lat', 'ext': 'xml', "freq": "1", 'urlfmt': 'https://cdn4.amuselabs.com/lat/crossword?id=tca%y%m%d&set=latimes'}

# returns most recent date actually gotten
def download_puzzles(puzsrc, pubid, dates_to_get):
    actually_gotten = []

    # AmuseLabs query urls require a pickerToken
    al_pubs_tokens = {'lat': 'https://cdn4.amuselabs.com/lat/date-picker?set=latimes'}
    token = None
    if pubid in al_pubs_tokens.keys():
        response = urllib.request.urlopen(al_pubs_tokens[pubid], timeout=10)
        picker_source = response.read()

        rawsps = next((line.strip() for line in picker_source.splitlines()
            if b'pickerParams.rawsps' in line), None)

        if rawsps:
            rawsps = rawsps.split(b"'")[1]
            picker_params = json.loads(base64.b64decode(rawsps).decode("utf-8"))
            token = picker_params.get('pickerToken', None)
            if token:
                token = '&pickerToken=' + token
        print("setting pickerToken '%s' for '%s'" % (token, pubid))


    for dt in sorted(dates_to_get):
        try:
            xdid = construct_xdid(pubid, dt)
            url = dt.strftime(puzsrc['urlfmt'])
            fn = "%s.%s" % (xdid, puzsrc['ext'])

            # AmuseLabs query urls require a pickerToken
            # TODO LaTimes queries require a pickerToken
            # TODO can we reuse the token across multiple dates?
            if token:
                url += token

            print("downloading '%s' from '%s'" % (fn, url))

            response = urllib.request.urlopen(url, timeout=10)
            content = response.read()

            # TODO is the downloaded file parsed as usual? or do we need to adjust the parsing logic, too
            ## TODO make this outf.write_file(fn, content)
            print(content)
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            print('%s %s: %s' % (xdid, err, url))
        except Exception as e:
            print(str(e))

#        sources_tsv += xd_sources_row(fn, url, todaystr)
        time.sleep(2)

    return max(actually_gotten) if actually_gotten else 0


download_puzzles(puzsrc, 'lat', [datetime.datetime(2022, 11, 1)])
