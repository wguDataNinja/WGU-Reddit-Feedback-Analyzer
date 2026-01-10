# sentiment.py

import pandas as pd
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from utils.paths import DATA_DIR
analyzer = SentimentIntensityAnalyzer()

def calculate_vader_sentiment(df):
    df = df.copy()
    df['VADER_Compound'] = df.apply(
        lambda row: analyzer.polarity_scores(f"{row['title']} {row['selftext']}")['compound'],
        axis=1
    )
    print(f"[calculate_vader_sentiment] VADER sentiment scored for {len(df)} posts.")
    return df





def analyze_proximity_sentiment(text_clean, window_size=30):
    """
    Analyzes sentiment of words within a window around course code mentions.

    Args:
        text_clean (str): Cleaned post text
        window_size (int): Number of words before/after course code to analyze

    Returns:
        list: [
            {'relative_position': -3, 'sentiment': -0.5},
            {'relative_position': 1, 'sentiment': -0.3},
            ...
        ]
    """
    # Load and normalize course list
    course_df = pd.read_csv(DATA_DIR / "courses_with_college_v10.csv")
    course_codes = set(course_df["CourseCode"].astype(str).str.upper().str.replace(r"[\s\-]", "", regex=True))

    # Initialize VADER analyzer
    analyzer = SentimentIntensityAnalyzer()

    # Split text into words
    words = text_clean.split()

    # Find course code positions
    results = []

    for i, word in enumerate(words):
        # Normalize word for comparison
        normalized_word = re.sub(r"[\s\-]", "", word).upper()

        # Check if this word is a course code
        if normalized_word in course_codes:
            # Extract window around course code
            start_pos = max(0, i - window_size)
            end_pos = min(len(words), i + window_size + 1)

            # Analyze each word in the window (except the course code itself)
            for j in range(start_pos, end_pos):
                if j != i:  # Skip the course code word itself
                    word_to_analyze = words[j]
                    sentiment = analyzer.polarity_scores(word_to_analyze)['compound']
                    relative_position = j - i

                    results.append({
                        'relative_position': relative_position,
                        'sentiment': sentiment,
                        'word': word_to_analyze
                    })

    return results


def vader_sentiment_spotlight(df):
    """
    Analyzes sentiment for every word in title and selftext separately.

    Args:
        df (DataFrame): DataFrame with 'title' and 'selftext' columns

    Returns:
        DataFrame: Original df with added 'sentiment_spotlight' column containing:
        {
            'title_words': [{'word': 'word', 'sentiment': 0.0, 'position': 0}, ...],
            'selftext_words': [{'word': 'word', 'sentiment': 0.0, 'position': 0}, ...]
        }
    """
    analyzer = SentimentIntensityAnalyzer()
    df = df.copy()

    def analyze_text_words(text):
        """Analyze sentiment for each word in text"""
        if pd.isna(text) or text == '':
            return []

        # Split into words while preserving positions
        words = re.findall(r'\S+', str(text))
        word_sentiments = []

        for i, word in enumerate(words):
            # Clean word for sentiment analysis (remove punctuation for analysis)
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word:  # Only analyze if there's actual text
                sentiment = analyzer.polarity_scores(clean_word)['compound']
            else:
                sentiment = 0.0

            word_sentiments.append({
                'word': word,  # Keep original word with punctuation
                'sentiment': sentiment,
                'position': i
            })

        return word_sentiments

    def process_row(row):
        """Process a single row to get sentiment spotlight data"""
        title_words = analyze_text_words(row.get('title', ''))
        selftext_words = analyze_text_words(row.get('selftext', ''))

        return {
            'title_words': title_words,
            'selftext_words': selftext_words
        }

    print(f"[vader_sentiment_spotlight] Analyzing sentiment for {len(df)} posts...")
    df['sentiment_spotlight'] = df.apply(process_row, axis=1)

    return df
