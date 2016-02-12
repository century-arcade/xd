from scrapers import basescraper


class chronicle(basescraper):
    FILENAME_PREFIX = 'chronicle'
    RAW_CONTENT_TYPE = 'puz'
    DAILY_PUZZLE_URL = 'http://chronicle.com/items/biz/puzzles/%s.puz'
    DATE_FORMAT = '%Y%m%d'
