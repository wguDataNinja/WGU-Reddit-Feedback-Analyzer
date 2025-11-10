"""
IO Layout Helpers

Purpose:
    Canonical path constructors for data, outputs, and reports.
"""

from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
LEGACY_OUTPUTS = ROOT / "outputs"


def data_path(*parts: str) -> Path:
    return DATA.joinpath(*parts)


def output_path(*parts: str) -> Path:
    path = OUTPUT.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def legacy_output_path(*parts: str) -> Path:
    return LEGACY_OUTPUTS.joinpath(*parts)


def stage_dir(stage_number: int) -> Path:
    return OUTPUT / f"stage{stage_number}"


def reports_dir() -> Path:
    return OUTPUT / "reports"


def runs_dir() -> Path:
    return OUTPUT / "runs"


def stage1_filtered_posts() -> Path:
    return data_path("filtered_posts.jsonl")


def stage1_locked_posts() -> Path:
    return data_path("stage1", "posts_locked.jsonl")