from yarl import URL

from feedsearch_crawler.feed_spider.link_filter import (
    feedlike_regex,
    podcast_regex,
    LinkFilter as lf,
)


def test_is_feedlike_href():
    assert lf.is_href_matching("test.com/feed", feedlike_regex) is True
    assert lf.is_href_matching("feed", feedlike_regex) is True
    assert lf.is_href_matching("feeds", feedlike_regex) is True
    assert lf.is_href_matching("test.com/feeds", feedlike_regex) is True
    assert lf.is_href_matching("test.com/feeds/test", feedlike_regex) is True
    assert lf.is_href_matching("test.com/podcasts/test", feedlike_regex) is False
    assert lf.is_href_matching("test.com/podcast/test", feedlike_regex) is False
    assert lf.is_href_matching("test.com/podcasts", feedlike_regex) is False
    assert lf.is_href_matching("test.com/podcast", feedlike_regex) is False


def test_is_feedlike_querystring():
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


def test_is_podcast_href():
    assert lf.is_href_matching("test.com/podcasts/test", podcast_regex) is True
    assert lf.is_href_matching("test.com/podcast/test", podcast_regex) is True
    assert lf.is_href_matching("test.com/podcasts", podcast_regex) is True
    assert lf.is_href_matching("test.com/podcast", podcast_regex) is True


def test_is_podcast_querystring():
    assert (
        lf.is_querystring_matching(URL("test.com?podcast=test"), podcast_regex) is True
    )
    assert (
        lf.is_querystring_matching(URL("test.com?podcasts=test"), podcast_regex) is True
    )
