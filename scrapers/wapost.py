from scrapers import latimes


class wapost(latimes):
    FILENAME_PREFIX = 'wapost'
    RAW_CONTENT_TYPE = 'xml'
    DAILY_PUZZLE_URL = 'https://washingtonpost.as.arkadiumhosted.com/clients/washingtonpost-content/SundayCrossword/ebirnholz_%s.xml'
    DATE_FORMAT = '%y%m%d'
