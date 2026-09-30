from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from hn_crawler.filters import filter_long_titles, filter_short_titles
from hn_crawler.models import Entry
from hn_crawler.parser import HNParseError, parse_homepage


def story(number, title=None, score="10 points", comments="2 comments"):
    """Synthetic row pair using the observed homepage structure."""
    item_id = 1000 + number
    title = f"Story {number}" if title is None else title
    return f'''
    <tr class="athing submission" id="{item_id}">
      <td><span class="rank">{number}.</span></td>
      <td class="votelinks"><a href="vote?id={item_id}">vote</a></td>
      <td><span class="titleline"><a href="https://example.test/">{title}</a>
        <span class="sitebit"><a href="from?site=example.test">example.test</a></span>
      </span></td>
    </tr>
    <tr><td colspan="2"></td><td class="subtext"><span class="subline">
      <span class="score" id="score_{item_id}">{score}</span> by
      <a class="hnuser" href="user?id=test">test</a>
      <span class="age"><a href="item?id={item_id}">2 hours ago</a></span> |
      <a href="hide?id={item_id}">hide</a> |
      <a href="item?id={item_id}">{comments}</a>
    </span></td></tr><tr class="spacer"><td></td></tr>
    '''


def page(rows=None):
    """A synthetic page; supplied rows can also include captured excerpts."""
    rows = [story(number) for number in range(1, 31)] if rows is None else rows
    return "<html><body><table>" + "".join(rows) + "</table></body></html>"


def test_representative_thirty_entry_page_preserves_all_fields_and_source_order():
    rows = [
        story(40, "First source row", "2 points", "10 comments"),
        story(2, "Second source row", "10 points", "1 comment"),
        *[story(number) for number in range(3, 31)],
    ]
    expected = [
        Entry(40, "First source row", 2, 10),
        Entry(2, "Second source row", 10, 1),
        *[Entry(number, f"Story {number}", 10, 2) for number in range(3, 31)],
    ]

    assert parse_homepage(page(rows)) == expected


@pytest.mark.parametrize("extra", [story(31), '<tr class="athing" id="broken"></tr>'])
def test_only_first_thirty_rows_are_extracted_and_later_malformed_rows_are_ignored(extra):
    html = page([*[story(number) for number in range(1, 31)], extra])

    assert parse_homepage(html) == [
        Entry(number, f"Story {number}", 10, 2) for number in range(1, 31)
    ]


@pytest.mark.parametrize(
    ("html", "count"),
    [(page([story(number) for number in range(1, 30)]), 29),
     ("", 0), ("<html><h1>Service unavailable</h1></html>", 0)],
)
def test_incomplete_or_unrelated_pages_fail_clearly(html, count):
    with pytest.raises(HNParseError, match=f"at least 30 entry rows; found {count}"):
        parse_homepage(html)


@pytest.mark.parametrize(
    ("label", "expected"),
    [("discuss", 0), ("1 comment", 1), ("10&nbsp;comments", 10), ("0 comments", 0)],
)
def test_comment_labels_are_distinct_from_age_hide_and_user_links(label, expected):
    result = parse_homepage(page([story(1, comments=label), *[story(n) for n in range(2, 31)]]))

    assert result[0] == Entry(1, "Story 1", 10, expected)


def test_entities_unicode_nested_text_and_meaningful_spacing():
    title = '  Café &amp; <b>你好</b>  tools&nbsp;— &quot;yes&quot;  '
    result = parse_homepage(page([story(1, title=title), *[story(n) for n in range(2, 31)]]))

    assert result[0].title == 'Café & 你好  tools\u00a0— "yes"'


def test_captured_story_singular_discuss_and_job_rows():
    excerpt = (Path(__file__).parent / "fixtures/captured_rows.html").read_text(encoding="utf-8")
    captured = BeautifulSoup(excerpt, "html.parser").select_one("table").decode_contents()
    result = parse_homepage(page([captured, *[story(n) for n in range(5, 31)]]))

    assert result[:4] == [
        Entry(1, "The AI Race Just Got Awkward", 235, 184),
        Entry(7, "Reverse-engineering a $35 backup camera display (AMT630A)", 18, 1),
        Entry(20, "What TLA+ can and can't check", 7, 0),
        Entry(1, "Stable (YC W20) Is Hiring Product Engineers", 0, 0),
    ]
    assert len(result) == 30


