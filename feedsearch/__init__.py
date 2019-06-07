import logging

from .feedsearch import search_async, search

logging.getLogger("feedsearch.crawler").addHandler(logging.NullHandler())
