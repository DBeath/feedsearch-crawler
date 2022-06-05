import asyncio
import logging
import json
import time
from pprint import pprint
from feedsearch_crawler import search, FeedsearchSpider, output_opml, sort_urls
from feedsearch_crawler.crawler import coerce_url
from datetime import datetime
import collections

urls = [
    "arstechnica.com",
    # "https://davidbeath.com",
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
    # "nypost.com",
    # "https://www.washingtonpost.com",
    # "localhost:5000",
    # "latimes.com",
    # "http://feeds.washingtonpost.com/rss/rss_fact-checker?noredirect=on",
    # "http://tabletopwhale.com/index.html"
    # "www.vanityfair.com",
    # "bloomberg.com",
    # "http://www.bloomberg.com/politics/feeds/site.xml",
    # "propublica.org"
    # "npr.org",
    # "rifters.com",
    # "https://www.bbc.co.uk/podcasts"
    # "https://www.bbc.co.uk/programmes/p02nrsln/episodes/downloads",
    # "https://breebird33.tumblr.com/",
    # "https://neurocorp.tumblr.com/",
    # "https://breebird33.tumblr.com/rss"
    # "https://resel.fr/rss-news"
    # "https://muhammadraza.me"
    # "https://www.franceinter.fr/rss/a-la-une.xml",
    # "harpers.org",
    # "slashdot.com",
    # "https://bearblog.dev",
    # "aeon.co",
    # "https://davidgerard.co.uk/blockchain/"
    # "raymii.org/s/"
    # "stratechery.com",
    # "www.internet-law.de",
    # "https://medium.com/zendesk-engineering/the-joys-of-story-estimation-cda0cd807903",
    # "https://danwang.co/",
    # "http://matthewdickens.me/podcasts/TWIS-feed.xml"
]


def get_pretty_print(json_object: object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(",", ": "))


# @profile()
def run_crawl():
    # user_agent = "Mozilla/5.0 (Compatible; Bot)"
    user_agent = "Mozilla/5.0 (Compatible; Feedsearch Bot)"
    # user_agent = "curl/7.58.0"
    # user_agent = (
    #     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0"
    # )
    # user_agent = (
    #     "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    # )

    # headers = {
    #     "User-Agent": user_agent,
    #     "DNT": "1",
    #     "Upgrade-Insecure-Requests": "1",
    #     "Accept-Language": "en-US,en;q=0.5",
    #     "Accept-Encoding": "gzip, deflate, br",
    #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    #     "Referrer": "https://www.google.com/",
    # }

    crawler = FeedsearchSpider(
        concurrency=10,
        total_timeout=30,
        request_timeout=30,
        user_agent=user_agent,
        # headers=headers,
        favicon_data_uri=False,
        max_depth=5,
        max_retries=3,
        ssl=True,
        full_crawl=False,
        delay=0,
        try_urls=True,
    )
    crawler.start_urls = urls
    # crawler.allowed_domains = create_allowed_domains(urls)
    asyncio.run(crawler.crawl())
    # asyncio.run(crawler.crawl(urls[0]))
    # items = search(urls, crawl_hosts=True)

    items = sort_urls(list(crawler.items))

    serialized = [item.serialize() for item in items]

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

    print(output_opml(items).decode())

    pprint([result["url"] for result in serialized])
    pprint(crawler.get_stats())

    print(f"Feeds found: {len(items)}")
    print(f"SiteMetas: {len(crawler.site_metas)}")
    print(f"Favicons fetched: {len(crawler.favicons)}")
    # pprint(crawler.queue_wait_times)
    pprint(list((x.score, x.url) for x in items))


def create_allowed_domains(urls):
    domain_patterns = []
    for url in urls:
        url = coerce_url(url)
        host = url.host
        pattern = f"*.{host}"
        domain_patterns.append(host)
        domain_patterns.append(pattern)
    return domain_patterns


if __name__ == "__main__":
    logger = logging.getLogger("feedsearch_crawler")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s [in %(pathname)s:%(lineno)d]"
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
