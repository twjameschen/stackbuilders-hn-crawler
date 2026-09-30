"""Parse the observed Hacker News row layout without network or storage access."""

from bs4 import BeautifulSoup, Tag

from hn_crawler.models import Entry


class HNParseError(ValueError):
    """The supplied HTML cannot provide the required homepage entries."""


def parse_homepage(html: str) -> list[Entry]:
    """Return the original first 30 entry rows in source order, or raise.

    Job rows with the observed spacer-image and age-only metadata signature
    normalize absent points and comments to zero. Normal stories require both
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
        age = subtext.select_one(":scope > span.age > a")
        if (
            age is None
            or age.get("href") != f"item?id={item_id}"
            or len(subtext.find_all("a")) != 1
            or subtext.select_one("span.score") is not None
            or subtext.get_text().strip() != age.get_text().strip()
        ):
            raise HNParseError(f"{context}: invalid job metadata; expected age only")
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
