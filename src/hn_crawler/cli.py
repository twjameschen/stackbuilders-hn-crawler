"""Command-line orchestration with usage saved before successful JSON output."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time

from requests import RequestException

from hn_crawler.fetch import fetch_homepage
from hn_crawler.filters import filter_long_titles, filter_short_titles
from hn_crawler.parser import HNParseError, parse_homepage
from hn_crawler.storage import initialize_storage, record_usage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read the first 30 Hacker News entries.")
    parser.add_argument("--filter", choices=("all", "long", "short"), default="all")
    parser.add_argument("--db", type=Path, default=Path("data/usage.sqlite3"))
    args = parser.parse_args(argv)

    requested_at = datetime.now(timezone.utc).isoformat()
    started_ns = time.monotonic_ns()
    try:
        initialize_storage(args.db)
    except (OSError, sqlite3.Error) as exc:
        print(f"Storage initialization failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    fetched_count = result_count = 0
    crawl_error = None
    try:
        entries = parse_homepage(fetch_homepage())
        fetched_count = len(entries)
        if args.filter == "long":
            results = filter_long_titles(entries)
        elif args.filter == "short":
            results = filter_short_titles(entries)
        else:
            results = entries
        result_count = len(results)
        payload = json.dumps([asdict(entry) for entry in results], ensure_ascii=False)
    except (RequestException, HNParseError) as exc:
        crawl_error = exc
        print(f"Crawl failed ({type(exc).__name__}): {exc}", file=sys.stderr)

    try:
        record_usage(
            args.db, requested_at=requested_at, filter_id=args.filter,
            status="success" if crawl_error is None else "failure",
            fetched_count=fetched_count, result_count=result_count,
            duration_ms=(time.monotonic_ns() - started_ns) // 1_000_000,
            error_type=None if crawl_error is None else type(crawl_error).__name__,
        )
    except (OSError, sqlite3.Error) as exc:
        print(f"Usage recording failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    if crawl_error is not None:
        return 1
    print(payload)
    return 0
