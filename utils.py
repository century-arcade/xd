import os
import urllib2
import zipfile

from datetime import timedelta
from datetime import datetime

from errors import ContentDownloadError


class URLUtils(object):
    @staticmethod
    def get_content(url):
        try:
            response = urllib2.urlopen(url)
            return response.read()
        except (urllib2.HTTPError, urllib2.URLError) as err:
            raise ContentDownloadError('%s: %s - %s' %(url, err.code, err.reason))


class DateUtils(object):
    DEFAULT_DATE_FORMAT = '%Y-%m-%d'

    @staticmethod
    def today():
        return datetime.today()

    @staticmethod
    def from_string(string, format=DEFAULT_DATE_FORMAT):
        return datetime.strptime(string, format)

    @staticmethod
    def to_string(date, format=DEFAULT_DATE_FORMAT):
        return date.strftime(format)

    @staticmethod
    def is_valid(string, format=DEFAULT_DATE_FORMAT):
        try:
            DateUtils.from_string(string, format)
        except ValueError:
            return False
        return True

    @staticmethod
    def get_dates_between(from_date, to_date, format=DEFAULT_DATE_FORMAT):
        if isinstance(from_date, basestring):
            from_date = DateUtils.from_string(from_date, format)
        if isinstance(to_date, basestring):
            to_date = DateUtils.from_string(to_date, format)

        if from_date == to_date:
            return [from_date]
        elif from_date > to_date:
            temp = from_date
            from_date = to_date
            to_date = from_date

        days_diff = (to_date - from_date).days + 1
        return [from_date + timedelta(days=x) for x in range(days_diff)]


class ZipUtils(object):
    @staticmethod
    def read(target_zip_file):
        with zipfile.ZipFile(target_zip_file, 'r') as zip:
            for zip_info in zip.infolist():
                filename = zip_info.filename
                content = zip.read(zip_info)
                yield (filename, content)

    @staticmethod
    def append(content, file_name, target_zip_file):
        zip_info = zipfile.ZipInfo()
        zip_info.volume = 0
        zip_info.filename = file_name
        zip_info.external_attr = 0444 << 16L
        zip_info.compress_type = zipfile.ZIP_DEFLATED

        with zipfile.ZipFile(target_zip_file, 'a') as zip:
            zip.writestr(zip_info, content)
