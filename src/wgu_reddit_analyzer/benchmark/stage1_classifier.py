from __future__ import annotations

"""
Stage 1 classifier.

Loads prompt templates, formats inputs, calls generate(), parses JSON output,
and validates predictions with Pydantic.
"""

import json
from pathlib import Path
from typing import Tuple

from pydantic import ValidationError

from wgu_reddit_analyzer.benchmark.stage1_types import (
    Stage1PredictionInput,
    Stage1PredictionOutput,
    LlmCallResult,
)
from wgu_reddit_analyzer.benchmark.model_client import generate
from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("benchmark.stage1_classifier")


def load_prompt_template(path: str | Path) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8")


def build_prompt(template: str, example: Stage1PredictionInput) -> str:
    # Use simple replacement so JSON braces in the template are not treated as format fields.
    return (
        template
        .replace("{post_id}", example.post_id)
        .replace("{course_code}", example.course_code)
        .replace("{post_text}", example.text)
    )


def _extract_json_block(text: str) -> str:
    """
    Best-effort extraction of the main JSON object from the model output.
    Strips code fences and trims to the outermost {...} block.
    """
    s = text.strip()

    if s.startswith("```"):
        lines = s.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start : end + 1]
    return s


def _extract_label_fallback(raw: str) -> str:
    """
    Fallback path: scan raw text for the first y/n/u label.
    """
    for ch in raw.lower():
        if ch in ("y", "n", "u"):
            return ch
    raise ValueError("No contains_painpoint label (y/n/u) found in raw output.")


def classify_post(
    model_name: str,
    example: Stage1PredictionInput,
    prompt_template: str,
) -> Tuple[Stage1PredictionOutput, LlmCallResult]:
    prompt = build_prompt(prompt_template, example)
    call_result = generate(model_name, prompt)

    json_text = _extract_json_block(call_result.raw_text)

    # Try JSON path first
    try:
        data = json.loads(json_text)
        try:
            pred = Stage1PredictionOutput.model_validate(
                {**data, "raw_response": call_result.raw_text}
            )
            return pred, call_result
        except ValidationError as e:
            logger.error(
                "Validation failed model=%s post_id=%s: %s data=%r",
                model_name,
                example.post_id,
                e,
                data,
            )
            print("\n=== VALIDATION FAILURE ===")
            print(f"model={model_name} post_id={example.post_id}")
            print(f"Error: {e}")
            print("Raw output:\n")
            print(call_result.raw_text)
            print("=== END RAW ===\n")
            # fall through to fallback
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON from model=%s post_id=%s: %s",
            model_name,
            example.post_id,
            e,
        )
        print("\n=== JSON PARSE FAILURE ===")
        print(f"model={model_name} post_id={example.post_id}")
        print(f"Error: {e}")
        print("Raw output:\n")
        print(call_result.raw_text)
        print("=== END RAW ===\n")
        # fall through to fallback

    # Fallback: label-only parse
    try:
        label = _extract_label_fallback(call_result.raw_text)
        pred = Stage1PredictionOutput(
            post_id=example.post_id,
            course_code=example.course_code,
            contains_painpoint=label,  # Pydantic still enforces y/n/u
            root_cause_summary=None,
            ambiguity_flag=None,
            raw_response=call_result.raw_text,
        )
        logger.warning(
            "Using label-only fallback for model=%s post_id=%s label=%s",
            model_name,
            example.post_id,
            label,
        )
        return pred, call_result
    except Exception as e:
        logger.error(
            "Fallback label extraction failed model=%s post_id=%s: %s",
            model_name,
            example.post_id,
            e,
        )
        raise