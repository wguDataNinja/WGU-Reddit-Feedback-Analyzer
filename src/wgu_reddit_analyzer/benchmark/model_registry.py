from __future__ import annotations
"""
Benchmark Model Registry

Purpose:
    Central registry of benchmark model configurations and lightweight
    client wrappers for evaluation scripts.

Inputs:
    Model names requested by benchmark scripts.

Outputs:
    ModelSpec objects and compatible BenchmarkModelClient instances.

Usage:
    from wgu_reddit_analyzer.benchmark.model_registry import (
        get_model_spec, get_model_client
    )
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class ModelSpec:
    """Static configuration for a benchmark model."""

    name: str
    provider: str
    max_input_tokens: int
    max_output_tokens: int
    input_cost_per_1k: float
    output_cost_per_1k: float
    rpm_limit: int | None = None
    metadata: Dict[str, Any] | None = None


class BenchmarkModelClient:
    """Minimal interface expected by benchmark scripts."""

    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec

    def complete(self, prompt: str, max_tokens: int) -> str:
        raise NotImplementedError

    def complete_structured(self, prompt: str) -> Dict[str, Any]:
        raise NotImplementedError

    def build_label_prompt(self, post: Dict[str, Any]) -> str:
        raise NotImplementedError


# Registry definitions
_MODEL_REGISTRY: Dict[str, ModelSpec] = {
    "example-model": ModelSpec(
        name="example-model",
        provider="example",
        max_input_tokens=8000,
        max_output_tokens=512,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        metadata={"description": "Local mock client for development."},
    ),
}


def list_models() -> List[ModelSpec]:
    """Return all registered models."""
    return list(_MODEL_REGISTRY.values())


def get_model_spec(name: str) -> ModelSpec:
    """Return the ModelSpec for the given name."""
    if name not in _MODEL_REGISTRY:
        raise KeyError(f"Unknown model: {name}")
    return _MODEL_REGISTRY[name]


def get_model_client(spec: ModelSpec) -> BenchmarkModelClient:
    """Return a lightweight client wrapper for the given model spec."""

    class _NoopClient(BenchmarkModelClient):
        def complete(self, prompt: str, max_tokens: int) -> str:
            return f"[noop: {self.spec.name}]"

        def complete_structured(self, prompt: str) -> Dict[str, Any]:
            return {"label": "noop", "confidence": None, "rationale": None}

        def build_label_prompt(self, post: Dict[str, Any]) -> str:
            return f"Classify the following post:\n\n{post.get('body') or post}"

    return _NoopClient(spec)


def iter_model_specs(names: Iterable[str] | None = None) -> Iterable[ModelSpec]:
    """Yield selected model specs, or all if none provided."""
    if names is None:
        return list_models()
    return (get_model_spec(name) for name in names)