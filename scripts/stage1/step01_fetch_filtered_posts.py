# filename: scripts/stage1/step01_fetch_filtered_posts.py

"""
Fetches Reddit posts from the database and applies filters for LLM Stage 1 classification.

Filter Criteria:
- Post must mention exactly one WGU course code
  - Based on the 2025_06 course list
- Post must have VADER compound sentiment score < -0.2

Behavior:
- Appends only new posts not already in /data/filtered_posts_stage1.jsonl
- Existing file is preserved (not cleaned or archived)
- Filtering takes several minutes
"""

from pathlib import Path
import pandas as pd
import json
import time
from utils.cleaning_functions import cleaning_vader
from utils.sentiment import calculate_vader_sentiment
from utils.filters import filter_by_course_codes, filter_sentiment
from utils.jsonl_io import write_jsonl, read_jsonl
from utils.paths import DATA_DIR
from utils.db_utils import load_posts_dataframe
from scripts.stage1.config_stage1 import INPUT_PATH

COURSE_LIST_PATH = DATA_DIR / "2025_06_course_list_with_college.csv"
print(f"[INFO] Output file path: {INPUT_PATH}")

def fetch_filtered_posts() -> None:
    df_courses = pd.read_csv(COURSE_LIST_PATH)
    course_codes = df_courses["CourseCode"]

    seen_post_ids = set()
    if INPUT_PATH.exists():
        seen_post_ids = {row["post_id"] for row in read_jsonl(INPUT_PATH)}
        print(f"[INFO] Loaded {len(seen_post_ids)} previously processed post_ids")

    df = load_posts_dataframe()
    print(f"[INFO] Loaded {len(df)} posts from DB")

    df = df[~df["post_id"].isin(seen_post_ids)]
    print(f"[INFO] {len(df)} new posts after removing previously seen")

    if df.empty:
        print("[INFO] No new posts to process.")
        return

    # TIMED FILTERING
    filter_start = time.time()

    df = cleaning_vader(df)
    df = filter_by_course_codes(df, course_codes=course_codes, exact_match_count=1, match_type="eq")
    df = calculate_vader_sentiment(df)
    df = filter_sentiment(df, max_score=-0.2)

    elapsed = time.time() - filter_start
    print(f"[INFO] {len(df)} new posts passed all filters in {elapsed:.1f} seconds")

    if df.empty:
        print("[INFO] No qualifying new posts after filtering.")
        return

    records = [
        {
            "post_id": row["post_id"],
            "text_clean": row["text_clean"],
            "matched_course_codes": row["matched_course_codes"]
        }
        for _, row in df.iterrows()
    ]

    INPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INPUT_PATH.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[INFO] Appended {len(records)} new posts → {INPUT_PATH}")

if __name__ == "__main__":
    fetch_filtered_posts()
