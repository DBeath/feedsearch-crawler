from typing import Tuple

import feedparser
from bs4 import BeautifulSoup

from crawler.item import Item
from crawler.response import Response
from feedsearch.lib import *


class Feed(Item):
    score: int = ""
    url: str = ""
    content_type: str = ""
    version: str = ""
    title: str = ""
    hubs: List[str] = []
    description: str = ""
    is_push: bool = False
    self_url: str = ""
    bozo: int = 0
    favicon: str = ""

    def serialize(self):
        return dict(
            url=self.url,
            title=self.title,
            version=self.version,
            score=self.score,
            hubs=self.hubs,
            description=self.description,
            is_push=self.is_push,
            self_url=self.self_url,
            favicon=self.favicon,
            content_type=self.content_type,
            bozo=self.bozo,
        )

    def __init__(self, url: str, content_type: str):
        super().__init__()
        self.url = url
        self.content_type = content_type

    def process_data(self, data: Union[dict, str], response: Response):
        self.logger.info("Parsing feed %s", self.url)

        # Check link headers first for WebSub content discovery
        # https://www.w3.org/TR/websub/#discovery
        if response.headers:
            self.hubs, self.self_url = self.header_links(response.headers)

        # Try to parse data as JSON
        if isinstance(data, dict):
            self.content_type = "application/json"
            self.parse_json(data)
            self.calculate_score()
            return

        try:
            self.parse_xml(data)
            self.calculate_score()
        except Exception as e:
            self.logger.exception("Failed to parse feed %s, Error: %s", self.url, e)

    def calculate_score(self):
        try:
            self.score = self.url_feed_score(self.url)
        except Exception as e:
            self.logger.exception(
                "Failed to create score for feed %s, Error: %s", self.url, e
            )

    def parse_xml(self, data: str) -> None:
        """
        Get info from XML (RSS or ATOM) feed.
        """

        # Parse data with feedparser
        # Don't wrap this in try/except, feedparser eats errors and returns bozo instead
        parsed = self.parse_feed(data)
        if not parsed or parsed.get("bozo") == 1:
            self.bozo = 1
            self.logger.warning("No valid feed data in %s", self.url)
            return

        feed = parsed.get("feed")

        # Only search if no hubs already present from headers
        if not self.hubs:
            self.hubs, self.self_url = self.websub_links(feed)

        if self.hubs and self.self_url:
            self.is_push = True

        self.version = parsed.get("version")
        self.title = self.feed_title(feed)
        self.description = self.feed_description(feed)

    def parse_json(self, data: dict) -> None:
        """
        Get info from JSON feed.

        :param data: JSON object
        :return: None
        """
        self.version = data.get("version")
        if "https://jsonfeed.org/version/" not in self.version:
            self.bozo = 1
            return

        self.title = data.get("title")
        self.description = data.get("description")

        favicon = data.get("favicon")
        if favicon:
            self.favicon = favicon

        # Only search if no hubs already present from headers
        if not self.hubs:
            try:
                self.hubs = list(hub.get("url") for hub in data.get("hubs", []))
            except (IndexError, AttributeError):
                pass

        if self.hubs:
            self.is_push = True

    @staticmethod
    def parse_feed(text: str) -> dict:
        """
        Parse feed with feedparser.

        :param text: Feed string
        :return: dict
        """
        return feedparser.parse(text)

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
            title = BeautifulSoup(title, "html.parser").get_text()
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
        return Feed.find_hubs_and_self_links(links)

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
            print(link_header)
            links = parse_header_links(link_header.decode("utf-8"))
        return Feed.find_hubs_and_self_links(links)

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
    def url_feed_score(url: str, original_url: str = "") -> int:
        """
        Return a Score based on estimated relevance of the feed Url
        to the original search Url

        :param url: Feed Url
        :param original_url: Searched Url
        :return: Score integer
        """
        score = 0

        if original_url:
            url_domain = get_site_root(url)
            original_domain = get_site_root(original_url)

            if original_domain not in url_domain:
                score -= 17

        if "comments" in url:
            score -= 15
        if "georss" in url:
            score -= 9
        if "alt" in url:
            score -= 7
        kw = ["atom", "rss", ".xml", "feed", "rdf"]
        for p, t in zip(range(len(kw) * 2, 0, -2), kw):
            if t in url:
                score += p
        if url.startswith("https"):
            score += 9
        return score
