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
| `fetch.py` | Implemented: fixed-URL Requests fetch with finite timeouts |
| `parser.py` | Implemented: parse the first 30 supplied HTML entry rows |
| `storage.py` | Implemented: initialize SQLite and append usage events |
| `cli.py`, `__main__.py` | Implemented: argparse, JSON output, operation orchestration |

`Entry.number` is the original homepage rank; numeric fields have integer type
annotations. The dataclass is frozen and adds no runtime validation or class
hierarchy. The parsing policy below handles missing HTML fields.

`count_words` uses whitespace splitting and Unicode-aware `str.isalnum`.
`filter_long_titles` sorts by `(-comments, number)` and
`filter_short_titles` sorts by `(-points, number)`. Each returns a new list,
leaving input order and field values unchanged. Empty results are valid.

The CLI initializes storage, fetches once, parses HTML, applies the requested
pure filter, and saves usage before outputting JSON.
Avoid inheritance, generic repositories, and unnecessary dependencies.

## HTML observations and parsing policy

Development inspection captured the homepage on 2026-10-01 (Asia/Taipei).
It contained 30 `tr.athing` rows, each followed by a sibling metadata `tr`,
then a spacer row. Ordinary metadata uses `td.subtext > span.subline` with
`span.score[id="score_<item ID>"]`. Both the nested age anchor and the direct
comments anchor use `item?id=<item ID>`, so matching the URL alone is unsafe.
Plural comments, singular `1 comment`, and `discuss` were observed.

No jobs appeared in the Phase 3 homepage capture. Inspection of the official jobs
page showed the same entry classes, but its second cell contains
`img[src="s.gif"][height="1"][width="14"]` instead of a voting control;
the adjacent `td.subtext` contains only a direct `span.age` with an item link.
Neither a `nofollow` title link nor missing metrics alone identifies a job:
the captured `discuss` story also has `nofollow`. Small exact captured row
pairs and source provenance are in `tests/fixtures/`; the full pages are not
submission fixtures. The remaining test HTML is explicitly synthetic.

The saved Phase 4 homepage response contains job `49911531` at rank 8, with
the same spacer image, no score/subline, and direct age plus hide metadata:
`<span class="age"><a href="item?id=49911531">51 minutes ago</a></span> |`
`<a href="hide?id=49911531&amp;goto=news">hide</a>`.
This valid homepage layout exposed the age-only rule's incompleteness.
Its exact row pair is retained in `tests/fixtures/homepage_job.html`, alongside
the unchanged age-only `/jobs` excerpt; provenance is recorded separately.

The parser uses Beautiful Soup and `html.parser`, without regex or network:

- Select `tr.athing` in source order and take the first 30 **before** extracting
  fields. Fewer than 30 rows raises `HNParseError`. A selected failure aborts
  parsing; do not substitute row 31. Later malformed entry fields are ignored.
- Require an ASCII decimal item ID for association and a positive ASCII decimal
  rank with the observed trailing dot. Preserve ranks and source order; ranks
  need not be consecutive or sorted numerically.
- Extract `.titleline > a` text, decoding entities and retaining nested text,
  punctuation, and internal spacing (including nonbreaking spaces). Trim only
  surrounding whitespace and reject empty titles. Exclude the site link.
- Read only the next sibling `tr` as metadata; never search across neighboring
  entries. For ordinary stories require a subline, exactly one matching score,
  and exactly one direct subline anchor pointing to the entry's item URL.
  This excludes the nested age link, user links, and hide links.
- Points accept `<integer> point` or `<integer> points`; comments accept
  `<integer> comment`, `<integer> comments`, or `discuss` (zero). Split metric
  labels on whitespace, including `&nbsp;`. Counts must be ASCII decimal
  nonnegative integers. Missing, malformed, ambiguous, or mismatched normal
  story metrics raise contextual errors rather than becoming zero.
- Normalize both missing job metrics to zero **only** with the observed
  second-cell spacer image plus either observed job metadata structure: no
  subline/score, one direct age span containing only a nonempty item link
  matching the current ID, optionally followed by `|` and one direct link
  labeled `hide` with href exactly `hide?id=<current ID>&goto=news`.
  Surrounding whitespace is allowed. Duplicate/unexpected links or tags,
  missing/mismatched age, mismatched hide, unexpected metrics, and unexplained
  metadata text are rejected. No arbitrary text/link removal is performed.
  Damaged job metadata fails. This zero is a filtering normalization, not an
  assertion that the site displayed numeric zero.

This recognizes the two observed job layouts, not every possible job presentation.
HTML provides no explicit job-type field here; the combined structure is the
evidence used. Unknown scoreless stories and future layouts fail rather than
triggering fallback selectors. Both captured job layouts are tested in clearly
assembled pages with synthetic ordinary rows. Errors include item ID and rank
where available. Parsing is atomic: no partial list is returned on failure.

## Unresolved decisions

- Reinspect HTML before supporting other scoreless/deleted-entry layouts;
  their behavior is not inferred from absence alone.

## HTTP and CLI policy

