from scrapers import basescraper
from errors import ScraperNotImplementedError


class wsj(basescraper):
    FILENAME_PREFIX = 'wsj'
    RAW_CONTENT_TYPE = 'pdf'
    DAILY_PUZZLE_URL = 'http://www.wsj.com/public/resources/documents/puzzle%s.pdf'
    DATE_FORMAT = '%Y%m%d'

    def build_crossword(self, content):
        raise ScraperNotImplementedError()
