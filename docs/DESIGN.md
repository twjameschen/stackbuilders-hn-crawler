# Design notes

## Choices and separation

Python 3.12 supports a small readable solution with dataclasses, Unicode string
operations, argparse, and SQLite in the standard library. Requests provides
explicit status/error handling and connect/read timeouts with little HTTP code.
Beautiful Soup with `html.parser` handles HTML entities and nested text without
regex or an additional parser backend. A CLI fits the exercise's inputs and
JSON output; SQLite provides durable local events without a database service.

| Module | Responsibility |
| --- | --- |
| `models.py` | Frozen `Entry(number, title, points, comments)`; no speculative validation |
| `fetch.py` | One fixed-URL request; explicit User-Agent, TLS, finite timeouts, no retries/redirects |
| `parser.py` | Supplied HTML to the original first 30 entries, or `HNParseError` |
| `filters.py` | Pure word counting, selection, and sorting; no fetch/truncation/mutation |
| `storage.py` | Initialize one SQLite table and insert parameterized usage events |
| `cli.py`, `__main__.py` | Argument parsing, orchestration, UTC/monotonic timing, UTF-8 JSON and errors |

`urllib` would avoid Requests but require more HTTP/error plumbing. A lower-level
HTML parser would require explicit tree handling; lxml would add a dependency
without a demonstrated need. JSON-line logging is simpler but less convenient
to query consistently. An API server, ORM, and scraping framework would add
scope without helping this single-operation exercise.

## Parsing and filtering policy

Select `tr.athing` in source order and take 30 before extracting fields.
Require at least 30; a selected malformed entry aborts parsing without partial
results or substitution from row 31. Malformed later entries are ignored.
Ranks remain original, positive ASCII decimals with a trailing dot; they need
not be consecutive. Item IDs are ASCII decimals used to associate metadata.

Titles come from `.titleline > a`, including nested text and decoded entities.
Only surrounding whitespace is trimmed. The next sibling `tr` must contain
the entry's metadata; never borrow a neighboring entry's metadata.
Normal stories require `span.subline`, one matching `span.score`, and one
matching direct comments link. Nested age, user, and hide links are excluded
from comment selection. Metrics accept nonnegative ASCII integers with
`point(s)`/`comment(s)` labels; `discuss` is zero comments.

Jobs are identified by the observed second-cell
`img[src="s.gif"][height="1"][width="14"]` and metadata without a subline.
Supported metadata is a direct age span containing only one nonempty matching
item link, optionally followed by whitespace, `|`, and one direct `hide` link.
The hide URL is parsed with `urllib.parse`: relative path `hide`, no scheme or
host, and exactly one matching `id` query value. Other query parameters and
their order are irrelevant. Missing/mismatched age, missing/mismatched/duplicate
hide IDs, unexpected links/tags/metrics, or unexplained text cause an error.
Absent job points/comments normalize to zero for filtering; absence alone
does not identify a job. Both layouts have captured fixture evidence.

Words are whitespace-separated tokens containing a Unicode letter or number.
Numeric tokens count by assumption; hyphenated tokens stay intact; standalone
symbols do not count. Long titles (>5 words) sort by comments descending,
short titles (<=5) by points descending. Both break ties by original rank
ascending. Filters return new lists; empty results are valid.

## Persistence and failure trade-offs

Initialize compatible, writable SQLite storage before requesting HTML.
After a successful or handled failed crawl, attempt exactly one usage insert
and close connections. Commit success before printing JSON. Storage can fail
after initialization; unavailable storage cannot always record its own error.
HTTP/parsing/storage failures are caught at the CLI boundary; programming bugs
are not hidden by a catch-all handler. Crawl and recording failures retain
both diagnostic contexts.

`requested_at` is UTC operation start after valid argument parsing.
`fetched_count` counts successfully parsed entries, so parse failure records
zero even after receiving HTML. `duration_ms` uses a monotonic clock and ends
immediately before usage recording, excluding the final SQLite write/output.
`status=success` describes successful processing and a committed usage event,
not guaranteed downstream output delivery. SQLite commit and stdout delivery
are not atomic. Only usage metadata is persisted, not scraped content.

## Limitations and potential production work

The parser supports observed layouts, not every deleted/scoreless entry or
future site change. It fails explicitly when required structure changes;
support should follow new captured evidence and regression tests. Compact
captured rows plus synthetic offline cases keep tests deterministic; provenance
is in `tests/fixtures/README.md`.

Requests connect/read timeouts do not impose a total deadline. A production
deployment could justify a total-operation budget, bounded retries for suitable
transient failures, request-rate controls, monitored parsing failures, and
broader captured-layout coverage. Persistent multi-user usage would require
retention, concurrency, and schema-evolution decisions. These are potential
improvements, not implemented features.
