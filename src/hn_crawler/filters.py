"""Pure title filtering and sorting, independent of network and storage."""

from collections.abc import Iterable

from hn_crawler.models import Entry


def count_words(title: str) -> int:
    """Count whitespace tokens containing a Unicode letter or number.

    Numeric tokens count as words by assumption. Hyphenated tokens remain
    intact, and symbol-only tokens are ignored.
    """
    return sum(any(character.isalnum() for character in token) for token in title.split())


def filter_long_titles(entries: Iterable[Entry]) -> list[Entry]:
    """Return titles over five words, by comments descending then rank ascending."""
    return sorted(
        (entry for entry in entries if count_words(entry.title) > 5),
        key=lambda entry: (-entry.comments, entry.number),
    )


def filter_short_titles(entries: Iterable[Entry]) -> list[Entry]:
    """Return titles up to five words, by points descending then rank ascending."""
    return sorted(
        (entry for entry in entries if count_words(entry.title) <= 5),
        key=lambda entry: (-entry.points, entry.number),
    )
