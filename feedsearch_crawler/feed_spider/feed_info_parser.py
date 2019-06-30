import time
from datetime import datetime, date
from types import AsyncGeneratorType
from typing import Tuple, List, Union, Dict

import feedparser
import udatetime
from bs4 import BeautifulSoup
from yarl import URL

from feedsearch_crawler.crawler import ItemParser, Request, Response, to_string
from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.lib import parse_header_links


class FeedInfoParser(ItemParser):
    async def parse_item(
        self, request: Request, response: Response, *args, **kwargs
    ) -> AsyncGeneratorType:
        self.logger.info("Parsing: Feed %s", response.url)

        content_type = response.headers.get("content-type", "")

        item = FeedInfo(response.url, content_type)

        # Check link headers first for WebSub content discovery
        # https://www.w3.org/TR/websub/#discovery
        if response.headers:
            item.hubs, item.self_url = self.header_links(response.headers)

        if "type" not in kwargs:
            raise ValueError("type keyword argument is required")

        try:
            data_type = kwargs["type"]
            if data_type == "json":
                item.content_type = "application/json"
                self.parse_json(item, response.json)
            elif data_type == "xml":
                self.parse_xml(item, response.data, response.encoding, response.headers)
                if not item.content_type:
                    item.content_type = "text/xml"
        except Exception as e:
            self.logger.exception("Failed to parse feed %s, Error: %s", item, e)

        if item.favicon and self.spider.favicon_data_uri:
            yield self.spider.follow(item.favicon, self.spider.create_data_uri)

        item.content_length = response.content_length
        self.score_item(item, response.history[0])
        yield item

    def parse_xml(
        self, item: FeedInfo, data: str, encoding: str, headers: Dict
    ) -> None:
        """
        Get info from XML (RSS or ATOM) feed.
        """

        # Parse data with feedparser
        # Don't wrap this in try/except, feedparser eats errors and returns bozo instead
        parsed = self.parse_raw_data(data, encoding, headers)
        if not parsed or parsed.get("bozo") == 1:
            if not isinstance(
                parsed.get("bozo_exception"), feedparser.CharacterEncodingOverride
            ):
                item.bozo = 1
                self.logger.warning("No valid feed data for %s", item)
                return

        feed = parsed.get("feed")
        if not feed:
            return

        # Only search if no hubs already present from headers
        if not item.hubs:
            item.hubs, item.self_url = self.websub_links(feed)

        if item.hubs and item.self_url:
            item.is_push = True

        item.version = parsed.get("version")
        item.title = self.feed_title(feed)
        item.description = self.feed_description(feed)

        try:
            dates = []
            now_date = datetime.utcnow().date()

            for entry in parsed.get("entries", None):
                if entry.get("published_parsed"):
                    published = datetime.fromtimestamp(
                        time.mktime(entry.get("published_parsed", ""))
                    )
                    if published.date() <= now_date:
                        dates.append(published)

                if entry.get("updated_parsed"):
                    updated = datetime.fromtimestamp(
                        time.mktime(entry.get("updated_parsed", ""))
                    )
                    if updated.date() <= now_date:
                        dates.append(updated)

            item.last_updated = sorted(dates, reverse=True)[0]
        except Exception as e:
            self.logger.error("Unable to get feed published date: %s", e)
            pass

    def parse_json(self, item: FeedInfo, data: dict) -> None:
        """
        Get info from JSON feed.

        :param item: FeedInfo object
        :param data: JSON object
        :return: None
        """
        item.version = data.get("version")
        if "https://jsonfeed.org/version/" not in item.version:
            item.bozo = 1
            return

        item.title = data.get("title")
        item.description = data.get("description")

        favicon = data.get("favicon")
        if favicon:
            item.favicon = URL(favicon)

        # Only search if no hubs already present from headers
        if not item.hubs:
            try:
                item.hubs = list(hub.get("url") for hub in data.get("hubs", []))
            except (IndexError, AttributeError):
                pass

        if item.hubs:
            item.is_push = True

        try:
            dates = []
            now_date: date = datetime.utcnow().date()

            for entry in data.get("items"):
                if entry.get("date_published"):
                    published: datetime = udatetime.from_string(entry["date_published"])
                    if published.date() <= now_date:
                        dates.append(published)

                if entry.get("date_modified"):
                    modified: datetime = udatetime.from_string(entry["date_modified"])
                    if modified.date() <= now_date:
                        dates.append(modified)

            item.last_updated = sorted(dates, reverse=True)[0]
        except Exception as e:
            self.logger.error("Unable to get feed published date: %s", e)
            pass

    def parse_raw_data(
        self, raw_data: Union[str, bytes], encoding: str = "utf-8", headers: Dict = None
    ) -> Dict:
        """
        Loads the raw RSS/Atom XML data.
        Returns feedparser Dict.
        https://pythonhosted.org/feedparser/

        :param raw_data: RSS/Atom XML feed
        :type raw_data: str
        :param encoding: Character encoding of raw_data
        :type encoding: str
        :param headers: Response headers
        :return: Dict
        """
        if not encoding:
            encoding = "utf-8"

        h = {}
        if headers:
            if isinstance(headers, dict):
                h = headers
            else:
                try:
                    h.update({k.lower(): v for (k, v) in headers.items()})
                except KeyError:
                    pass

            h.pop("content-encoding", None)

        try:
            start = time.perf_counter()

            if isinstance(raw_data, str):
                raw_data: bytes = raw_data.encode(encoding)

            content_length = len(raw_data)

            # We want to pass data into feedparser as bytes, otherwise if we accidentally pass a url string
            # it will attempt a fetch
            data = feedparser.parse(raw_data, response_headers=h)

            dur = int((time.perf_counter() - start) * 1000)
            self.logger.debug("Feed Parse: size=%s dur=%sms", content_length, dur)

            return data
        except Exception as e:
            self.logger.exception("Could not parse RSS data: %s", e)

    def feed_title(self, feed: dict) -> str:
        """
        Get feed title

        :param feed: feed dict
        :return: str
        """
        title = feed.get("title", None)
        if not title:
            return ""
        return self.clean_title(title)

    def clean_title(self, title: str) -> str:
        """
        Cleans title string, and shortens if too long.
        Have had issues with dodgy feed titles.

        :param title: Title string
        :return: str
        """
        try:
            title = BeautifulSoup(title, self.spider.htmlparser).get_text()
            if len(title) > 1024:
                title = title[:1020] + "..."
            return title
        except Exception as ex:
            self.logger.exception("Failed to clean title: %s", ex)
            return ""

    @staticmethod
    def feed_description(feed: dict) -> str:
        """
        Get feed description.

        :param feed: feed dict
        :return: str
        """
        subtitle = feed.get("subtitle", None)
        if subtitle:
            return subtitle
        return feed.get("description", None)

    @staticmethod
    def websub_links(feed: dict) -> Tuple[List[str], str]:
        """
        Returns a tuple containing the hub url and the self url for
        a parsed feed.

        :param feed: An RSS feed parsed by feedparser
        :type feed: dict
        :return: tuple
        """
        links = feed.get("links", [])
        return FeedInfoParser.find_hubs_and_self_links(links)

    @staticmethod
    def header_links(headers: dict) -> Tuple[List[str], str]:
        """
        Attempt to get self and hub links from HTTP headers
        https://www.w3.org/TR/websub/#x4-discovery

        :param headers: Dict of HTTP headers
        :return: None
        """
        link_header = headers.get("Link")
        links: list = []
        if link_header:

            links = parse_header_links(to_string(link_header))
        return FeedInfoParser.find_hubs_and_self_links(links)

    @staticmethod
    def find_hubs_and_self_links(links: List[dict]) -> Tuple[List[str], str]:
        """
        Parses a list of links into self and hubs urls

        :param links: List of parsed HTTP Link Dicts
        :return: Tuple
        """
        hub_urls: List[str] = []
        self_url: str = ""

        if not links:
            return [], ""

        for link in links:
            try:
                if link["rel"] == "hub":
                    href: str = link["href"]
                    hub_urls.append(href)
                elif link["rel"] == "self":
                    self_url = link["href"]
            except KeyError:
                continue

        return hub_urls, self_url

    @staticmethod
    def score_item(item: FeedInfo, original_url: URL):
        score = 0

        url_str = str(item.url)

        # -- Score Decrement --

        if original_url:
            host = original_url.host
            if host.startswith("www."):
                host = host[len("www.") :]

            if host not in item.url.host:
                score -= 20

        # Decrement the score by every extra path in the url
        parts_len = len(item.url.parts)
        if parts_len > 2:
            score -= (parts_len - 2) * 2

        if item.bozo:
            score -= 20
        if not item.description:
            score -= 10
        if "georss" in url_str:
            score -= 10
        if "alt" in url_str:
            score -= 7
        if "comments" in url_str or "comments" in item.title.lower():
            score -= 15

        # -- Score Increment --
        if item.url.scheme == "https":
            score += 10
        if item.is_push:
            score += 10
        if "index" in url_str:
            score += 15

        kw = ["atom", "rss", ".xml", "feed", "rdf"]
        for p, t in zip(range(len(kw) * 2, 0, -2), kw):
            if t in url_str:
                score += p

        item.score = score
