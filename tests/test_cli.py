import json
import subprocess
import sys
from unittest.mock import Mock

import pytest
import requests

from hn_crawler import cli
from hn_crawler.models import Entry
from hn_crawler.parser import HNParseError


@pytest.fixture
def entries():
    return [
        Entry(9, "Café 你好 😀", 2, 100),
        Entry(7, "one two three four five six", 100, 2),
        Entry(3, "Short title", 10, 0),
        Entry(2, "a b c d e f", 1, 10),
    ]


@pytest.mark.parametrize(
    ("arguments", "expected_numbers"),
    [([], [9, 7, 3, 2]), (["--filter", "all"], [9, 7, 3, 2]),
     (["--filter", "long"], [2, 7]), (["--filter", "short"], [3, 9])],
)
def test_modes_default_and_json_fields(monkeypatch, capsys, entries, arguments, expected_numbers):
    fetch = Mock(return_value="html")
    parse = Mock(return_value=entries)
    monkeypatch.setattr(cli, "fetch_homepage", fetch)
    monkeypatch.setattr(cli, "parse_homepage", parse)

    assert cli.main(arguments) == 0

    output = capsys.readouterr()
    assert output.err == ""
    rows = json.loads(output.out)
    assert [row["number"] for row in rows] == expected_numbers
    assert all(set(row) == {"number", "title", "points", "comments"} for row in rows)
    if 9 in expected_numbers:
        assert "Café 你好 😀" in output.out
        assert next(row for row in rows if row["number"] == 9) == {
            "number": 9, "title": "Café 你好 😀", "points": 2, "comments": 100,
        }
    fetch.assert_called_once_with()
    parse.assert_called_once_with("html")


@pytest.mark.parametrize(
    ("mode", "entry"),
    [("long", Entry(1, "Short", 2, 10)),
     ("short", Entry(1, "one two three four five six", 2, 10))],
)
def test_empty_filtered_results_are_successful(monkeypatch, capsys, mode, entry):
    monkeypatch.setattr(cli, "fetch_homepage", Mock(return_value="html"))
    monkeypatch.setattr(cli, "parse_homepage", Mock(return_value=[entry]))

    assert cli.main(["--filter", mode]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == []
    assert output.err == ""


@pytest.mark.parametrize("arguments", [["--filter", "bad"], ["--unknown"], ["--filter"]])
def test_invalid_arguments_use_argparse_and_do_not_fetch(monkeypatch, capsys, arguments):
    fetch = Mock()
    monkeypatch.setattr(cli, "fetch_homepage", fetch)

    with pytest.raises(SystemExit) as error:
        cli.main(arguments)

    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "usage:" in output.err
    fetch.assert_not_called()


@pytest.mark.parametrize(
    "error", [requests.HTTPError("503"), requests.Timeout("slow"), requests.ConnectionError("offline")],
)
def test_fetch_failures_have_no_success_output(monkeypatch, capsys, error):
    fetch = Mock(side_effect=error)
    parse = Mock()
    monkeypatch.setattr(cli, "fetch_homepage", fetch)
    monkeypatch.setattr(cli, "parse_homepage", parse)

    assert cli.main([]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert type(error).__name__ in output.err
    assert str(error) in output.err
    fetch.assert_called_once()
    parse.assert_not_called()


def test_parse_failure_is_reported_on_stderr(monkeypatch, capsys):
    monkeypatch.setattr(cli, "fetch_homepage", Mock(return_value="bad html"))
    monkeypatch.setattr(cli, "parse_homepage", Mock(side_effect=HNParseError("missing rows")))

    assert cli.main([]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "HNParseError" in output.err
    assert "missing rows" in output.err


def test_programming_errors_are_not_hidden(monkeypatch):
    monkeypatch.setattr(cli, "fetch_homepage", Mock(side_effect=RuntimeError("bug")))

    with pytest.raises(RuntimeError, match="bug"):
        cli.main([])


def test_module_entry_point_help_is_offline():
    result = subprocess.run(
        [sys.executable, "-m", "hn_crawler", "--help"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )

    assert result.returncode == 0
    assert "--filter {all,long,short}" in result.stdout
    assert result.stderr == ""
