## Usage

1. Download RAW Format Crosswords:

    python main.py --download-raw --scraper latimes --outfile latraw.zip --from-date 2016-01-01 --to-date 2016-01-31`

2. Download XD Format Crosswords:

    python main.py --download-xd --scraper latimes --outfile lat2016.zip  --from-date 2016-01-01 --to-date 2016-01-31`

3. Convert raw crosswords to .xd format crosswords:

    python main.py --raw-to-xd -s latimes -i latraw.zip -o lat2016.zip

## How to write and plug in a new scraper

* Implement the following methods:

    * get_content(self, date)

This method should be able to build a website specific URL and retrive content from the web (you can use URLUtils to facilitate download)
Raise NoCrosswordError or ContentDownloadError appropriately, just in case.

    * build_crossword(self, content)

This method should build and return a valid Crossword instance (import from crosswords.py module).

    * RAW_CONTENT_TYPE, FILENAME_PREFIX

These constants are to be overridden as well.

* Import your scraper in scrapers/__init__.py so that it is directly accessible

* After this you can just execute main.py as you usually would and everything should work as is.

* The Core module is capable to converting and writing RAW/XD Crossword files with just these info.

* If the new scraper has any dependencies (like on 3rd party Python modules), make sure to add it to the requirements.txt file.

