from scrapers import basescraper


class newsday(basescraper):
    FILENAME_PREFIX = 'newsday'
    RAW_CONTENT_TYPE = 'pdf'
    DAILY_PUZZLE_URL = 'http://www.brainsonly.com/servlets-newsday-crossword/newsdaycrosswordPDF?pm=pdf&data=%%3CNAME%%3E%s%%3C%%2FNAME%%3E%%3CTYPE%%3E2%%3C%%2FTYPE%%3E'
    DATE_FORMAT = '%y%m%d'
