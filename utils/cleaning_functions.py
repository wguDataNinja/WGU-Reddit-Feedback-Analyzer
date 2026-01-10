# cleaning_functions.py

import re
import nltk
import string
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import pandas as pd




lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# --- Core Cleaning Functions ---

def merge_title_selftext(row):
    return f"{row['title']} {row['selftext']}"



import re

def remove_urls(text):
    if not isinstance(text, str):
        return text

    # Remove Markdown-style links like [text](http://...)
    text = re.sub(r"\[.*?\]\((https?://|www\.)\S+\)", "", text)

    # Remove raw URLs with or without punctuation, across newlines
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # Remove domain-based links that don't start with http (e.g. preview.redd.it/...)
    text = re.sub(r"\b\w+\.(com|org|net|edu|gov|io|co|redd|reddit)\S*", "", text)

    return text
def remove_emojis_punct(text):
    text = re.sub(r"[^\w\s.,!?]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return text

def remove_special_chars_digits(text):
    return re.sub(r"[^a-zA-Z\s]", "", text)

def lowercase(text):
    return text.lower()

def tokenize(text):
    return nltk.word_tokenize(text)

def remove_stopwords(tokens):
    return [t for t in tokens if t not in stop_words]

def lemmatize(tokens):
    return [lemmatizer.lemmatize(t) for t in tokens]

# --- Full Cleaning Pipelines ---

def cleaning_vader(df):
    df = df.copy()
    df['text_clean'] = df.apply(merge_title_selftext, axis=1)
    df['text_clean'] = df['text_clean'].apply(remove_urls)

    # Remove u/username and r/subreddit patterns
    df['text_clean'] = df['text_clean'].str.replace(r"\bu\/\w+", "", regex=True)
    df['text_clean'] = df['text_clean'].str.replace(r"\br\/\w+", "", regex=True)

    # Normalize whitespace
    df['text_clean'] = df['text_clean'].str.replace(r"\s+", " ", regex=True).str.strip()

    # Calculate text length
    df['text_length'] = df['text_clean'].str.len()
    return df

# Add to cleaning_functions.py

def cleaning_ngrams(df):
    df = df.copy()
    df['text_clean'] = df['text_clean'].apply(lowercase)
    df['text_clean'] = df['text_clean'].apply(remove_emojis_punct)
    df['text_clean'] = df['text_clean'].apply(remove_special_chars_digits)
    df['tokens'] = df['text_clean'].apply(tokenize)
    return df
def cleaning_nltk(df):
    df = df.copy()

    # Ensure title and selftext are strings
    df['title'] = df['title'].astype(str).fillna("")
    df['selftext'] = df['selftext'].astype(str).fillna("")

    df['text_clean'] = df.apply(merge_title_selftext, axis=1)
    df['text_clean'] = df['text_clean'].apply(lowercase)
    df['text_clean'] = df['text_clean'].apply(remove_emojis_punct)
    df['text_clean'] = df['text_clean'].apply(remove_special_chars_digits)
    df['tokens'] = df['text_clean'].apply(tokenize)
    # df['tokens'] = df['tokens'].apply(remove_stopwords)
    # df['tokens'] = df['tokens'].apply(lemmatize)
    # df['text_clean'] = df['tokens'].apply(lambda tokens: " ".join(tokens))
    # df['text_length'] = df['text_clean'].str.len()
    return df

def cleaning_bertopic(df):
    df = df.copy()
    df['text_clean'] = df.apply(merge_title_selftext, axis=1)
    df['text_clean'] = df['text_clean'].apply(lowercase)
    df['text_clean'] = df['text_clean'].apply(remove_urls)
    df['text_clean'] = df['text_clean'].apply(remove_emojis_punct)
    df['text_clean'] = df['text_clean'].apply(remove_special_chars_digits)
    df['tokens'] = df['text_clean'].apply(tokenize)
    df['tokens'] = df['tokens'].apply(remove_stopwords)
    df['tokens'] = df['tokens'].apply(lemmatize)
    df['text_clean'] = df['tokens'].apply(lambda tokens: " ".join(tokens))
    return df

def validate_cleaning():
    # Sample test data
    test_data = {
        'title': ['Test Title!', 'Another Post 😀', 'URL Post'],
        'selftext': ['This has http://example.com URLs!', 'Clean text here.', 'More text with 123 numbers']
    }
    df_test = pd.DataFrame(test_data)

    print("=== ORIGINAL DATA ===")
    print(df_test)

    print("\n=== CLEANING_VADER ===")
    df_vader = cleaning_vader(df_test)
    print(df_vader[['text_clean', 'text_length']])

    print("\n=== CLEANING_NLTK ===")
    df_nltk = cleaning_nltk(df_test)
    print(df_nltk[['text_clean', 'tokens']])

    print("\n=== CLEANING_BERTOPIC ===")
    df_bertopic = cleaning_bertopic(df_test)
    print(df_bertopic[['text_clean']])