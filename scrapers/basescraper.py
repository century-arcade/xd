from utils import URLUtils
from utils import DateUtils
from errors import ContentDownloadError
from errors import NoCrosswordError


class basescraper(object):
    def get_content(self, date):
        date = DateUtils.to_string(date, self.__class__.DATE_FORMAT)
        url = self.__class__.DAILY_PUZZLE_URL %date
        try:
            content = URLUtils.get_content(url)
        except ContentDownloadError:
            raise NoCrosswordError('Date: %s; URL: %s' %(date, url))
        return content
