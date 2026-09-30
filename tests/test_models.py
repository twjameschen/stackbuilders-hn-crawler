from dataclasses import FrozenInstanceError

import pytest

from hn_crawler.models import Entry


def test_entry_preserves_supplied_fields():
    entry = Entry(number=17, title="Python 3.12", points=10, comments=2)

    assert (entry.number, entry.title, entry.points, entry.comments) == (
        17,
        "Python 3.12",
        10,
        2,
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [("number", 1), ("title", "Changed"), ("points", 0), ("comments", 0)],
)
def test_entry_fields_are_frozen(field, replacement):
    entry = Entry(number=17, title="Python 3.12", points=10, comments=2)

    with pytest.raises(FrozenInstanceError):
        setattr(entry, field, replacement)
