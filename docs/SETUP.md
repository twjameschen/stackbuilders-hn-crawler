# Development setup

Tested on Windows with Python 3.12.3 and pip 24.0. Use the project-local
interpreter explicitly; activation and execution-policy changes are unnecessary.

## Reproduce the environment

Run from the project root. If `.venv` is absent:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
```

Preserve an existing environment and verify it before installation:

```powershell
& .\.venv\Scripts\python.exe -c "import sys; assert sys.version_info[:2] == (3, 12); assert sys.prefix != sys.base_prefix; print(sys.executable); print(sys.version)"
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-dev.txt -e ".[dev]"
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pytest --version
```

## Recorded versions

| Component | Version |
| --- | --- |
| Python | 3.12.3 |
| pip | 24.0 |
| Isolated build backend: setuptools | 80.9.0 |
| Editable project | 0.1.0 |
| Beautiful Soup (beautifulsoup4) | 4.15.0 |
| soupsieve | 2.10 |
| typing_extensions | 4.16.0 |
| Requests | 2.34.2 |
| certifi | 2026.7.22 |
| charset-normalizer | 3.5.2 |
| idna | 3.20 |
| urllib3 | 2.8.0 |
| pytest | 9.1.1 |
| colorama | 0.4.6 |
| iniconfig | 2.3.0 |
| packaging | 26.3 |
| pluggy | 1.6.0 |
| Pygments | 2.21.0 |

`pyproject.toml` pins Beautiful Soup, Requests, pytest, and the build backend.
`requirements-dev.txt` records the resolved runtime and development dependencies,
including transitive packages. Existing dependency versions were preserved.
Setuptools runs in pip's isolated build environment; it is not a runtime
dependency. Beautiful Soup and Requests are the direct runtime dependencies.
Parsing uses standard-library `html.parser` without lxml or html5lib.

The original development installation used
`& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -e ".[dev]"`.
The dependency snapshot was generated with
`& .\.venv\Scripts\python.exe -m pip freeze --exclude-editable`.
Refresh and review the snapshot only when deliberately changing dependencies.

Phase 1 verified editable installation, import from `src/hn_crawler/`, and
`pip check` (`No broken requirements found.`). Test collection found no tests
and returned exit 5, as expected before behavior was implemented.

Phase 3 verified the updated editable installation, Beautiful Soup on Python
3.12.3, all 70 offline tests, and `pip check`. Run tests with
`& .\.venv\Scripts\python.exe -m pytest -q`.

Increment A verified Requests 2.34.2 on the same interpreter, preserving
existing versions, all 91 offline tests, and `pip check`.

Increment B uses standard-library SQLite with no new dependencies. All 112
offline tests and `pip check` passed on the existing Python 3.12.3 environment.
