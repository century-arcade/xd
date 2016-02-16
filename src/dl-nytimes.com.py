#!/usr/bin/python

import json
import urllib
import urllib2
import cookielib
import os.path
import sys
from datetime import date, datetime, timedelta


# constants
LOGIN = {
    'user': 'saul@example.com',
    'password': 'password'
}
HOME_URL = 'http://www.nytimes.com/crosswords/index.html'
AUTH_URL = 'https://myaccount.nytimes.com/auth/login?URI=http%3A%2F%2Fwww.nytimes.com%2Fcrosswords%2Findex.html'
AUTH_VALIDATE_URL = 'http://www.nytimes.com/svc/web-products/userinfo-v2.json'
TOKEN_GEN_URL = 'http://www.nytimes.com/svc/profile/token.json'
DAILY_PUZZLE_URL = 'http://www.nytimes.com/svc/crosswords/v2/puzzle/daily-%s.puz'
OUTPUT_DIR = './'

COOKIES = cookielib.CookieJar()
HANDLERS = [
    urllib2.HTTPRedirectHandler(),
    urllib2.HTTPCookieProcessor(COOKIES)
]
OPENER = urllib2.build_opener(*HANDLERS)

# utils
def generate_token():
    response = OPENER.open(TOKEN_GEN_URL)
    json_response = json.load(response)
    token = json_response['data']['token']
    return str(token)

def downloadFile(url, filename):
    if os.path.exists(filename):
        return
    try:
        response = OPENER.open(url)
        with open(filename, 'wb') as local_file:
            local_file.write(response.read())
    except urllib2.HTTPError, err:
        print "HTTP Error: %s ; URL: %s" %(err.code, url)
    except urllib2.URLError, err:
        print "URL Error: %s ; URL: %s" %(err.reason, url)

# main

def main(dates):
    # login
    print "Logging in..."
    data = urllib.urlencode({
        'userid': LOGIN['user'],
        'password': LOGIN['password'],
        'is_continue': '1',
        'remember': '0',
        'expires': '9999999999',
        'token': generate_token()
    })
    response = OPENER.open(AUTH_URL, data)

    # validate login
    response = OPENER.open(AUTH_VALIDATE_URL)
    json_response = json.load(response)
    user_id = json_response['data']['id']
    user_name = json_response['data']['name']
    is_loggedin = user_id and user_name
    if is_loggedin:
        print "Login successful! Logged in as '%s' (ID=%s)" %(user_name, user_id)
    else:
        print "Login failure!"
        exit(1)

# download .puz files

    for d in dates:
        puzzle_url = DAILY_PUZZLE_URL % d.strftime("%Y-%m-%d")
        puzzle_file = OUTPUT_DIR + d.strftime("%Y-%m-%d") + '.puz'
        print "Downloading... " + puzzle_file
        downloadFile(puzzle_url, puzzle_file)

d1 = datetime.strptime(sys.argv[1], "%Y-%m-%d")
d2 = datetime.strptime(sys.argv[2], "%Y-%m-%d")

# this will give you a list containing all of the dates
dd = [d1 + timedelta(days=x) for x in range((d2-d1).days + 1)]

main(dd)

