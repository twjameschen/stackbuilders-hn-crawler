# Stack Builders Hacker News crawler

An incremental Python 3.12 hiring exercise. The intended application will read
the first 30 entries directly from Hacker News HTML, apply two title-length
filters, and persist usage data in local SQLite.

## Current status: Phase 1

This phase contains packaging configuration, an empty importable package,
development environment setup, and design notes. The crawler, HTML parser,
word counter, filters, SQLite storage, and CLI are **not implemented**. There
are no automated tests yet; behavioral tests will accompany implementation.
Requests and Beautiful Soup are planned for a later phase and are not installed.

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

These identifiers and CLI details are proposals. After tests are implemented,
run `& .\.venv\Scripts\python.exe -m pytest`; currently it would find no tests
and exit with pytest's no-tests status (5).

## Organization and ownership

`src/hn_crawler/` holds application code; `tests/` will hold offline tests and
HTML fixtures; `docs/DESIGN.md` records requirements and decisions. Keep pure
filtering independent of network access and persistence. No frontend, API
server, Docker, browser automation, async, or cloud deployment is planned.

Make genuine commits as reviewed increments are completed. Phase 1 initializes
a local repository but creates no commits, remotes, or GitHub repository. AI
assistance is allowed; the candidate remains responsible for understanding,
explaining, and owning every implementation decision.
