import boto3

from xdfile.utils import log

def xd_send_email(destaddr, fromaddr='admin@xd.saul.pw', subject='', body=''):
    client = boto3.client('ses')
    log("sending email to %s (subject '%s')" % (destaddr, subject))
    try:
        response = client.send_email(
                Source=fromaddr,
                Destination= {'ToAddresses': [ destaddr ] },
                Message={ 'Subject': { 'Data': subject },
                'Body': { 'Text': { 'Data': body } } })
        return response
    except Exception as e:
        log(str(e))
        return None


