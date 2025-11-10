"""Helpers for building and validating pain-point IDs."""

import re

ID_RE = re.compile(r"^[A-Za-z0-9\-]+_[A-Za-z0-9\-]+\[\d+\]$")


def make_pain_point_id(course: str, post_id: str, idx: int) -> str:
    """Return standardized pain-point ID like 'C951_abcd123[0]'."""
    return f"{course}_{post_id}[{idx}]"


def is_valid_pain_point_id(s: str) -> bool:
    """Check if string matches pain-point ID format."""
    return bool(s and ID_RE.match(s))