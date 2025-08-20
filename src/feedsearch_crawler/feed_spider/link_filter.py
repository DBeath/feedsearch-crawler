import logging
import pathlib
import re
from typing import Optional, Tuple, List

import bs4
from w3lib.url import url_query_cleaner
from yarl import URL

from feedsearch_crawler.crawler import Response, Request
from feedsearch_crawler.crawler.lib import parse_href_to_url
from feedsearch_crawler.feed_spider.regexes import (
    feedlike_regex,
    podcast_regex,
    author_regex,
    date_regex,
)

# List of invalid filetypes
invalid_filetypes: List[str] = [
    "jpeg",
    "jpg",
    "png",
    "gif",
    "bmp",
    "mp4",
    "mp3",
    "mkv",
    "md",
    "css",
    "avi",
    "pdf",
    "js",
    "woff",
    "woff2",
    "svg",
    "ttf",
]

# List of strings that are invalid as querystring keys
invalid_querystring_keys: List[str] = ["comment", "comments", "post", "view", "theme"]

# List of strings that indicate a URL is invalid for crawling
invalid_url_contents: List[str] = [
    "wp-includes",
    "wp-content",
    "wp-json",
    "xmlrpc",
    "wp-admin",
    "/amp/",  # Theoretically there could be a feed at an AMP url, but not worth checking.
    "mailto:",
    "//font.",
]

# List of strings that indicate a URL should be low priority
low_priority_urls: List[str] = [
    "/archive/",  # Archives are less likely to contain feeds.
    "/page/",  # Articles pages are less likely to contain feeds.
    "forum",  # Forums are not likely to contain interesting feeds.
    "//cdn.",  # Can't guarantee that someone won't put a feed at a CDN url, so we can't outright ignore it.
    "video",
]

# Link Types that should always be searched for feeds
feed_link_types: List[str] = ["application/json", "rss", "atom", "rdf"]


logger = logging.getLogger(__name__)


