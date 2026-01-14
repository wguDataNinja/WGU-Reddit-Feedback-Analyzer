# reddit_fetcher/fetcher.py

from typing import List, Dict, Any, Optional
from .reddit_client import make_reddit


def fetch_user_posts(username: str, limit: int) -> List[Dict[str, Any]]:
    reddit = make_reddit()
    user = reddit.redditor(username)

    results: List[Dict[str, Any]] = []
    for submission in user.submissions.new(limit=limit):
        results.append(
            {
                "id": submission.id,
                "title": submission.title,
                "selftext": submission.selftext,
                "subreddit": submission.subreddit.display_name,
                "score": submission.score,
                "created_utc": float(submission.created_utc or 0.0),
                "num_comments": int(submission.num_comments or 0),
                "permalink": "https://www.reddit.com" + submission.permalink,
            }
        )
    return results


def fetch_subreddit_posts(subreddit_name: str, sort: str, limit: int) -> List[Dict[str, Any]]:
    reddit = make_reddit()
    subreddit = reddit.subreddit(subreddit_name)

    if sort == "new":
        iterator = subreddit.new(limit=limit)
    elif sort == "hot":
        iterator = subreddit.hot(limit=limit)
    elif sort == "top":
        iterator = subreddit.top(limit=limit)
    else:
        raise ValueError(f"Unsupported sort: {sort}")

    results: List[Dict[str, Any]] = []
    for submission in iterator:
        results.append(
            {
                "id": submission.id,
                "title": submission.title,
                "selftext": submission.selftext,
                "author": getattr(submission.author, "name", None),
                "score": submission.score,
                "created_utc": float(submission.created_utc or 0.0),
                "num_comments": int(submission.num_comments or 0),
                "permalink": "https://www.reddit.com" + submission.permalink,
            }
        )
    return results


def fetch_subreddit_comments(subreddit_name: str, limit: int) -> List[Dict[str, Any]]:
    reddit = make_reddit()
    subreddit = reddit.subreddit(subreddit_name)

    results: List[Dict[str, Any]] = []
    for c in subreddit.comments(limit=limit):
        # c.link_id is like "t3_<id>", c.parent_id like "t1_<id>" or "t3_<id>"
        results.append(
            {
                "id": c.id,
                "subreddit": c.subreddit.display_name,
                "author": getattr(c.author, "name", None),
                "body": getattr(c, "body", "") or "",
                "score": int(getattr(c, "score", 0) or 0),
                "created_utc": float(getattr(c, "created_utc", 0.0) or 0.0),
                "link_id": getattr(c, "link_id", None),
                "parent_id": getattr(c, "parent_id", None),
                "permalink": "https://www.reddit.com" + (getattr(c, "permalink", "") or ""),
            }
        )
    return results


def fetch_subreddit_about(subreddit_name: str) -> Dict[str, Any]:
    reddit = make_reddit()
    s = reddit.subreddit(subreddit_name)

    return {
        "name": s.display_name,
        "title": getattr(s, "title", "") or "",
        "public_description": getattr(s, "public_description", "") or "",
        "description": getattr(s, "description", "") or "",
        "subscribers": int(getattr(s, "subscribers", 0) or 0),
        "active_user_count": int(getattr(s, "active_user_count", 0) or 0),
        "created_utc": float(getattr(s, "created_utc", 0.0) or 0.0),
        "over18": bool(getattr(s, "over18", False)),
        "url": "https://www.reddit.com" + (getattr(s, "url", "") or ""),
    }


from reddit_fetcher.limits import MAX_REPLACE_MORE_LIMIT, MAX_COMMENT_DEPTH

def fetch_submission_comments(
    submission_id: str,
    replace_more_limit: int,
    max_depth: int,
) -> List[Dict[str, Any]]:
    """
    Fetch comments with bounded expansion.
    - replace_more_limit: passed to submission.comments.replace_more(limit=...)
    - max_depth: how deep to traverse replies (0 = none, 1 = top-level only, etc.)
    """

    if replace_more_limit is None or max_depth is None:
        raise ValueError("replace_more_limit and max_depth are required")

    if not isinstance(replace_more_limit, int) or not isinstance(max_depth, int):
        raise ValueError("replace_more_limit and max_depth must be integers")

    if replace_more_limit < 0 or replace_more_limit > MAX_REPLACE_MORE_LIMIT:
        raise ValueError(f"replace_more_limit out of range (0..{MAX_REPLACE_MORE_LIMIT})")

    if max_depth <= 0 or max_depth > MAX_COMMENT_DEPTH:
        raise ValueError(f"max_depth out of range (1..{MAX_COMMENT_DEPTH})")
    reddit = make_reddit()
    submission = reddit.submission(id=submission_id)

    # Expand MoreComments in a bounded way
    submission.comments.replace_more(limit=replace_more_limit)

    results: List[Dict[str, Any]] = []

    def walk(node, depth: int) -> None:
        if depth > max_depth:
            return

        body = getattr(node, "body", None)
        if body is None:
            return

        results.append(
            {
                "id": node.id,
                "submission_id": submission.id,
                "subreddit": submission.subreddit.display_name,
                "author": getattr(node.author, "name", None),
                "body": body or "",
                "score": int(getattr(node, "score", 0) or 0),
                "created_utc": float(getattr(node, "created_utc", 0.0) or 0.0),
                "link_id": getattr(node, "link_id", None),
                "parent_id": getattr(node, "parent_id", None),
                "depth": depth,
                "permalink": "https://www.reddit.com" + (getattr(node, "permalink", "") or ""),
            }
        )

        if depth == max_depth:
            return

        for reply in getattr(node, "replies", []):
            walk(reply, depth + 1)

    for top in submission.comments:
        walk(top, 1)

    return results