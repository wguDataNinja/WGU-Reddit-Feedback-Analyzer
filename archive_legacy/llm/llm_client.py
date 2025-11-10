import os
import re
import json
from typing import Any, Dict, Optional, Tuple
from openai import OpenAI

_FALLBACK = {"num_pain_points": 0, "pain_points": []}

# replace the old _safe_json with this
def _safe_json(s: Optional[str]) -> Dict[str, Any]:
    if not s:
        return {"num_pain_points": 0, "pain_points": []}

    # 1) direct
    try:
        return json.loads(s)
    except Exception:
        pass

    # 2) pull from fenced code block ```...``` (with or without a language tag)
    fence = re.search(r"```(?:json)?\s*(.*?)```", s, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        block = fence.group(1).strip()
        try:
            return json.loads(block)
        except Exception:
            # fall through to brace-balanced extraction
            s = block  # make the next step work on the block

    # 3) brace-balanced extraction of the first JSON object
    def _extract_first_json_obj(text: str) -> Optional[str]:
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]
        return None

    candidate = _extract_first_json_obj(s)
    if candidate:
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 4) fallback
    return {"num_pain_points": 0, "pain_points": []}

def _build_client(provider: str, *, ollama_base_url: Optional[str], openai_api_key_env: str) -> OpenAI:
    p = provider.lower().strip()
    if p == "ollama":
        if not ollama_base_url:
            raise ValueError("ollama_base_url required for provider='ollama'")
        return OpenAI(base_url=ollama_base_url, api_key="ollama")
    if p == "openai":
        key = os.getenv(openai_api_key_env or "OPENAI_API_KEY")
        if not key:
            raise RuntimeError(f"Missing environment variable {openai_api_key_env or 'OPENAI_API_KEY'}")
        return OpenAI(api_key=key)
    raise ValueError(f"Unknown provider: {provider}")

def generate_json(
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    ollama_base_url: Optional[str] = None,
    openai_api_key_env: str = "OPENAI_API_KEY",
    return_raw: bool = False,
) -> Dict[str, Any] | Tuple[Dict[str, Any], str]:
    """
    temperature=0, seed=1. For OpenAI, try response_format json_object then fall back.
    Safe JSON parsing; on failure returns empty result. If return_raw=True, returns (parsed, raw_text).
    """
    try:
        client = _build_client(provider, ollama_base_url=ollama_base_url, openai_api_key_env=openai_api_key_env)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        base = dict(model=model, messages=messages, temperature=0)

        attempts = []
        if provider.lower() == "openai":
            attempts.append({**base, "response_format": {"type": "json_object"}, "seed": 1})
            attempts.append({**base, "response_format": {"type": "json_object"}})
            attempts.append({**base, "seed": 1})
            attempts.append({**base})
        else:
            attempts.append({**base, "seed": 1})
            attempts.append({**base})

        last_err = None
        for kwargs in attempts:
            try:
                resp = client.chat.completions.create(**kwargs)
                content = (resp.choices[0].message.content or "").strip()
                parsed = _safe_json(content)
                return (parsed, content) if return_raw else parsed
            except Exception as e:
                last_err = e
                continue

        if last_err:
            print(f"[llm_client] attempts failed: {last_err}")
        return (dict(_FALLBACK), "") if return_raw else dict(_FALLBACK)
    except Exception as e:
        print(f"[llm_client] error: {e}")
        return (dict(_FALLBACK), "") if return_raw else dict(_FALLBACK)