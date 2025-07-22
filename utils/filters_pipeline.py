# filters_pipeline.py

from pathlib import Path
import pandas as pd
from utils.cleaning_functions import cleaning_nltk, cleaning_vader
from utils.sentiment import calculate_vader_sentiment
from utils.filters import apply_filters
import re


# filters_pipeline.py

def run_vader_filters(df: pd.DataFrame, course_list_path: str, output_path: str = None) -> pd.DataFrame:
    """
    Runs VADER cleaning and filtering on pre-scored DataFrame (assumes VADER sentiment already applied),
    with an added filter for posts containing help-seeking keywords.

    Parameters:
        df (pd.DataFrame): DataFrame with raw or pre-scored posts.
        course_list_path (str): Path to the course list CSV file.
        output_path (str, optional): Path to save the filtered DataFrame as CSV.

    Returns:
        pd.DataFrame: Filtered DataFrame after cleaning and applying filters.
    """

    # Keyword-based filtering (customize this list)
    HELP_KEYWORDS = ["?"]

    # Combine title + selftext, check if any keyword is present (case-insensitive)
    combined_text = df['title'].fillna('') + ' ' + df['selftext'].fillna('')
    pattern = '|'.join([re.escape(k) for k in HELP_KEYWORDS])
    df = df[combined_text.str.contains(pattern, case=False, na=False)]

    print(f"[run_vader_filters] Filtered to {len(df)} posts containing help-seeking keywords.")

    # Load course codes
    course_list = pd.read_csv(course_list_path)
    course_codes = course_list["CourseCode"].dropna().astype(str).tolist()

    print("[run_vader_filters] Starting VADER cleaning...")
    df = cleaning_vader(df)

    print("[run_vader_filters] Skipping VADER sentiment step (assumed pre-scored).")

    filters_config = {
        'length': {
            'enabled': True,
            'params': {'min_length': 40, 'max_length': 1000}
        },
        'course_codes': {
            'enabled': True,
            'params': {'course_codes': course_codes, 'exact_match_count': 1}
        },
        'sentiment': {
            'enabled': True,
            'params': {'max_score': -0.6}
        }
    }

    print("[run_vader_filters] Applying filters...")
    df_filtered = apply_filters(df, filters_config)

    if output_path:
        df_filtered.to_csv(output_path, index=False)
        print(f"[run_vader_filters] Saved filtered output to: {output_path}")

    return df_filtered


def run_nltk_filters(df: pd.DataFrame, course_list_path: str) -> pd.DataFrame:
    """
    Runs the full NLTK-based cleaning and filtering pipeline.

    Parameters:
        df (pd.DataFrame): Raw posts DataFrame.
        course_list_path (str): Path to the course list CSV file.

    Returns:
        pd.DataFrame: Filtered DataFrame after applying NLTK cleaning.
    """
    course_list = pd.read_csv(course_list_path)
    course_codes = course_list["CourseCode"].dropna().astype(str).tolist()

    print("[run_nltk_filters] Starting NLTK cleaning...")
    df = cleaning_nltk(df)

    # Placeholder for future NLTK sentiment support
    # df = calculate_nltk_sentiment(df)

    filters_config = {
        'length': {
            'enabled': True,
            'params': {
                'min_length': 40,
                'max_length': 1000
            }
        },
        'course_codes': {
            'enabled': True,
            'params': {
                'course_codes': course_codes,  # full list of valid codes
                'exact_match_count': 1  # only posts mentioning one course code
            }
        },
        'sentiment': {
            'enabled': False,
            'params': {}
        }
    }

    print("[run_nltk_filters] Applying filters...")
    return apply_filters(df, filters_config)