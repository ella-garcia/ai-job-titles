"""Polite HTTP: one request at a time per host, backoff on 429/5xx, honest User-Agent.

Only public endpoints. Never imitate a browser or reuse session tokens to get past a bot check.
"""
import time
from urllib.parse import urlparse

import requests

from .config import CFG, USER_AGENT

_last_call: dict[str, float] = {}


def min_interval(host: str) -> float:
    intervals = CFG.get("min_interval", {})
    return float(intervals.get(host, intervals.get("default", 1.0)))


def polite(method: str, url: str, *, headers: dict | None = None, max_tries: int = 5,
           timeout: int = 90, gap: float | None = None, **kwargs) -> requests.Response:
    host = urlparse(url).netloc
    gap = min_interval(host) if gap is None else gap
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    response = None
    for attempt in range(max_tries):
        wait = _last_call.get(host, 0) + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.time()
        try:
            response = requests.request(method, url, headers=hdrs, timeout=timeout, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == max_tries - 1:
                raise
            delay = 30 * (attempt + 1)
            print(f"  connection problem with {host} ({type(exc).__name__}); waiting {delay}s")
            time.sleep(delay)
            continue
        if response.status_code == 429 or response.status_code >= 500:
            try:
                delay = float(response.headers.get("Retry-After", ""))
            except ValueError:
                delay = 0
            delay = delay or 30 * (attempt + 1)
            print(f"  {response.status_code} from {host}; waiting {delay:.0f}s")
            time.sleep(delay)
            continue
        response.raise_for_status()
        return response
    response.raise_for_status()
    return response
