from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ModelInfo:
    name: str
    provider: str
    input_per_1k: float
    output_per_1k: float
    cached_input_per_1k: float = 0.0
    is_local: bool = False


MODEL_REGISTRY: Dict[str, ModelInfo] = {
    # Local model via Ollama (no API cost accounting)
    "llama3": ModelInfo(
        name="llama3",
        provider="ollama",
        input_per_1k=0.0,
        output_per_1k=0.0,
        cached_input_per_1k=0.0,
        is_local=True,
    ),

    # Prices derived from official per-1M rates (divide by 1000 to get per-1K)

    # gpt-5-nano: $0.05 / 1M input, $0.40 / 1M output, $0.005 / 1M cached
    "gpt-5-nano": ModelInfo(
        name="gpt-5-nano",
        provider="openai",
        input_per_1k=0.05 / 1000.0,          # 0.00005
        cached_input_per_1k=0.005 / 1000.0,  # 0.000005
        output_per_1k=0.40 / 1000.0,         # 0.0004
    ),

    # gpt-5-mini: $0.25 / 1M input, $2.00 / 1M output, $0.025 / 1M cached
    "gpt-5-mini": ModelInfo(
        name="gpt-5-mini",
        provider="openai",
        input_per_1k=0.25 / 1000.0,          # 0.00025
        cached_input_per_1k=0.025 / 1000.0,  # 0.000025
        output_per_1k=2.00 / 1000.0,         # 0.002
    ),

    # gpt-5 (flagship): $1.25 / 1M input, $10.00 / 1M output, $0.125 / 1M cached
    "gpt-5": ModelInfo(
        name="gpt-5",
        provider="openai",
        input_per_1k=1.25 / 1000.0,          # 0.00125
        cached_input_per_1k=0.125 / 1000.0,  # 0.000125
        output_per_1k=10.00 / 1000.0,        # 0.01
    ),

    # gpt-4o-mini: $0.15 / 1M input, $0.60 / 1M output, $0.075 / 1M cached
    "gpt-4o-mini": ModelInfo(
        name="gpt-4o-mini",
        provider="openai",
        input_per_1k=0.15 / 1000.0,          # 0.00015
        cached_input_per_1k=0.075 / 1000.0,  # 0.000075
        output_per_1k=0.60 / 1000.0,         # 0.0006
    ),
}


def get_model_info(name: str) -> ModelInfo:
    try:
        return MODEL_REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"Unknown model: {name}") from e