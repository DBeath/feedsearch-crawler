from feedsearch_crawler.feed_spider.favicon import Favicon


def test_matches_host() -> None:
    favicon = Favicon(
        site_host="test.com",
        url="test.com/favicon.ico",
        priority=1,
        data_uri="data_uri",
    )
    assert favicon.matches_host("test.com")


def test_matches_host_no_match() -> None:
    favicon = Favicon(
        site_host="test.com",
        url="test.com/favicon.ico",
        priority=1,
        data_uri="data_uri",
    )
    assert not favicon.matches_host("test2.com")


def test_matches_host_no_site_host() -> None:
    favicon = Favicon(
        site_host="",
        url="test.com/favicon.ico",
        priority=1,
        data_uri="data_uri",
    )
    assert not favicon.matches_host("test2.com")


def test_matches_host_data_uri() -> None:
    favicon = Favicon(
        site_host="test.com",
        url="test.com/favicon.ico",
        priority=1,
        data_uri="data_uri",
    )
    assert favicon.matches_host("test.com", requires_data_uri=True)


def test_matches_host_no_data_uri() -> None:
    favicon = Favicon(
        site_host="test.com",
        url="test.com/favicon.ico",
        priority=1,
    )
    assert not favicon.matches_host("test.com", requires_data_uri=True)


def test_matches_host_no_url() -> None:
    favicon = Favicon(site_host="test.com", priority=1, data_uri="data_uri")
    assert not favicon.matches_host("test.com", requires_data_uri=True)
