# anchors_and_patterns.py

import re

# Anchors
ANCHOR_CCN_HEADER = re.compile(r"CCN.*Course Number", re.IGNORECASE)
ANCHOR_COURSE_CODE = re.compile(r"^[A-Z]{2,4}\s+\d{4}")
ANCHOR_COURSES_SECTION_BREAK = re.compile(r"^Courses", re.IGNORECASE)
ANCHOR_PROGRAM_OUTCOMES = re.compile(r"^Program Outcomes$", re.IGNORECASE)
ANCHOR_SCHOOL_OF = re.compile(r"^School of ", re.IGNORECASE)
ANCHOR_FOOTER_COPYRIGHT = re.compile(r"©", re.IGNORECASE)
ANCHOR_FOOTER_TOTAL_CUS = re.compile(r"Total CUs", re.IGNORECASE)

# Filters
PROGRAM_TITLE_EXCLUDE_PATTERNS = re.compile(r"^(Steps|[0-9]|[•\-])")

# Course row patterns
PATTERN_CCN_FULL = re.compile(
    r'^([A-Z]{2,5})\s+(\d{1,4})\s+([A-Z0-9]{2,5})\s+(.+?)\s+(\d+)\s+(\d+)$'
)
PATTERN_CODE_ONLY = re.compile(
    r'^([A-Z0-9]{1,6})\s+(.+?)\s+(\d+)\s+(\d+)$'
)
PATTERN_FALLBACK = re.compile(
    r'^(.+?)\s+(\d+)\s+(\d+)$'
)

# Registered
ANCHORS = {
    "CCN_HEADER": ANCHOR_CCN_HEADER,
    "COURSE_CODE": ANCHOR_COURSE_CODE,
    "COURSES_SECTION_BREAK": ANCHOR_COURSES_SECTION_BREAK,
    "PROGRAM_OUTCOMES": ANCHOR_PROGRAM_OUTCOMES,
    "SCHOOL_OF": ANCHOR_SCHOOL_OF,
    "FOOTER_COPYRIGHT": ANCHOR_FOOTER_COPYRIGHT,
    "FOOTER_TOTAL_CUS": ANCHOR_FOOTER_TOTAL_CUS
}

FILTERS = {
    "PROGRAM_TITLE_EXCLUDE_PATTERNS": PROGRAM_TITLE_EXCLUDE_PATTERNS
}

COURSE_PATTERNS = {
    "CCN_FULL": PATTERN_CCN_FULL,
    "CODE_ONLY": PATTERN_CODE_ONLY,
    "FALLBACK": PATTERN_FALLBACK
}
def match_course_row(row: str) -> dict | None:
    """
    Attempts to classify a given course row using known regex patterns.
    Order: CCN_FULL → CODE_ONLY → FALLBACK
    Returns:
        dict: {
            "matched_pattern": str,
            "groups": tuple
        }
        or None if no match
    """
    for pattern_name, pattern in COURSE_PATTERNS.items():
        match = pattern.match(row)
        if match:
            return {
                "matched_pattern": pattern_name,
                "groups": match.groups()
            }
    return None
print("Anchors & Patterns loaded.")
