"""Exception and error types for feedsearch-crawler."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorType(Enum):
    """Types of errors that can occur during feed search."""

    DNS_FAILURE = "dns_failure"
    CONNECTION_ERROR = "connection_error"
    SSL_ERROR = "ssl_error"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    INVALID_URL = "invalid_url"
    OTHER = "other"


@dataclass
class SearchError:
    """Error that occurred during feed search."""

    url: str
    """The URL that failed"""

    error_type: ErrorType
    """Type of error that occurred"""

    message: str
    """Human-readable error message"""

    status_code: Optional[int] = None
    """HTTP status code if applicable"""

    original_exception: Optional[str] = None
    """String representation of original exception"""

    def __str__(self) -> str:
        """Human-readable error string."""
        if self.status_code:
            return f"{self.error_type.value}: {self.message} (HTTP {self.status_code}) - {self.url}"
        return f"{self.error_type.value}: {self.message} - {self.url}"
