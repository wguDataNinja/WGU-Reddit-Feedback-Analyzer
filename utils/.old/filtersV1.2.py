import re
import pandas as pd
import logging
from datetime import datetime
from utils.paths import DATA_DIR
from utils.logger import ensure_pipeline_logger

ensure_pipeline_logger()
logger = logging.getLogger("pipeline")

# Load and normalize course list
course_df = pd.read_csv(DATA_DIR / "2025_06_course_list_with_college.csv")
course_codes_default = set(
    course_df["CourseCode"]
    .astype(str)
    .str.upper()
    .str.replace(r"[\s\-]", "", regex=True)
)

# === Course Filtering ===
def filter_posts_by_course_code(df, course_codes=None, exact_match_count=1):
    """Keep only posts matching exactly N course codes."""
    df = df.copy()

    def normalize_code(code):
        return str(code).upper().replace("-", "").replace(" ", "")

    if course_codes is None:
        course_path = DATA_DIR / "2025_06_course_list_with_college.csv"
        course_codes_raw = pd.read_csv(course_path, usecols=["CourseCode"])["CourseCode"]
        course_codes_set = {normalize_code(code) for code in course_codes_raw.dropna()}
    else:
        course_codes_set = {normalize_code(code) for code in course_codes}

    def extract_matches(row):
        text = f"{row.get('title', '')} {row.get('selftext', '')}".upper()
        matches = []
        for code in course_codes_set:
            if len(code) < 2:
                continue
            if any(char.isdigit() for char in code):
                letter_part = "".join(c for c in code if c.isalpha())
                number_part = "".join(c for c in code if c.isdigit())
                pattern = rf"\b{re.escape(letter_part)}[- ]?{re.escape(number_part)}\b"
            else:
                pattern = rf"\b{re.escape(code)}\b"
            if re.search(pattern, text):
                matches.append(code)
        return matches

    df["matched_course_codes"] = df.apply(extract_matches, axis=1)
    df = df[df["matched_course_codes"].apply(len) == exact_match_count]

    logger.info(f"[filter_posts_by_course_code] kept {len(df)} posts matching exactly {exact_match_count} course codes")
    return df


# === Sentiment Filtering ===
def filter_posts_by_sentiment(df, min_score=None, max_score=None):
    """Filter posts by VADER compound sentiment score range."""
    df = df.copy()
    if min_score is not None:
        df = df[df["VADER_Compound"] >= min_score]
    if max_score is not None:
        df = df[df["VADER_Compound"] <= max_score]

    logger.info(f"[filter_posts_by_sentiment] kept {len(df)} posts in compound score range {min_score} to {max_score}")
    return df


# === Length Filtering ===
def filter_posts_by_length(df, min_length=40, max_length=1000):
    """Filter posts by text length range."""
    df = df.copy()
    df = df[(df["text_length"] >= min_length) & (df["text_length"] < max_length)]
    logger.info(f"[filter_posts_by_length] kept {len(df)} posts in length range {min_length}-{max_length}")
    return df


# === Date Filtering ===
def filter_posts_by_date(df, start_date=None, end_date=None, date_column="created_utc"):
    """Filter posts between start and end date."""
    df = df.copy()
    if start_date:
        start_ts = int(pd.to_datetime(start_date).timestamp())
        df = df[df[date_column] >= start_ts]
    if end_date:
        end_ts = int(pd.to_datetime(end_date).timestamp())
        df = df[df[date_column] <= end_ts]

    logger.info(f"[filter_posts_by_date] kept {len(df)} posts between {start_date} and {end_date}")
    return df




# === Pipeline Application ===
def apply_post_filters(df, filters_config):
    """Apply multiple post filters in sequence using a config dict."""
    result_df = df.copy()

    for filter_name, config in filters_config.items():

        if filter_name == 'length' and config.get('enabled', True):
            result_df = filter_posts_by_length(result_df, **config.get('params', {}))
        elif filter_name == 'sentiment' and config.get('enabled', True):
            result_df = filter_posts_by_sentiment(result_df, **config.get('params', {}))
        elif filter_name == 'course_codes' and config.get('enabled', True):
            result_df = filter_posts_by_course_code(result_df, **config.get('params', {}))

    return result_df