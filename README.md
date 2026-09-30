# Stack Builders Hacker News crawler

An incremental Python 3.12 hiring exercise. The intended application will read
the first 30 entries directly from Hacker News HTML, apply two title-length
filters, and persist usage data in local SQLite.

## Current status: Phase 4, Increment A

Implemented: a frozen `Entry(number, title, points, comments)` dataclass,
Unicode-aware title word counting, two pure filters, and a pure HTML parser
with offline tests. `parse_homepage(html)` uses Beautiful Soup with the
standard-library `html.parser` backend and returns the first 30 entry rows
in source order. The Requests fetcher and argparse CLI are implemented.
SQLite usage recording is **not implemented yet**.

`count_words` splits on whitespace and counts a token once if it contains a
Unicode letter or number. Numeric tokens count as words by assumption;
hyphenated tokens remain intact and symbol-only tokens are ignored.
`This is - a self-explained example` counts as five words.

`filter_long_titles` selects titles with more than five words and sorts by
comments descending. `filter_short_titles` selects titles with five or fewer
words and sorts by points descending. Both break ties by original `number`
ascending, preserve entries and ranks, and return new lists without changing
the input. They process all supplied entries; the parser selects the original
first 30 homepage entry rows before extracting fields.

The parser requires positive ranks, nonempty titles, and valid nonnegative
metrics for normal stories. `discuss` means zero comments. Only identifiable
job rows with the observed spacer-image and age-only metadata structure
normalize absent points/comments to zero. Missing normal-story metadata is an
error. Pages with fewer than 30 entry rows fail; selected malformed rows are
not replaced by later rows. See [the parsing policy](docs/DESIGN.md).

## Setup (PowerShell)

Run every command from `D:\CodexProjects\stackbuilders-hn-crawler`.
Check the launcher first; create the environment only if `.venv` is absent:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
```

If `.venv` already exists, preserve it and verify its interpreter before use:

```powershell
& .\.venv\Scripts\python.exe -c "import sys; assert sys.version_info[:2] == (3, 12); assert sys.prefix != sys.base_prefix; print(sys.executable); print(sys.version)"
```

Install the recorded dependency snapshot plus the local editable package:

```powershell
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-dev.txt -e ".[dev]"
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pytest --version
```

No PowerShell activation or execution-policy change is needed. Exact versions,
commands, and observed verification results are recorded in
[the setup record](docs/SETUP.md). The development snapshot pins transitive
packages; the build backend is pinned separately in `pyproject.toml`.

## Run

The module entry point outputs a Unicode-preserving JSON array with only
`number`, `title`, `points`, and `comments`. The default mode is `all`:

```powershell
& .\.venv\Scripts\python.exe -m hn_crawler --filter all
& .\.venv\Scripts\python.exe -m hn_crawler --filter long
& .\.venv\Scripts\python.exe -m hn_crawler --filter short
```

`all` preserves the original 30-entry source order. `long` and `short` use
the pure filters described above. Empty filtered results produce `[]`.
Success returns exit 0; HTTP/parsing failures return exit 1 with diagnostics
on stderr and no result JSON. Invalid arguments use argparse's exit 2.

Each valid invocation fetches the fixed HTTPS homepage once, with User-Agent
`stackbuilders-hn-crawler/0.1.0`, TLS verification, and connect/read timeouts
of 5/10 seconds. There are no retries. Redirects are rejected to avoid
requesting a different URL. Requests timeouts are **not a strict total-operation
deadline**; read timeout limits inactivity between received data, not total
download duration. No scheduling, caching, or asynchronous execution is used.

## Run the implemented tests

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m pip check
```

Increment A verification: 91 offline tests passed; `pip check` reported no
broken requirements. HTTP tests mock Requests and CLI tests use small
monkeypatch seams. Existing model/filter/parser tests still pass.

## Organization and ownership

`src/hn_crawler/models.py` holds the entry model and `filters.py` holds pure
word counting, selection, and sorting. `parser.py` converts supplied HTML to
entries. `fetch.py` handles HTTP; `cli.py` orchestrates the module entry point.
`tests/` holds offline tests and small captured row excerpts with
provenance; its fixture builder supplies clearly synthetic test pages.
`docs/DESIGN.md` records decisions. Keep pure
filtering independent of network access and persistence. No frontend, API
server, Docker, browser automation, async, or cloud deployment is planned.

Make genuine commits as verified increments are completed. The repository is
local; no remote or GitHub repository is configured. AI
assistance is allowed; the candidate remains responsible for understanding,
explaining, and owning every implementation decision.
