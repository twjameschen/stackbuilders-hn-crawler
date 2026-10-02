# Design notes

## 1. Brief design rationale

I chose a small Python CLI because the exercise requires a single fetch-and-filter operation. Python is my strongest language, and a CLI keeps setup and execution straightforward.

- **HTML scraping:** Requests fetches the homepage, and Beautiful Soup extracts the first 30 entries. This directly meets the scraping requirement without browser automation or a larger scraping framework.
- **Separation of responsibilities:** Fetching, parsing, filtering, and storage are separate modules. Filtering uses pure functions, making the rules easy to understand and test independently.
- **Usage storage:** SQLite provides persistent, queryable usage records without requiring a separate database service.
- **Correctness and failures:** Filtering preserves the original selection and ranks. Malformed required data causes an explicit error rather than silently producing incomplete results.
- **Verification:** Offline tests use HTML fixtures, mocked HTTP, and temporary databases. A captured live response also provides a regression test for a job layout that the initial parser rejected.

The sections below explain the execution flow, assumptions, trade-offs, and limitations. Setup and run commands are in the [README](https://chatgpt.com/g/g-p-6a5e40e452048191b4741ece15ef8b46-jhengying/README.md).

## 2. Execution flow

`cli.py` coordinates the successful path in this order:

| Step | Module/responsibility | Reason |
| --- | --- | --- |
| Validate, then start timing | `cli.py`: parse arguments, capture UTC time, start monotonic timer. | Reject invalid input before side effects. |
| Initialize storage | `storage.py`: create/check the database and close the connection. | Avoid fetching when usage storage is unusable. |
| Fetch, then parse | `fetch.py` requests HTML; `parser.py` extracts the first 30 rows. | Separate network access from HTML interpretation. |
| Filter, then prepare JSON | `filters.py` selects/sorts; `cli.py` serializes four fields. | Prepare the result before recording success. |
| Commit usage | `storage.py` inserts one event with parameterized SQL. | Save usage before successful output. |
| Print | `cli.py` emits Unicode-preserving JSON and returns 0. | Keep results on stdout and diagnostics on stderr. |

`models.py` defines the frozen `Entry(number, title, points, comments)`.
Fields cannot be reassigned; HTML validation belongs to the parser. Pure filters
return new lists without changing entries or input order. They neither fetch
nor truncate data, so their rules can be tested without network or storage.
`__main__.py` configures UTF-8 streams and the process exit code.

## 3. Key design decisions

| Choice | Reason | Alternative/trade-off |
| --- | --- | --- |
| Python 3.12 | Dataclasses, Unicode strings, and built-in tools suit this exercise. | Another language could work; Python keeps the solution small. |
| Requests | Concise status/error handling and connect/read timeouts. | `urllib` removes a dependency but requires more HTTP plumbing. |
| Beautiful Soup with `html.parser` | Handles entities and nested text through tree queries. | Lower-level parsing needs explicit tree handling; lxml adds a parser dependency. |
| CLI with argparse | Simple input validation and output suitable for other tools. | An API server adds deployment and interface scope. |
| SQLite via `sqlite3` | Durable, queryable local events without a database service. | JSON-line logs are simpler but less convenient to query; an ORM adds an unnecessary layer here. |

## 4. Rules, failures, and testing

**Selection and assumptions**

- Select the original first 30 entries before extraction/filtering. Preserve
  ranks; never substitute row 31. Fewer than 30 entries or malformed selected
  data causes an explicit error. Empty filtered results are valid (`[]`).
- Split titles on whitespace; count tokens containing a Unicode letter or
  number. **Numeric tokens count by assumption.** Hyphenated tokens remain
  intact; symbol-only tokens are ignored. `This is - a self-explained example`
  counts as five words.
- Long titles (>5 words) sort by comments; short titles (<=5) by points.
  Descending order and original rank ascending for ties are implementation
  assumptions. `all`, the default, preserves source order.
- Normal stories require valid metrics; `discuss` means zero comments.
  Recognized jobs normalize absent points/comments to zero. Absence alone
  does not identify a job; damaged job metadata fails.

**Failures and usage**

- Invalid arguments exit 2. Handled HTTP/parsing/storage failures return 1
  with stderr diagnostics. Crawl failures attempt one failure record; usage-write
  failures suppress successful JSON. If both fail, both diagnostics remain.
  Unexpected programming errors propagate rather than being hidden.
- UTC start timestamps identify operations; a monotonic clock measures elapsed
  duration. Only usage metadata is stored, not scraped content or personal data.

**Testing**

- Offline tests cover pure rules, captured and synthetic HTML, mocked HTTP,
  and temporary SQLite databases. Integration tests replace only HTTP and use
  the real parser, filters, CLI, and storage. Tests reopen databases and check
  failure paths and recording before output.
- A live response exposed age-plus-hide job metadata rejected by the earlier
  age-only rule. Its compact captured excerpt now supports a regression test,
  alongside the age-only case and hide-URL identity tests. See
  [test coverage](../tests/README.md) and
  [fixture provenance](../tests/fixtures/README.md).

## 5. Limitations

Observed HTML layouts are supported; offline tests cannot guarantee future site
compatibility. Connect/read timeouts are not a strict total-operation deadline.
Storage can fail after initialization and cannot always log its own failure.
SQLite commit and stdout delivery are not atomic: a committed success event
cannot guarantee downstream receipt of JSON.

**Possible production improvements, not implemented:** a total-operation budget,
bounded transient retries, request-rate controls, monitored parsing failures,
and broader captured-layout coverage. Multi-user persistence would also need
retention, concurrency, and schema-evolution decisions.

## 6. Optional implementation details

<details>
<summary>Implementation details</summary>

### HTTP and parser safeguards

- Fetch only `https://news.ycombinator.com/`, once, with application User-Agent,
  TLS verification, and 5/10-second connect/read timeouts. Check status before
  parsing, reject redirects, decode UTF-8, close the response, and do not retry.
- Use Beautiful Soup's `html.parser` backend, without regex or network access
  in the parser. Select `tr.athing` in source order and slice to 30 before field
  extraction. Parsing returns no partial list; malformed later entry fields
  are ignored. Errors include ID and rank when available.
- Require an ASCII decimal row ID and a positive ASCII decimal in `span.rank`
  followed by `.`. Ranks need not be consecutive or numerically sorted.
- Read `.titleline > a`, including nested text and decoded entities. Preserve
  punctuation/internal spacing, trim only surrounding whitespace, reject empty
  titles, and exclude the separate site link.
- Read metadata only from the next sibling `tr`, rejecting a missing row or a
  following entry row. Require `td.subtext`; never borrow neighboring metadata.
- Normal stories require `span.subline`, exactly one `span.score` with ID
  `score_<item ID>`, and exactly one direct subline anchor with href
  `item?id=<item ID>`. This distinguishes comments from nested age, user, and
  hide links. Metric labels accept nonnegative ASCII integers with
  `point`/`points` or `comment`/`comments`, separated by whitespace including
  nonbreaking spaces.
- Jobs require the second-cell
  `img[src="s.gif"][height="1"][width="14"]` and no subline. Metadata must
  contain a direct `span.age` with only one nonempty link to `item?id=<item ID>`.
  Accept age alone or age followed by `|` and one direct anchor labeled `hide`,
  allowing surrounding whitespace. Reject extra tags, duplicate/unexpected
  links, scores, and unexplained text.
- Parse the optional hide URL with `urlsplit`/`parse_qs`, keeping blank query
  values. Require path exactly `hide`, no scheme/host, and exactly one matching
  `id`. Reject missing/blank/mismatched/duplicate IDs, malformed URLs,
  absolute/external URLs, and paths such as `/hide` or `item`. Other parameters,
  query order, and fragments do not affect identity.

### Usage semantics

`--db` defaults to `data/usage.sqlite3` relative to the working directory.
Initialization creates parents and `usage_events`, checks required columns in
a writable transaction, and closes the connection before HTTP. Inserts are
parameterized. Transactions commit or roll back, and connections close.
There is no recursive attempt to log a logging failure.

| Field | Meaning |
| --- | --- |
| `id` | SQLite event identifier. |
| `requested_at` | UTC operation start with timezone information, after valid arguments and before storage initialization. |
| `filter_id` | `all`, `long`, or `short`. |
| `status` | `success` for completed crawl/filter processing, otherwise `failure` for handled crawl errors. Success is committed before JSON is printed. |
| `fetched_count` | Successfully parsed entries, not HTTP responses. Request/atomic parse failure records zero even if HTML arrived. |
| `result_count` | Selected entries; zero on request/parsing failure. |
| `duration_ms` | Monotonic elapsed milliseconds from just after timestamp capture to immediately before recording. Includes initialization and crawl/result preparation; excludes the final SQLite write/output. |
| `error_type` | Exception class name for a handled crawl error, otherwise null. |

Initialization and recording catch `OSError`/SQLite errors; crawling catches
Requests exceptions and `HNParseError`. Initialization failure prevents HTTP
and may leave no event. A failed insert does not become a successfully saved
record. The frozen model has integer type annotations for numeric fields but
adds no runtime type validation.

</details>
