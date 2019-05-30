from bs4 import BeautifulSoup

from crawler.crawler import Crawler
from feedsearch.feed import Feed
from crawler.request import Request
from crawler.response import Response
from feedsearch.dupefilter import NoQueryDupeFilter


class FeedsearchSpider(Crawler):
    dupefilter = NoQueryDupeFilter()

    async def parse(self, request: Request, response: Response):
        url = response.url
        content_type = response.headers.get("content-type")

        if response.json:
            if "version" in response.json:
                item = Feed(str(response.url), content_type)
                item.process_data(response.json, response)
                yield item
                return
        else:
            print(f"No content type at URL: {url}")

        if not response.text:
            print(f"No text at {url}")
            return

        soup = BeautifulSoup(response.text, features="html.parser")
        data = response.text.lower()[:500]

        if not data:
            return

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            item = Feed(str(response.url), content_type)
            item.process_data(response.text, response)
            yield item
            return

        link_tags = soup.find_all("link")
        if not link_tags:
            return
        for link in link_tags:
            if link.get("type") in [
                "application/rss+xml",
                "text/xml",
                "application/atom+xml",
                "application/x.atom+xml",
                "application/x-atom+xml",
                "application/json",
            ]:
                href = link.get("href", "")
                yield self.follow(href, self.parse, response)
