"""
LLM Query Translation: converts natural language to QueryPlan JSON.

Responsibilities:
- Translate natural language → QueryPlan JSON
- Strict JSON output only
- One retry on parse/validation failure
- No execution or SQL generation logic

Optional tracing (for calibration / Claude Code):
- If REDDIT_QUERY_LLM_TRACE_DIR is set, writes JSON trace files
- Tag is taken from REDDIT_QUERY_LLM_TRACE_TAG

LLM contract knobs (prompts, normalization) are in llm_query_contract.py.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import ollama

from .llm_query_contract import (
    QUERY_TRANSLATION_PROMPT,
    QUERY_REPAIR_PROMPT,
    normalize_query_plan_data,
)
from .query_contract import (
    QueryPlan,
    QuerySpec,
    TemplateID,
    enforce_limit,
)


Provider = Literal["llama3", "gpt"]


def _debug_print_raw(provider: str, content: str) -> None:
    """Print raw LLM output for debugging."""
    if os.environ.get("REDDIT_QUERY_LLM_DEBUG") == "1":
        print(f"\n--- QUERY LLM RAW OUTPUT ({provider}) ---", file=sys.stderr)
        print(content, file=sys.stderr)
        print("--- END QUERY LLM RAW OUTPUT ---\n", file=sys.stderr)


def _maybe_write_trace(tag: str, provider: str, model: str, prompt: str, raw: str) -> None:
    """Write trace file if REDDIT_QUERY_LLM_TRACE_DIR is set."""
    trace_dir = os.environ.get("REDDIT_QUERY_LLM_TRACE_DIR")
    if not trace_dir:
        return

    p = Path(trace_dir)
    p.mkdir(parents=True, exist_ok=True)

    safe_tag = re.sub(r"[^a-zA-Z0-9_.-]+", "_", (tag or "untagged")).strip("_")
    ts = int(time.time() * 1000)

    out = {
        "ts_ms": ts,
        "tag": safe_tag,
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "raw": raw,
    }
    (p / f"query_{safe_tag}.{ts}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))


def _call_ollama(prompt: str, model: str = "llama3") -> str:
    """Call Ollama LLM with the given prompt."""
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        options={
            "temperature": 0.0,  # Deterministic
            "num_predict": 500,  # Limit output length
        },
    )
    content = response["message"]["content"]
    _debug_print_raw("ollama", content)
    _maybe_write_trace(
        os.environ.get("REDDIT_QUERY_LLM_TRACE_TAG", ""),
        "ollama", model, prompt, content
    )
    return content


def _call_gpt(prompt: str, model: str = "gpt-5-nano") -> str:
    """Call OpenAI GPT with the given prompt."""
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package not installed. Install with: pip install openai")

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for --llm gpt")

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,  # Deterministic
        max_tokens=500,
    )
    content = response.choices[0].message.content
    _debug_print_raw("gpt", content)
    _maybe_write_trace(
        os.environ.get("REDDIT_QUERY_LLM_TRACE_TAG", ""),
        "gpt", model, prompt, content
    )
    return content


def _extract_json_obj(text: str) -> str:
    """
    Extract a JSON object from LLM output.
    Handles code fences, leading commentary, and extra trailing text.
    """
    t = (text or "").strip()

    # Strip code fences
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()

    # Broadest {...} slice
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start : end + 1].strip()

    return t


def _parse_day_to_timestamps(day: Optional[str]) -> tuple:
    """
    Convert day string to UTC timestamp bounds.

    Args:
        day: Date string in YYYY-MM-DD format or None

    Returns:
        Tuple of (day_start_utc, day_end_utc) as ints, or (None, None)
    """
    if not day:
        return (None, None)

    try:
        dt = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return (None, None)

    start = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=timezone.utc)

    return (int(start.timestamp()), int(end.timestamp()))


def translate_to_query_plan(
    nl_query: str,
    run_slug: str,
    day: Optional[str] = None,
    limit: int = 20,
    provider: Provider = "llama3",
    gpt_model: str = "gpt-5-nano",
) -> QueryPlan:
    """
    Translate natural language query to QueryPlan using LLM.

    Args:
        nl_query: Natural language query string
        run_slug: Run slug to query against
        day: Optional day filter (YYYY-MM-DD)
        limit: Default limit for results
        provider: LLM provider ("llama3" or "gpt")
        gpt_model: GPT model to use if provider is "gpt"

    Returns:
        QueryPlan ready for SQL compilation

    Raises:
        ValueError: If translation fails after retry
    """
    effective_limit = enforce_limit(limit)

    # Format day for prompt
    day_display = f'"{day}"' if day else "null"

    # Build prompt
    prompt = QUERY_TRANSLATION_PROMPT.format(
        nl_query=nl_query,
        run_slug=run_slug,
        day=day_display,
        limit=effective_limit,
    )

    # Call LLM
    if provider == "llama3":
        raw = _call_ollama(prompt)
    elif provider == "gpt":
        raw = _call_gpt(prompt, gpt_model)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Extract and parse JSON
    json_text = _extract_json_obj(raw)

    try:
        data = json.loads(json_text)
        data = normalize_query_plan_data(data, run_slug, effective_limit)
        plan = _data_to_query_plan(data, nl_query, run_slug, day, effective_limit)
        plan.validate()
        return plan
    except Exception as first_error:
        # Retry with repair prompt
        repair_prompt = QUERY_REPAIR_PROMPT.format(
            nl_query=nl_query,
            run_slug=run_slug,
            day=day_display,
            limit=effective_limit,
            previous_attempt=raw,
            error=str(first_error),
        )

        if provider == "llama3":
            raw2 = _call_ollama(repair_prompt)
        else:
            raw2 = _call_gpt(repair_prompt, gpt_model)

        json_text2 = _extract_json_obj(raw2)

        try:
            data2 = json.loads(json_text2)
            data2 = normalize_query_plan_data(data2, run_slug, effective_limit)
            plan2 = _data_to_query_plan(data2, nl_query, run_slug, day, effective_limit)
            plan2.validate()
            return plan2
        except Exception as second_error:
            raise ValueError(
                f"Failed to translate query after retry.\n"
                f"Original error: {first_error}\n"
                f"Retry error: {second_error}\n"
                f"Last raw output: {raw2}\n"
                f"Last extracted JSON: {json_text2}"
            )


def _data_to_query_plan(
    data: dict,
    nl_query: str,
    run_slug: str,
    day: Optional[str],
    limit: int,
) -> QueryPlan:
    """
    Convert normalized dict to QueryPlan.

    Args:
        data: Normalized dict with template_id and params
        nl_query: Original natural language query
        run_slug: Run slug
        day: Day filter (for adding timestamps if LLM didn't)
        limit: Default limit

    Returns:
        QueryPlan object
    """
    template_id_str = data["template_id"]
    params = data["params"]

    # Ensure template_id is valid enum
    template_id = TemplateID(template_id_str)

    # If day was provided but timestamps weren't added by LLM, add them
    if day:
        day_start, day_end = _parse_day_to_timestamps(day)
        if day_start is not None:
            # For *_day templates
            if template_id in (
                TemplateID.TOP_POSTERS_DAY,
                TemplateID.TOP_COMMENTERS_DAY,
                TemplateID.TOP_POSTS_SCORE_DAY,
            ):
                if "day_start_utc" not in params:
                    params["day_start_utc"] = day_start
                if "day_end_utc" not in params:
                    params["day_end_utc"] = day_end
            # For items_filtered
            elif template_id == TemplateID.ITEMS_FILTERED:
                if "created_utc_start" not in params:
                    params["created_utc_start"] = day_start
                if "created_utc_end" not in params:
                    params["created_utc_end"] = day_end

    # Create QuerySpec
    spec = QuerySpec(template_id=template_id, params=params)

    # Create QueryPlan
    # Create QueryPlan
    return QueryPlan(
        dataset_slug=run_slug,
        spec=spec,
    )


def translate_nl_to_plan_llm(nl_query: str, model: str = "llama3:latest", *, limit: int | None = None, day: str | None = None, run_slug: str = "posts"):
    provider = "llama3"
    gpt_model = "gpt-5-nano"
    if model.startswith("gpt"):
        provider = "gpt"
        gpt_model = model

    plan = translate_to_query_plan(
        nl_query,
        run_slug=run_slug,
        day=day,
        limit=limit if limit is not None else 50,
        provider=provider,
        gpt_model=gpt_model,
    )

    return plan, None
