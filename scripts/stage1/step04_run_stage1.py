# scripts/stage1/step04_run_stage1.py

"""
Entrypoint for Stage 1: Reddit post → pain point extractor.

Input:  /outputs/stage1/filtered_posts_stage1.jsonl
Output: /outputs/stage1/pain_points_stage1.jsonl
"""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.stage1.step03_classify_file import classify_file
from utils.logger import setup_logger

def run_stage1(limit: int | None = None, verbose: bool = False) -> None:
    logger = setup_logger("stage1_entry", filename="stage1.log", to_console=True, verbose=verbose)
    logger.info("Running Stage 1 pain point classification...")
    classify_file(limit=limit)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of posts to process")
    parser.add_argument("--verbose", action="store_true", help="Enable debug-level logging")
    args = parser.parse_args()

    run_stage1(limit=args.limit, verbose=args.verbose)