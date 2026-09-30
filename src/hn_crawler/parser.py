"""Parse the observed Hacker News row layout without network or storage access."""

from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup, NavigableString, Tag

from hn_crawler.models import Entry


class HNParseError(ValueError):
    """The supplied HTML cannot provide the required homepage entries."""


def parse_homepage(html: str) -> list[Entry]:
    """Return the original first 30 entry rows in source order, or raise.

    Job rows with the observed spacer image and age (plus optional matching
    hide link) normalize absent points and comments to zero. Stories require both
    metrics. Titles retain internal spacing; only surrounding whitespace is trimmed.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr.athing")[:30]
    if len(rows) < 30:
        raise HNParseError(f"Expected at least 30 entry rows; found {len(rows)}")
    return [_parse_entry(row) for row in rows]


def _integer(text: str, context: str, field: str) -> int:
    if not text.isascii() or not text.isdecimal():
        raise HNParseError(f"{context}: invalid {field}: {text!r}")
    return int(text)


def _metric(text: str, units: tuple[str, ...], context: str, field: str) -> int:
    parts = text.split()
    if len(parts) != 2 or parts[1] not in units:
        raise HNParseError(f"{context}: invalid {field} label: {text!r}")
    return _integer(parts[0], context, field)


def _matches_hide_url(href: str, item_id: str) -> bool:
    """Navigation parameters do not identify the entry; one matching ID does."""
    try:
        url = urlsplit(href)
    except ValueError:
        return False
    return (
        not url.scheme and not url.netloc and url.path == "hide"
        and parse_qs(url.query, keep_blank_values=True).get("id") == [item_id]
    )


def _validate_job_metadata(subtext: Tag, item_id: str, context: str) -> None:
    """Accept only the captured age-only and age | hide job structures."""
    error = HNParseError(
        f"{context}: invalid job metadata; expected age with optional matching hide link"
    )
    age = subtext.select_one(":scope > span.age > a")
    if age is None or age.get("href") != f"item?id={item_id}" or not age.get_text().strip():
        raise error

    parts = [node for node in subtext.contents if isinstance(node, Tag) or node.strip()]
    age_parts = [node for node in age.parent.contents if isinstance(node, Tag) or node.strip()]
    if not parts or parts[0] is not age.parent or age_parts != [age]:
        raise error

    expected_tags = [age.parent, age]
    if len(parts) == 3:
        separator, hide = parts[1:]
        if (
            not isinstance(separator, NavigableString) or separator.strip() != "|"
            or not isinstance(hide, Tag) or hide.name != "a"
            or not _matches_hide_url(hide.get("href", ""), item_id)
            or hide.get_text().strip() != "hide"
        ):
            raise error
        expected_tags.append(hide)
    elif len(parts) != 1:
        raise error

    if subtext.find_all(True) != expected_tags or subtext.select_one("span.score") is not None:
        raise error


def _parse_entry(row: Tag) -> Entry:
    item_id = row.get("id", "<missing>")
    context = f"Entry id={item_id}"
    if not isinstance(item_id, str) or not item_id.isascii() or not item_id.isdecimal():
        raise HNParseError(f"{context}: missing or invalid item ID")

    rank = row.select_one("span.rank")
    rank_text = rank.get_text().strip() if rank is not None else ""
    if not rank_text.endswith("."):
        raise HNParseError(f"{context}: missing or invalid rank: {rank_text!r}")
    number = _integer(rank_text[:-1], context, "rank")
    if number == 0:
        raise HNParseError(f"{context}: rank must be positive")
    context += f" (rank {number})"

    title_link = row.select_one(".titleline > a")
    title = title_link.get_text().strip() if title_link is not None else ""
    if not title:
        raise HNParseError(f"{context}: missing or empty title")

    metadata_row = row.find_next_sibling("tr")
    if metadata_row is None or "athing" in metadata_row.get("class", []):
        raise HNParseError(f"{context}: missing adjacent metadata row")
    subtext = metadata_row.select_one("td.subtext")
    if subtext is None:
        raise HNParseError(f"{context}: missing adjacent metadata cell")

    subline = subtext.select_one("span.subline")
    spacer = row.select_one('td:nth-of-type(2) > img[src="s.gif"][height="1"][width="14"]')
    if spacer is not None and subline is None:
        _validate_job_metadata(subtext, item_id, context)
        return Entry(number, title, 0, 0)

    if subline is None:
        raise HNParseError(f"{context}: missing normal-story metadata subline")
    scores = subline.select("span.score")
    if len(scores) != 1 or scores[0].get("id") != f"score_{item_id}":
        raise HNParseError(f"{context}: missing, ambiguous, or mismatched score")
    points = _metric(scores[0].get_text(), ("point", "points"), context, "points")

    comment_links = [
        link for link in subline.find_all("a", recursive=False)
        if link.get("href") == f"item?id={item_id}"
    ]
    if len(comment_links) != 1:
        raise HNParseError(f"{context}: missing, ambiguous, or mismatched comments link")
    label = comment_links[0].get_text().strip()
    comments = 0 if label == "discuss" else _metric(
        label, ("comment", "comments"), context, "comments"
    )
    return Entry(number, title, points, comments)
