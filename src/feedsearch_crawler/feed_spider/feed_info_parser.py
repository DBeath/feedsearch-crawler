import logging
from datetime import datetime, date, timezone
from statistics import mean
from typing import AsyncGenerator, Tuple, List, Union, Dict, Any

import feedparser
import time
from aiohttp import hdrs
from bs4 import BeautifulSoup
from yarl import URL

from feedsearch_crawler.crawler import ItemParser, Request, Response, to_string
from feedsearch_crawler.crawler.lib import headers_to_dict, remove_www
from feedsearch_crawler.feed_spider.favicon import Favicon
from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.lib import (
    parse_header_links,
    datestring_to_utc_datetime,
    parse_date_with_comparison,
    create_content_type,
    ParseTypes,
)

logger = logging.getLogger(__name__)


class FeedInfoParser(ItemParser):
    async def parse_item(
        self, request: Request, response: Response, *args, **kwargs
    ) -> AsyncGenerator:
        logger.info("Parsing: Feed %s", response.url)

        if "parse_type" not in kwargs:
            raise ValueError("type keyword argument is required")

        parse_type = kwargs["parse_type"]

        content_type = create_content_type(
            parse_type,
            response.encoding,
            response.headers.get(hdrs.CONTENT_TYPE, "").lower(),
        )

        item = FeedInfo(url=response.url, content_type=content_type)

        # Check link headers first for WebSub content discovery
        # https://www.w3.org/TR/websub/#discovery
        if response.headers:
            hubs, self_url = self.header_links(response.headers)
            item.hubs = hubs
            item.self_url = URL(self_url)

        try:
            valid_feed = False

            if parse_type == ParseTypes.JSON:
                valid_feed = self.parse_json(item, response.json)
            elif parse_type == ParseTypes.XML:
                valid_feed = self.parse_xml(
                    item,
                    response.data,
                    response.encoding,
                    headers_to_dict(response.headers),
                )

            if not valid_feed:
                logger.debug("Invalid Feed: %s", item)
                return
        except Exception as e:
            logger.exception("Failed to parse feed %s, Error: %s", item, e)
            return

        if item.favicon and self.crawler.favicon_data_uri:
            favicon = Favicon(
                url=item.favicon,
                priority=1,
            )
            yield self.follow(
                item.favicon,
                self.crawler.parse_favicon_data_uri,
                cb_kwargs=dict(favicon=favicon),
            )

        self.validate_self_url(item)

        item.content_length = response.content_length
        self.score_item(item, response.history[0])
        yield item

    def parse_xml(
        self, item: FeedInfo, data: Union[str, bytes], encoding: str, headers: Dict
    ) -> bool:
        """
        Get info from XML (RSS or ATOM) feed.
        """

        # Parse data with feedparser
        try:
            parsed: dict = self.parse_raw_data(data, encoding, headers)
        except Exception as e:
            logger.exception("Unable to parse feed %s: %s", item, e)
            return False

        if not parsed:
            logger.warning("No valid feed data for %s", item)
            return False

        if parsed.get("bozo") == 1:
            bozo_exception = parsed.get("bozo_exception", None)
            if isinstance(bozo_exception, feedparser.CharacterEncodingOverride):
                item.bozo = 1
            elif isinstance(
                bozo_exception,
                (feedparser.CharacterEncodingUnknown, feedparser.UndeclaredNamespace),
            ):
                logger.warning("No valid feed data for %s: %s", item, bozo_exception)
                return False

        feed = parsed.get("feed")
        if not feed:
            return False
        if not parsed.get("entries"):
            return False

        # Only search if no hubs already present from headers
        if not item.hubs:
            item.hubs, item.self_url = self.websub_links(feed)

        if item.hubs and item.self_url:
            item.is_push = True

        item.version = parsed.get("version", "")
        item.title = self.feed_title(feed)
        item.description = self.feed_description(feed)
        item.is_podcast = self.is_podcast(parsed)

        try:
            dates = []
            now_date = datetime.now(timezone.utc).date()

            entries = parsed.get("entries", [])
            item.item_count = len(entries)

            # Extract locale/language from feed if available
            locale = feed.get("language")

            dates.extend(
                FeedInfoParser.entry_dates(
                    entries, ["updated", "published"], now_date, locale
                )
            )

            if dates:
                item.last_updated = sorted(dates, reverse=True)[0]
                item.velocity = self.entry_velocity(dates)
            elif feed.get("updated"):
                # Use comparison for feed-level date as well
                feed_date = parse_date_with_comparison(
                    feed.get("updated"), feed.get("updated_parsed"), locale
                )
                item.last_updated = (
                    feed_date
                    if feed_date
                    else datestring_to_utc_datetime(feed.get("updated"))
                )
        except Exception as e:
            logger.exception("Unable to get feed published date: %s", e)
            pass

        return True

    def parse_json(self, item: FeedInfo, data: dict) -> bool:
        """
        Get info from JSON feed.

        :param item: FeedInfo object
        :param data: JSON object
        :return: None
        """
        item.version = data.get("version", "")
        if "https://jsonfeed.org/version/" not in item.version:
            item.bozo = 1
            return False

        if not data.get("items"):
            return False

        item.title = data.get("title", "")
        item.description = data.get("description", "")

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
            now_date: date = datetime.now(timezone.utc).date()

            entries = data.get("items", [])
            item.item_count = len(entries)

            # Extract locale/language from feed if available
            locale = data.get("language")

            # Note: JSON feeds don't have *_parsed fields, so comparison will
            # only use dateutil parsing (parsed_tuple will be None)
            dates.extend(
                FeedInfoParser.entry_dates(
                    entries, ["date_modified", "date_published"], now_date, locale
                )
            )

            if dates:
                item.last_updated = sorted(dates, reverse=True)[0]
                item.velocity = self.entry_velocity(dates)
        except Exception as e:
            logger.exception("Unable to get feed published date: %s", e)
            pass

        return True

    @staticmethod
    def parse_raw_data(
        raw_data: Union[str, bytes], encoding: str = "utf-8", headers: Dict = None
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
                raw_data = raw_data.encode(encoding)

            raw_data = raw_data.strip()
            content_length = len(raw_data)

            # We want to pass data into feedparser as bytes, otherwise if we accidentally pass a url string
            # it will attempt a fetch
            data = feedparser.parse(raw_data, response_headers=h)

            dur = int((time.perf_counter() - start) * 1000)
            logger.debug("Feed Parse: size=%s dur=%sms", content_length, dur)

            return data
        except Exception as e:
            logger.exception("Could not parse RSS data: %s", e)

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
            title = BeautifulSoup(title, self.crawler.htmlparser).get_text()
            if len(title) > 1024:
                title = title[:1020] + "..."
            return title
        except Exception as ex:
            logger.exception("Failed to clean title: %s", ex)
            return ""

    @staticmethod
    def is_podcast(parsed: dict) -> bool:
        """
        Check if the feed is a Podcast.

        :param parsed: Feedparser dict
        :return: bool
        """
        if not parsed:
            return False

        has_itunes: bool = "itunes" in parsed.get("namespaces", {})

        has_enclosures = False

        for entry in parsed.get("entries", []):
            for enclosure in entry.get("enclosures", []):
                if "audio" in enclosure.get("type", ""):
                    has_enclosures = True

        return has_itunes and has_enclosures

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
    def score_item(item: FeedInfo, original_url: URL) -> None:
        score = 0

        url_str = str(item.url).lower()

        # -- Score Decrement --

        if original_url:
            host = remove_www(original_url.host)

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
        if "feedburner" in url_str:
            score -= 10

        # -- Score Increment --
        if item.url.scheme == "https":
            score += 10
        if item.is_push:
            score += 10
        if "index" in url_str:
            score += 30

        if "comments" in url_str or "comments" in item.title.lower():
            score -= 15
        else:
            score += int(item.velocity)

        if any(map(url_str.count, ["/home", "/top", "/most", "/magazine"])):
            score += 10

        kw = ["atom", "rss", ".xml", "feed", "rdf"]
        for p, t in zip(range(len(kw) * 2, 0, -2), kw):
            if t in url_str:
                score += p

        item.score = score

    @staticmethod
    def entry_dates(
        entries: List[Dict],
        date_names: List[str],
        current_date: date,
        locale: Union[str, None] = None,
    ) -> Any:
        """
        Return published or updated dates from feed entries.

        Compares feedparser's parsed dates with dateutil parsing. If they differ,
        dateutil's result is used as it handles locale and edge cases better.

        :param entries: List of feed entries as dicts.
        :param date_names: List of key names of entry published or updated values.
        :param current_date: The current date.
        :param locale: Optional locale string for date parsing (e.g., 'en_US', 'fr_FR').
        :return: generator that returns datetimes.
        """
        for entry in entries:
            for name in date_names:
                try:
                    # Get the raw date string
                    date_string = entry.get(name)
                    # Get feedparser's parsed struct_time (if available)
                    parsed_tuple = entry.get(f"{name}_parsed")

                    # Use comparison function to get best result
                    entry_date = parse_date_with_comparison(
                        date_string, parsed_tuple, locale
                    )

                    if entry_date and entry_date.date() <= current_date:
                        yield entry_date
                except (KeyError, ValueError, AttributeError):
                    pass

    @staticmethod
    def entry_velocity(dates: List[datetime]) -> float:
        """
        Calculate velocity of posted entries, returns a float of the average number of entries posted per day.

        :param dates: List of entry dates
        :return: Average entries per day
        """
        if not dates or len(dates) < 3:
            return 0

        dates = sorted(dates)
        deltas = []
        previous_date: datetime = dates[0]

        for current_date in dates[1:]:
            if current_date == previous_date:
                continue
            delta = current_date - previous_date
            deltas.append(delta.total_seconds())
            previous_date = current_date

        if not deltas:
            return 0

        mean_seconds_delta = mean(deltas)

        result = round(86400 / mean_seconds_delta, 3)
        return result

    @staticmethod
    def validate_self_url(item: FeedInfo) -> None:
        """
        Validate the self url

        :param item: FeedInfo item
        """
        try:
            item.self_url = URL(item.self_url)
        except ValueError:
            item.self_url = ""
            return

        if item.self_url and item.self_url != item.url:
            # Handle a case where the item url contains a trailing slash and the self url doesn't.
            if str(item.url).strip("/") == str(item.self_url):
                item.url = URL(str(item.url).strip("/"))
                return

            # The self url should be an absolute url.
            if not item.self_url.is_absolute():
                if str(item.self_url) in str(item.url):
                    item.self_url = item.url
                else:
                    item.self_url = ""
