from scrapers import latimes


class washingtonpost(latimes):
    FILENAME_PREFIX = 'washingtonpost'
    RAW_CONTENT_TYPE = 'xml'
    DAILY_PUZZLE_URL = 'https://washingtonpost.as.arkadiumhosted.com/clients/washingtonpost-content/SundayCrossword/ebirnholz_%s.xml'
    DATE_FORMAT = '%y%m%d'
