# Stack Builders Hacker News crawler

An incremental Python 3.12 hiring exercise. The intended application will read
the first 30 entries directly from Hacker News HTML, apply two title-length
filters, and persist usage data in local SQLite.

## Current status: Phase 2

Implemented: a frozen `Entry(number, title, points, comments)` dataclass,
Unicode-aware title word counting, and two pure filters with offline tests.
The crawler, HTML parser, SQLite storage, and CLI are **not implemented**.
Requests and Beautiful Soup are planned for a later phase and are not installed.

`count_words` splits on whitespace and counts a token once if it contains a
Unicode letter or number. Numeric tokens count as words by assumption;
hyphenated tokens remain intact and symbol-only tokens are ignored.
`This is - a self-explained example` counts as five words.

`filter_long_titles` selects titles with more than five words and sorts by
comments descending. `filter_short_titles` selects titles with five or fewer
words and sorts by points descending. Both break ties by original `number`
ascending, preserve entries and ranks, and return new lists without changing
the input. They process all supplied entries; a later pipeline stage will
select the original first 30 homepage entries.

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

Keep package-manager temporary files inside the project and install the
recorded development environment plus the local editable package:

```powershell
New-Item -ItemType Directory -Path .\.setup-tmp -Force | Out-Null
$env:TEMP = Join-Path (Get-Location).Path '.setup-tmp'
$env:TMP = $env:TEMP
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

Phase 2 verification: 32 tests passed; `pip check` reported no broken
requirements. Tests use in-memory entries and access no network or database.

## Organization and ownership

`src/hn_crawler/models.py` holds the entry model and `filters.py` holds pure
word counting, selection, and sorting. `tests/` holds offline tests; HTML
fixtures will be added with parsing. `docs/DESIGN.md` records decisions. Keep pure
filtering independent of network access and persistence. No frontend, API
server, Docker, browser automation, async, or cloud deployment is planned.

Make genuine commits as verified increments are completed. The repository is
local; no remote or GitHub repository is configured. AI
assistance is allowed; the candidate remains responsible for understanding,
explaining, and owning every implementation decision.
