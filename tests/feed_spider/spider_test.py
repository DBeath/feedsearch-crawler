from yarl import URL

from feedsearch_crawler.feed_spider.spider import FeedsearchSpider as fs, feedlike_regex


def test_is_feedlike_href():
    assert fs.is_href_matching("test.com/feed", feedlike_regex) == True
    assert fs.is_href_matching("feed", feedlike_regex) == True
    assert fs.is_href_matching("feeds", feedlike_regex) == True
    assert fs.is_href_matching("test.com/feeds", feedlike_regex) == True
    assert fs.is_href_matching("test.com/feeds/test", feedlike_regex) == True
    assert fs.is_href_matching("test.com/podcasts/test", feedlike_regex) == True
    assert fs.is_href_matching("test.com/podcast/test", feedlike_regex) == True
    assert fs.is_href_matching("test.com/podcasts", feedlike_regex) == True
    assert fs.is_href_matching("test.com/podcast", feedlike_regex) == True


def test_is_feedlike_querystring():
    assert fs.is_querystring_matching(URL("test.com?feed"), feedlike_regex) == True
    assert fs.is_querystring_matching(URL("test.com/test?feed"), feedlike_regex) == True
    assert (
        fs.is_querystring_matching(
            URL("test.com/test?url=feed&test=true"), feedlike_regex
        )
        == False
    )
    assert (
        fs.is_querystring_matching(URL("test.com/test?url=feed"), feedlike_regex)
        == False
    )
    assert (
        fs.is_querystring_matching(URL("test.com/feed?url=test"), feedlike_regex)
        == False
    )
    assert (
        fs.is_querystring_matching(URL("test.com/test?feed=test"), feedlike_regex)
        == True
    )
    assert (
        fs.is_querystring_matching(URL("test.com?podcast=test"), feedlike_regex) == True
    )
    assert (
        fs.is_querystring_matching(URL("test.com?feeds=test"), feedlike_regex) == True
    )
    assert (
        fs.is_querystring_matching(URL("test.com?podcasts=test"), feedlike_regex)
        == True
    )
