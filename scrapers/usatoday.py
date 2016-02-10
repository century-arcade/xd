from scrapers import theglobeandmail


class usatoday(theglobeandmail):
    FILENAME_PREFIX = 'usatoday'
    RAW_CONTENT_TYPE = 'xml'
    DAILY_PUZZLE_URL = 'http://www.uclick.com/puzzles/usaon/data/usaon%s-data.xml'
    DATE_FORMAT = '%y%m%d'