@pytest.mark.parametrize(
    ("selector", "operation", "value", "message"),
    [
        (".rank", "remove", None, "rank"),
        (".rank", "text", "oops", "rank"),
        (".rank", "text", "0.", "rank"),
        (".rank", "text", "-1.", "rank"),
        (".titleline > a", "remove", None, "title"),
        (".titleline > a", "text", " \t ", "title"),
        ("span.score", "remove", None, "score"),
        ("span.score", "text", "-1 points", "points"),
        ("span.score", "text", "1.5 points", "points"),
        ("span.score", "text", "ten points", "points"),
        ("span.score", "text", "10 votes", "points"),
        (".subline > a:last-child", "remove", None, "comments"),
        (".subline > a:last-child", "text", "-1 comments", "comments"),
        (".subline > a:last-child", "text", "many comments", "comments"),
        (".subline > a:last-child", "text", "2 replies", "comments"),
        ("td.subtext", "remove", None, "metadata"),
    ],
)
def test_malformed_selected_story_fails_without_substituting_entry_thirty_one(
    selector, operation, value, message
):
    soup = BeautifulSoup(page([story(n) for n in range(1, 32)]), "html.parser")
    element = soup.select_one(selector)
    if operation == "remove":
        element.decompose()
    else:
        element.string = value

    with pytest.raises(HNParseError, match=f"Entry id=1001.*{message}"):
        parse_homepage(str(soup))


@pytest.mark.parametrize("metric", ["score", "comments"])
def test_metadata_ids_must_match_the_entry(metric):
    soup = BeautifulSoup(page(), "html.parser")
    if metric == "score":
        soup.select_one("span.score")["id"] = "score_1002"
    else:
        soup.select_one(".subline > a:last-child")["href"] = "item?id=1002"

    with pytest.raises(HNParseError, match=f"Entry id=1001.*{metric}"):
        parse_homepage(str(soup))


def test_missing_metadata_row_does_not_borrow_from_neighbor():
    soup = BeautifulSoup(page(), "html.parser")
    soup.select_one("tr.athing").find_next_sibling("tr").decompose()

    with pytest.raises(HNParseError, match="Entry id=1001.*metadata"):
        parse_homepage(str(soup))


def test_absent_metrics_without_job_spacer_signature_fail():
    soup = BeautifulSoup(page(), "html.parser")
    subtext = soup.select_one("td.subtext")
    subtext.clear()
    subtext.append(BeautifulSoup(
        '<span class="age"><a href="item?id=1001">2 hours ago</a></span>',
        "html.parser",
    ))

    with pytest.raises(HNParseError, match="Entry id=1001.*normal-story metadata"):
        parse_homepage(str(soup))


@pytest.mark.parametrize("damage", ["age-id", "missing-age", "extra-metric"])
def test_damaged_job_metadata_is_not_normalized(damage):
    excerpt = (Path(__file__).parent / "fixtures/captured_rows.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(excerpt, "html.parser")
    job = soup.select_one('tr[id="49834893"]')
    metadata = job.find_next_sibling("tr")
    if damage == "age-id":
        metadata.select_one(".age > a")["href"] = "item?id=49910553"
    elif damage == "missing-age":
        metadata.select_one(".age").decompose()
    else:
        metadata.select_one("td.subtext").append(" 10 comments")
    job_pair = str(job) + str(metadata)

    with pytest.raises(HNParseError, match="Entry id=49834893.*job metadata"):
        parse_homepage(page([job_pair, *[story(n) for n in range(2, 31)]]))


@pytest.mark.parametrize("item_id", [None, "bad"])
def test_missing_or_invalid_item_id_fails(item_id):
    soup = BeautifulSoup(page(), "html.parser")
    row = soup.select_one("tr.athing")
    if item_id is None:
        del row["id"]
    else:
        row["id"] = item_id

    with pytest.raises(HNParseError, match="item ID"):
        parse_homepage(str(soup))


def test_offline_parser_to_filter_integration():
    rows = [
        story(1, "one two three four five six", "1 point", "2 comments"),
        story(2, "Short title", "10 points", "900 comments"),
        story(3, "another long title with six words", "2 points", "10 comments"),
        story(4, "Other short title", "10 points", "1 comment"),
        *[story(n, score="0 points", comments="discuss") for n in range(5, 31)],
    ]
    entries = parse_homepage(page(rows))

    assert [entry.number for entry in filter_long_titles(entries)] == [3, 1]
    assert [entry.number for entry in filter_short_titles(entries)] == [2, 4, *range(5, 31)]
