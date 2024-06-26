"""

    pilka.stadiums.utils.scrape.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    Utilities for scraping.

    @author: z33k

"""
import logging
import time
from functools import wraps
from typing import Callable, Dict

import requests
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup

from pilka.constants import REQUEST_TIMEOUT
from pilka.utils import timed
from pilka.utils.check_type import type_checker


_log = logging.getLogger(__name__)


class ScrapingError(IOError):
    """Raised whenever scraping produces unexpected results.
    """


http_requests_count = 0


@timed("request")
@type_checker(str)
def getsoup(url: str, headers: Dict[str, str] | None = None) -> BeautifulSoup:
    """Return BeautifulSoup object based on ``url``.

    Args:
        url: URL string
        headers: a dictionary of headers to add to the request

    Returns:
        a BeautifulSoup object
    """
    _log.info(f"Requesting: {url!r}")
    global http_requests_count
    response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
    http_requests_count += 1
    if str(response.status_code)[0] in ("4", "5"):
        msg = f"Request failed with: '{response.status_code} {response.reason}'"
        if response.status_code in (502, 503, 504):
            raise HTTPError(msg)
        _log.warning(msg)
    return BeautifulSoup(response.text, "lxml")


def throttle(delay: float | Callable[..., float]) -> None:
    amount = delay() if callable(delay) else delay
    _log.info(f"Throttling for {amount} seconds...")
    time.sleep(amount)


def throttled(delay: float | Callable[..., float]) -> Callable:
    """Add throttling delay after the decorated operation.

    Args:
        throttling delay in fraction of seconds

    Returns:
        the decorated function
    """
    def decorate(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            throttle(delay)
            return result
        return wrapper
    return decorate


def http_requests_counted(operation="") -> Callable:
    """Count HTTP requests done by the decorated operation.

    Args:
        name of the operation

    Returns:
        the decorated function
    """
    def decorate(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            global http_requests_count
            initial_count = http_requests_count
            result = func(*args, **kwargs)
            requests_made = http_requests_count - initial_count
            nonlocal operation
            operation = operation or f"{func.__name__!r}"
            _log.info(f"Needed {requests_made} HTTP request(s) to carry out {operation}")
            return result
        return wrapper
    return decorate
