import os
import boto3

from xdfile.utils import log, info, debug, error


boto3.set_stream_logger('botocore')

def xd_send_email(destaddr, fromaddr='admin@xd.saul.pw', subject='', body=''):
    client = boto3.client('ses', region_name=os.environ['REGION'])
    info("sending email to %s (subject '%s')" % (destaddr, subject))
    try:
        response = client.send_email(
                Source=fromaddr,
                Destination= {'ToAddresses': [ destaddr ] },
                Message={ 'Subject': { 'Data': subject },
                'Body': { 'Text': { 'Data': body } } })
        return response
    except Exception as e:
        error("xd_send_email(): %s" % str(e))
        return None


def create_merge_request():
    import urllib.request
    import urllib.parse
    parms = {
        'id': '',
        'source_branch': '',
        'target_branch': '',
        'title': '',
    }

    url = 'https://gitlab.com/projects/:id/merge_requests'
    r = urllib.request.urlopen(url, urllib.parse.urlencode(parms))
    info('create_merge_request POST: %s' % r.getcode())