class LinkFilter:
    def __init__(
        self, response: Response, request: Request, full_crawl: bool = False
    ) -> None:
        self.response = response
        self.request = request
        self.full_crawl = full_crawl

    def should_follow_link(self, link: bs4.Tag) -> Optional[Tuple[URL, int]]:
        """
        Check that the link should be followed if it may contain feed information.

        :param link: Link tag
        :return: boolean
        """
        href: str = link.get("href")
        link_type: str = link.get("type")

        url: URL = parse_href_to_url(href)
        if not url:
            return None

        # If the link may have a valid feed type then follow it regardless of the url text.
        if (
            link_type
            and any(map(link_type.lower().count, feed_link_types))
            and "json+oembed" not in link_type
        ):
            # A link with a possible feed type has the highest priority after callbacks.
            return url, 2

        is_feedlike_href: bool = self.is_href_matching(str(url), feedlike_regex)
        is_feedlike_querystring: bool = self.is_querystring_matching(
            url, feedlike_regex
        )

        is_podcast_href: bool = self.is_href_matching(str(url), podcast_regex)
        is_podcast_querystring: bool = self.is_querystring_matching(url, podcast_regex)

        is_feedlike_url = is_feedlike_querystring or is_feedlike_href
        is_podcast_url = is_podcast_href or is_podcast_querystring

        if not self.full_crawl and not is_feedlike_url and not is_podcast_url:
            return

        # This check is deprecated, as it has been moved to the spider to prevent the crawling of any links
        # from responses that are not the same as the original domain
        #
        # is_one_jump: bool = self.is_one_jump_from_original_domain(url, self.response)
        # if not is_one_jump:
        #     return

        has_author_info: bool = self.is_href_matching(href, author_regex)
        is_low_priority: bool = self.is_low_priority(href)

        # Default priority for new requests
        priority: int = 100
        # A low priority url should be fetched last.
        if is_low_priority:
            priority = priority + 2
        # Podcast pages are lower priority than authors or feeds.
        if is_podcast_url:
            priority = 5
        # Potential author info has a medium priority.
        if has_author_info:
            priority = 4
        # A feedlike url has high priority.
        if is_feedlike_url:
            priority = 3

        # Validate the actual URL string.
        follow = (
            # is_one_jump
            not self.has_invalid_contents(href)
            and self.is_valid_filetype(href)
            and not self.has_invalid_querystring(url)
        )
        # If full_crawl then follow all valid URLs regardless of the feedlike quality of the URL.
        # Otherwise only follow URLs if they look like they might contain feed information.
        if follow and (self.full_crawl or is_feedlike_url or is_podcast_href):
            # Remove the querystring unless it may point to a feed.
            if not is_feedlike_querystring:
                url = url.with_query(None)

            return url, priority

    @staticmethod
    def is_one_jump_from_original_domain(url: URL, response: Response) -> bool:
        """
        Check that the current URL is only one response away from the originally queried domain.

        We want to be able to follow potential feed links that point to a different domain than
        the originally queried domain, but not to follow any deeper than that.

        Sub-domains of the original domain are ok.

        i.e: the following are ok
            "test.com" -> "feedhost.com"
            "test.com/feeds" -> "example.com/feed.xml"
            "test.com" -> "feeds.test.com"

        not ok:
            "test.com" -> "feedhost.com" (we stop here) -> "feedhost.com/feeds"

        :param url: URL object or string
        :param response: Response object
        :return: boolean
        """

        # This is the first Response in the chain
        if len(response.history) < 2:
            return True

        # The URL is relative, so on the same domain
        if not url.is_absolute():
            return True

        # URL is same domain
        if url.host == response.history[0].host:
            return True

        # URL is sub-domain
        if response.history[0].host in url.host:
            return True

        # URL domain and current Response domain are different from original domain
        if (
            response.history[-1].host != response.history[0].host
            and url.host != response.history[0].host
        ):
            return False

        return True

    @staticmethod
    def is_valid_filetype(url: str) -> bool:
        """
        Check if url string has an invalid filetype extension.

        :param url: URL string
        :return: boolean
        """
        # if file_regex.search(url.strip()):
        #     return False
        # return True
        suffix = pathlib.Path(url_query_cleaner(url)).suffix.strip(".").lower()
        if suffix in invalid_filetypes:
            return False
        return True

    @staticmethod
    def has_invalid_querystring(url: URL) -> bool:
        """
        Check if URL querystring contains invalid keys.

        :param url: URL object
        :return: boolean
        """
        return any(key in url.query for key in invalid_querystring_keys)

    @staticmethod
    def is_href_matching(url_string: str, regex: re) -> bool:
        """
        Check if the regex has any match in the url string.

        :param url_string: URL as string
        :param regex: Regex used to search URL
        :return: boolean
        """
        if regex.search(url_query_cleaner(url_string)):
            return True
        return False

    @staticmethod
    def is_querystring_matching(url: URL, regex: re) -> bool:
        """
        Check if the regex has any match in the URL query parameters.

        :param url: URL object
        :param regex: Regex used to search query
        :return: boolean
        """
        for key in url.query:
            if regex.search(key):
                return True
        return False

    @staticmethod
    def has_invalid_contents(string: str) -> bool:
        """
        Ignore any string containing the following strings.

        :param string: String to check
        :return: boolean
        """
        return any(value in string.lower() for value in invalid_url_contents)

    @staticmethod
    def is_low_priority(url_string: str) -> bool:
        """
        Check if the url contains any strings that indicate the url should be low priority.

        :param url_string: URL string
        :return: boolean
        """
        if any(value in url_string.lower() for value in low_priority_urls):
            return True

        # Search for dates in url, this generally indicates an article page.
        if date_regex.search(url_string):
            return True
        return False

    @staticmethod
    def is_subdomain_matching(url: URL, regex: re) -> bool:
        """
        Check if the url subdomain matches the regex

        :param url: URL object
        :param regex: regex object
        :return: boolean
        """
        if not url.host:
            return False

        split = url.host.split(".")
        if len(split) <= 2:
            return False

        sub_domains = ".".join(split[:-2])
        if regex.search(sub_domains):
            return True
        return False
