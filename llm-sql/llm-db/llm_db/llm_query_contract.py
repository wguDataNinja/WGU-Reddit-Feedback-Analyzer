"""
LLM Query Contract: prompt strings and normalization for NL → QueryPlan translation.

This file isolates all LLM-specific "knobs" for Phase 2 query translation.
Changes here do not affect the SQL compiler, storage, or stub translator.

Editable by calibration agent:
- QUERY_TRANSLATION_PROMPT
- QUERY_REPAIR_PROMPT
- normalize_query_plan_data()
"""

from typing import Any, Dict

from .query_contract import TEMPLATE_ALLOWED_PARAMS, TemplateID


# Template ID synonyms for normalization
TEMPLATE_SYNONYMS: Dict[str, str] = {
    "run_counts": "run_item_counts",
    "item_counts": "run_item_counts",
    "counts": "run_item_counts",
    "stats": "run_item_counts",
    "summary": "run_item_counts",
    "how_many": "run_item_counts",
    "top_posters": "top_posters_day",
    "top_authors": "top_posters_day",
    "top_commenters": "top_commenters_day",
    "top_posts": "top_posts_score_day",
    "top_posts_by_score": "top_posts_score_day",
    "items": "items_filtered",
    "filter_items": "items_filtered",
    "metadata": "run_metadata",
    "run_info": "run_metadata",
    "about_the_run": "run_metadata",
}


QUERY_TRANSLATION_PROMPT = """You are a precise assistant that converts natural language queries about Reddit data into structured JSON.

Return ONLY a single JSON object. No markdown. No explanation. No extra text.

You are querying a database that contains posts and comments from Reddit runs. A "run" is a fetch operation identified by run_slug.

CONTEXT VALUES (use these exactly):
- run_slug: "{run_slug}"
- day: {day}
- default limit: {limit}

ALLOWED TEMPLATE IDs (choose exactly ONE):
- "run_item_counts": Get counts of items by type in a run. Params: run_slug (required)
- "top_posters_day": Get top posters by post count. Params: run_slug, limit, day_start_utc, day_end_utc
- "top_commenters_day": Get top commenters by comment count. Params: run_slug, limit, day_start_utc, day_end_utc
- "top_posts_score_day": Get top posts by score. Params: run_slug, limit, day_start_utc, day_end_utc
- "items_filtered": Filter items by type/author/subreddit/time. Params: run_slug, limit, item_type, author, subreddit, created_utc_start, created_utc_end
- "run_metadata": Get run metadata. Params: run_slug

OUTPUT JSON SCHEMA:
{{
  "template_id": "one of the allowed template IDs",
  "params": {{
    "run_slug": "the run_slug provided above (REQUIRED)",
    "limit": integer (use provided limit when template supports it),
    ... other params as needed for the template
  }}
}}

STRICT RULES:
1. ALWAYS include run_slug in params using the exact value provided: "{run_slug}"
2. ALWAYS include limit in params when the template supports it (use {limit} unless user specifies different)
3. If day is provided ("{day}"), include timestamp bounds:
   - For top_posters_day, top_commenters_day, top_posts_score_day: use day_start_utc and day_end_utc
   - For items_filtered: use created_utc_start and created_utc_end
4. Timestamps are Unix epoch integers
5. Do NOT add params that aren't in the allowed list for the template
6. Return ONLY valid JSON, nothing else

INTENT DISAMBIGUATION:
- If the query asks for counts, totals, stats, summary, or "how many", use "run_item_counts".
- If the query asks for metadata, run info, or about the run, use "run_metadata".
- If the query asks to show/list/filter posts or comments, use "items_filtered" and set item_type to "post" or "comment".

TIMESTAMP CONVERSION:
If day = "YYYY-MM-DD", convert to:
- day_start_utc = midnight UTC of that day (e.g., 2026-01-14 → 1736812800)
- day_end_utc = 23:59:59 UTC of that day (e.g., 2026-01-14 → 1736899199)

EXAMPLES:

Query: "top posters of the day"
Response:
{{"template_id":"top_posters_day","params":{{"run_slug":"{run_slug}","limit":{limit}}}}}

Query: "how many posts and comments"
Response:
{{"template_id":"run_item_counts","params":{{"run_slug":"{run_slug}"}}}}

Query: "run stats"
Response:
{{"template_id":"run_item_counts","params":{{"run_slug":"{run_slug}"}}}}

Query: "show me the top 5 posts by score"
Response:
{{"template_id":"top_posts_score_day","params":{{"run_slug":"{run_slug}","limit":5}}}}

Query: "who commented the most"
Response:
{{"template_id":"top_commenters_day","params":{{"run_slug":"{run_slug}","limit":{limit}}}}}

Query: "run metadata"
Response:
{{"template_id":"run_metadata","params":{{"run_slug":"{run_slug}"}}}}

Query: "list posts by user spez"
Response:
{{"template_id":"items_filtered","params":{{"run_slug":"{run_slug}","limit":{limit},"item_type":"post","author":"spez"}}}}

Query: "show all posts"
Response:
{{"template_id":"items_filtered","params":{{"run_slug":"{run_slug}","limit":{limit},"item_type":"post"}}}}

Now translate this query:
Query: "{nl_query}"
Response:
"""


