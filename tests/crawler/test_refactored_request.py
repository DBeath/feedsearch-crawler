import pytest
from feedsearch_crawler.crawler.refactored_request import Request
from yarl import URL


# Test Initialization with default and provided values
def test_initialization():
    req = Request(url=URL("http://example.com"))
    assert req.url == URL("http://example.com")
    assert req.method == "GET"


# Test HTTP Method Validation
def test_valid_http_methods():
    valid_methods = ["GET", "POST", "PUT", "DELETE"]
    for method in valid_methods:
        req = Request(url=URL("http://example.com"), method=method)
        assert req.method == method


def test_invalid_http_method():
    with pytest.raises(ValueError):
        Request(url=URL("http://example.com"), method="INVALID")


# Test Callback Flexibility
def test_callback_flexibility():
    def success_func(arg1, arg2):
        return arg1 + arg2

    def failure_func():
        return "Failure"

    # Test with function only
    req1 = Request(
        url=URL("http://example.com"),
        success_callback=success_func,
        failure_callback=failure_func,
    )
    assert req1.success_callback == success_func
    assert req1.failure_callback == failure_func

    # Test with function and arguments
    req2 = Request(
        url=URL("http://example.com"),
        success_callback=(success_func, (1, 2)),
        failure_callback=failure_func,
    )
    assert req2.success_callback == (success_func, (1, 2))
    assert req2.failure_callback == failure_func


# Test Attributes
def test_attributes():
    req = Request(
        url=URL("http://example.com"),
        method="POST",
        headers={"User-Agent": "test"},
        params={"key": "value"},
        data={"data_key": "data_value"},
        json_data={"json_key": "json_value"},
        encoding="utf-8",
        success_callback=(lambda x: x, (10,)),
        failure_callback=lambda: "Failed",
        max_content_length=500_000,
        delay=1.0,
        retries=2,
        history=[URL("http://redirect.com")],
        timeout=5.0,
    )
    assert req.method == "POST"
    assert req.headers == {"User-Agent": "test"}
    assert req.params == {"key": "value"}
    assert req.data == {"data_key": "data_value"}
    assert req.json_data == {"json_key": "json_value"}
    assert req.encoding == "utf-8"
    assert req.success_callback[0](10) == 10
    assert req.failure_callback() == "Failed"
    assert req.max_content_length == 500_000
    assert req.delay == 1.0
    assert req.retries == 2
    assert req.history == [URL("http://redirect.com")]
    assert req.timeout == 5.0
