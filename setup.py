"""Setup module for xdfile"""

from setuptools import setup
from os import path

package_root = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open('README.md') as readme:
    long_description = readme.read()

with open('VERSION') as version_file:
    version = version_file.read().strip()

setup(
    name='xdfile',
    version=version,
    description='A futureproof crossword corpus toolset',
    long_description=long_description,
    url='http://xd.saul.pw',
    python_requires='>=3.5',
    author='Saul Pwanson',
    author_email='xd@saul.pw',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Crossword Nerds',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],

    keywords='crossword puzzles',

    packages=['xdfile'],

    install_requires=['crossword', 'puzpy'],

)
