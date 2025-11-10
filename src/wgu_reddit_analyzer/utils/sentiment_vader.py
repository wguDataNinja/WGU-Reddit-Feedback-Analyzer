_analyzer = None

def _get():
    global _analyzer
    if _analyzer is None:
        try:
            from nltk.sentiment import SentimentIntensityAnalyzer
            _analyzer = SentimentIntensityAnalyzer()
        except Exception as e:
            raise RuntimeError("VADER not available. Install nltk + vader_lexicon.") from e
    return _analyzer

def calculate_vader_sentiment(text: str) -> float:
    if not text:
        return 0.0
    return _get().polarity_scores(text)["compound"]
