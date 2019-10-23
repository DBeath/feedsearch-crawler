from yarl import URL

from feedsearch_crawler.feed_spider.spider import FeedsearchSpider as fs


def test_is_feedlike_href():
    assert fs.is_feedlike_href("test.com/feed") == True
    assert fs.is_feedlike_href("feed") == True
    assert fs.is_feedlike_href("feeds") == True
    assert fs.is_feedlike_href("test.com/feeds") == True
    assert fs.is_feedlike_href("test.com/feeds/test") == True
    assert fs.is_feedlike_href("test.com/podcasts/test") == True
    assert fs.is_feedlike_href("test.com/podcast/test") == True
    assert fs.is_feedlike_href("test.com/podcasts") == True
    assert fs.is_feedlike_href("test.com/podcast") == True


def test_is_feedlike_querystring():
    assert fs.is_feedlike_querystring(URL("test.com?feed")) == True
    assert fs.is_feedlike_querystring(URL("test.com/test?feed")) == True
    assert fs.is_feedlike_querystring(URL("test.com/test?url=feed&test=true")) == False
    assert fs.is_feedlike_querystring(URL("test.com/test?url=feed")) == False
    assert fs.is_feedlike_querystring(URL("test.com/feed?url=test")) == False
    assert fs.is_feedlike_querystring(URL("test.com/test?feed=test")) == True
    assert fs.is_feedlike_querystring(URL("test.com?podcast=test")) == True
    assert fs.is_feedlike_querystring(URL("test.com?feeds=test")) == True
    assert fs.is_feedlike_querystring(URL("test.com?podcasts=test")) == True
