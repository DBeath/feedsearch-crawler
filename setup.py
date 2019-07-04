#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from codecs import open

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "Readme.md"), encoding="utf-8") as f:
    readme = f.read()


def build():
    os.system("python3 setup.py sdist bdist_wheel")


def publish():
    os.system("twine upload dist/*")


if sys.argv[-1] == "build":
    build()
    sys.exit()
elif sys.argv[-1] == "publish":
    build()
    publish()
    sys.exit()
elif sys.argv[-1] == "publish-only":
    publish()
    sys.exit()


packages = [
    "feedsearch_crawler",
    "feedsearch_crawler.crawler",
    "feedsearch_crawler.feed_spider",
]

required = [
    "aiohttp",
    "beautifulsoup4",
    "feedparser",
    "cchardet",
    "aiodns",
    "w3lib",
    "uvloop",
]

setup(
    name="feedsearch-crawler",
    version="0.1.3",
    description="Search sites for RSS, Atom, and JSON feeds",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="David Beath",
    author_email="davidgbeath@gmail.com",
    url="https://github.com/DBeath/feedsearch-crawler",
    license="MIT",
    packages=packages,
    install_requires=required,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
    ],
    python_requires=">=3.7",
)
