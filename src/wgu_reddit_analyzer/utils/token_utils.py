from __future__ import annotations

import math
from functools import lru_cache


@lru_cache(maxsize=None)
def _get_encoding_or_none(model_name: str):
    """
    Best-effort tokenizer lookup.

    - Uses tiktoken if installed.
    - Maps known model families to stable encodings.
    - Falls back to cl100k_base.
    - Returns None if anything fails (caller must handle).
    """
    try:
        import tiktoken
    except ImportError:
        return None

    normalized = (model_name or "").lower().strip()

    try:
        # Our benchmark models are gpt-5-nano/mini/base; treat them as gpt-4o family.
        if "gpt-5" in normalized or "gpt-4o" in normalized or "gpt-4-turbo" in normalized:
            return tiktoken.encoding_for_model("gpt-4o")
        if "gpt-3.5" in normalized:
            return tiktoken.encoding_for_model("gpt-3.5-turbo")

        # Fallback: generic modern encoding
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None


def count_tokens(text: str, model: str = "gpt-5-mini", chars_per_token: int = 4) -> int:
    """
    Approximate token count for text.

    - Uses model-aware tiktoken encoding when available.
    - Falls back to a simple char-based estimate if unavailable.
    - Safe for all existing callers.
    """
    if not text:
        return 0

    enc = _get_encoding_or_none(model)
    if enc is not None:
        try:
            return len(enc.encode(text))
        except Exception:
            # fall through to char-based approximation
            pass

    # Fallback: cheap and conservative
    return max(1, math.ceil(len(text) / chars_per_token))


def count_tokens_batch(texts: list[str], model: str = "gpt-5-mini") -> list[int]:
    """
    Count tokens for a list of strings.

    - Reuses a shared encoding when possible.
    - Falls back per-string if needed.
    """
    if not texts:
        return []

    enc = _get_encoding_or_none(model)
    out: list[int] = []

    if enc is not None:
        for t in texts:
            if not t:
                out.append(0)
                continue
            try:
                out.append(len(enc.encode(t)))
            except Exception:
                out.append(max(1, math.ceil(len(t) / 4)))
        return out

    # No encoding available; use the scalar helper
    return [count_tokens(t, model=model) for t in texts]