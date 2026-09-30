# Tests

Run from the project root with the existing Python 3.12 environment:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
```

`test_models.py` checks field preservation and frozen fields.
`test_filters.py` specifies expected word counts, filter membership, numeric
ordering, rank ties, unchanged input, empty results, complementary sets,
and processing of more than 30 supplied entries. Tests use only in-memory data.

Phase 2 test-first record: both test files were written before implementation.
The first run returned exit 2 with `ModuleNotFoundError` for the missing
`hn_crawler.models` and `hn_crawler.filters` modules. After implementation,
32 tests passed (exit 0). `pip check` found no broken requirements.

`test_parser.py` adds 38 offline parser/integration tests. A compact local
`story`/`page` builder produces synthetic HTML; expected fields and ordering
are specified independently of the parser. Four captured row pairs in
`fixtures/captured_rows.html` cover ordinary/plural comments, singular comments,
`discuss`, and a job. See `fixtures/README.md` for provenance and limitations.
The captured excerpts are not a complete homepage and are combined with
synthetic rows only in explicitly assembled test inputs.

Phase 3 initial parser tests failed with a missing-module collection error
(exit 2). After implementation, all 70 tests passed, including the original
32 model/filter tests. No test accesses the network or a database. Full-page
captures used for development inspection are not required to run tests.
`test_fetch.py` mocks Requests to check URL, headers, finite timeouts, TLS,
response closure, status/redirect failures, and transport errors without retry.
`test_cli.py` checks all/default/long/short modes, JSON fields and Unicode,
empty filtered results, argparse errors, operational diagnostics, and the
module help entry point. Increment A passes 91 offline tests.

Increment B adds real SQLite tests using `tmp_path`. CLI tests temporarily
change the working directory so default-path tests never use the developer's
database. They check successful/failed events, UTC operation-start timestamps,
monotonic duration, counts, filter IDs, append behavior, initialization before
HTTP, record-before-output ordering, write failures, and combined diagnostics.
`test_storage.py` checks table initialization, parameterized values, reopened
persistence, and connection closure. `conftest.py` supplies a small synthetic
30-entry response for end-to-end tests; only HTTP is replaced while parsing,
filtering, and storage remain real. Increment B passes 112 offline tests.
No normal test contacts the network or writes to the developer's usage database.
