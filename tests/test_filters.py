from dataclasses import astuple

import pytest

from hn_crawler.filters import count_words, filter_long_titles, filter_short_titles
from hn_crawler.models import Entry


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("This is - a self-explained example", 5),
        ("one two three four five", 5),
        ("one two three four five six", 6),
        ("state-of-the-art tools", 2),
        ("Python 3.12", 2),
        ("hello/world", 1),
        ("!!! - + 😀", 0),
        ("", 0),
        ("  one\ttwo\nthree\r\nfour   five\t", 5),
        ("你好 café Ελληνικά", 3),
        ("42 ٣ ½ ²", 4),
        (" \t\r\n ", 0),
    ],
)
def test_count_words(title, expected):
    assert count_words(title) == expected


@pytest.fixture
def entries():
    return [
        Entry(9, "one two three four five", 10, 999),
        Entry(7, "one two three four five six", 999, 2),
        Entry(3, "This is - a self-explained example", 10, 100),
        Entry(8, "a b c d e f g", 1, 10),
        Entry(2, "one two three four five six seven", 2, 10),
        Entry(4, "state-of-the-art tools", 2, 200),
        Entry(11, "!!! - + 😀", 0, 0),
    ]


@pytest.mark.parametrize(
    ("filter_entries", "expected_numbers"),
    [
        (filter_long_titles, [2, 8, 7]),
        (filter_short_titles, [3, 9, 4, 11]),
    ],
)
def test_filters_select_and_sort_by_their_own_numeric_metric(
    entries, filter_entries, expected_numbers
):
    result = filter_entries(entries)

    assert [entry.number for entry in result] == expected_numbers


@pytest.mark.parametrize(
    ("filter_entries", "expected_numbers"),
    [(filter_long_titles, [2]), (filter_short_titles, [1])],
)
def test_exact_five_and_six_word_boundary(filter_entries, expected_numbers):
    entries = [
        Entry(1, "one two three four five", 100, 100),
        Entry(2, "one two three four five six", 1, 1),
    ]

    assert [entry.number for entry in filter_entries(entries)] == expected_numbers


@pytest.mark.parametrize(
    ("filter_entries", "title"),
    [
        (filter_long_titles, "one two three four five six"),
        (filter_short_titles, "one two"),
    ],
)
def test_equal_metrics_use_original_number_ascending(filter_entries, title):
    entries = [Entry(30, title, 10, 10), Entry(4, title, 10, 10), Entry(12, title, 10, 10)]

    assert [entry.number for entry in filter_entries(entries)] == [4, 12, 30]


@pytest.mark.parametrize("filter_entries", [filter_long_titles, filter_short_titles])
def test_empty_input_returns_a_new_empty_list(filter_entries):
    entries = []

    result = filter_entries(entries)

    assert result == []
    assert result is not entries


@pytest.mark.parametrize(
    ("filter_entries", "excluded_title"),
    [
        (filter_long_titles, "one two three four five"),
        (filter_short_titles, "one two three four five six"),
    ],
)
def test_no_matching_entries(filter_entries, excluded_title):
    assert filter_entries([Entry(23, excluded_title, 10, 10)]) == []


@pytest.mark.parametrize("filter_entries", [filter_long_titles, filter_short_titles])
def test_filters_preserve_input_order_and_all_field_values(entries, filter_entries):
    before = [astuple(entry) for entry in entries]

    result = filter_entries(entries)

    assert result is not entries
    assert [astuple(entry) for entry in entries] == before
    assert all(astuple(entry) in before for entry in result)


def test_filters_select_complementary_sets(entries):
    long_numbers = {entry.number for entry in filter_long_titles(entries)}
    short_numbers = {entry.number for entry in filter_short_titles(entries)}

    assert long_numbers == {2, 7, 8}
    assert short_numbers == {3, 4, 9, 11}
    assert long_numbers.isdisjoint(short_numbers)
    assert long_numbers | short_numbers == {2, 3, 4, 7, 8, 9, 11}


@pytest.mark.parametrize(
    ("filter_entries", "title"),
    [
        (filter_long_titles, "one two three four five six"),
        (filter_short_titles, "one two"),
    ],
)
def test_filters_do_not_truncate_supplied_entries(filter_entries, title):
    entries = [Entry(number, title, 0, 0) for number in range(35, 0, -1)]

    result = filter_entries(entries)

    assert [entry.number for entry in result] == list(range(1, 36))
