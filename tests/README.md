# Offline tests

Run from the project root after installing the development dependencies:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
```

```sh
.venv/bin/python -m pytest -q
```

| Test file | Coverage |
| --- | --- |
| `test_models.py` | Field preservation and frozen entries |
| `test_filters.py` | Word-count assumptions, boundaries, complementary sets, numeric sorts, rank ties, unchanged input |
| `test_parser.py` | First-30/source-order extraction, valid fields, entities/nested text, incomplete/malformed pages, metadata ownership, age-only jobs |
| `test_homepage_job.py` | Captured age-plus-hide jobs, whitespace, URL identity independent of navigation, damaged jobs, CLI integration |
| `test_fetch.py` | Fixed URL, headers, timeouts, TLS, response closure, HTTP/redirect/transport failures without retries |
| `test_cli.py` | Modes/default/JSON, errors, event timing/counts, storage failures, record-before-output, real parser/filter/storage integration |
| `test_storage.py` | Initialization, parameterized inserts, reopened persistence, connection closure |

HTTP is mocked; normal tests never contact the network. SQLite tests use
`tmp_path`, and default-path tests change to a temporary working directory.
Integration tests replace only the HTTP boundary and keep parsing, filtering,
and storage real. Expected fields and rank sequences are specified explicitly.

`conftest.py` and local builders create synthetic HTML. Compact captured row
pairs are combined with synthetic rows to reach 30 entries; those composites
are not represented as captured full homepages. See [fixture provenance](fixtures/README.md).
Full development snapshots are ignored and not required to run the suite.
