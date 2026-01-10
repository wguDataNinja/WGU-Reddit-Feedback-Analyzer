# scripts/stage1/config_stage1.py

"""Stage 1 config: constants, paths, model settings."""

from pathlib import Path

# Directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "stage1"
LOG_DIR = PROJECT_ROOT / "logs"

# Files
INPUT_PATH = OUTPUT_DIR / "filtered_posts_stage1.jsonl"
OUTPUT_PATH = OUTPUT_DIR / "pain_points_stage1.jsonl"
LOG_PATH = LOG_DIR / "stage1.log"

# Model config
MODEL_NAME = "gpt-4o-mini"
MAX_CHARS_PER_POST = 2000
MAX_RETRIES = 4
RETRY_SLEEP_SECONDS = 2
