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

Parser fixtures and storage tests remain for later phases.
