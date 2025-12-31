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

Features:
    - Per-call timeout.
    - Simple retry with exponential backoff.
    - llm_failure / num_retries / error_message flags on LlmCallResult.

Decoding:
    - Stage-1 benchmarks are expected to use deterministic decoding
      (e.g., temperature=0, top_p=1, single candidate) at the provider layer.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Tuple

from wgu_reddit_analyzer.utils.config_loader import get_config
from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.benchmark.cost_latency import estimate_cost
from wgu_reddit_analyzer.benchmark.stage1_types import LlmCallResult
from wgu_reddit_analyzer.benchmark.llm_connectivity_check import (
    _call_openai_responses,
    _call_ollama,
)
from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("benchmark.model_client")

DEFAULT_TIMEOUT_SEC = 90.0
MAX_RETRIES = 2


def _call_model_once(
    model_name: str,
    prompt: str,
    provider: str,
    cfg: Any,
) -> str:
    """
    Single underlying model call.

    Provider-specific helpers are responsible for configuring decoding
    (e.g., deterministic settings for benchmarking).
    """
    if provider == "openai":
        return _call_openai_responses(model_name, prompt, cfg.openai_api_key or "")
    if provider == "ollama":
        return _call_ollama(model_name, prompt)
    raise RuntimeError(f"Unsupported provider for model '{model_name}': {provider}")


def _call_model_with_retry(
    model_name: str,
    prompt: str,
    provider: str,
    cfg: Any,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    max_retries: int = MAX_RETRIES,
) -> Tuple[str | None, bool, int, str | None]:
    """
    Run the underlying model call with a per-attempt timeout and simple retries.

    Returns:
        raw_text (str | None)
        llm_failure (bool)
        num_retries (int)  # how many retries were actually attempted
        error_message (str | None)
    """
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                backoff = 2**attempt
                logger.warning(
                    "Retrying model call model=%s provider=%s attempt=%d backoff=%ds",
                    model_name,
                    provider,
                    attempt,
                    backoff,
                )
                time.sleep(backoff)

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    _call_model_once,
                    model_name,
                    prompt,
                    provider,
                    cfg,
                )
                raw_text: str = future.result(timeout=timeout_sec)

            if attempt > 0:
                logger.info(
                    "Model call succeeded after %d retries model=%s provider=%s",
                    attempt,
                    model_name,
                    provider,
                )
            return raw_text, False, attempt, None

        except FuturesTimeoutError:
            last_error = f"Timeout after {timeout_sec}s"
            logger.error(
                "Model call timeout model=%s provider=%s attempt=%d timeout_sec=%.1f",
                model_name,
                provider,
                attempt,
                timeout_sec,
            )
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.error(
                "Model call failed model=%s provider=%s attempt=%d error=%s",
                model_name,
                provider,
                attempt,
                e,
            )

    logger.error(
        "Model call giving up after %d retries model=%s provider=%s last_error=%s",
        max_retries,
        model_name,
        provider,
        last_error,
    )
    return None, True, max_retries, last_error


def generate(model_name: str, prompt: str) -> LlmCallResult:
    """
    Provider-agnostic LLM invocation.

    Parameters
    ----------
    model_name : str
        Registry key for the model.
    prompt : str
        Fully rendered prompt text.

    Returns
    -------
    LlmCallResult
        Structured result including raw text, cost, latency, and failure flags.
    """
    cfg = get_config()
    info = get_model_info(model_name)
    if info is None:
        raise RuntimeError(f"Model '{model_name}' not found in MODEL_REGISTRY.")

    started_at = time.time()

    raw_text, llm_failure, num_retries, error_message = _call_model_with_retry(
        model_name=model_name,
        prompt=prompt,
        provider=info.provider,
        cfg=cfg,
        timeout_sec=DEFAULT_TIMEOUT_SEC,
        max_retries=MAX_RETRIES,
    )

    if raw_text is None:
        raw_text = ""

    cost = estimate_cost(prompt, raw_text, model_name, start_time=started_at)
    cdict = cost.to_dict()
    finished_at = started_at + (cdict.get("elapsed_sec") or 0.0)

    logger.info(
        "LLM call finished model=%s provider=%s elapsed=%.3f cost=%.6f "
        "input_tokens=%s output_tokens=%s llm_failure=%s retries=%d",
        model_name,
        info.provider,
        cdict.get("elapsed_sec"),
        cdict.get("total_cost_usd"),
        cdict.get("input_tokens"),
        cdict.get("output_tokens"),
        llm_failure,
        num_retries,
    )

    return LlmCallResult(
        model_name=model_name,
        provider=info.provider,
        raw_text=raw_text,
        input_tokens=cdict.get("input_tokens", 0),
        output_tokens=cdict.get("output_tokens", 0),
        total_cost_usd=cdict.get("total_cost_usd", 0.0),
        elapsed_sec=cdict.get("elapsed_sec", 0.0),
        llm_failure=llm_failure,
        num_retries=num_retries,
        error_message=error_message,
        timeout_sec=DEFAULT_TIMEOUT_SEC,
        started_at=started_at,
        finished_at=finished_at,
    )