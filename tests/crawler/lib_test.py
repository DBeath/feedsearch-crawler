from feedsearch_crawler.crawler.lib import coerce_url
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
