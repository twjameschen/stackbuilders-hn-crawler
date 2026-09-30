from contextlib import closing
import sqlite3

import pytest

from hn_crawler.storage import initialize_storage, record_usage


def test_initialize_creates_parents_and_is_idempotent_without_events(tmp_path):
    database = tmp_path / "nested" / "usage.sqlite3"

    initialize_storage(database)
    initialize_storage(database)

    with closing(sqlite3.connect(database)) as connection:
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert tables == [("usage_events",)]
        assert connection.execute("SELECT COUNT(*) FROM usage_events").fetchone() == (0,)


def test_parameterized_values_persist_and_connections_are_closed(tmp_path):
    database = tmp_path / "usage.sqlite3"
    initialize_storage(database)
    quoted_value = "all'); DROP TABLE usage_events; --"

    record_usage(
        database, requested_at="2026-10-01T00:00:00+00:00", filter_id=quoted_value,
        status="success", fetched_count=30, result_count=30, duration_ms=5, error_type=None,
    )

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT filter_id FROM usage_events").fetchall() == [(quoted_value,)]
        columns = [row[1] for row in connection.execute("PRAGMA table_info(usage_events)")]
        assert columns == ["id", "requested_at", "filter_id", "status", "fetched_count",
                           "result_count", "duration_ms", "error_type"]
    database.unlink()
    assert not database.exists()


def test_recording_errors_propagate_without_leaking_connection(tmp_path):
    database = tmp_path / "missing-table.sqlite3"

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        record_usage(
            database, requested_at="2026-10-01T00:00:00+00:00", filter_id="all",
            status="failure", fetched_count=0, result_count=0, duration_ms=0, error_type="Timeout",
        )

    database.unlink()
    assert not database.exists()
