import logging
import re
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
            parsed: dict = self.parse_raw_data(
                data, encoding, headers, base_url=str(item.url) if item.url else None
            )
        except Exception as e:
            logger.exception("Unable to parse feed %s: %s", item, e)
            return False

        if not parsed:
            logger.warning("No valid feed data for %s", item)
            return False

        if parsed.get("bozo") == 1:
            bozo_exception = parsed.get("bozo_exception", None)
            if isinstance(
                bozo_exception,
                (feedparser.CharacterEncodingUnknown, feedparser.UndeclaredNamespace),
            ):
                logger.warning("No valid feed data for %s: %s", item, bozo_exception)
                return False
            # NonXMLContentType only means the server did not declare an XML
            # content type - the document itself may be a perfectly valid
            # feed, so it does not count as malformed.
            if not isinstance(bozo_exception, feedparser.NonXMLContentType):
                # Any other recoverable parse problem (malformed XML, encoding
                # override, etc.) means the feed is not well formed.
                item.bozo = 1

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

        # Feed-declared metadata (RSS 2.0 channel / Atom feed elements).
        # feedparser normalizes RSS and Atom element names to common keys.
        item.language = feed.get("language") or ""
        item.link = self.to_url(feed.get("link"))
        item.author = self.feed_author(feed)
        item.copyright = feed.get("rights") or ""
        item.generator = feed.get("generator") or ""
        item.tags = self.feed_tags(feed)
        # RSS <image><url> and itunes:image both normalize to feed.image.href
        # (itunes:image wins when both are present); Atom uses <logo>.
        item.image = self.to_url(feed.get("image", {}).get("href") or feed.get("logo"))
        # Atom <icon> is the small square icon, equivalent to a favicon.
        if not item.favicon:
            item.favicon = self.to_url(feed.get("icon"))
        item.is_explicit = self.itunes_explicit(feed, data)
        # itunes:new-feed-url signals the feed has permanently moved.
        item.new_feed_url = self.to_url(feed.get("itunes_new-feed-url"))

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

        # JSON Feed feed_url is the canonical self URL of the feed.
        feed_url = self.to_url(data.get("feed_url"))
        if feed_url and not item.self_url:
            item.self_url = feed_url

        item.is_podcast = self.is_json_podcast(data)

        # Feed-declared metadata (JSON Feed 1.1 top-level fields).
        item.language = data.get("language") or ""
        item.link = self.to_url(data.get("home_page_url"))
        item.author = self.json_feed_author(data)
        # JSON Feed `icon` is the larger artwork; `favicon` the small icon.
        item.image = self.to_url(data.get("icon"))

        favicon = data.get("favicon")
        if favicon:
            item.favicon = URL(favicon)

        # Only search if no hubs already present from headers
        if not item.hubs:
            try:
                item.hubs = list(hub.get("url") for hub in data.get("hubs", []))
            except (IndexError, AttributeError):
                pass

        # WebSub requires both a hub and a self URL (feed_url in JSON Feed),
        # matching the XML path's requirement.
        if item.hubs and item.self_url:
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
        raw_data: Union[str, bytes],
        encoding: str = "utf-8",
        headers: Dict = None,
        base_url: str = None,
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
        :param base_url: URL the feed was fetched from; used as the document
            base so relative URLs in the feed are resolved to absolute ones
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

        # feedparser resolves relative URLs against the content-location
        # header. A genuine header from the response takes precedence.
        if base_url:
            h.setdefault("content-location", base_url)

        try:
            start = time.perf_counter()

            if isinstance(raw_data, str):
                raw_data = raw_data.encode(encoding)

            raw_data = raw_data.strip()
            content_length = len(raw_data)

            # We want to pass data into feedparser as bytes, otherwise if we accidentally pass a url string
            # it will attempt a fetch.
            # HTML sanitization is disabled: entry content is discarded by this
            # crawler, and sanitizing it costs more than the rest of the parse.
            # Feed fields are therefore unsanitized - treat them as untrusted.
            data = feedparser.parse(raw_data, response_headers=h, sanitize_html=False)

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

        Both audio and video enclosures count - Apple supports video podcasts.

        :param parsed: Feedparser dict
        :return: bool
        """
        if not parsed:
            return False

        has_itunes: bool = "itunes" in parsed.get("namespaces", {})

        has_enclosures = False

        for entry in parsed.get("entries", []):
            for enclosure in entry.get("enclosures", []):
                media_type = enclosure.get("type", "")
                if "audio" in media_type or "video" in media_type:
                    has_enclosures = True

        return has_itunes and has_enclosures

    @staticmethod
    def is_json_podcast(data: dict) -> bool:
        """
        Check if a JSON Feed is a Podcast.

        JSON Feed items declare media as attachments; audio or video
        attachment mime types mark the feed as a podcast.

        :param data: JSON Feed dict
        :return: bool
        """
        for entry in data.get("items", []):
            try:
                attachments = entry.get("attachments") or []
            except AttributeError:
                continue
            for attachment in attachments:
                try:
                    mime_type = attachment.get("mime_type") or ""
                except AttributeError:
                    continue
                if "audio" in mime_type or "video" in mime_type:
                    return True
        return False

    # Apple's spec uses true/false; yes/no/clean/explicit occur historically.
    ITUNES_EXPLICIT_VALUES = {
        "yes": True,
        "true": True,
        "explicit": True,
        "no": False,
        "false": False,
        "clean": False,
    }

    # Channel-level metadata precedes the first item/entry in a feed document.
    _CHANNEL_SECTION_SPLIT = re.compile(r"<item[\s>]|<entry[\s>]", re.IGNORECASE)
    _ITUNES_EXPLICIT_ELEMENT = re.compile(
        r"<itunes:explicit[^>]*>\s*([a-zA-Z]+)\s*<", re.IGNORECASE
    )

    @classmethod
    def itunes_explicit(cls, feed: dict, data: Union[str, bytes]) -> Union[bool, None]:
        """
        Get the channel-level itunes:explicit value.

        feedparser only maps "yes" (True) and "clean" (False); the other
        values - including "true"/"false", which Apple's current spec
        mandates - are normalized to None. When the element is present but
        unmapped, the value is recovered from the channel-level section of
        the raw XML (everything before the first item/entry).

        :param feed: feedparser feed dict
        :param data: Raw feed XML
        :return: True/False, or None when not declared
        """
        explicit = feed.get("itunes_explicit")
        if explicit is not None:
            return bool(explicit)
        if "itunes_explicit" not in feed:
            return None

        try:
            if isinstance(data, bytes):
                text = data.decode("utf-8", errors="ignore")
            else:
                text = str(data)
            channel_section = cls._CHANNEL_SECTION_SPLIT.split(text, maxsplit=1)[0]
            match = cls._ITUNES_EXPLICIT_ELEMENT.search(channel_section)
            if match:
                return cls.ITUNES_EXPLICIT_VALUES.get(match.group(1).lower())
        except Exception as e:
            logger.warning("Failed to parse itunes:explicit value: %s", e)
        return None

    @staticmethod
    def to_url(value: Union[str, None]) -> Union[URL, None]:
        """
        Convert a string to a URL, returning None for empty or invalid values.

        :param value: URL string or None
        :return: URL or None
        """
        if not value or not isinstance(value, str):
            return None
        try:
            return URL(value.strip())
        except (ValueError, TypeError):
            return None

    @staticmethod
    def feed_author(feed: dict) -> str:
        """
        Get the feed author name.

        Prefers the parsed name from author_detail (RSS managingEditor,
        Atom <author><name>, or itunes:author) over the raw author string,
        which may include an email address.

        :param feed: feed dict
        :return: str
        """
        author_detail = feed.get("author_detail") or {}
        return author_detail.get("name") or feed.get("author") or ""

    @staticmethod
    def json_feed_author(data: dict) -> str:
        """
        Get the author name from a JSON Feed.

        JSON Feed 1.1 uses a top-level `authors` array; 1.0 used a single
        `author` object. The first author's name is returned.

        :param data: JSON Feed dict
        :return: str
        """
        authors = data.get("authors")
        if not authors and data.get("author"):
            authors = [data["author"]]
        if not authors:
            return ""
        try:
            return authors[0].get("name") or ""
        except (AttributeError, IndexError):
            return ""

    @staticmethod
    def feed_tags(feed: dict) -> List[str]:
        """
        Get category/tag terms from a parsed feed.

        feedparser normalizes RSS <category>, Atom <category term=...>, and
        itunes:category elements into feed.tags. Duplicate terms are removed
        while preserving order.

        :param feed: feed dict
        :return: List of unique tag terms
        """
        tags: List[str] = []
        for tag in feed.get("tags", []):
            try:
                term = tag.get("term")
            except AttributeError:
                continue
            if term and term not in tags:
                tags.append(term)
        return tags

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
