"""Small SQLite usage log; scraped entry content is never stored."""

from contextlib import closing
from pathlib import Path
import sqlite3


def initialize_storage(path: Path) -> None:
    """Create parents/table and check writable, compatible storage before HTTP."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY,
                requested_at TEXT NOT NULL,
                filter_id TEXT NOT NULL,
                status TEXT NOT NULL,
                fetched_count INTEGER NOT NULL,
                result_count INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                error_type TEXT
            )
        """)
        connection.execute("""
            SELECT requested_at, filter_id, status, fetched_count,
                   result_count, duration_ms, error_type
            FROM usage_events LIMIT 0
        """)


def record_usage(
    path: Path, *, requested_at: str, filter_id: str, status: str,
    fetched_count: int, result_count: int, duration_ms: int, error_type: str | None,
) -> None:
    """Commit one event with parameterized values, then close the connection."""
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("""
            INSERT INTO usage_events (
                requested_at, filter_id, status, fetched_count,
                result_count, duration_ms, error_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            requested_at, filter_id, status, fetched_count,
            result_count, duration_ms, error_type,
        ))
