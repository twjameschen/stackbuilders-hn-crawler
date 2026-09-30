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

## Proposed assumptions for review

- Both sorts are descending; ties use original rank ascending.
- Filtering operates only on the original first 30 entries; do not fetch
  extra entries to replace those removed by a filter.
- Preserve original ranks in results, rather than renumbering.
- Each whitespace-separated token containing at least one Unicode letter or
  number counts as one word. Hyphenated words stay one token; symbol-only
  tokens count as zero. In the required example, the standalone `-` is ignored
  and `self-explained` counts once.
- An empty filtered result is valid.
- A CLI request timestamp is the operation start time, stored in UTC with
  explicit timezone information.

## Planned structure (modules are not implemented)

Use Python 3.12, Requests, Beautiful Soup, standard-library `sqlite3` and
`argparse`, and pytest. Add runtime dependencies only when needed.

| Proposed module | Responsibility |
| --- | --- |
| `models.py` | A simple entry representation shared across the application |
| `fetch.py` | HTTP access with explicit timeout and error handling |
| `parser.py` | Convert supplied HTML into the original entries |
| `filters.py` | Pure word counting, selection, and deterministic sorting |
| `storage.py` | Local SQLite usage persistence |
| `cli.py`, `__main__.py` | Argument parsing and operation orchestration |

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

## Planned verification

Use saved, representative HTML fixtures for parser tests without live network
dependencies. Cover Unicode letters/numbers, symbol-only tokens, the exact
5-word example, title-length boundaries, both descending sorts, rank ties,
preserved ranks, and empty results. Test persistence with temporary SQLite
databases and explicit timezone-aware timestamps. Keep HTTP and CLI tests
separate from pure logic tests. No behavioral tests exist in Phase 1.
