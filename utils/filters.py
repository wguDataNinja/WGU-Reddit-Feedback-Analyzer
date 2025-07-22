# filters.py

import re
import pandas as pd
from datetime import datetime
from utils.paths import DATA_DIR

# Load and normalize course list
course_df = pd.read_csv(DATA_DIR / "2025_06_course_list.csv")
course_codes_default = set(course_df["CourseCode"].astype(str).str.upper().str.replace(r"[\s\-]", "", regex=True))

def filter_by_course_codes(df, course_codes=None, exact_match_count=1):
    """
    Filters posts containing exactly `exact_match_count` matching course codes.

    Course codes are matched as full words, allowing optional dash/space between letters and digits.
    Letters-only codes must match exactly with no space or dash.

    Args:
        df (pd.DataFrame): DataFrame with 'title' and 'selftext' columns.
        course_codes (list[str], optional): Specific course codes to match.
        exact_match_count (int): Number of course code matches required per post.

    Returns:
        pd.DataFrame: Filtered DataFrame with a new 'matched_course_codes' column.
    """
    import re
    import pandas as pd

    df = df.copy()

    def normalize_code(code):
        return str(code).upper().replace("-", "").replace(" ", "")

    if course_codes is None:
        from utils.paths import DATA_DIR
        course_path = DATA_DIR / "2025_06_course_list.csv"
        course_codes_raw = pd.read_csv(course_path, usecols=["CourseCode"])["CourseCode"]
        course_codes_set = {normalize_code(code) for code in course_codes_raw.dropna()}
    else:
        course_codes_set = {normalize_code(code) for code in course_codes}

    def extract_matches(row):
        text = f"{row.get('title', '')} {row.get('selftext', '')}".upper()
        matches = []

        for code in course_codes_set:
            if len(code) < 2:
                continue  # skip malformed codes

            if any(char.isdigit() for char in code):
                # Letter + digit code: allow optional space or dash
                letter_part = "".join(c for c in code if c.isalpha())
                number_part = "".join(c for c in code if c.isdigit())
                pattern = rf"\b{re.escape(letter_part)}[- ]?{re.escape(number_part)}\b"
            else:
                # Letters-only code: exact match only, no space/dash allowed
                pattern = rf"\b{re.escape(code)}\b"

            if re.search(pattern, text):
                matches.append(code)

        return matches

    df["matched_course_codes"] = df.apply(extract_matches, axis=1)
    df = df[df["matched_course_codes"].apply(len) == exact_match_count]
    print(f"[filter_by_course_codes] {len(df)} posts matched {exact_match_count} course codes")
    return df

def filter_by_length(df, min_length=40, max_length=1000):
    df = df.copy()
    df = df[(df["text_length"] >= min_length) & (df["text_length"] < max_length)]
    print(f"[filter_by_length] {len(df)} posts kept (length {min_length}-{max_length})")
    return df



def filter_by_date(df, start_date=None, end_date=None, date_column="created_utc"):
    df = df.copy()

    if start_date:
        start_ts = int(pd.to_datetime(start_date).timestamp())
        df = df[df[date_column] >= start_ts]

    if end_date:
        end_ts = int(pd.to_datetime(end_date).timestamp())
        df = df[df[date_column] <= end_ts]

    print(f"[filter_by_date] {len(df)} posts between {start_date} and {end_date}")
    return df




def filter_by_questions(df):
    df = df.copy()
    df = df[df['text_clean'].str.contains(r'\?', na=False)]
    print(f"[filter_by_questions] {len(df)} posts contain question marks")
    return df


def filter_sentiment(df, min_score=None, max_score=None):
    df = df.copy()
    if min_score is not None:
        df = df[df["VADER_Compound"] >= min_score]
    if max_score is not None:
        df = df[df["VADER_Compound"] <= max_score]

    print(f"[filter_sentiment] {len(df)} posts after sentiment filter")
    return df


def apply_filters(df, filters_config):
    result_df = df.copy()

    for filter_name, config in filters_config.items():
        if filter_name == 'questions' and config.get('enabled', True):
            result_df = filter_by_questions(result_df)
        elif filter_name == 'length' and config.get('enabled', True):
            result_df = filter_by_length(result_df, **config.get('params', {}))
        elif filter_name == 'sentiment' and config.get('enabled', True):
            result_df = filter_sentiment(result_df, **config.get('params', {}))
        elif filter_name == 'course_codes' and config.get('enabled', True):
            result_df = filter_by_course_codes(result_df, **config.get('params', {}))

    return result_df