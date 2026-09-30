# Design notes

## Requirements

- Fetch `https://news.ycombinator.com/` directly and parse its HTML.
- Extract the original rank, title, points, and comment count of the first
  30 entries.
- Select titles with more than five words and sort by comment count.
- Select titles with five or fewer words and sort by points.
- Count whitespace-separated tokens, excluding symbol-only tokens.
  `This is - a self-explained example` must count as **5** words.
- Persist usage data including a request timestamp and filter identifier.
- Include automated tests, a clear README, and brief design documentation.
- Keep genuine incremental Git history. The candidate must understand and own
  the solution, including any AI-assisted work.

## Filtering decisions and remaining assumptions

- Both sorts are descending; ties use original rank ascending.
- The final pipeline will select the original first 30 entries before
  filtering; do not fetch extra entries to replace those removed by a filter.
  The pure filters process all supplied entries and do not fetch or truncate.
- Preserve original ranks in results, rather than renumbering.
- Each whitespace-separated token containing at least one Unicode letter or
  number counts as one word. **Numeric tokens count as words by assumption.**
  Hyphenated words stay one token; symbol-only
  tokens count as zero. In the required example, the standalone `-` is ignored
  and `self-explained` counts once.
- An empty filtered result is valid.
- A CLI request timestamp is the operation start time, stored in UTC with
  explicit timezone information.

## Structure and implementation status

Use Python 3.12, Requests, Beautiful Soup, standard-library `sqlite3` and
`argparse`, and pytest. Add runtime dependencies only when needed.

| Module | Status and responsibility |
| --- | --- |
| `models.py` | Implemented: frozen `Entry` with `number`, `title`, `points`, `comments` |
| `filters.py` | Implemented: pure word counting, selection, and deterministic sorting |
| `fetch.py` | Planned: HTTP access with explicit timeout and error handling |
| `parser.py` | Planned: convert supplied HTML into the original entries |
| `storage.py` | Planned: local SQLite usage persistence |
| `cli.py`, `__main__.py` | Planned: argument parsing and operation orchestration |

`Entry.number` is the original homepage rank; numeric fields have integer type
annotations. The dataclass is frozen and adds no runtime validation or class
hierarchy. Missing HTML fields are a later parser decision.

`count_words` uses whitespace splitting and Unicode-aware `str.isalnum`.
`filter_long_titles` sorts by `(-comments, number)` and
`filter_short_titles` sorts by `(-points, number)`. Each returns a new list,
leaving input order and field values unchanged. Empty results are valid.

The CLI will record the start time, fetch and parse HTML, call a pure filter,
and persist usage. Exact failure and persistence semantics remain unresolved.
Avoid inheritance, generic repositories, and unnecessary dependencies.

## Unresolved decisions

- Inspect representative HTML before deciding missing points/comments behavior
  (including job posts, new stories, `discuss` links, and deleted entries).
  Do not silently assume missing values are zero.
- Decide behavior when fewer than 30 valid entries exist or markup is malformed.
- Confirm CLI names, output format, database path, and filter identifiers;
  proposed identifiers are `long-title-comments` and `short-title-points`.
- Decide whether failed operations are logged, what additional usage fields are
  useful, and how database write failures affect CLI output and exit status.
- Confirm HTTP timeout/retry policy after inspecting the source and its usage
  expectations. HTML inspection is deferred to a later phase.

## Verification

Phase 2 tests were specified before implementation. The first run failed
because the model and filter modules were missing; after implementation,
32 tests passed. Coverage includes frozen fields, Unicode letters/numbers,
symbol-only tokens, the exact 5-word example, whitespace variants, title-length
boundaries, numeric descending sorts, rank ties, preserved input and ranks,
empty results, complementary selections, and no truncation above 30 entries.
Tests access no real network or database.

Later phases will use representative saved HTML fixtures for parser tests and
temporary SQLite databases for persistence tests, including timezone-aware
timestamps. Keep HTTP and CLI tests separate from pure logic tests.
