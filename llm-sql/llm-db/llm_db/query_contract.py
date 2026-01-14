from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

HARD_MAX_LIMIT = 200
DEFAULT_LIMIT = 50


class TemplateID(str, Enum):
    POST_COUNTS = "post_counts"
    TOP_POSTS_SCORE = "top_posts_score"
    TOP_POSTS_COMMENTS = "top_posts_comments"
    POSTS_FILTERED = "posts_filtered"
    POSTS_METADATA = "posts_metadata"


TEMPLATE_ALLOWED_PARAMS: Dict[TemplateID, set[str]] = {
    TemplateID.POST_COUNTS: {
        "course_code",
        "post_type",
        "min_created_utc",
        "max_created_utc",
        "is_removed",
        "is_deleted",
    },
    TemplateID.TOP_POSTS_SCORE: {"limit", "course_code", "min_created_utc"},
    TemplateID.TOP_POSTS_COMMENTS: {"limit", "course_code", "min_created_utc"},
    TemplateID.POSTS_FILTERED: {
        "limit",
        "course_code",
        "post_type",
        "min_created_utc",
        "max_created_utc",
        "is_removed",
        "is_deleted",
    },
    TemplateID.POSTS_METADATA: set(),
}


def enforce_limit(limit: Optional[int]) -> int:
    if limit is None:
        limit = DEFAULT_LIMIT
    if not isinstance(limit, int):
        raise ValueError("limit must be int")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > HARD_MAX_LIMIT:
        raise ValueError(f"limit {limit} exceeds HARD_MAX_LIMIT {HARD_MAX_LIMIT}")
    return limit


@dataclass(frozen=True)
class QuerySpec:
    template_id: TemplateID
    params: Dict[str, Any]

    def validate(self) -> None:
        allowed = TEMPLATE_ALLOWED_PARAMS[self.template_id]
        unknown = set(self.params.keys()) - allowed
        if unknown:
            raise ValueError(f"Unknown params for {self.template_id}: {sorted(unknown)}")
        if "limit" in allowed:
            self.params["limit"] = enforce_limit(self.params.get("limit"))


@dataclass(frozen=True)
class QueryPlan:
    dataset_slug: str
    spec: QuerySpec

    def validate(self) -> None:
        if self.dataset_slug != "posts":
            raise ValueError("only dataset_slug='posts' is supported")
        self.spec.validate()