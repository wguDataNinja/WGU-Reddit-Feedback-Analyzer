# fetchers/helpers.py

from utils.paths import project_path
import pandas as pd

def load_tracked_subreddits():
    csv_path = project_path("data", "wgu_subreddits.csv")
    df = pd.read_csv(csv_path)
    return df.iloc[:, 0].dropna().tolist()