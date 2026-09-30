# Environment verification

Use Python 3.12. The [README](../README.md) contains Windows and macOS/Linux
setup, run, test, and SQLite inspection commands. Interpreter paths are explicit;
activation or execution-policy changes are unnecessary.

`pyproject.toml` pins Requests 2.34.2, Beautiful Soup 4.15.0, pytest 9.1.1,
and isolated build backend setuptools 80.9.0. `requirements-dev.txt` pins the
resolved runtime/development packages. No dependency upgrades were made during
final preparation. Installation needs access to a package index (or a separately
prepared local package source).

## Clean verification on Windows

From the project root, create a separate environment at an unused ignored path,
preserving the original `.venv`:

```powershell
py -3.12 -m venv .setup-tmp/review-venv
& .\.setup-tmp\review-venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-dev.txt -e ".[dev]"
& .\.setup-tmp\review-venv\Scripts\python.exe -m pytest -q --basetemp .setup-tmp/pytest-clean-review
& .\.setup-tmp\review-venv\Scripts\python.exe -m pip check
& .\.setup-tmp\review-venv\Scripts\python.exe -m hn_crawler --help
& .\.setup-tmp\review-venv\Scripts\python.exe -I -c "import hn_crawler, hn_crawler.cli, requests, bs4, pytest; print(hn_crawler.__file__)"
```

The install arguments are identical to the normal README installation;
only the interpreter path changes. The package is editable, so project imports
resolve to `src/hn_crawler`; dependencies must resolve inside the new environment.
The test base directory keeps temporary databases inside the ignored project area.

Final clean verification used Windows and CPython 3.12.3: 152 offline tests
passed, `pip check` found no broken requirements, the module help exited 0,
and isolated-mode imports succeeded without the original `.venv` on `sys.path`.
The macOS/Linux commands are provided but were not executed on those platforms.
No additional live homepage request was made during final preparation.
