class RetryRequestException(Exception):
    """Exception raised when a request should be retried."""

    def __init__(self, request, *args: object) -> None:
        self.request = request
        super().__init__(*args)