QUERY_REPAIR_PROMPT = """Your previous output was not valid JSON or had invalid fields.

Fix it. Return ONLY a single JSON object. No markdown. No explanation.

CONTEXT VALUES:
- run_slug: "{run_slug}"
- day: {day}
- default limit: {limit}

ALLOWED TEMPLATE IDs:
- "run_item_counts": Params: run_slug
- "top_posters_day": Params: run_slug, limit, day_start_utc, day_end_utc
- "top_commenters_day": Params: run_slug, limit, day_start_utc, day_end_utc
- "top_posts_score_day": Params: run_slug, limit, day_start_utc, day_end_utc
- "items_filtered": Params: run_slug, limit, item_type, author, subreddit, created_utc_start, created_utc_end
- "run_metadata": Params: run_slug

Original query: "{nl_query}"

Your previous output:
{previous_attempt}

Error:
{error}

Return corrected JSON:
"""


def normalize_query_plan_data(
    data: Dict[str, Any],
    run_slug: str,
    default_limit: int = 20,
) -> Dict[str, Any]:
    """
    Apply bounded post-parse normalization to fix common LLM errors.

    This normalizes the raw JSON from the LLM into a structure that can
    be converted to QuerySpec. It does not add any new capabilities.

    Args:
        data: Raw dict parsed from LLM JSON output
        run_slug: The run_slug to ensure is present
        default_limit: Default limit to use if template expects limit

    Returns:
        Normalized dict with template_id and params
    """
    # Ensure top-level structure
    if "template_id" not in data:
        # Try to infer from other fields
        if "params" in data and isinstance(data["params"], dict):
            pass  # Keep looking
        else:
            # Default fallback
            data["template_id"] = "run_item_counts"

    if "params" not in data:
        data["params"] = {}

    # Ensure params is a dict
    if not isinstance(data["params"], dict):
        data["params"] = {}

    # Normalize template_id
    template_id = str(data.get("template_id", "")).lower().strip()

    # Apply synonyms
    if template_id in TEMPLATE_SYNONYMS:
        template_id = TEMPLATE_SYNONYMS[template_id]

    # Validate template_id is known
    valid_ids = {t.value for t in TemplateID}
    if template_id not in valid_ids:
        # Default to run_item_counts for safety
        template_id = "run_item_counts"

    data["template_id"] = template_id

    # Get allowed params for this template
    template_enum = TemplateID(template_id)
    allowed = TEMPLATE_ALLOWED_PARAMS.get(template_enum, set())

    # Build clean params dict
    params = data["params"]
    clean_params: Dict[str, Any] = {}

    # Always include run_slug
    clean_params["run_slug"] = run_slug

    # Coerce and filter params
    for key, value in params.items():
        key_clean = key.lower().strip()

        # Skip if not allowed
        if key_clean not in allowed:
            continue

        # Skip run_slug (we already set it)
        if key_clean == "run_slug":
            continue

        # Coerce types
        if key_clean == "limit":
            try:
                clean_params["limit"] = int(value)
            except (TypeError, ValueError):
                pass
        elif key_clean in ("day_start_utc", "day_end_utc", "created_utc_start", "created_utc_end"):
            try:
                clean_params[key_clean] = int(value)
            except (TypeError, ValueError):
                pass
        elif key_clean in ("item_type", "author", "subreddit"):
            if value is not None:
                clean_params[key_clean] = str(value)
        else:
            clean_params[key_clean] = value

    # Add default limit if template supports it and not provided
    if "limit" in allowed and "limit" not in clean_params:
        clean_params["limit"] = default_limit

    data["params"] = clean_params

    # Remove any extra top-level fields
    return {
        "template_id": data["template_id"],
        "params": data["params"],
    }
