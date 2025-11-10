"""Course and sentiment filters for WGU Reddit Analyzer."""

from __future__ import annotations
from pathlib import Path
import re
import pandas as pd

COURSE_CSV = Path("data/course_list_with_college.csv")


def normalize_code(code: str) -> str:
    """Normalize course code (uppercase, no dash or space)."""
    return str(code).upper().replace("-", "").replace(" ", "")


def _build_course_patterns(course_codes):
    """Return {normalized_code: compiled_regex} allowing dash/space variants."""
    patterns = {}
    for raw in (course_codes or []):
        code = normalize_code(raw)
        if len(code) < 2:
            continue
        letters = "".join(c for c in code if c.isalpha())
        digits = "".join(c for c in code if c.isdigit())
        if letters and digits:
            inner = rf"{re.escape(letters)}(?:[ -]?){re.escape(digits)}"
        else:
            inner = rf"{re.escape(code)}"
        pat = re.compile(rf"(?<![A-Za-z0-9])(?:{inner})(?![A-Za-z0-9])", re.I)
        patterns[code] = pat
    return patterns


def _combine_text(row, title_col="title", text_col="text", selftext_fallback="selftext"):
    """Combine title and text fields with safe fallbacks."""
    title = row.get(title_col) or ""
    body = row.get(text_col) or row.get(selftext_fallback) or ""
    if not isinstance(title, str):
        title = ""
    if not isinstance(body, str):
        body = ""
    return f"{title} {body}"


def filter_posts_by_course_code(
    df: pd.DataFrame,
    course_codes=None,
    exact_match_count: int = 1,
    title_col: str = "title",
    text_col: str = "text",
    out_col: str = "matched_course_codes",
) -> pd.DataFrame:
    """Keep rows mentioning a specific number of distinct course codes."""
    df = df.copy()
    if course_codes is None:
        if COURSE_CSV.exists():
            course_codes = pd.read_csv(COURSE_CSV, usecols=["CourseCode"])["CourseCode"].dropna().tolist()
        else:
            course_codes = []

    pats = _build_course_patterns(course_codes)

    def match_codes(row):
        text = _combine_text(row, title_col=title_col, text_col=text_col).upper()
        return sorted({code for code, pat in pats.items() if pat.search(text)})

    df[out_col] = df.apply(match_codes, axis=1)
    return df[df[out_col].apply(len) == int(exact_match_count)]


def filter_by_course_exact(df, text_col="text", course_codes=None):
    """Simple exact match using raw course codes and word boundaries."""
    if not course_codes:
        return df
    pat = re.compile(r"\b(" + "|".join(map(re.escape, course_codes)) + r")\b", re.I)
    return df[df[text_col].fillna("").str.contains(pat, regex=True)]


def filter_by_vader(df, score_col="vader_compound", threshold=-0.2):
    """Filter by VADER score (<= threshold)."""
    if score_col not in df.columns:
        return df
    return df[df[score_col] <= threshold]


def filter_posts_by_sentiment(df, max_score=-0.2, score_col="vader_compound"):
    if score_col not in df.columns:
        return df
    return df[df[score_col] <= float(max_score)]