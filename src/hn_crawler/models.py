"""Entry data shared by the pure filters and future HTML parser."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    """A homepage entry whose number is its original rank."""

    number: int
    title: str
    points: int
    comments: int
