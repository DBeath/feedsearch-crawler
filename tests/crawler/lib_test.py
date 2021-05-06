from feedsearch_crawler.crawler.lib import coerce_url, is_same_domain
from yarl import URL


def test_coerce_url():
    assert coerce_url("test.com") == URL("http://test.com")
    assert coerce_url("https://test.com") == URL("https://test.com")
    assert coerce_url(" https://test.com") == URL("https://test.com")
    assert coerce_url("test.com/path/path2") == URL("http://test.com/path/path2")

    assert coerce_url("test.com", https=True) == URL("https://test.com")
    assert coerce_url("https://test.com", https=True) == URL("https://test.com")
    assert coerce_url(" https://test.com", https=True) == URL("https://test.com")
    assert coerce_url("http://test.com", https=True) == URL("https://test.com")
    assert coerce_url("test.com/path/path2", https=True) == URL(
        "https://test.com/path/path2"
    )
    assert coerce_url("//test.com") == URL("http://test.com")
    assert coerce_url("feed://test.com") == URL("feed://test.com")
    assert coerce_url("feed://www.internet-law.de/?feed=/feed/") == URL(
        "feed://www.internet-law.de/?feed=/feed/"
    )


def test_is_same_domain():
    assert is_same_domain("test.com", "test.com") is True
    assert is_same_domain("example.com", "test.com") is False
    assert is_same_domain("feeds.test.com", "test.com") is False
    assert is_same_domain("test.com", "feeds.test.com") is True
    assert is_same_domain("test.com", "test.feeds.test.com") is True
    assert is_same_domain("www.test.com", "test.com") is True
    assert is_same_domain("www.test.com", "feed.test.com") is True
    assert is_same_domain("test.www.test.com", "test.com") is False
