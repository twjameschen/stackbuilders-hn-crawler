"""Support python -m hn_crawler with Unicode-safe console and redirected output."""

import sys

from hn_crawler.cli import main

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
