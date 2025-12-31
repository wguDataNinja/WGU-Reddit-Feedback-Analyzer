from __future__ import annotations

"""
Stage 1 classifier.

Loads prompt templates, formats inputs, calls generate(), parses JSON output,
and validates predictions with Pydantic.

Implements safe_parse_stage1_response and surfaces all schema/parse issues as
contains_painpoint="u" plus error flags. The classify_post function is the
primary entry point used by the Stage 1 benchmark runner.
"""

import json
import re
from pathlib import Path

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
    """Load a prompt template from disk."""
    p = Path(path)
    return p.read_text(encoding="utf-8")


def build_prompt(template: str, example: Stage1PredictionInput) -> str:
    """
    Render a prompt template for a single post.

    Uses simple replacement so JSON braces in the template are not
    treated as format fields.
    """
    return (
        template.replace("{post_id}", example.post_id)
        .replace("{course_code}", example.course_code)
        .replace("{post_text}", example.text)
    )


def _strip_code_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _extract_json_block(text: str) -> str:
    """
    Best-effort extraction of the main JSON object from the model output.

    Strips code fences and trims to the outermost {...} block. If no
    braces are found, returns the original text.
    """
    s = _strip_code_fences(text)

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start : end + 1]
    return s


def _regex_contains_painpoint(text: str) -> tuple[str | None, bool]:
    """
    Try to extract an unambiguous y/n/u from a contains_painpoint field.

    Returns (label, ambiguous_flag).
    """
    pattern = r'"contains_painpoint"\s*:\s*"([ynu])"'
    matches = re.findall(pattern, text, flags=re.IGNORECASE)

    if not matches:
        return None, False

    distinct = {m.lower() for m in matches}
    if len(distinct) == 1:
        return distinct.pop(), False

    return None, True


def safe_parse_stage1_response(
    raw_text: str,
) -> tuple[str, str, str, float, bool, bool, bool]:
    """
    Safe parsing for Stage 1 responses.

    Returns:
        contains_painpoint (str: y/n/u)
        root_cause_summary (str)
        pain_point_snippet (str)
        confidence (float)
        parse_error (bool)
        schema_error (bool)
        used_fallback (bool)
    """
    parse_error = False
    schema_error = False
    used_fallback = False

    json_text = _extract_json_block(raw_text)

    # Strict JSON parse path
    try:
        data = json.loads(json_text)

        cp_raw = str(data.get("contains_painpoint", "")).strip().lower()
        if cp_raw not in {"y", "n", "u"}:
            schema_error = True
            cp = "u"
        else:
            cp = cp_raw

        root_cause = ""
        snippet = ""

        pain_points = data.get("pain_points")
        if isinstance(pain_points, list) and pain_points:
            first = pain_points[0] or {}
            root_cause = (first.get("root_cause_summary") or "").strip()
            snippet = (first.get("pain_point_snippet") or "").strip()
        else:
            root_cause = (data.get("root_cause_summary") or "").strip()
            snippet = (data.get("pain_point_snippet") or "").strip()

        conf_val = data.get("confidence", None)
        try:
            confidence = float(conf_val)
        except (TypeError, ValueError):
            confidence = 0.0

        return cp, root_cause, snippet, confidence, parse_error, schema_error, used_fallback

    except json.JSONDecodeError:
        parse_error = True
        schema_error = True
    except Exception:
        schema_error = True

    # Fallback: regex on contains_painpoint field only
    used_fallback = True
    label, ambiguous = _regex_contains_painpoint(raw_text)
    if ambiguous:
        schema_error = True
        return "u", "", "", 0.0, parse_error, schema_error, used_fallback

    if label in {"y", "n", "u"}:
        schema_error = True
        return label, "", "", 0.0, parse_error, schema_error, used_fallback

    schema_error = True
    return "u", "", "", 0.0, parse_error, schema_error, used_fallback


def _clamp_confidence(value: float) -> float:
    """
    Clamp confidence into [0.0, 1.0]. If it's NaN or out-of-range, return 0.0.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0

    if v < 0.0 or v > 1.0:
        return 0.0
    return v


def classify_post(
    model_name: str,
    example: Stage1PredictionInput,
    prompt_template: str,
    debug: bool = False,
) -> tuple[Stage1PredictionOutput, LlmCallResult]:
    """
    Classify a single post using the Stage 1 schema.

    Parameters
    ----------
    model_name : str
        Name of the model to use.
    example : Stage1PredictionInput
        Input post fields.
    prompt_template : str
        Template string containing {post_id}, {course_code}, {post_text}.
    debug : bool, optional
        When true, logs rendered prompts and raw outputs.

    Returns
    -------
    (Stage1PredictionOutput, LlmCallResult)
        Parsed prediction and low-level call metadata.
    """
    prompt = build_prompt(prompt_template, example)

    if debug:
        logger.info(
            "DEBUG prompt for model=%s post_id=%s:\n%s",
            model_name,
            example.post_id,
            prompt,
        )

    call_result = generate(model_name, prompt)

    if debug:
        logger.info(
            "DEBUG raw output for model=%s post_id=%s:\n%s",
            model_name,
            example.post_id,
            call_result.raw_text,
        )

    (
        cp,
        root_cause,
        snippet,
        confidence,
        parse_error,
        schema_error,
        used_fallback,
    ) = safe_parse_stage1_response(call_result.raw_text)

    rc_for_csv = root_cause if cp == "y" else ""
    snip_for_csv = snippet if cp == "y" else ""
    conf_for_csv = _clamp_confidence(confidence)

    try:
        pred = Stage1PredictionOutput(
            post_id=example.post_id,
            course_code=example.course_code,
            contains_painpoint=cp,
            root_cause_summary=rc_for_csv,
            pain_point_snippet=snip_for_csv,
            confidence=conf_for_csv,
            raw_response=call_result.raw_text,
            parse_error=parse_error,
            schema_error=schema_error,
            used_fallback=used_fallback,
        )
        return pred, call_result
    except ValidationError as e:
        logger.error(
            "Validation failed model=%s post_id=%s: %s",
            model_name,
            example.post_id,
            e,
        )
        print("\n=== VALIDATION FAILURE ===")
        print(f"model={model_name} post_id={example.post_id}")
        print(f"Error: {e}")
        print("Raw output:\n")
        print(call_result.raw_text)
        print("=== END RAW ===\n")

        try:
            pred = Stage1PredictionOutput(
                post_id=example.post_id,
                course_code=example.course_code,
                contains_painpoint="u",
                root_cause_summary="",
                pain_point_snippet="",
                confidence=0.0,
                raw_response=call_result.raw_text,
                parse_error=True,
                schema_error=True,
                used_fallback=True,
            )
            return pred, call_result
        except Exception as e2:
            logger.error(
                "Failed to build fallback Stage1PredictionOutput "
                "model=%s post_id=%s: %s",
                model_name,
                example.post_id,
                e2,
            )
            raise