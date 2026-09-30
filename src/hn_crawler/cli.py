"""Command-line orchestration for fetching, parsing, and pure filtering."""

import argparse
from dataclasses import asdict
import json
import sys

from requests import RequestException

from hn_crawler.fetch import fetch_homepage
from hn_crawler.filters import filter_long_titles, filter_short_titles
from hn_crawler.parser import HNParseError, parse_homepage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read the first 30 Hacker News entries.")
    parser.add_argument("--filter", choices=("all", "long", "short"), default="all")
    args = parser.parse_args(argv)

    try:
        entries = parse_homepage(fetch_homepage())
        if args.filter == "long":
            results = filter_long_titles(entries)
        elif args.filter == "short":
            results = filter_short_titles(entries)
        else:
            results = entries
    except (RequestException, HNParseError) as exc:
        print(f"Crawl failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    print(json.dumps([asdict(entry) for entry in results], ensure_ascii=False))
    return 0
