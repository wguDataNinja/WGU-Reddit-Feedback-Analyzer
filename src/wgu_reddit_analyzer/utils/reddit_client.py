from __future__ import annotations
import praw
from .config_loader import get_config, require_reddit_creds


def make_reddit() -> praw.Reddit:
    """
    Canonical Reddit client for all fetchers.
    """
    cfg = get_config()
    require_reddit_creds(cfg)

    return praw.Reddit(
        client_id=cfg.reddit_client_id,
        client_secret=cfg.reddit_client_secret,
        user_agent=cfg.reddit_user_agent,
    )