# scripts/stage1/step04_run_stage1.py

"""
Entrypoint for Stage 1: Reddit post → pain point extractor.

Input:  /outputs/stage1/filtered_posts_stage1.jsonl
Output: /outputs/stage1/pain_points_stage1.jsonl
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
from scripts.stage1.step03_classify_file import classify_file  # updated import

def run_stage1(limit: int | None = None) -> None:
    print("Running Stage 1 pain point classification...")
    classify_file(limit=limit)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of posts to process")
    args = parser.parse_args()
    run_stage1(limit=args.limit)
