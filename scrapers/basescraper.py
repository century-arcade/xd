from utils.general import URLUtils
from utils.general import DateUtils
from errors import NoCrosswordError
from errors import ContentDownloadError


class basescraper(object):
    def get_content(self, date):
        date = DateUtils.to_string(date, self.__class__.DATE_FORMAT)
        url = self.__class__.DAILY_PUZZLE_URL %date
        try:
            content = URLUtils.get_content(url)
        except ContentDownloadError:
            raise NoCrosswordError('Date: %s; URL: %s' %(date, url))
        return content
