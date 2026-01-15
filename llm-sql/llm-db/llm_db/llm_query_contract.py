"""
Editable by calibration agent:
- QUERY_TRANSLATION_PROMPT
- QUERY_REPAIR_PROMPT
- normalize_query_plan_data()
"""

from __future__ import annotations

from typing import Any, Dict

from .query_contract import TEMPLATE_ALLOWED_PARAMS, TemplateID


DEFAULT_LIMIT = 50


TEMPLATE_ALIASES: Dict[str, str] = {
    "posts_recent": "posts_filtered",
    "recent_posts": "posts_filtered",
    "posts": "posts_filtered",
    "recent": "posts_filtered",
    "list_posts": "posts_filtered",
    "show_posts": "posts_filtered",
    "filtered_posts": "posts_filtered",
    "top_posts": "top_posts_score",
    "top_posts_by_score": "top_posts_score",
    "top_posts_score_day": "top_posts_score",
    "top_by_score": "top_posts_score",
    "most_upvoted": "top_posts_score",
    "top_posts_comments": "top_posts_comments",
    "top_posts_comments_day": "top_posts_comments",
    "most_commented": "top_posts_comments",
    "post_count": "post_counts",
    "post_counts": "post_counts",
    "counts": "post_counts",
    "stats": "post_counts",
    "summary": "post_counts",
    "how_many": "post_counts",
    "metadata": "posts_metadata",
    "posts_metadata": "posts_metadata",
    "run_metadata": "posts_metadata",
    "run_info": "posts_metadata",
    "about_the_run": "posts_metadata",
    "run_item_counts": "post_counts",
    "items_filtered": "posts_filtered",
    "top_posts_score_day": "top_posts_score",
}


QUERY_TRANSLATION_PROMPT = """You are a precise assistant that converts natural language queries about WGU subreddit POSTS into structured JSON.

Return ONLY a single JSON object. No markdown. No explanation. No extra text.

CONTEXT VALUES (use these exactly):
- dataset: "{run_slug}"
- day: {day}
- default limit: {limit}

ALLOWED TEMPLATE IDs (choose exactly ONE):
- "posts_filtered": Show posts (most recent first). Params: course_code (optional), min_created_utc (optional), max_created_utc (optional), is_removed (optional 0/1), is_deleted (optional 0/1), limit (optional).
- "top_posts_score": Top posts by score. Params: course_code (optional), min_created_utc (optional), max_created_utc (optional), is_removed (optional 0/1), is_deleted (optional 0/1), limit (optional).
- "top_posts_comments": Top posts by num_comments. Params: course_code (optional), min_created_utc (optional), max_created_utc (optional), is_removed (optional 0/1), is_deleted (optional 0/1), limit (optional).
- "post_counts": Count posts. Params: course_code (optional), min_created_utc (optional), max_created_utc (optional), is_removed (optional 0/1), is_deleted (optional 0/1).
- "posts_metadata": Dataset metadata. Params: (none)

OUTPUT JSON SCHEMA:
{{
  "template_id": "one of the allowed template IDs",
  "params": {{
    ... template params ...
  }}
}}

STRICT RULES:
1) Only use allowed template IDs.
2) Only use allowed params for that template.
3) If the user asks for "recent posts" or "show posts", use "posts_filtered".
4) If the user asks "top" or "highest score" or "most upvoted", use "top_posts_score".
5) If the user asks "most commented", use "top_posts_comments".
6) If the user asks "how many" or "count", use "post_counts".
7) If a course code like D335/C214 appears, set params.course_code to that exact string.
8) If the user does not specify a limit, include params.limit = {limit} when the template supports it.
9) Do NOT invent templates like "items_filtered" or "run_item_counts".

User request:
{nl_query}
"""


QUERY_REPAIR_PROMPT = """You previously returned invalid JSON for the user's request.

Return ONLY a single JSON object. No markdown. No explanation. No extra text.

CONTEXT VALUES (use these exactly):
- dataset: "{run_slug}"
- day: {day}
- default limit: {limit}

ALLOWED TEMPLATE IDs (choose exactly ONE):
- "posts_filtered"
- "top_posts_score"
- "top_posts_comments"
- "post_counts"
- "posts_metadata"

Allowed params depend on template:
- posts_filtered/top_posts_score/top_posts_comments: course_code, min_created_utc, max_created_utc, is_removed (0/1), is_deleted (0/1), limit
- post_counts: course_code, min_created_utc, max_created_utc, is_removed (0/1), is_deleted (0/1)
- posts_metadata: no params

Previous attempt:
{previous_attempt}

Error:
{error}

User request:
{nl_query}
"""


def _to_int(x: Any) -> int | None:
    if x is None:
        return None
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        try:
            return int(x)
        except Exception:
            return None
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except Exception:
            return None
    return None


def normalize_query_plan_data(data: Dict[str, Any], run_slug: str, default_limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}

    template_id = str(data.get("template_id", "")).strip()
    template_key = template_id.lower().strip()
    if template_key in TEMPLATE_ALIASES:
        template_id = TEMPLATE_ALIASES[template_key]

    if not template_id:
        template_id = "posts_filtered"

    valid_ids = {t.value for t in TemplateID}
    if template_id not in valid_ids:
        template_id = "posts_filtered"

    params = data.get("params", {})
    if not isinstance(params, dict):
        params = {}

    template_enum = TemplateID(template_id)
    allowed = TEMPLATE_ALLOWED_PARAMS.get(template_enum, set())

    clean: Dict[str, Any] = {}

    if "course_code" in allowed and "course_code" in params and params["course_code"] not in (None, ""):
        clean["course_code"] = str(params["course_code"]).strip()

    if "min_created_utc" in allowed:
        v = _to_int(params.get("min_created_utc"))
        if v is not None and v != 0:
            clean["min_created_utc"] = v

    if "max_created_utc" in allowed:
        v = _to_int(params.get("max_created_utc"))
        if v is not None and v != 0:
            clean["max_created_utc"] = v

    if "is_removed" in allowed:
        v = _to_int(params.get("is_removed"))
        if v is not None and v in (0, 1) and v != 0:
            clean["is_removed"] = v

    if "is_deleted" in allowed:
        v = _to_int(params.get("is_deleted"))
        if v is not None and v in (0, 1) and v != 0:
            clean["is_deleted"] = v

    if "limit" in allowed:
        v = _to_int(params.get("limit"))
        if v is None:
            v = int(default_limit)
        if v < 1:
            v = 1
        clean["limit"] = v

    return {"template_id": template_id, "params": clean}


def build_prompt(nl_query: str, run_slug: str, day: str | None, limit: int) -> str:
    day_display = f'"{day}"' if day else "null"
    return QUERY_TRANSLATION_PROMPT.format(nl_query=nl_query, run_slug=run_slug, day=day_display, limit=limit)
