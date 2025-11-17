from __future__ import annotations
"""
Typed data structures used by Stage 1 benchmarking.

Defines the input format sent to the LLM, the normalized prediction returned
from the LLM, and the metadata collected for each model call. These types
provide a stable interface for all Stage 1 code.
"""
from typing import Literal, Optional
from pydantic import BaseModel


class Stage1PredictionInput(BaseModel):
    post_id: str
    course_code: str
    text: str  # usually "title\\n\\nselftext"


class Stage1PredictionOutput(BaseModel):
    post_id: str
    course_code: str
    contains_painpoint: Literal["y", "n", "u"]
    root_cause_summary: Optional[str] = None
    ambiguity_flag: Optional[bool] = None
    raw_response: str  # the raw model output


class LlmCallResult(BaseModel):
    model_name: str
    provider: str
    raw_text: str
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    elapsed_sec: float