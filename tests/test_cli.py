import json
from contextlib import closing
from datetime import datetime, timedelta, timezone
import sqlite3
import subprocess
import sys
from unittest.mock import Mock

import pytest
import requests

from hn_crawler import cli
from hn_crawler.models import Entry
from hn_crawler.parser import HNParseError


@pytest.fixture(autouse=True)
def temporary_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def read_events(path):
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("SELECT * FROM usage_events ORDER BY id")]


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


@pytest.mark.parametrize("mode", ["all", "long", "short"])
def test_success_events_have_start_time_counts_and_monotonic_duration(
    monkeypatch, capsys, tmp_path, entries, mode
):
    database = tmp_path / "nested" / "custom.sqlite3"
    monkeypatch.setattr(cli, "fetch_homepage", Mock(return_value="html"))
    monkeypatch.setattr(cli, "parse_homepage", Mock(return_value=entries))
    monkeypatch.setattr(cli.time, "monotonic_ns", Mock(side_effect=[1_000_000_000, 1_025_000_000]))
    before = datetime.now(timezone.utc)

    assert cli.main(["--filter", mode, "--db", str(database)]) == 0

    after = datetime.now(timezone.utc)
    rows = json.loads(capsys.readouterr().out)
    events = read_events(database)
    assert len(events) == 1
    event = events[0]
    timestamp = datetime.fromisoformat(event["requested_at"])
    assert timestamp.utcoffset() == timedelta(0)
    assert before <= timestamp <= after
    assert event["filter_id"] == mode
    assert event["status"] == "success"
    assert event["fetched_count"] == 4
    assert event["result_count"] == len(rows)
    assert event["duration_ms"] == 25
    assert event["error_type"] is None


@pytest.mark.parametrize(
    "error", [requests.HTTPError("503"), requests.Timeout("slow"),
              requests.ConnectionError("offline"), HNParseError("bad HTML")],
)
def test_operational_failure_records_are_persisted(monkeypatch, capsys, tmp_path, error):
    database = tmp_path / "failure.sqlite3"
    if isinstance(error, HNParseError):
        monkeypatch.setattr(cli, "fetch_homepage", Mock(return_value="bad HTML"))
        monkeypatch.setattr(cli, "parse_homepage", Mock(side_effect=error))
    else:
        monkeypatch.setattr(cli, "fetch_homepage", Mock(side_effect=error))

    assert cli.main(["--filter", "short", "--db", str(database)]) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert type(error).__name__ in output.err
    events = read_events(database)
    assert len(events) == 1
    event = events[0]
    assert event["filter_id"] == "short"
    assert event["status"] == "failure"
    assert event["fetched_count"] == event["result_count"] == 0
    assert event["duration_ms"] >= 0
    assert datetime.fromisoformat(event["requested_at"]).utcoffset() == timedelta(0)
    assert event["error_type"] == type(error).__name__


def test_multiple_invocations_append_separate_events(monkeypatch, capsys, tmp_path, entries):
    database = tmp_path / "usage.sqlite3"
    fetch = Mock(return_value="html")
    monkeypatch.setattr(cli, "fetch_homepage", fetch)
    monkeypatch.setattr(cli, "parse_homepage", Mock(return_value=entries))

    for mode in ("all", "long", "short"):
        assert cli.main(["--filter", mode, "--db", str(database)]) == 0
        capsys.readouterr()

    events = read_events(database)
    assert [event["filter_id"] for event in events] == ["all", "long", "short"]
    assert [event["result_count"] for event in events] == [4, 2, 2]
    assert [event["id"] for event in events] == [1, 2, 3]
    fetch.assert_called_with()
    assert fetch.call_count == 3


@pytest.mark.parametrize("cause", ["parent-file", "incompatible-schema"])
def test_storage_initialization_failure_prevents_http(monkeypatch, capsys, tmp_path, cause):
    if cause == "parent-file":
        parent = tmp_path / "blocked"
        parent.write_text("not a directory")
        database = parent / "usage.sqlite3"
    else:
        database = tmp_path / "wrong.sqlite3"
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("CREATE TABLE usage_events (unrelated TEXT)")
    fetch = Mock()
    monkeypatch.setattr(cli, "fetch_homepage", fetch)

    assert cli.main(["--db", str(database)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "Storage initialization failed" in output.err
    fetch.assert_not_called()


@pytest.mark.parametrize("crawl_fails", [False, True])
def test_record_write_failure_suppresses_success_and_preserves_both_errors(
    monkeypatch, capsys, tmp_path, entries, crawl_fails
):
    database = tmp_path / "usage.sqlite3"
    fetch = Mock(side_effect=requests.Timeout("crawl timeout")) if crawl_fails else Mock(return_value="html")
    monkeypatch.setattr(cli, "fetch_homepage", fetch)
    monkeypatch.setattr(cli, "parse_homepage", Mock(return_value=entries))
    monkeypatch.setattr(cli, "record_usage", Mock(side_effect=sqlite3.OperationalError("disk full")))

    assert cli.main(["--db", str(database)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "Usage recording failed" in output.err
    assert "disk full" in output.err
    if crawl_fails:
        assert "Crawl failed (Timeout)" in output.err
        assert "crawl timeout" in output.err
    assert read_events(database) == []
    fetch.assert_called_once()


def test_json_is_emitted_only_after_record_has_been_saved(monkeypatch, capsys, entries):
    monkeypatch.setattr(cli, "fetch_homepage", Mock(return_value="html"))
    monkeypatch.setattr(cli, "parse_homepage", Mock(return_value=entries))
    save = cli.record_usage

    def checked_save(path, **values):
        assert capsys.readouterr().out == ""
        save(path, **values)
        assert len(read_events(path)) == 1

    monkeypatch.setattr(cli, "record_usage", checked_save)

    assert cli.main([]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 4


@pytest.mark.parametrize(
    ("mode", "expected_numbers"),
    [("all", [9, 7, 3, 2, *range(10, 36)]),
     ("long", [2, 7]), ("short", [3, 9, *range(10, 36)])],
)
def test_offline_end_to_end_with_only_http_replaced(
    monkeypatch, capsys, tmp_path, homepage_response, mode, expected_numbers
):
    from hn_crawler import fetch

    get = Mock(return_value=homepage_response)
    monkeypatch.setattr(fetch.requests, "get", get)
    database = tmp_path / "end-to-end.sqlite3"

    assert cli.main(["--filter", mode, "--db", str(database)]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert [row["number"] for row in json.loads(output.out)] == expected_numbers
    event, = read_events(database)
    assert event["status"] == "success"
    assert event["fetched_count"] == 30
    assert event["result_count"] == len(expected_numbers)
    assert event["filter_id"] == mode
    get.assert_called_once()


def test_default_database_is_relative_to_working_directory(monkeypatch, capsys, tmp_path, entries):
    monkeypatch.setattr(cli, "fetch_homepage", Mock(return_value="html"))
    monkeypatch.setattr(cli, "parse_homepage", Mock(return_value=entries))

    assert cli.main([]) == 0
    assert len(read_events(tmp_path / "data" / "usage.sqlite3")) == 1
    capsys.readouterr()


def test_invalid_arguments_do_not_initialize_storage(monkeypatch, capsys):
    initialize = Mock()
    monkeypatch.setattr(cli, "initialize_storage", initialize)

    with pytest.raises(SystemExit) as error:
        cli.main(["--filter", "invalid"])

    assert error.value.code == 2
    initialize.assert_not_called()
    assert capsys.readouterr().out == ""
