from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from yarl import URL


@dataclass(slots=True)
class Request:
    """
    Represents an HTTP request for the web crawler.

    Attributes:
        url (URL): The target URL for the request.
        method (str): The HTTP method (default: "GET").
        headers (Optional[Dict[str, str]]): Request headers.
        params (Optional[Dict[str, str]]): Query parameters.
        data (Optional[Union[Dict[str, str], bytes]]): Request body data.
        json_data (Optional[Dict[str, Any]]): JSON data to be sent in the request body.
        encoding (str): Encoding type (default: "").
        success_callback (Optional[Tuple[Callable[..., Any], Tuple[Any, ...]]]):
            Callback function for successful response. Tuple of the function and its arguments.
            If no arguments are required, only the function can be provided.
        failure_callback (Optional[Union[Callable[..., Any], Tuple[Callable[..., Any], Tuple[Any, ...]]]]):
            Callback function for failed response. Tuple of the function and its arguments.
            If no arguments are required, only the function can be provided.
        max_content_length (int): Maximum allowable content length for the response (default: 1,000,000).
        delay (float): Time to delay before executing the request (default: 0.0).
        retries (int): Number of retries if the request fails (default: 3).
        history (Optional[List[URL]]): List to track redirections or sequence of URLs fetched.
        timeout (float): Maximum time to wait for the server's response (default: 10.0 seconds).

    Example Usage:
        req = Request(
            url=my_url,
            success_callback=(my_success_function, (arg1, arg2)),
            failure_callback=my_failure_function  # No arguments provided for failure callback
        )
    """

    url: URL
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    data: Optional[Union[Dict[str, str], bytes]] = None
    json_data: Optional[Dict[str, Any]] = None
    encoding: str = ""

    # Using Union to allow callback functions with or without arguments
    success_callback: Optional[Tuple[Callable[..., Any], Tuple[Any, ...]]] = None
    failure_callback: Optional[
        Union[Callable[..., Any], Tuple[Callable[..., Any], Tuple[Any, ...]]]
    ] = None

    max_content_length: int = 1_000_000
    delay: float = 0.0
    retries: int = 3
    history: Optional[List[URL]] = None
    timeout: float = 10.0

    # Default lowest queue priority is 100 (higher number means lower priority)
    priority: int = 100

    def __post_init__(self):
        # HTTP method validation
        if self.method not in ["GET", "POST", "PUT", "DELETE"]:
            raise ValueError(f"Invalid method: {self.method}")
