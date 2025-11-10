"""
Canonical fetcher namespace.

Current stages:
- posts
- comments
- subreddits

User-level tracking is intentionally disabled in this pipeline.
"""

from __future__ import annotations

from . import fetch_posts_daily
from . import fetch_comments_daily
from . import fetch_subreddits_daily

__all__ = [
    "fetch_posts_daily",
    "fetch_comments_daily",
    "fetch_subreddits_daily",
]