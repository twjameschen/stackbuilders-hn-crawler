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
| `parser.py` | Implemented: parse the first 30 supplied HTML entry rows |
| `storage.py` | Planned: local SQLite usage persistence |
| `cli.py`, `__main__.py` | Planned: argument parsing and operation orchestration |

`Entry.number` is the original homepage rank; numeric fields have integer type
annotations. The dataclass is frozen and adds no runtime validation or class
hierarchy. The parsing policy below handles missing HTML fields.

`count_words` uses whitespace splitting and Unicode-aware `str.isalnum`.
`filter_long_titles` sorts by `(-comments, number)` and
`filter_short_titles` sorts by `(-points, number)`. Each returns a new list,
leaving input order and field values unchanged. Empty results are valid.

The CLI will record the start time, fetch and parse HTML, call a pure filter,
and persist usage. Exact failure and persistence semantics remain unresolved.
Avoid inheritance, generic repositories, and unnecessary dependencies.

## HTML observations and parsing policy

Development inspection captured the homepage on 2026-10-01 (Asia/Taipei).
It contained 30 `tr.athing` rows, each followed by a sibling metadata `tr`,
then a spacer row. Ordinary metadata uses `td.subtext > span.subline` with
`span.score[id="score_<item ID>"]`. Both the nested age anchor and the direct
comments anchor use `item?id=<item ID>`, so matching the URL alone is unsafe.
Plural comments, singular `1 comment`, and `discuss` were observed.

No jobs appeared in that homepage capture. Inspection of the official jobs
page showed the same entry classes, but its second cell contains
`img[src="s.gif"][height="1"][width="14"]` instead of a voting control;
the adjacent `td.subtext` contains only a direct `span.age` with an item link.
Neither a `nofollow` title link nor missing metrics alone identifies a job:
the captured `discuss` story also has `nofollow`. Small exact captured row
pairs and source provenance are in `tests/fixtures/`; the full pages are not
submission fixtures. The remaining test HTML is explicitly synthetic.

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
  second-cell spacer image plus age-only metadata signature: no subline,
  no score, one age link matching the item ID, and no other metadata text.
  Damaged job metadata fails. This zero is a filtering normalization, not an
  assertion that the site displayed numeric zero.

This recognizes the observed job layout, not every possible job presentation.
HTML provides no explicit job-type field here; the combined structure is the
evidence used. Unknown scoreless stories and future layouts fail rather than
triggering fallback selectors. Job normalization on the homepage is tested
using a captured jobs-page row in a clearly assembled test page; it was not
observed on the captured homepage itself. Errors include item ID and rank
where available. Parsing is atomic: no partial list is returned on failure.

## Unresolved decisions

- Reinspect HTML before supporting other scoreless/deleted-entry layouts;
  their behavior is not inferred from absence alone.
- Confirm CLI names, output format, database path, and filter identifiers;
  proposed identifiers are `long-title-comments` and `short-title-points`.
- Decide whether failed operations are logged, what additional usage fields are
  useful, and how database write failures affect CLI output and exit status.
- Confirm HTTP timeout/retry policy and usage expectations when implementing
  the application fetcher.

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

Later phases will use temporary SQLite databases for persistence tests,
including timezone-aware timestamps. Keep HTTP and CLI tests separate from
pure logic tests.
