"""HTTP helper with timeouts, exponential backoff and readable errors."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)
USER_AGENT = "geo-import-pipeline/0.1 (+https://github.com/)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class FetchError(RuntimeError):
    """Source could not be fetched after all retries."""


def get(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 120.0,
    retries: int = 3,
    backoff: float = 2.0,
    session: requests.Session | None = None,
) -> requests.Response:
    """GET with retries on network errors and 429/5xx; raises FetchError with the cause."""
    sess = session or requests.Session()
    last = "unbekannter Fehler"
    for attempt in range(retries + 1):
        try:
            resp = sess.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            if resp.status_code not in RETRY_STATUS:
                if resp.status_code >= 400:
                    raise FetchError(f"HTTP {resp.status_code} von {url}")
                return resp
            last = f"HTTP {resp.status_code}"
        except requests.Timeout:
            last = f"Zeitüberschreitung nach {timeout:.0f} s"
        except requests.ConnectionError as exc:
            last = f"Verbindung fehlgeschlagen: {type(exc).__name__}"
        if attempt < retries:
            delay = backoff**attempt
            log.warning(
                "fetch failed (%s), retry %d/%d in %.0fs", last, attempt + 1, retries, delay
            )
            time.sleep(delay)
    raise FetchError(f"{url}: {last} (nach {retries + 1} Versuchen)")
