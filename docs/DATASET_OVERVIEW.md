# WGU Reddit Analyzer – Dataset Overview

_Last updated: 2025-11-08_

---

## 1. Purpose
Summarizes the database schema used to prepare Reddit data for the LLM benchmarking and classification pipeline.  
This document provides a transparent, public-safe overview of the structured dataset used for analysis.

---

## 2. Core Tables

| Table | Description |
|--------|-------------|
| **posts** | Reddit submissions referencing WGU courses. Columns: `post_id`, `subreddit`, `author`, `title`, `selftext`, `created_utc`, `sentiment`. |
| **comments** | Associated discussion comments. Columns: `comment_id`, `post_id`, `author`, `body`, `created_utc`. |
| **subreddits** | Metadata on monitored subreddits. Columns: `name`, `subscribers`, `active_users`, `snapshot_time`. |

---

## 3. Integration with Pipeline
Data are accessed through:

```
src/wgu_reddit_analyzer/utils/db.py
```

and exported as:

```
data/raw_reddit.jsonl
```

for preprocessing, sampling, and benchmark evaluation.

---

## 4. Notes
All records originate from public Reddit content collected via official APIs.  
Sensitive data, API credentials, and local scheduler configurations are not included in this release.

---

