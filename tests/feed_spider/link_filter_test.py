from yarl import URL

from feedsearch_crawler.feed_spider.link_filter import (
    LinkFilter as lf,
)
from feedsearch_crawler.feed_spider.regexes import feedlike_regex, podcast_regex


def test_feedlike_regex() -> None:
    valid = [
        "rss",
        "testing/rss",
        "testing/rss-test",
        "test-rss-test",
        "test.rss.test",
        "RSS",
        "test/RSS/test",
        "feed",
        "testing/feed/",
        "test-feed-test",
        "test.feed.test",
        "FEED",
        "FeeD",
        "test/FEED/test",
        "feeds",
        "testing/feeds",
        "test-feeds-test",
        "test.feeds.test",
        "FEEDS",
        "FeedS",
        "test/FEEDS/test",
        "atom",
        "json",
        "xml",
        "rdf",
        "blog",
        "blogs",
        "test/subscribe/testing",
    ]
    for value in valid:
        assert feedlike_regex.search(value)


def test_feedlike_regex_invalid() -> None:
    invalid = ["rsss", "rs-s", "feedss", "tfeed", "fee-d", "fee.d"]
    for value in invalid:
        assert not feedlike_regex.search(value)


def test_podcast_regex() -> None:
    pass


def test_is_feedlike_href() -> None:
    assert lf.is_href_matching("test.com/feed", feedlike_regex) is True
    assert lf.is_href_matching("feed", feedlike_regex) is True
    assert lf.is_href_matching("feeds", feedlike_regex) is True
    assert lf.is_href_matching("test.com/feeds", feedlike_regex) is True
    assert lf.is_href_matching("test.com/feeds/test", feedlike_regex) is True
    assert lf.is_href_matching("test.com/podcasts/test", feedlike_regex) is False
    assert lf.is_href_matching("test.com/podcast/test", feedlike_regex) is False
    assert lf.is_href_matching("test.com/podcasts", feedlike_regex) is False
    assert lf.is_href_matching("test.com/podcast", feedlike_regex) is False


def test_is_feedlike_querystring() -> None:
    assert lf.is_querystring_matching(URL("test.com?feed"), feedlike_regex) is True
    assert lf.is_querystring_matching(URL("test.com/test?feed"), feedlike_regex) is True
    assert (
        lf.is_querystring_matching(
            URL("test.com/test?url=feed&test=true"), feedlike_regex
        )
        is False
    )
    assert (
        lf.is_querystring_matching(URL("test.com/test?url=feed"), feedlike_regex)
        is False
    )
    assert (
        lf.is_querystring_matching(URL("test.com/feed?url=test"), feedlike_regex)
        is False
    )
    assert (
        lf.is_querystring_matching(URL("test.com/test?feed=test"), feedlike_regex)
        is True
    )
    assert (
        lf.is_querystring_matching(URL("test.com?podcast=test"), feedlike_regex)
        is False
    )
    assert (
        lf.is_querystring_matching(URL("test.com?feeds=test"), feedlike_regex) is True
    )
    assert (
        lf.is_querystring_matching(URL("test.com?podcasts=test"), feedlike_regex)
        is False
    )


def test_is_podcast_href() -> None:
    assert lf.is_href_matching("test.com/podcasts/test", podcast_regex) is True
    assert lf.is_href_matching("test.com/podcast/test", podcast_regex) is True
    assert lf.is_href_matching("test.com/podcasts", podcast_regex) is True
    assert lf.is_href_matching("test.com/podcast", podcast_regex) is True


def test_is_podcast_querystring() -> None:
    assert (
        lf.is_querystring_matching(URL("test.com?podcast=test"), podcast_regex) is True
    )
    assert (
        lf.is_querystring_matching(URL("test.com?podcasts=test"), podcast_regex) is True
    )
