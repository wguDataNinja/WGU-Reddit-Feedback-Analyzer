# src/wgu_reddit_analyzer/benchmark/model_client.py
"""
Model client wrapper for Stage 1 benchmarking.

Responsibility:
    - Hide provider-specific details (OpenAI vs Ollama).
    - Use the model registry for provider and pricing metadata.
    - Call the underlying LLM (Chat Completions for OpenAI, HTTP for Ollama).
    - Run cost/latency estimation via cost_latency.estimate_cost.
    - Return a structured LlmCallResult object for downstream use.

This is the single entry point Stage 1 code should use:
    generate(model_name: str, prompt: str) -> LlmCallResult
"""

from __future__ import annotations

import time
from typing import Any

from wgu_reddit_analyzer.utils.config_loader import get_config
from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.benchmark.cost_latency import estimate_cost
from wgu_reddit_analyzer.benchmark.stage1_types import LlmCallResult
from wgu_reddit_analyzer.benchmark.llm_sanity_check import (
    _call_openai_responses,
    _call_ollama,
)
from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("benchmark.model_client")


def generate(model_name: str, prompt: str) -> LlmCallResult:
    """
    Provider-agnostic LLM invocation.

    - Looks up model metadata via get_model_info(model_name).
    - Uses OpenAI Chat Completions for provider='openai'.
    - Uses Ollama HTTP API for provider='ollama'.
    - Calls estimate_cost(prompt, output, model_name, start_time).
    - Returns LlmCallResult with raw_text and cost/latency fields.
    """
    cfg = get_config()
    info = get_model_info(model_name)
    if info is None:
        raise RuntimeError(f"Model '{model_name}' not found in MODEL_REGISTRY.")

    start = time.time()

    if info.provider == "openai":
        raw_text = _call_openai_responses(model_name, prompt, cfg.openai_api_key or "")
    elif info.provider == "ollama":
        raw_text = _call_ollama(model_name, prompt)
    else:
        raise RuntimeError(f"Unsupported provider for model '{model_name}': {info.provider}")

    cost = estimate_cost(prompt, raw_text, model_name, start_time=start)
    cdict = cost.to_dict()

    logger.info(
        "LLM call finished model=%s provider=%s elapsed=%.3f cost=%.6f input_tokens=%s output_tokens=%s",
        model_name,
        info.provider,
        cdict.get("elapsed_sec"),
        cdict.get("total_cost_usd"),
        cdict.get("input_tokens"),
        cdict.get("output_tokens"),
    )

    return LlmCallResult(
        model_name=model_name,
        provider=info.provider,
        raw_text=raw_text,
        input_tokens=cdict.get("input_tokens", 0),
        output_tokens=cdict.get("output_tokens", 0),
        total_cost_usd=cdict.get("total_cost_usd", 0.0),
        elapsed_sec=cdict.get("elapsed_sec", 0.0),
    )