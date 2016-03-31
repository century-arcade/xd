# Contributing to xdfile

## setting up the environment

Install dependencies:

        $ pip install puzpy crossword 
        $ pip install pytest tox flake8

Setup tox:

        $ tox setup

This creates a virtualenv and runs tests against the package. A couple points:

* Eventually, **pip install -e dev** will get all dependencies.
* tox requires MANIFEST.in to locate files to copy into the virtualenv test environments.

## running tests

To execute everything for packaging and testing:

        $ tox

To just run unit tests:

        $ python setup.py test

## code style

Line length: 90-ish is OK, flake8 is set to 95.

## packaging and setup

Test the setup with a dry run:

        $ python setup.py install -n

