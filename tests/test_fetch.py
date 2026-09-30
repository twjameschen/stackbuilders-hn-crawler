from unittest.mock import Mock

import pytest
import requests

from hn_crawler import fetch


def response(status=200, html="<html>Café 你好 😀</html>"):
    result = requests.Response()
    result.status_code = status
    result.url = "https://news.ycombinator.com/"
    result._content = html.encode("utf-8")
    result._content_consumed = True
    return result


def test_fetch_uses_fixed_url_explicit_headers_timeouts_and_tls(monkeypatch):
    result = response()
    close = Mock(wraps=result.close)
    monkeypatch.setattr(result, "close", close)
    get = Mock(return_value=result)
    monkeypatch.setattr(fetch.requests, "get", get)

    assert fetch.fetch_homepage() == "<html>Café 你好 😀</html>"
    get.assert_called_once_with(
        "https://news.ycombinator.com/",
        headers={"User-Agent": "stackbuilders-hn-crawler/0.1.0"},
        timeout=(5, 10),
        allow_redirects=False,
        verify=True,
    )
    close.assert_called_once()


@pytest.mark.parametrize("status", [404, 503, 302])
def test_http_errors_and_redirects_are_rejected(monkeypatch, status):
    result = response(status)
    close = Mock(wraps=result.close)
    monkeypatch.setattr(result, "close", close)
    get = Mock(return_value=result)
    monkeypatch.setattr(fetch.requests, "get", get)

    with pytest.raises(requests.HTTPError):
        fetch.fetch_homepage()

    get.assert_called_once()
    close.assert_called_once()


@pytest.mark.parametrize("error", [requests.Timeout("slow"), requests.ConnectionError("offline")])
def test_transport_failures_propagate_without_retry(monkeypatch, error):
    get = Mock(side_effect=error)
    monkeypatch.setattr(fetch.requests, "get", get)

    with pytest.raises(type(error), match=str(error)):
        fetch.fetch_homepage()

    get.assert_called_once()
