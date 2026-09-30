"""Fetch the fixed Hacker News homepage once, without parsing it."""

import requests

HOMEPAGE_URL = "https://news.ycombinator.com/"
USER_AGENT = "stackbuilders-hn-crawler/0.1.0"
TIMEOUT = (5, 10)


def fetch_homepage() -> str:
    """Return UTF-8 homepage HTML; propagate Requests operational errors.

    Connect/read timeouts are finite, but are not a total-operation deadline.
    Redirects are rejected to keep the request restricted to the fixed URL.
    """
    with requests.get(
        HOMEPAGE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        allow_redirects=False,
        verify=True,
    ) as response:
        response.raise_for_status()
        if 300 <= response.status_code < 400:
            raise requests.HTTPError("Homepage redirect rejected", response=response)
        response.encoding = "utf-8"
        return response.text
