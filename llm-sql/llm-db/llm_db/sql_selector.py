from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .query_contract import HARD_MAX_LIMIT, QueryPlan, QuerySpec, TemplateID, enforce_limit


@dataclass(frozen=True)
class CompiledQuery:
    template_id: TemplateID
    sql: str
    params: Tuple[Any, ...]
    max_rows: int


def _coerce_bool01(v: Any) -> int:
    if v is True:
        return 1
    if v is False:
        return 0
    if isinstance(v, int) and v in (0, 1):
        return v
    raise ValueError("bool param must be 0/1")


def _base_where(params: Dict[str, Any]) -> Tuple[str, Tuple[Any, ...]]:
    parts = ["1=1"]
    out: list[Any] = []

    if params.get("course_code"):
        parts.append("course_code = ?")
        out.append(params["course_code"])

    if params.get("post_type"):
        parts.append("post_type = ?")
        out.append(params["post_type"])

    if params.get("min_created_utc") is not None:
        parts.append("created_utc >= ?")
        out.append(int(params["min_created_utc"]))

    if params.get("max_created_utc") is not None:
        parts.append("created_utc <= ?")
        out.append(int(params["max_created_utc"]))

    if params.get("is_removed") is not None:
        parts.append("is_removed = ?")
        out.append(_coerce_bool01(params["is_removed"]))
    else:
        parts.append("is_removed = 0")

    if params.get("is_deleted") is not None:
        parts.append("is_deleted = ?")
        out.append(_coerce_bool01(params["is_deleted"]))
    else:
        parts.append("is_deleted = 0")

    return " AND ".join(parts), tuple(out)


def _gen_post_counts(params: Dict[str, Any]):
    where, wparams = _base_where(params)
    sql = f"""
SELECT COUNT(*) AS posts_count
FROM posts
WHERE {where}
"""
    return sql, wparams, 1


def _gen_top_posts_score(params: Dict[str, Any]):
    limit = enforce_limit(params.get("limit"))
    where, wparams = _base_where(params)
    sql = f"""
SELECT post_id, title, score, num_comments, created_utc
FROM posts
WHERE {where}
ORDER BY score DESC, post_id ASC
LIMIT ?
"""
    return sql, wparams + (limit,), limit


def _gen_top_posts_comments(params: Dict[str, Any]):
    limit = enforce_limit(params.get("limit"))
    where, wparams = _base_where(params)
    sql = f"""
SELECT post_id, title, score, num_comments, created_utc
FROM posts
WHERE {where}
ORDER BY num_comments DESC, post_id ASC
LIMIT ?
"""
    return sql, wparams + (limit,), limit


def _gen_posts_filtered(params: Dict[str, Any]):
    limit = enforce_limit(params.get("limit"))
    where, wparams = _base_where(params)
    sql = f"""
SELECT post_id, title, score, num_comments, created_utc
FROM posts
WHERE {where}
ORDER BY created_utc DESC, post_id ASC
LIMIT ?
"""
    return sql, wparams + (limit,), limit


def _gen_posts_metadata(params: Dict[str, Any]):
    sql = """
SELECT
  COUNT(*) AS posts_count,
  MIN(created_utc) AS min_created_utc,
  MAX(created_utc) AS max_created_utc,
  MIN(score) AS min_score,
  MAX(score) AS max_score,
  MIN(num_comments) AS min_num_comments,
  MAX(num_comments) AS max_num_comments
FROM posts
"""
    return sql, (), 1


_TEMPLATE_GENERATORS = {
    TemplateID.POST_COUNTS: _gen_post_counts,
    TemplateID.TOP_POSTS_SCORE: _gen_top_posts_score,
    TemplateID.TOP_POSTS_COMMENTS: _gen_top_posts_comments,
    TemplateID.POSTS_FILTERED: _gen_posts_filtered,
    TemplateID.POSTS_METADATA: _gen_posts_metadata,
}


def compile_query(spec: QuerySpec) -> CompiledQuery:
    spec.validate()
    gen = _TEMPLATE_GENERATORS[spec.template_id]
    sql, params, max_rows = gen(spec.params)
    return CompiledQuery(
        template_id=spec.template_id,
        sql=sql,
        params=params,
        max_rows=min(max_rows, HARD_MAX_LIMIT),
    )


def compile_plan(plan: QueryPlan) -> CompiledQuery:
    plan.validate()
    return compile_query(plan.spec)