from __future__ import annotations
"""
Typed data structures used by Stage 1 benchmarking.

Defines the input format sent to the LLM, the normalized prediction returned
from the LLM, and the metadata collected for each model call. These types
provide a stable interface for all Stage 1 code.
"""

from typing import Literal
from pydantic import BaseModel


class Stage1PredictionInput(BaseModel):
    """Single post input to the Stage 1 classifier."""
    post_id: str
    course_code: str
    text: str  # usually "title\n\nselftext"


class Stage1PredictionOutput(BaseModel):
    """Normalized Stage 1 prediction and parse flags."""
    post_id: str
    course_code: str

    # Core decision
    contains_painpoint: Literal["y", "n", "u"]

    # Only meaningful when contains_painpoint == "y"
    root_cause_summary: str = ""
    pain_point_snippet: str = ""

    # Confidence in [0.0, 1.0]
    confidence: float = 0.0

    # Raw model output
    raw_response: str

    # Error / parsing flags
    parse_error: bool = False
    schema_error: bool = False
    used_fallback: bool = False


class LlmCallResult(BaseModel):
    """
    Metadata for a single LLM call.

    Captures low-level details needed for cost, latency, and failure
    analysis. Everything inside here should be provider-agnostic.
    """
    model_name: str
    provider: str
    raw_text: str
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    elapsed_sec: float

    # Failure / retry metadata
    llm_failure: bool = False
    num_retries: int = 0
    error_message: str | None = None
    timeout_sec: float | None = None

    # Timing metadata
    started_at: float | None = None
    finished_at: float | None = None