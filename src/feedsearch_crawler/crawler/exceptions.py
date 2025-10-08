from feedsearch_crawler.crawler.request import Request


class RetryRequestException(Exception):
    """Exception raised when a request should be retried."""

    def __init__(self, request: Request, *args: object) -> None:
        self.request = request
        super().__init__(*args)