The fetcher uses Requests at the fixed `https://news.ycombinator.com/` URL,
an application User-Agent, TLS verification, and `(5, 10)` connect/read
timeouts. It checks status before returning HTML and closes the response.
Automatic redirects are disabled and 3xx responses rejected; there are no
automatic retries. Requests timeouts do not impose a total deadline, including
DNS/address-attempt and sustained-download time.

The CLI accepts `--filter all|long|short`, defaulting to `all`. Identifiers are
used consistently; `all` preserves source order. Output is a JSON array with
exactly the four entry fields, using UTF-8 at the module entry point and
unescaped Unicode. Diagnostics go to stderr. Request/parsing failures return
1 without JSON; argparse errors return 2 before fetching. Programming errors
are not hidden by a catch-all handler.

## Usage storage and failures

`--db PATH` defaults to `data/usage.sqlite3` relative to the current working
directory. Initialization creates parent directories and one `usage_events`
table. A short `BEGIN IMMEDIATE` transaction checks writable storage and a
column query checks schema compatibility before HTTP. No migration layer is
provided. The initialization connection is closed before fetching.

The CLI captures UTC `requested_at` immediately after valid argument parsing,
before storage initialization, and measures elapsed time with `monotonic_ns`.
Each event stores an integer ID, requested time, filter ID, `success`/`failure`,
fetched count, result count, integer duration milliseconds, and nullable error
class name. `fetched_count` means successfully parsed entries, and `result_count`
means selected results. Atomic parse failure records zero for both even if HTTP
returned a response. `duration_ms` ends immediately before usage recording:
it includes initialization and crawl/result preparation, and excludes the final
SQLite write and output. `status=success` describes successful crawl/filter
processing and a committed usage record; it cannot guarantee downstream stdout
delivery. Only usage metadata is stored, not scraped content or personal
information. All INSERT values are parameterized. Transactions commit/rollback
and connections close on both success and exceptions.

For a successful or handled failed crawl, attempt one event insertion. A
successful event is committed before JSON is emitted. Request and parser
errors are diagnosed on stderr, recorded as failures if possible, and return
exit 1. Storage initialization errors return 1 before HTTP and may leave no
event. Record-write errors return 1 without successful JSON; if crawling also
failed, both contexts remain in stderr. There are no recursive logging attempts
or claims that an unavailable database can record its own failure.

Filesystem/SQLite errors are caught at the CLI boundary along with Requests
and domain parsing exceptions. Unexpected programming exceptions propagate.
Storage can become unavailable after the initial check. SQLite commit and
stdout delivery are not a shared transaction, so a committed crawl event is
not a guarantee that a downstream consumer received the output.

## Verification

Phase 2 tests were specified before implementation. The first run failed
because the model and filter modules were missing; after implementation,
32 tests passed. Coverage includes frozen fields, Unicode letters/numbers,
symbol-only tokens, the exact 5-word example, whitespace variants, title-length
boundaries, numeric descending sorts, rank ties, preserved input and ranks,
empty results, complementary selections, and no truncation above 30 entries.
Tests access no real network or database.

Phase 3 added 38 parser/integration tests, bringing the total to 70. Initial
parser tests failed because the module was missing. Tests cover source-order
extraction, the 30-row boundary, malformed selected/later rows, incomplete
pages, observed comment labels, job normalization and failures, metadata
ownership, entities, nested title text, spacing, and parser-to-filter behavior.
A separate development check successfully parsed all 30 captured homepage rows.

Keep HTTP, CLI, and storage tests separate from pure logic tests.

Increment A passes 91 offline tests. HTTP tests mock the Requests boundary;
CLI tests check modes, fields, Unicode, empty results, errors, and the module
help entry point. The representative parser fixture's duplicate synthetic
item ID was corrected without adding parser uniqueness validation.

Increment B passes 112 offline tests using `tmp_path` databases. Tests reopen
SQLite to verify persistence, check identifiers/timestamps/counts/durations,
append multiple events, exercise initialization/write failures, preserve dual
error diagnostics, and run real parser/filter/storage integration with only
the Requests boundary mocked.

The homepage-job regression failed before the fix with the rank-8 age-only
parsing error. The focused extension passes 135 offline tests, including
strict damaged-job cases and CLI/parser/filter/storage integration for all
three modes. The complete saved Phase 4 response parses to 30 entries;
same-response checks confirmed ranks 1, 2, 8, 15, and 30. CLI validation using
only substituted HTTP produced 30/23/7 entries for all/long/short and one
successful usage event per invocation. Expected ordering was calculated
independently of the application filters. The full page stays ignored because
the compact job excerpt adds the needed new structure coverage.

After the fix, one fresh live `all` invocation started at
`2026-09-30T18:25:20.830155+00:00` and made exactly one HTTP request. It exited
0 with 30 JSON entries and one committed success event (`fetched_count=30`,
`result_count=30`, `error_type=NULL`). The same job appeared at rank 9 with
age-plus-hide metadata and normalized zero metrics. Fields at ranks 1, 2, 9,
15, and 30 matched that invocation's retained response. Live artifacts remain
ignored; no comparison used a later refresh. Dependencies and schema are unchanged.
