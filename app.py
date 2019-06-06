import asyncio
from feedsearch.feedsearch_crawler import FeedsearchSpider
import logging
import json
from pprint import pprint

urls = [
    "http://arstechnica.com",
    # "http://davidbeath.com",
    # "http://xkcd.com",
    # "http://jsonfeed.org",
    # "en.wikipedia.com",
    # "scientificamerican.com",
    # "newyorktimes.com"
]


def get_pretty_print(json_object: object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(",", ": "))


if __name__ == "__main__":
    logger = logging.getLogger("crawler")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    crawler = FeedsearchSpider(start_urls=urls, max_tasks=30, timeout=100000)
    asyncio.run(crawler.crawl())

    serialized = [item.serialize() for item in crawler.items]
    results = get_pretty_print(serialized)
    print(results)
    pprint([result["url"] for result in serialized])

    site_metas = [item.serialize() for item in crawler.site_metas]
    metas = get_pretty_print(site_metas)
    print(metas)
    # pprint(site_metas)

    pprint(crawler.dupefilter.fingerprints)
