# Stack Builders Hacker News crawler

An incremental Python 3.12 hiring exercise. The intended application will read
the first 30 entries directly from Hacker News HTML, apply two title-length
filters, and persist usage data in local SQLite.

## Current status: Phase 3

Implemented: a frozen `Entry(number, title, points, comments)` dataclass,
Unicode-aware title word counting, two pure filters, and a pure HTML parser
with offline tests. `parse_homepage(html)` uses Beautiful Soup with the
standard-library `html.parser` backend and returns the first 30 entry rows
in source order. The application HTTP fetcher, SQLite storage, and CLI are
**not implemented**. Requests is not installed.

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

## Planned commands (not available yet)

The proposed argparse interface is:

```powershell
& .\.venv\Scripts\python.exe -m hn_crawler --filter long-title-comments
& .\.venv\Scripts\python.exe -m hn_crawler --filter short-title-points
```

These identifiers and CLI details are proposals.

## Run the implemented tests

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m pip check
```

Phase 3 verification: 70 tests passed, including the existing 32 model/filter
tests; `pip check` reported no broken requirements. Tests use in-memory entries
and offline HTML, and access no network or database.

## Organization and ownership

`src/hn_crawler/models.py` holds the entry model and `filters.py` holds pure
word counting, selection, and sorting. `parser.py` converts supplied HTML to
entries. `tests/` holds offline tests and small captured row excerpts with
provenance; its fixture builder supplies clearly synthetic test pages.
`docs/DESIGN.md` records decisions. Keep pure
filtering independent of network access and persistence. No frontend, API
server, Docker, browser automation, async, or cloud deployment is planned.

Make genuine commits as verified increments are completed. The repository is
local; no remote or GitHub repository is configured. AI
assistance is allowed; the candidate remains responsible for understanding,
explaining, and owning every implementation decision.
