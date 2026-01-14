from __future__ import annotations

import re
from typing import Any, Dict

from .query_contract import QueryPlan, QuerySpec, TemplateID


def translate_nl_to_plan(nl_query: str) -> QueryPlan:
    q = (nl_query or "").lower()

    m = re.search(r"\b([cd]\d{3})\b", q)
    course_code = m.group(1).upper() if m else None

    if any(k in q for k in ["metadata", "summary", "stats", "overview"]):
        return QueryPlan(
            dataset_slug="posts",
            spec=QuerySpec(template_id=TemplateID.POSTS_METADATA, params={}),
        )

    if any(k in q for k in ["count", "how many"]):
        params: Dict[str, Any] = {}
        if course_code:
            params["course_code"] = course_code
        return QueryPlan(
            dataset_slug="posts",
            spec=QuerySpec(template_id=TemplateID.POST_COUNTS, params=params),
        )

    if "comment" in q:
        params = {"limit": 20}
        if course_code:
            params["course_code"] = course_code
        return QueryPlan(
            dataset_slug="posts",
            spec=QuerySpec(template_id=TemplateID.TOP_POSTS_COMMENTS, params=params),
        )

    if any(k in q for k in ["top", "best", "score"]):
        params = {"limit": 20}
        if course_code:
            params["course_code"] = course_code
        return QueryPlan(
            dataset_slug="posts",
            spec=QuerySpec(template_id=TemplateID.TOP_POSTS_SCORE, params=params),
        )

    params = {"limit": 20}
    if course_code:
        params["course_code"] = course_code
    return QueryPlan(
        dataset_slug="posts",
        spec=QuerySpec(template_id=TemplateID.POSTS_FILTERED, params=params),
    )