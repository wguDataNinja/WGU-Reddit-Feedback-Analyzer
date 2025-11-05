# config/stage1.py

from pathlib import Path
import datetime
from config import common

today = datetime.date.today().isoformat()

# Main run output directories
STAGE1_OUTPUT_DIR = common.OUTPUT_DIR / "runs" / today / "stage1"
STAGE1_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Primary paths for stage 1
INPUT_PATH = STAGE1_OUTPUT_DIR / "filtered_posts.jsonl"
RAW_POSTS_PATH = STAGE1_OUTPUT_DIR / "unfiltered_posts_with_sentiment.jsonl"

OUTPUT_PATH = STAGE1_OUTPUT_DIR / "pain_points_stage1.jsonl"
LOG_PATH = common.OUTPUT_DIR / "runs" / today / "logs" / "stage1.log"

# Latest snapshot paths
LATEST_DIR = common.OUTPUT_DIR / "latest"
LATEST_INPUT_PATH = LATEST_DIR / "filtered_posts_stage1.jsonl"
LATEST_OUTPUT_PATH = LATEST_DIR / "pain_points_stage1.jsonl"
LATEST_LOG_PATH = LATEST_DIR / "logs" / "stage1.log"

FILTERED_SENTIMENT_PATH = INPUT_PATH