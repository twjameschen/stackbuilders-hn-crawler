from contextlib import closing
import json
from pathlib import Path
import sqlite3
from unittest.mock import Mock

import pytest
import requests
from bs4 import BeautifulSoup

from hn_crawler import cli, fetch
from hn_crawler.models import Entry
from hn_crawler.parser import HNParseError, parse_homepage


@pytest.fixture
def job_page(homepage_response):
    """One captured homepage job plus 29 explicitly synthetic stories."""
    excerpt = (Path(__file__).parent / "fixtures/homepage_job.html").read_text(encoding="utf-8")
    captured = BeautifulSoup(excerpt, "html.parser")
    soup = BeautifulSoup(homepage_response.text, "html.parser")
    first = soup.select_one("tr.athing")
    first.find_next_sibling("tr").replace_with(captured.select_one("td.subtext").parent)
    first.replace_with(captured.select_one("tr.athing"))
    return soup


def test_captured_homepage_job_with_hide_link(job_page):
    entries = parse_homepage(str(job_page))

    assert len(entries) == 30
    assert entries[0] == Entry(
        8, "Bild AI (YC W25) Is Hiring a Founding Product Engineer", 0, 0,
    )
    assert entries[1] == Entry(7, "one two three four five six", 100, 2)


@pytest.mark.parametrize("separator", [" | ", "\n\t|  \n", "\u00a0|\u00a0"])
def test_job_hide_separator_allows_whitespace(job_page, separator):
    job_page.select_one("td.subtext").contents[1].replace_with(separator)

    assert parse_homepage(str(job_page))[0].points == 0


@pytest.mark.parametrize(
    "damage",
    ["missing-age", "age-id", "hide-id", "hide-destination", "hide-label",
     "duplicate-age", "duplicate-hide", "unexpected-link", "score",
     "comment-text", "unexplained-text", "wrong-separator", "missing-separator",
     "nested-hide", "empty-age", "unexpected-empty-metric"],
)
def test_damaged_homepage_job_is_rejected(job_page, damage):
    metadata = job_page.select_one("td.subtext")
    age = metadata.select_one(".age")
    hide = metadata.find("a", recursive=False)
    if damage == "missing-age":
        age.decompose()
    elif damage == "age-id":
        age.a["href"] = "item?id=49911532"
    elif damage == "hide-id":
        hide["href"] = "hide?id=49911532&goto=news"
    elif damage == "hide-destination":
        hide["href"] = "hide?id=49911531&goto=jobs"
    elif damage == "hide-label":
        hide.string = "10 comments"
    elif damage == "duplicate-age":
        metadata.append(BeautifulSoup(str(age), "html.parser").span)
    elif damage == "duplicate-hide":
        metadata.append(BeautifulSoup(str(hide), "html.parser").a)
    elif damage == "unexpected-link":
        metadata.append(BeautifulSoup('<a href="user?id=test">test</a>', "html.parser").a)
    elif damage == "score":
        metadata.append(BeautifulSoup(
            '<span class="score" id="score_49911531">1 point</span>', "html.parser",
        ).span)
    elif damage == "comment-text":
        metadata.append(" 10 comments")
    elif damage == "unexplained-text":
        metadata.insert(0, "by someone ")
    elif damage == "wrong-separator":
        metadata.contents[1].replace_with(" / ")
    elif damage == "missing-separator":
        metadata.contents[1].extract()
    elif damage == "nested-hide":
        hide.wrap(job_page.new_tag("span"))
    elif damage == "empty-age":
        age.a.string = " "
    else:
        metadata.append(BeautifulSoup('<span class="score"></span>', "html.parser").span)

    with pytest.raises(HNParseError, match="Entry id=49911531.*rank 8.*job metadata"):
        parse_homepage(str(job_page))


@pytest.mark.parametrize(
    ("mode", "expected_numbers"),
    [("all", [8, 7, 3, 2, *range(10, 36)]),
     ("long", [2, 7, 8]), ("short", [3, *range(10, 36)])],
)
def test_captured_job_through_cli_with_real_parser_filters_and_storage(
    job_page, monkeypatch, capsys, tmp_path, mode, expected_numbers,
):
    response = requests.Response()
    response.status_code = 200
    response._content = str(job_page).encode("utf-8")
    response._content_consumed = True
    get = Mock(return_value=response)
    monkeypatch.setattr(fetch.requests, "get", get)
    database = tmp_path / "job.sqlite3"

    assert cli.main(["--filter", mode, "--db", str(database)]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    rows = json.loads(output.out)
    assert [row["number"] for row in rows] == expected_numbers
    if mode != "short":
        assert next(row for row in rows if row["number"] == 8) == {
            "number": 8, "title": "Bild AI (YC W25) Is Hiring a Founding Product Engineer",
            "points": 0, "comments": 0,
        }
    with closing(sqlite3.connect(database)) as connection:
        events = connection.execute(
            "SELECT filter_id, status, fetched_count, result_count, error_type FROM usage_events"
        ).fetchall()
    assert events == [(mode, "success", 30, len(expected_numbers), None)]
    get.assert_called_once()
