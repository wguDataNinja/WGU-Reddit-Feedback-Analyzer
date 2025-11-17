"""
Hello LLM Benchmark

Purpose:
    Minimal connectivity and configuration sanity check for the benchmark
    environment. Confirms that the selected LLM can be called using the
    model registry configuration.

Inputs:
    Model name and prompt text, typically from CLI arguments or defaults.

Outputs:
    Prints the model name and short response to stdout.
    Writes a manifest and log file under artifacts/runs/<timestamp>/.

Usage:
    python -m wgu_reddit_analyzer.benchmark.hello_llm --model my_model

Notes:
    This module is intended as a fast, side-effect-free connectivity check.
"""

from __future__ import annotations

import json
import sys
import time
from typing import List, Any, Dict

from wgu_reddit_analyzer.utils.config_loader import get_config
from wgu_reddit_analyzer.benchmark.model_registry import (
    get_model_info,
    MODEL_REGISTRY,
)
from wgu_reddit_analyzer.benchmark.cost_latency import estimate_cost


def _extract_from_output_list(output: Any) -> str:
    """
    Best-effort extraction of human-readable text from a responses.output-style list.
    """
    if not output:
        return ""

    parts: List[str] = []

    for item in output:
        item_type = getattr(item, "type", None)
        if isinstance(item, dict):
            item_type = item.get("type", item_type)

        # Look for text-like items
        if item_type in ("message", "output_text", "text"):
            content = getattr(item, "content", None)
            if isinstance(item, dict) and content is None:
                content = item.get("content")

            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, str) and c.strip():
                        parts.append(c.strip())
                    elif isinstance(c, dict):
                        t = (
                            c.get("text")
                            or c.get("value")
                            or c.get("content")
                        )
                        if isinstance(t, str) and t.strip():
                            parts.append(t.strip())

    return " ".join(parts).strip()


def _call_openai_responses(model_name: str, prompt: str, api_key: str) -> str:
    """
    Call OpenAI Responses API for models configured in MODEL_REGISTRY.
    Aims to avoid reasoning-only partial outputs.
    """
    from openai import OpenAI

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY (or equivalent) is missing; cannot call OpenAI models.")

    client = OpenAI(api_key=api_key)

    resp = client.responses.create(
        model=model_name,
        input=prompt,
        max_output_tokens=256,
        reasoning={"effort": "low"},
    )

    # Preferred: direct text accessor if available.
    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    # Fallback: reconstruct from output list.
    output = getattr(resp, "output", None)
    alt = _extract_from_output_list(output)
    if alt:
        return alt

    # Final debug dump if nothing usable was found.
    try:
        dumped = resp.model_dump_json(indent=2)
    except Exception:
        dumped = repr(resp)

    print("DEBUG: No text extracted from Responses API. Raw response:\n")
    print(dumped)
    print("\nEND DEBUG\n")

    return ""


def _call_ollama(model_name: str, prompt: str) -> str:
    """
    Call a local Ollama instance for the given model.
    """
    import requests

    payload = {"model": model_name, "prompt": prompt, "stream": False}
    r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()


def run_hello_for_model(model_name: str) -> Dict[str, Any]:
    """
    Run a single hello test for the given model and return metrics dict.
    """
    cfg = get_config()
    info = get_model_info(model_name)
    if info is None:
        raise RuntimeError(f"Model '{model_name}' not found in MODEL_REGISTRY.")

    prompt = "Say 'hello' from the WGU Reddit Analyzer project in one short sentence."
    start = time.time()

    if info.provider == "openai":
        output = _call_openai_responses(model_name, prompt, cfg.openai_api_key or "")
    elif info.provider == "ollama":
        output = _call_ollama(model_name, prompt)
    else:
        raise RuntimeError(f"Unsupported provider for model '{model_name}': {info.provider}")

    # estimate_cost is expected to return an object with .to_dict()
    cost = estimate_cost(prompt, output, model_name, start_time=start)

    result = cost.to_dict()
    result["output"] = output
    return result


def run_single(model_name: str) -> None:
    """
    Run hello test for a single model and print JSON result.
    """
    print(f"\n=== Testing {model_name} ===")
    try:
        result = run_hello_for_model(model_name)
    except Exception as e:
        print(f"X {model_name} failed: {e}")
        return

    print(json.dumps(result, indent=2))
    if not result.get("output"):
        print("Result has empty output; see any DEBUG block above.")
    else:
        print("OK")


def run_all() -> None:
    """
    Run hello tests for all models in MODEL_REGISTRY and print a brief summary.
    """
    models: List[str] = list(MODEL_REGISTRY.keys())
    summary: List[Dict[str, Any]] = []

    print("Running hello test for all registered models (sequential)...")
    for m in models:
        print(f"\n=== {m} ===")
        try:
            r = run_hello_for_model(m)
            print(json.dumps(r, indent=2))
            if not r.get("output"):
                print("Empty output; see any DEBUG block above.")
            summary.append(
                {
                    "model_name": r.get("model_name", m),
                    "total_cost_usd": r.get("total_cost_usd"),
                    "elapsed_sec": r.get("elapsed_sec"),
                    "input_tokens": r.get("input_tokens"),
                    "output_tokens": r.get("output_tokens"),
                }
            )
        except Exception as e:
            print(f"X {m} failed: {e}")

    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    # Default: quick smoke test using a sensible default from MODEL_REGISTRY
    if len(sys.argv) == 1:
        default_model = "gpt-5-nano"
        if default_model not in MODEL_REGISTRY and MODEL_REGISTRY:
            # fallback to first registered model if default is absent
            default_model = next(iter(MODEL_REGISTRY.keys()))
        run_single(default_model)
    elif sys.argv[1] == "--all":
        run_all()
    else:
        run_single(sys.argv[1])