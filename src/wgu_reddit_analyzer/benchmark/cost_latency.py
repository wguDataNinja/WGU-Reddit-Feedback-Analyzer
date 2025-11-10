"""
Cost and Latency Utilities

Purpose:
    Provide reusable helpers to estimate token usage, API cost, and latency
    for LLM calls used in benchmark scripts.

Inputs:
    - Model metadata from benchmark.model_registry.
    - Text prompts and completions from calling code.

Outputs:
    - CostResult objects per call.
    - Aggregated summaries via summarize_costs.

Usage:
    from wgu_reddit_analyzer.benchmark.cost_latency import estimate_cost

Notes:
    - All pricing is read from model_registry; update that registry to match
      current provider pricing.
    - Local models are treated as zero-cost.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Iterable

from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.utils.token_utils import count_tokens


@dataclass
class CostResult:
    model_name: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    total_cost_usd: float
    elapsed_sec: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def estimate_cost(
    text_in: str,
    text_out: str,
    model_name: str,
    cached_input_tokens: int = 0,
    start_time: Optional[float] = None,
) -> CostResult:
    """
    Estimate token usage, cost, and optional latency for a single LLM call.

    Args:
        text_in: Full prompt text sent to the model.
        text_out: Full completion text returned by the model.
        model_name: Key for model_registry.get_model_info.
        cached_input_tokens: Portion of input tokens eligible for cached
            (e.g., prompt cache) pricing.
        start_time: If provided, wall-clock start time (time.time()) used
            to compute elapsed_sec.

    Returns:
        CostResult with token counts, total_cost_usd, and elapsed_sec.
    """
    model = get_model_info(model_name)

    # Token counting is delegated; model_name is passed for model-specific rules.
    input_tokens = count_tokens(text_in, model_name)
    output_tokens = count_tokens(text_out, model_name)

    # Guard against bad inputs so we never charge negative paid tokens.
    cached_effective = max(0, min(cached_input_tokens, input_tokens))
    paid_input = max(0, input_tokens - cached_effective)

    total_cost_usd = 0.0
    # Local / non-metered models are treated as zero-cost.
    if not getattr(model, "is_local", False):
        total_cost_usd = (
            paid_input / 1000 * model.input_per_1k
            + cached_effective / 1000 * getattr(model, "cached_input_per_1k", model.input_per_1k)
            + output_tokens / 1000 * model.output_per_1k
        )

    if start_time is not None:
        elapsed = max(0.0, time.time() - start_time)
    else:
        elapsed = 0.0

    return CostResult(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_effective,
        total_cost_usd=round(total_cost_usd, 6),
        elapsed_sec=round(elapsed, 3),
    )


def summarize_costs(results: Iterable[CostResult]) -> Dict[str, Any]:
    """
    Aggregate a collection of CostResult objects into a run-level summary.

    Returns:
        {
            "total_cost_usd": float,
            "avg_latency_sec": float,
            "total_input_tokens": int,
            "total_output_tokens": int,
            "count": int,
        }
    """
    results = list(results)
    if not results:
        return {
            "total_cost_usd": 0.0,
            "avg_latency_sec": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "count": 0,
        }

    total_cost = sum(r.total_cost_usd for r in results)
    total_in = sum(r.input_tokens for r in results)
    total_out = sum(r.output_tokens for r in results)
    total_elapsed = sum(r.elapsed_sec for r in results)
    n = len(results)

    return {
        "total_cost_usd": round(total_cost, 4),
        "avg_latency_sec": round(total_elapsed / n, 3) if n else 0.0,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "count": n,
    }