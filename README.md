# Stack Builders Hacker News crawler

A Python 3.12 command-line exercise that fetches
https://news.ycombinator.com/ directly as HTML, extracts the original first
30 entries, applies title-length filters, and records usage in local SQLite.
Each JSON entry contains only `number`, `title`, `points`, and `comments`.

## Setup

Install Python 3.12 and run commands from the project root. Create `.venv`
only if it is absent; preserve an existing environment. Activation is not needed.

Windows PowerShell:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-dev.txt -e ".[dev]"
```

macOS/Linux:

```sh
python3.12 --version
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r requirements-dev.txt -e ".[dev]"
```

`requirements-dev.txt` pins the tested runtime/development dependencies;
`pyproject.toml` pins direct dependencies and the build backend.
See [environment verification](docs/SETUP.md) for clean-install checks.

## Run

Windows PowerShell:

```powershell
& .\.venv\Scripts\python.exe -m hn_crawler --filter all
& .\.venv\Scripts\python.exe -m hn_crawler --filter long
& .\.venv\Scripts\python.exe -m hn_crawler --filter short
& .\.venv\Scripts\python.exe -m hn_crawler --filter long --db .\data\custom.sqlite3
```

macOS/Linux:

```sh
.venv/bin/python -m hn_crawler --filter all
.venv/bin/python -m hn_crawler --filter long
.venv/bin/python -m hn_crawler --filter short
.venv/bin/python -m hn_crawler --filter long --db data/custom.sqlite3
```

The default filter is `all`. Successful stdout is a Unicode-preserving JSON
array; diagnostics go to stderr. Empty filtered results produce `[]`.

| Filter | Selection | Order |
| --- | --- | --- |
| `all` | Original first 30 entry rows | HTML source order |
| `long` | More than five words | Comments descending, original rank ascending for ties |
| `short` | Five or fewer words | Points descending, original rank ascending for ties |

Word counting splits on whitespace. A token counts once if it contains a
Unicode letter or number; **numeric tokens count as words by assumption**.
Hyphenated tokens remain intact; symbol-only tokens are ignored.
`This is - a self-explained example` counts as five words. Filtering preserves
original ranks and never substitutes later entries for removed entries.

Normal stories require valid nonnegative points/comments; `discuss` means zero
comments. Identifiable jobs with the observed spacer image and age-only or
age-plus-hide metadata normalize absent metrics to zero. A job hide URL must
have relative path `hide` and exactly one matching `id`; navigation parameters
do not affect identity. Missing/malformed story metadata, damaged job metadata,
or fewer than 30 entry rows cause a parsing error. See [design notes](docs/DESIGN.md).

## Usage records and failures

`--db PATH` defaults to `data/usage.sqlite3`, relative to the current working
directory. Parent directories and the `usage_events` table are created automatically.
After running a command, inspect that database using Python's `sqlite3` module:

```powershell
& .\.venv\Scripts\python.exe -m sqlite3 .\data\usage.sqlite3 "SELECT * FROM usage_events ORDER BY id DESC LIMIT 10;"
```

```sh
.venv/bin/python -m sqlite3 data/usage.sqlite3 "SELECT * FROM usage_events ORDER BY id DESC LIMIT 10;"
```

Use the custom database path instead if supplied with `--db`.
Records contain `id`, UTC operation-start `requested_at` with timezone,
`filter_id`, `status`, `fetched_count`, `result_count`, monotonic `duration_ms`,
and nullable `error_type`. No scraped content or personal information is stored.

- `fetched_count` means successfully parsed entries. Parse failure records
  zero even if an HTTP response was received; `result_count` is the selected count.
- Duration ends immediately before usage recording, excluding the final
  SQLite write and output.
- Success returns exit 0 after committing one event, then prints JSON.
  `status=success` describes successful crawl/filter processing and a committed
  usage record; it cannot guarantee downstream stdout delivery.
- HTTP/parsing failures return exit 1 and record one failure when storage is
  usable. Storage initialization failure prevents HTTP. Record-write failure
  prevents successful JSON; if crawling also failed, both errors reach stderr.
  Unavailable storage cannot always persist its own failure.
- Invalid arguments use argparse's exit 2 before storage/network access.

Each valid invocation with usable storage makes one request, with an application
User-Agent, TLS verification, and connect/read timeouts of 5/10 seconds.
There are no retries; redirects are rejected. Requests timeouts are not a
strict total-operation deadline. Unknown HTML layouts fail explicitly.

## Tests

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m pip check
```

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

Tests are offline: HTTP is mocked, SQLite uses temporary databases, and compact
captured fixtures are distinguished from synthetic HTML. Integration tests use
the real parser, filters, and storage. See [test coverage](tests/README.md).

## AI assistance

AI helped with planning, implementation, tests, and review. A live test exposed
an overly restrictive job rule; the captured response enabled a regression test
and correction. The candidate remains responsible for understanding and owning
the solution.
