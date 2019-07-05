import asyncio
import logging
import json
import time
from pprint import pprint
from feedsearch_crawler import search, FeedsearchSpider, output_opml
from datetime import datetime
import collections

urls = [
    "arstechnica.com",
    # "http://davidbeath.com",
    # "http://xkcd.com",
    # "http://jsonfeed.org",
    # "en.wikipedia.com",
    # "scientificamerican.com",
    # "newyorktimes.com",
    # "https://www.dancarlin.com",
    # "https://www.hanselminutes.com/",
    # "nytimes.com",
    # "https://www.jeremydaly.com/serverless-microservice-patterns-for-aws/",
    # "feedhandbook.com",
    # "https://americanaffairsjournal.org/2019/05/ubers-path-of-destruction/",
    # "localhost:8080/test",
    # "theatlantic.com",
    # "nypost.com"
]


def get_pretty_print(json_object: object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(",", ": "))


# @profile()
def run_crawl():
    user_agent = "Mozilla/5.0 Compatible"

    # headers = {
    #     "User-Agent": "Feedsearch Bot",
    #     "X-Testing-Header": "Testing,testing,123",
    # }

    crawler = FeedsearchSpider(
        concurrency=10,
        total_timeout=20,
        request_timeout=5,
        user_agent=user_agent,
        favicon_data_uri=False,
        max_depth=4,
        # full_crawl=True,
        delay=0,
        # headers=headers,
    )
    crawler.start_urls = urls
    asyncio.run(crawler.crawl())
    # asyncio.run(crawler.crawl(urls[0]))

    serialized = [item.serialize() for item in crawler.items]

    # items = search(urls[0], concurrency=40, try_urls=False, favicon_data_uri=False)
    # serialized = [item.serialize() for item in items]

    results = get_pretty_print(serialized)
    print(results)

    site_metas = [item.serialize() for item in crawler.site_metas]
    metas = get_pretty_print(site_metas)
    print(metas)
    # pprint(site_metas)

    pprint(crawler.favicons)
    pprint(crawler._duplicate_filter.fingerprints)

    print(output_opml(list(crawler.items)).decode())

    pprint([result["url"] for result in serialized])
    pprint(crawler.get_stats())

    print(f"Feeds found: {len(crawler.items)}")
    print(f"SiteMetas: {len(crawler.site_metas)}")
    print(f"Favicons fetched: {len(crawler.favicons)}")
    # pprint(crawler.queue_wait_times)


if __name__ == "__main__":
    logger = logging.getLogger("feedsearch_crawler")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]"
    )
    ch.setFormatter(formatter)
    fl = logging.FileHandler(
        f"/home/dbeath/code/feedsearch-crawler/logs/feedsearch_crawl_{datetime.utcnow().isoformat()}"
    )
    fl.setLevel((logging.DEBUG))
    fl.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fl)

    start = time.perf_counter()
    run_crawl()
    duration = int((time.perf_counter() - start) * 1000)
    print(f"Entire process ran in {duration}ms")
