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

def run_stage1(limit: int | None = None, verbose: bool = False, output_dir: Path | None = None) -> None:
    # If output_dir is provided, update paths dynamically
    if output_dir:
        from scripts.stage1 import config_stage1
        config_stage1.OUTPUT_DIR = output_dir
        config_stage1.INPUT_PATH = output_dir / "filtered_posts_stage1.jsonl"
        config_stage1.OUTPUT_PATH = output_dir / "pain_points_stage1.jsonl"

    logger = setup_logger("stage1_entry", filename="stage1.log", to_console=True, verbose=verbose)
    logger.info("Running Stage 1 pain point classification...")
    classify_file(limit=limit)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output_dir", type=Path, help="Override Stage 1 output directory")
    args = parser.parse_args()

    run_stage1(limit=args.limit, verbose=args.verbose, output_dir=args.output_dir)