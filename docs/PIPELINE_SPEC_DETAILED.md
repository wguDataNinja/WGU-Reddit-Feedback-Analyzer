# WGU Reddit Analyzer — Detailed Pipeline Specification

**Generated:** 2026-01-10
**Method:** Code execution trace and database schema analysis
**Authority:** Actual implementation, not intended behavior

---

## Overview

This document specifies the WGU Reddit Analyzer pipeline as verified through code execution paths, database schema inspection, and artifact tracing. All claims are supported by code evidence.

---

## Database Foundation

### Schema Location
`db/WGU-Reddit.db` (SQLite 3)

### Database Statistics (as of verification)
- **Total posts:** 30,730
- **Date range:** 2014-12-28 to 2026-01-04 (Unix timestamps 1419791192 to 1767081623)
- **Active tables:** 10 tables + 8 indexes

### Table Schemas

#### posts
Primary ingestion target for Reddit submissions.

```sql
CREATE TABLE posts (
    post_id VARCHAR NOT NULL PRIMARY KEY,
    subreddit_id VARCHAR NOT NULL,
    username VARCHAR,
    title TEXT NOT NULL,
    selftext TEXT,
    created_utc INTEGER NOT NULL,
    edited_utc INTEGER,
    score INTEGER,
    upvote_ratio FLOAT,
    is_promotional BOOLEAN,
    is_removed BOOLEAN,
    is_deleted BOOLEAN,
    flair VARCHAR,
    post_type VARCHAR,
    num_comments INTEGER,
    url TEXT,
    permalink TEXT,
    extra_metadata JSON,
    captured_at INTEGER,
    matched_course_codes TEXT,
    course_code VARCHAR,
    course_code_count INTEGER,
    vader_compound REAL,
    processed_stage0_at INTEGER,
    FOREIGN KEY(subreddit_id) REFERENCES subreddits(subreddit_id) ON DELETE CASCADE,
    FOREIGN KEY(username) REFERENCES users(username)
);
```

**Indexes:**
- `idx_posts_created_utc ON posts(created_utc)`
- `idx_posts_course_code ON posts(course_code)`
- `idx_posts_vader ON posts(vader_compound)`
- `idx_posts_processed ON posts(processed_stage0_at)`

#### comments
```sql
CREATE TABLE comments (
    comment_id VARCHAR NOT NULL PRIMARY KEY,
    post_id VARCHAR NOT NULL,
    username VARCHAR,
    parent_comment_id VARCHAR,
    body TEXT NOT NULL,
    created_utc INTEGER NOT NULL,
    edited_utc INTEGER,
    score INTEGER,
    is_promotional BOOLEAN,
    is_removed BOOLEAN,
    is_deleted BOOLEAN,
    extra_metadata JSON,
    captured_at INTEGER,
    FOREIGN KEY(post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY(username) REFERENCES users(username) ON DELETE SET NULL,
    FOREIGN KEY(parent_comment_id) REFERENCES comments(comment_id) ON DELETE CASCADE
);
```

**Indexes:**
- `idx_comments_post_id ON comments(post_id)`
- `idx_comments_created_utc ON comments(created_utc)`

#### subreddits
```sql
CREATE TABLE subreddits (
    subreddit_id VARCHAR NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    description TEXT,
    is_nsfw BOOLEAN,
    created_utc INTEGER NOT NULL,
    rules TEXT,
    sidebar_text TEXT
);
```

#### users
```sql
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    karma_comment INTEGER,
    karma_post INTEGER,
    created_utc INTEGER,
    first_captured_at INTEGER,
    last_seen_at INTEGER
);
```

#### run_log
Tracks daily ingestion runs.

```sql
CREATE TABLE run_log (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at INTEGER,
    finished_at INTEGER,
    seeds_read INTEGER,
    posts_attempted INTEGER,
    comments_inserted INTEGER,
    failures INTEGER
);
```

#### posts_keyword, comments_keyword
Specialized tables for keyword-based search (currently unused in main pipeline).

#### subreddit_stats, user_stats
Time-series tracking tables (populated by daily fetchers).

---

## Stage -1: Daily Ingestion (Continuous)

### Purpose
Incremental ingestion of new Reddit posts and comments from configured subreddits.

### Execution Context
- **Scheduler:** launchd (macOS) — **Status: NOT CURRENTLY ACTIVE**
- **Evidence:** Log file exists at `logs/launchd_daily_update.log` (last run: 2025-11-07)
- **Last run result:** FAILED (database file not accessible from launchd context)
- **No active plist found** in `~/Library/LaunchAgents/` or system locations

### Entry Point
```bash
python -m wgu_reddit_analyzer.daily.daily_update
```

**File:** `src/wgu_reddit_analyzer/daily/daily_update.py`

### Orchestration Flow
```
daily_update.py
    ├─ load_env() → loads .env credentials
    ├─ require_reddit_creds() → validates PRAW config
    ├─ fetch_posts() → fetchers/fetch_posts_daily.py
    ├─ fetch_comments() → fetchers/fetch_comments_daily.py
    └─ fetch_subreddits() → fetchers/fetch_subreddits_daily.py
```

### Stage -1A: Posts Fetcher

**File:** `src/wgu_reddit_analyzer/fetchers/fetch_posts_daily.py`

**Input:**
- `data/wgu_subreddits.txt` — newline-delimited subreddit names
- Reddit API via PRAW (`make_reddit()`)
- Database frontier query: `MAX(created_utc)` per subreddit via permalink pattern

**Output:**
- New rows in `posts` table (INSERT OR IGNORE)
- Returns summary dict: `{"stage": "posts", "posts_fetched": int, "failures": int, "duration_sec": float}`

**Algorithm:**
1. Read subreddit list from `data/wgu_subreddits.txt`
2. For each subreddit:
   - Validate access (handle 404/403)
   - Query frontier: latest `created_utc` where `permalink LIKE '%/r/{name}/%'`
   - Fetch up to 1000 posts via `subreddit.new(limit=1000)`
   - Break when `created_utc <= frontier` (reached known territory)
   - Extract fields: `post_id`, `subreddit_id`, `username`, `title`, `selftext`, `created_utc`, `edited_utc`, `score`, `upvote_ratio`, `is_promotional`, `is_removed`, `is_deleted`, `flair`, `post_type`, `num_comments`, `url`, `permalink`, `captured_at`
   - Insert with `INSERT OR IGNORE` (idempotent by `post_id`)

**Promotional Classification:**
```python
"is_promotional": int(not bool(getattr(submission, "is_self", False)))
```
- Non-self posts (link posts) are marked promotional
- Self-posts (text-only) are marked non-promotional

**Frontier Logic:**
```sql
SELECT MAX(created_utc)
FROM posts
WHERE permalink LIKE '%/r/{subreddit_name}/%'
```

### Stage -1B: Comments Fetcher

**File:** `src/wgu_reddit_analyzer/fetchers/fetch_comments_daily.py`

**Input:**
- Posts from last 14 days (`created_utc >= now - 14*86400`)
- Reddit API via PRAW

**Output:**
- New rows in `comments` table
- Returns summary dict

**Algorithm:**
1. Query posts from last 14 days
2. For each post:
   - Fetch submission via `reddit.submission(id=post_id)`
   - Call `submission.comments.replace_more(limit=0)`
   - Extract all top-level and nested comments
   - Insert with `INSERT OR IGNORE`

### Stage -1C: Subreddit Stats Fetcher

**File:** `src/wgu_reddit_analyzer/fetchers/fetch_subreddits_daily.py`

**Input:**
- `data/wgu_subreddits.txt`
- Reddit API

**Output:**
- Updates to `subreddits` table
- New rows in `subreddit_stats` table (time-series)

### Logging

**Log file:** `logs/daily_update.log`

**Log format:**
```
YYYY-MM-DD HH:MM:SS [LEVEL] logger_name: message
```

**Run metadata:** Written to `run_log` table with:
- `started_at`, `finished_at` (Unix timestamps)
- `posts_attempted`, `comments_inserted`, `failures`

---

## Stage 0: Dataset Build

### Purpose
Create a fixed, sentiment-filtered, course-verified corpus from the database.

### Execution Context
**One-time historical build** (artifact committed to repository)

### Entry Point
```bash
python -m wgu_reddit_analyzer.pipeline.run_stage0
```

**Files:**
- `src/wgu_reddit_analyzer/pipeline/run_stage0.py` (orchestrator)
- `src/wgu_reddit_analyzer/pipeline/build_stage0_dataset.py` (logic)

### Lock Mechanism
**File:** `artifacts/stage0_lock.json`

```json
{
  "status": "locked"
}
```

If this file exists with `status="locked"`, Stage 0 will skip rebuild.

### Input
1. **Database:** `db/WGU-Reddit.db` (posts table)
2. **Course list:** `data/course_list_with_college.csv` (CourseCode column)
3. **Base query:**
   ```sql
   SELECT
       p.post_id, p.subreddit_id, s.name AS subreddit_name,
       p.title, p.selftext, p.created_utc, p.score, p.upvote_ratio,
       p.flair, p.post_type, p.num_comments, p.url, p.permalink,
       p.is_promotional, p.is_removed, p.is_deleted,
       p.extra_metadata, p.captured_at, p.vader_compound
   FROM posts AS p
   LEFT JOIN subreddits AS s ON p.subreddit_id = s.subreddit_id
   WHERE
       COALESCE(p.is_deleted, 0) = 0
       AND COALESCE(p.is_removed, 0) = 0
       AND COALESCE(p.is_promotional, 0) = 0
       AND length(trim(COALESCE(p.title, '') || ' ' || COALESCE(p.selftext, ''))) > 0
   ;
   ```

### Filtering Pipeline

#### 1. Structural Filter (SQL)
- `is_deleted = 0`
- `is_removed = 0`
- `is_promotional = 0`
- Non-empty text: `length(trim(title || ' ' || selftext)) > 0`

#### 2. Course Code Filter
**Function:** `filters.filter_posts_by_course_code()`

**Location:** `src/wgu_reddit_analyzer/utils/filters.py`

**Parameters:**
- `exact_match_count=1` — posts must match exactly one course code
- `title_col="title"`
- `text_col="selftext"`
- `out_col="matched_course_codes"`

**Behavior:**
- Regex-based course code extraction from `title + " " + selftext`
- Course codes validated against `data/course_list_with_college.csv`
- Output: `matched_course_codes` column (list of matched codes)
- Adds: `course_code` (first match), `course_code_count` (number of matches)
- **Enforced constraint:** `course_code_count == 1`

#### 3. Sentiment Filter
**Threshold:** `vader_compound < -0.2`

**Computation:**
- Uses VADER (Valence Aware Dictionary and sEntiment Reasoner)
- **Function:** `calculate_vader_sentiment()` from `utils/sentiment_vader.py`
- **Input text:** `title.strip() + " " + selftext.strip()`
- **Output:** Float in range [-1.0, 1.0]
- **Negative bias:** Only posts with compound score < -0.2 are retained

**VADER missing handling:**
- If `vader_compound` column is NULL or non-numeric, recompute from text
- Ensures all Stage 0 rows have valid sentiment scores

### Output

**File:** `artifacts/stage0_filtered_posts.jsonl`

**Format:** JSON Lines (one JSON object per line)

**Schema:**
```json
{
  "post_id": "str",
  "subreddit_id": "str",
  "subreddit_name": "str",
  "title": "str",
  "selftext": "str",
  "created_utc": "int",
  "score": "int",
  "upvote_ratio": "float",
  "flair": "str|null",
  "post_type": "str",
  "num_comments": "float",
  "url": "str",
  "permalink": "str",
  "matched_course_codes": ["str"],
  "course_code": "str",
  "course_code_count": "int",
  "vader_compound": "float",
  "is_promotional": "int",
  "is_removed": "int",
  "is_deleted": "float",
  "extra_metadata": "null",
  "captured_at": "NaN|int"
}
```

**Current corpus size:** 1,103 posts

### Manifest

**File:** `artifacts/runs/<run_id>/manifest.json`

```json
{
  "stage": "stage0",
  "run_id": "stage0_YYYYMMDDTHHMMSSz",
  "timestamp_utc": "ISO 8601",
  "git_commit": "uncommitted-local",
  "script_name": "run_stage0.py",
  "inputs": {
    "db_path": "db/WGU-Reddit.db",
    "course_csv": "data/course_list_with_college.csv"
  },
  "outputs": {
    "stage0_path": "artifacts/stage0_filtered_posts.jsonl",
    "stage0_line_count": 1103
  },
  "constraints": {
    "sentiment": "vader_compound < -0.2",
    "course_code": "exactly one regex-verified course_code per row"
  },
  "counts": {
    "stage0_records_written": 1103
  }
}
```

### Reproducibility Note

**Stage 0 artifact is committed** to the repository. External users do not need to rebuild Stage 0. Re-running Stage 0 with a different database will produce a different corpus, invalidating all downstream counts.

---

## Stage 1: Pain-Point Classification

### Purpose
Classify each post as containing a fixable course-side pain point or not.

### Modes

#### Mode 1A: Full Corpus (Production)

**Entry point:**
```bash
python -m wgu_reddit_analyzer.stage1.run_stage1_full_corpus \
  --model gpt-5-mini \
  --prompt prompts/s1_optimal.txt
```

**File:** `src/wgu_reddit_analyzer/stage1/run_stage1_full_corpus.py`

**Input:**
- `artifacts/stage0_filtered_posts.jsonl` (default)
- Prompt template from `--prompt` (default: `prompts/s1_optimal.txt`)

**Output directory:** `artifacts/stage1/full_corpus/<run_slug>_<timestamp>/`

**Artifacts:**
- `predictions_FULL.csv`
- `raw_io_FULL.jsonl`
- `manifest.json`
- `prompt_used.txt` (or `s1_optimal.txt` or `s1_refined.txt`)

**Schema: predictions_FULL.csv**
```
post_id,course_code,pred_contains_painpoint,root_cause_summary_pred,
pain_point_snippet_pred,confidence_pred,parse_error,schema_error,
used_fallback,llm_failure
```

#### Mode 1B: Benchmark (Evaluation)

**Entry point:**
```bash
python -m wgu_reddit_analyzer.benchmark.run_stage1_benchmark \
  --model gpt-5-mini \
  --prompt prompts/s1_optimal.txt \
  --split DEV \
  --gold-path artifacts/benchmark/gold/gold_labels.csv \
  --candidates-path artifacts/benchmark/DEV_candidates.jsonl
```

**File:** `src/wgu_reddit_analyzer/benchmark/run_stage1_benchmark.py`

**Input:**
- Gold labels: `artifacts/benchmark/gold/gold_labels.csv`
- Candidates: `artifacts/benchmark/DEV_candidates.jsonl` or `TEST_candidates.jsonl`
- Prompt template

**Gold labels schema:**
```
post_id,split,contains_painpoint,course_code
```
- `split ∈ {"DEV", "TEST"}`
- `contains_painpoint ∈ {"y", "n"}`

**Output directory:** `artifacts/benchmark/stage1/runs/<run_slug>_<timestamp>_<run_id>/`

**Artifacts:**
- `predictions.csv`
- `metrics.json`
- `raw_io.jsonl`
- `manifest.json`
- `prompt_used.txt`

**Schema: predictions.csv**
```
post_id,course_code,true_contains_painpoint,pred_contains_painpoint,
root_cause_summary_pred,pain_point_snippet_pred,confidence_pred,
parse_error,schema_error,used_fallback,llm_failure
```

**Schema: metrics.json**
```json
{
  "schema_version": "1.0.0",
  "model_name": "gpt-5-mini",
  "provider": "openai",
  "split": "DEV",
  "run_id": "b1_YYYYMMDDTHHMMSSz",
  "run_slug": "gpt-5-mini_s1_optimal_fulldev",
  "prompt_name": "s1_optimal.txt",
  "prompt_sha256": "hex",
  "num_examples": 100,
  "tp": 45.0,
  "fp": 5.0,
  "fn": 10.0,
  "tn": 40.0,
  "precision": 0.9,
  "recall": 0.818,
  "f1": 0.857,
  "accuracy": 0.85,
  "total_cost_usd": 0.123,
  "total_elapsed_sec_model_calls": 245.6,
  "wallclock_sec": 250.2,
  "avg_elapsed_sec_per_example": 2.456,
  "num_parse_errors": 2,
  "num_schema_errors": 2,
  "num_llm_failures": 0,
  "num_fallbacks": 2
}
```

**Run index:**
- `artifacts/benchmark/stage1_run_index.csv` (append-only log of all runs)

### Classification Schema

**Top-level label:** `contains_painpoint ∈ {"y", "n", "u"}`

- `"y"` — contains a fixable course-side pain point
- `"n"` — does not contain a fixable course-side pain point
- `"u"` — unknown/unusable (parse error, schema error, or LLM failure)

**Fixable course-side pain point definition (from prompts):**
> A post reports a fixable course-side pain point if it describes a persistent, actionable issue arising from course design, content, structure, assessment, tooling, or staffing that could plausibly be addressed by institutional action.

**Error handling:**
- On parse error or expected-format failure:
  - `pred_contains_painpoint = "u"`
  - `confidence_pred = None`
  - `parse_error = True` or `schema_error = True`
  - `used_fallback = True`

### LLM Call Flow

**Module:** `src/wgu_reddit_analyzer/benchmark/stage1_classifier.py`

**Function:** `classify_post(model_name, example, prompt_template, debug)`

**Steps:**
1. Build prompt: `build_prompt(prompt_template, example)`
2. Call LLM: `model_client.generate(model_name, prompt_text, debug)`
3. Parse response: Extract JSON block with fields:
   - `contains_painpoint` (required)
   - `root_cause_summary` (required if "y")
   - `pain_point_snippet` (required if "y")
   - `confidence` (optional)
4. Validate schema
5. Return `Stage1PredictionOutput` and `LlmCallResult`

**Prompt templates:**
- `prompts/s1_zero.txt` — zero-shot
- `prompts/s1_few.txt` — few-shot (with examples)
- `prompts/s1_optimal.txt` — tuned prompt (final version)

**Prompt aliasing:**
- `s1_refined` == `s1_optimal` (same content, different label)

### Cost Tracking

**Per-call cost fields (in raw_io.jsonl):**
```json
{
  "total_cost_usd": 0.001234,
  "elapsed_sec": 2.45,
  "started_at_epoch": 1234567890.123,
  "finished_at_epoch": 1234567892.573
}
```

**Aggregate cost (in metrics.json):**
- `total_cost_usd` — sum of all LLM call costs
- `avg_cost_usd_per_example` — total_cost / num_examples

---

## Stage 2: Pain-Point Preprocessing

### Purpose
Filter Stage 1 predictions to create a clean input for clustering.

### Entry Point
```bash
python -m wgu_reddit_analyzer.stage2.preprocess_painpoints \
  --input-predictions artifacts/stage1/full_corpus/LATEST/predictions_FULL.csv \
  --output-csv artifacts/stage2/painpoints_llm_friendly.csv
```

**File:** `src/wgu_reddit_analyzer/stage2/preprocess_painpoints.py`

### Input
- `artifacts/stage1/full_corpus/LATEST/predictions_FULL.csv` (default)
- Or explicit path via `--input-predictions`

### Filtering Rules (Code-Verified)

**Keep rows where:**
```python
pred_contains_painpoint == "y"
AND parse_error == False
AND schema_error == False
AND llm_failure == False
AND root_cause_summary_pred is not empty
AND pain_point_snippet_pred is not empty
```

**Exclude rows with:**
- Any error flag True
- Empty `root_cause_summary_pred`
- Empty `pain_point_snippet_pred`

### Output

**File:** `artifacts/stage2/painpoints_llm_friendly.csv`

**Schema:**
```
post_id,course_code,root_cause_summary,pain_point_snippet
```

**Field mapping:**
- `root_cause_summary` ← `root_cause_summary_pred`
- `pain_point_snippet` ← `pain_point_snippet_pred`

**Typical size:** ~390 rows (from 1103 Stage 0 posts)

### Manifest

**File:** `artifacts/stage2/manifest.json`

```json
{
  "stage": "stage2_preprocess",
  "input_path": "artifacts/stage1/full_corpus/.../predictions_FULL.csv",
  "output_path": "artifacts/stage2/painpoints_llm_friendly.csv",
  "num_input_rows": 1103,
  "num_output_rows": 390,
  "timestamp_utc": "ISO 8601"
}
```

---

## Stage 2: Course-Level Clustering

### Purpose
Group pain points within each course into thematic clusters using LLM batch clustering.

### Entry Point
```bash
python -m wgu_reddit_analyzer.stage2.run_stage2_clustering \
  --model gpt-5-mini \
  --prompt prompts/s2_cluster_batch.txt \
  --painpoints-csv artifacts/stage2/painpoints_llm_friendly.csv
```

**File:** `src/wgu_reddit_analyzer/stage2/run_stage2_clustering.py`

### Input
1. **Painpoints CSV:** `artifacts/stage2/painpoints_llm_friendly.csv` (default)
2. **Course metadata:** `data/course_list_with_college.csv`
3. **Prompt template:** `prompts/s2_cluster_batch.txt` (default)

### Algorithm

**Per-course processing:**
1. Filter painpoints to single course
2. If < 2 painpoints, skip (no clustering needed)
3. Build batch prompt with all painpoints for course
4. Send to LLM
5. Parse JSON response: list of cluster objects
6. Validate schema
7. Write cluster output

**Prompt structure (s2_cluster_batch.txt):**
- System instructions on clustering criteria
- Input: JSON array of painpoint objects
- Output: JSON array of cluster objects

**Cluster object schema (output):**
```json
{
  "cluster_id": "int",
  "cluster_label": "str (short title)",
  "cluster_summary": "str (detailed description)",
  "post_ids": ["str", ...]
}
```

### Output Directory
`artifacts/stage2/runs/<run_slug>_<timestamp>/`

### Artifacts

**Per-course files:**
- `clusters/<course_code>.json` — cluster definitions (170 files)
- `painpoints_used_<course_code>.jsonl` — input painpoints used (170 files)

**Example: clusters/C949.json**
```json
[
  {
    "cluster_id": 0,
    "cluster_label": "Assessment retake barriers",
    "cluster_summary": "Students report excessive requirements for retake vouchers including multiple practice tests with 90%+ scores and mandatory CertMaster completion.",
    "post_ids": ["1k5qft9", "1k6eaph", "1k6e9jx"]
  },
  {
    "cluster_id": 1,
    "cluster_label": "Exam difficulty mismatch",
    "cluster_summary": "Complaints that assessment questions don't align with course materials or practice tests.",
    "post_ids": ["1k66sct"]
  }
]
```

**Run metadata:**
- `manifest.json`
- `stage2_prompt.txt` (snapshot of prompt used)

### Manifest Schema

```json
{
  "stage2_run_dir": "artifacts/stage2/runs/gpt-5-mini_s2_cluster_full_20251126_080011",
  "stage2_run_slug": "gpt-5-mini_s2_cluster_full",
  "painpoints_csv_path": "artifacts/stage2/painpoints_llm_friendly.csv",
  "course_meta_csv_path": "data/course_list_with_college.csv",
  "cluster_model_name": "gpt-5-mini",
  "cluster_prompt_path": "prompts/s2_cluster_batch.txt",
  "num_courses": 170,
  "total_painpoints": 390,
  "num_cluster_calls": 170,
  "total_cost_usd": 0.097156,
  "wallclock_sec": 1558.22
}
```

### Cluster ID Assignment

**Per-course scope:** Cluster IDs are unique within a course, starting from 0.

**Cross-course:** Cluster IDs may collide across courses (e.g., C949 cluster_id=0 vs C955 cluster_id=0).

**Uniqueness:** `(course_code, cluster_id)` is the unique key.

---

## Stage 3: Preprocessing for Global Clustering

### Purpose
Transform per-course cluster JSONs into a flat CSV for LLM batch processing.

### Entry Point
```bash
python -m wgu_reddit_analyzer.stage3.preprocess_clusters \
  --stage2-run-dir artifacts/stage2/runs/gpt-5-mini_s2_cluster_full_20251126_080011 \
  --out-path artifacts/stage3/preprocessed/gpt-5-mini_s2_cluster_full_20251126_080011/clusters_llm.csv
```

**File:** `src/wgu_reddit_analyzer/stage3/preprocess_clusters.py`

### Input
- `<stage2_run_dir>/clusters/*.json` (170 files)

### Algorithm
1. Read all cluster JSON files
2. Flatten to one row per cluster
3. Add fields: `course_code`, `course_cluster_id`, `cluster_label`, `cluster_summary`, `post_ids` (JSON string)

### Output

**File:** `artifacts/stage3/preprocessed/<stage2_slug>/clusters_llm.csv`

**Schema:**
```
course_code,course_cluster_id,cluster_label,cluster_summary,post_ids
```

**Row count:** ~327 course-level clusters (from 170 courses, 390 painpoints)

---

## Stage 3: Global Cluster Normalization

### Purpose
Map course-level clusters to global issue instances using LLM-based semantic grouping.

### Entry Point
```bash
python -m wgu_reddit_analyzer.stage3.run_stage3_global_clusters \
  --model gpt-5-mini \
  --prompt prompts/s3_normalize_clusters.txt \
  --stage2-run-dir artifacts/stage2/runs/gpt-5-mini_s2_cluster_full_20251126_080011
```

**File:** `src/wgu_reddit_analyzer/stage3/run_stage3_global_clusters.py`

### Input
1. **Preprocessed clusters:** `artifacts/stage3/preprocessed/<stage2_slug>/clusters_llm.csv`
2. **Prompt template:** `prompts/s3_normalize_clusters.txt`
3. **Stage 2 manifest:** For traceability

### Global Issue Families (Schema v1.0.0)

**Hardcoded enum (from `src/wgu_reddit_analyzer/core/schema_definitions.py`):**

```python
GlobalIssueLabel = Literal[
    "assessment_material_misalignment",
    "unclear_or_ambiguous_instructions",
    "course_pacing_or_workload",
    "technology_or_platform_issues",
    "staffing_or_instructor_availability",
    "course_structure_or_navigation",
    "prerequisite_or_readiness_mismatch",
    "other_or_uncategorized",
]
```

**Families are fixed.** Instances are data-driven outputs.

### Algorithm

**Batch normalization:**
1. Read all course-level clusters
2. Send batch to LLM with prompt template
3. Parse JSON response: list of global cluster mappings
4. Validate schema
5. Write outputs

**LLM output schema:**
```json
{
  "global_clusters": [
    {
      "global_cluster_id": "int",
      "global_issue_label": "str (one of 8 families)",
      "global_cluster_title": "str",
      "global_cluster_summary": "str",
      "course_cluster_keys": [
        {
          "course_code": "str",
          "course_cluster_id": "int"
        }
      ]
    }
  ],
  "unassigned_clusters": []
}
```

### Output Directory
`artifacts/stage3/runs/<run_slug>_<timestamp>/`

### Artifacts

**Primary outputs:**
- `global_clusters.json` — global issue instance definitions
- `cluster_global_index.csv` — course cluster → global cluster mapping
- `post_global_index.csv` — post → global cluster mapping

**Supporting files:**
- `manifest.json`
- `stage3_prompt.txt`
- `batches/` — intermediate batch files (if large)

### Schema: global_clusters.json

```json
[
  {
    "global_cluster_id": 0,
    "global_issue_label": "assessment_material_misalignment",
    "global_cluster_title": "Assessment retake barriers and rigid requirements",
    "global_cluster_summary": "Students across multiple courses report excessive requirements for retake vouchers, including mandatory 90%+ practice test scores, CertMaster completion, and screenshot submissions. These requirements are perceived as overly rigid and time-consuming, especially for students who scored close to passing.",
    "course_cluster_keys": [
      {"course_code": "D325", "course_cluster_id": 2},
      {"course_code": "C949", "course_cluster_id": 0},
      {"course_code": "D080", "course_cluster_id": 1}
    ],
    "num_courses": 3,
    "num_painpoints": 8
  }
]
```

**Current size:** ~63 global clusters (from 327 course clusters)

### Schema: cluster_global_index.csv

```
course_code,course_cluster_id,global_cluster_id,global_issue_label,
global_cluster_title,assignment_confidence
```

**Purpose:** Many-to-one mapping from course clusters to global clusters.

**Uniqueness:** Each `(course_code, course_cluster_id)` appears exactly once.

### Schema: post_global_index.csv

```
post_id,course_code,course_cluster_id,global_cluster_id,global_issue_label
```

**Purpose:** Many-to-many mapping from posts to global clusters (posts can appear in multiple course clusters).

### Manifest Schema

```json
{
  "run_id": "gpt-5-mini_s3_global_gpt-5-mini_s2_cluster_full_20251130_084422",
  "stage3_run_dir": "artifacts/stage3/runs/...",
  "source_stage2_run": {
    "run_id": "gpt-5-mini_s2_cluster_full_20251126_080011",
    "stage2_run_dir": "artifacts/stage2/runs/..."
  },
  "global_model_name": "gpt-5-mini",
  "global_prompt_path": "prompts/s3_normalize_clusters.txt",
  "num_input_clusters": 327,
  "num_input_courses": 170,
  "num_global_clusters": 63,
  "num_unassigned_clusters": 0,
  "total_cost_usd": 0.023146,
  "wallclock_sec": 580.46
}
```

---

## Stage 4: Report Generation

### Purpose
Produce analytics tables and summary reports for external consumption.

### Components

#### 4A: Build Analytics Tables

**Entry point:**
```bash
python -m wgu_reddit_analyzer.report_data.build_analytics
```

**File:** `src/wgu_reddit_analyzer/report_data/build_analytics.py`

**Inputs:**
1. `artifacts/stage0_filtered_posts.jsonl`
2. `artifacts/stage2/painpoints_llm_friendly.csv`
3. `artifacts/stage3/runs/<latest>/cluster_global_index.csv`
4. `artifacts/stage3/runs/<latest>/post_global_index.csv`
5. `artifacts/stage3/runs/<latest>/global_clusters.json`
6. `data/course_list_with_college.csv`

**Outputs:**
- `artifacts/report_data/post_master.csv`
- `artifacts/report_data/course_summary.csv`
- `artifacts/report_data/course_cluster_detail.jsonl`
- `artifacts/report_data/global_issues.csv`
- `artifacts/report_data/issue_course_matrix.csv`

**Schema: post_master.csv**
```
post_id,course_code,title,selftext,created_utc,score,upvote_ratio,
permalink,vader_compound,contains_painpoint,root_cause_summary,
pain_point_snippet,global_cluster_ids,global_issue_labels
```

**Schema: course_summary.csv**
```
course_code,course_name,college,num_stage0_posts,num_painpoints,
num_course_clusters,num_global_issues_touched,top_global_issues
```

**Schema: global_issues.csv**
```
global_cluster_id,global_issue_label,global_cluster_title,
global_cluster_summary,num_courses,num_painpoints,affected_courses
```

**Schema: issue_course_matrix.csv**
```
global_cluster_id,global_issue_label,course_code,num_painpoints
```

#### 4B: Build Pipeline Counts

**Entry point:**
```bash
python -m wgu_reddit_analyzer.report_data.build_pipeline_counts
```

**File:** `src/wgu_reddit_analyzer/report_data/build_pipeline_counts.py`

**Inputs:**
- All `report_data/*` tables from 4A
- `artifacts/stage2/painpoints_llm_friendly.csv`

**Outputs:**
- `artifacts/report_data/pipeline_counts_by_course.csv`
- `artifacts/report_data/pipeline_counts_by_college.csv`
- `artifacts/report_data/pipeline_counts_overview.md`

**Schema: pipeline_counts_by_course.csv**
```
course_code,stage0_posts,stage1_painpoints,stage2_clusters,stage3_global_issues
```

**Schema: pipeline_counts_by_college.csv**
```
college,stage0_posts,stage1_painpoints,stage2_clusters,stage3_global_issues
```

**pipeline_counts_overview.md:**
Markdown table summarizing funnel metrics:
- Total posts at each stage
- Retention rates
- Top courses by volume
- Top colleges by volume

#### 4C: Build Overview Reports

**Entry point:**
```bash
python -m wgu_reddit_analyzer.report_data.build_reports
```

**File:** `src/wgu_reddit_analyzer/report_data/build_reports.py`

**Inputs:**
- `artifacts/report_data/course_summary.csv`
- `artifacts/report_data/global_issues.csv`

**Outputs:**
- `artifacts/report_data/courses_overview.csv`
- `artifacts/report_data/issues_overview.csv`

---

## Pipeline Flow Summary

```
[Database: db/WGU-Reddit.db]
    ↓ (daily fetch via launchd — NOT ACTIVE)
    ↓
[30,730 total posts in database]
    ↓ (Stage 0: filters + sentiment + course gating)
    ↓
[1,103 posts] → artifacts/stage0_filtered_posts.jsonl
    ↓ (Stage 1: LLM pain-point classification)
    ↓
[1,103 classified] → artifacts/stage1/full_corpus/.../predictions_FULL.csv
    ↓ (Stage 2 preprocess: filter to "y" only)
    ↓
[~390 painpoints] → artifacts/stage2/painpoints_llm_friendly.csv
    ↓ (Stage 2 clustering: per-course LLM batch clustering)
    ↓
[~327 course clusters across 170 courses]
    ↓ → artifacts/stage2/runs/.../clusters/*.json
    ↓
    ↓ (Stage 3 preprocess: flatten to CSV)
    ↓
[clusters_llm.csv]
    ↓ (Stage 3: global normalization via LLM)
    ↓
[~63 global issue instances] → artifacts/stage3/runs/.../global_clusters.json
    ↓
    ↓ (Stage 4: analytics + reporting)
    ↓
[Report tables] → artifacts/report_data/*.csv, *.jsonl, *.md
```

---

## Launchd Integration (Historical)

### Configuration Status
**INACTIVE** — No active plist found in:
- `~/Library/LaunchAgents/`
- `/Library/LaunchAgents/`
- `/Library/LaunchDaemons/`

### Last Known Execution
**Date:** 2025-11-07 03:00:03
**Result:** FAILED
**Error:** `sqlite3.OperationalError: unable to open database file`

**Root cause:** Database path inaccessible from launchd execution context (likely working directory mismatch).

### Expected Plist Structure (Unverified)

**Label:** `com.wgu.reddit.daily_update` (inferred)

**Expected location:** `~/Library/LaunchAgents/com.wgu.reddit.daily_update.plist`

**Expected schedule:** Daily at 03:00 (inferred from log timestamp)

**Expected program arguments:**
```xml
<key>ProgramArguments</key>
<array>
    <string>/path/to/.venv/bin/python</string>
    <string>-m</string>
    <string>wgu_reddit_analyzer.daily.daily_update</string>
</array>
```

**Expected working directory:**
```xml
<key>WorkingDirectory</key>
<string>/Users/buddy/Desktop/WGU-Reddit</string>
```

**Status:** Plist was removed or never created after 2025-11-07 failures.

---

## Model Registry

### Supported Models

**File:** `src/wgu_reddit_analyzer/benchmark/model_registry.py`

**Registry structure:**
```python
MODEL_REGISTRY = {
    "gpt-5-mini": {
        "provider": "openai",
        "api_model_name": "gpt-4o-mini",
        "supports_json_mode": True
    },
    "gpt-5": {
        "provider": "openai",
        "api_model_name": "gpt-4o",
        "supports_json_mode": True
    },
    "llama3": {
        "provider": "lmstudio",
        "api_model_name": "llama-3.2-3b-instruct",
        "supports_json_mode": False
    },
    "gpt-5-nano": {
        "provider": "openai",
        "api_model_name": "gpt-4o-nano",
        "supports_json_mode": True
    }
}
```

**Lookup function:** `get_model_info(model_name: str) -> ModelInfo`

### LLM Client

**File:** `src/wgu_reddit_analyzer/benchmark/model_client.py`

**Function:** `generate(model_name: str, prompt: str, debug: bool = False) -> str`

**Supported providers:**
- `openai` — via OpenAI Python SDK
- `lmstudio` — via LM Studio local API (OpenAI-compatible)

**JSON mode:**
- Used when `supports_json_mode=True`
- Forces structured JSON output from model

---

## Configuration and Credentials

### Environment Loading

**File:** `src/wgu_reddit_analyzer/utils/config_loader.py`

**Function:** `load_env()`

**Search paths (in order):**
1. `.env` (repository root)
2. `configs/.env`
3. System environment variables

### Required Environment Variables

**For Reddit API (PRAW):**
```
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
```

**For OpenAI:**
```
OPENAI_API_KEY
```

**For LM Studio (local):**
```
LMSTUDIO_BASE_URL  (default: http://localhost:1234/v1)
```

### Validation

**Function:** `require_reddit_creds(config: dict)`

Raises exception if Reddit credentials are missing or invalid.

---

## File Organization

### Source Code
```
src/wgu_reddit_analyzer/
├── benchmark/
│   ├── run_stage1_benchmark.py
│   ├── stage1_classifier.py
│   ├── stage1_types.py
│   ├── model_registry.py
│   └── model_client.py
├── daily/
│   └── daily_update.py
├── fetchers/
│   ├── fetch_posts_daily.py
│   ├── fetch_comments_daily.py
│   └── fetch_subreddits_daily.py
├── pipeline/
│   ├── run_stage0.py
│   └── build_stage0_dataset.py
├── stage1/
│   └── run_stage1_full_corpus.py
├── stage2/
│   ├── preprocess_painpoints.py
│   └── run_stage2_clustering.py
├── stage3/
│   ├── preprocess_clusters.py
│   └── run_stage3_global_clusters.py
├── report_data/
│   ├── build_analytics.py
│   ├── build_pipeline_counts.py
│   └── build_reports.py
├── core/
│   └── schema_definitions.py
└── utils/
    ├── config_loader.py
    ├── db.py
    ├── filters.py
    ├── logging_utils.py
    ├── reddit_client.py
    └── sentiment_vader.py
```

### Artifacts
```
artifacts/
├── stage0_filtered_posts.jsonl          (committed, immutable)
├── stage0_lock.json                      (optional lock file)
├── runs/
│   └── stage0_*/                         (historical run logs)
├── benchmark/
│   ├── gold/
│   │   └── gold_labels.csv
│   ├── DEV_candidates.jsonl              (MISSING)
│   ├── TEST_candidates.jsonl             (MISSING)
│   ├── stage1_panel_DEV.csv
│   ├── stage1_panel_TEST.csv
│   ├── stage1_run_index.csv
│   └── stage1/
│       └── runs/                         (18+ benchmark runs)
├── stage1/
│   └── full_corpus/
│       └── <run_id>/
├── stage2/
│   ├── painpoints_llm_friendly.csv
│   ├── manifest.json
│   └── runs/
│       └── <run_id>/
│           ├── clusters/*.json           (170 files)
│           ├── painpoints_used_*.jsonl   (170 files)
│           ├── manifest.json
│           └── stage2_prompt.txt
├── stage3/
│   ├── preprocessed/
│   │   └── <stage2_slug>/
│   │       └── clusters_llm.csv
│   └── runs/
│       └── <run_id>/
│           ├── global_clusters.json
│           ├── cluster_global_index.csv
│           ├── post_global_index.csv
│           ├── manifest.json
│           └── stage3_prompt.txt
└── report_data/
    ├── post_master.csv
    ├── course_summary.csv
    ├── course_cluster_detail.jsonl
    ├── global_issues.csv
    ├── issue_course_matrix.csv
    ├── pipeline_counts_by_course.csv
    ├── pipeline_counts_by_college.csv
    ├── pipeline_counts_overview.md
    ├── courses_overview.csv
    └── issues_overview.csv
```

### Data
```
data/
├── course_list_with_college.csv          (required by all stages)
└── wgu_subreddits.txt                    (required by daily fetch)
```

### Database
```
db/
└── WGU-Reddit.db                         (SQLite 3, 30,730 posts)
```

### Prompts
```
prompts/
├── s1_zero.txt                           (Stage 1 zero-shot)
├── s1_few.txt                            (Stage 1 few-shot)
├── s1_optimal.txt                        (Stage 1 final, aka s1_refined)
├── s2_cluster_batch.txt                  (Stage 2 clustering)
└── s3_normalize_clusters.txt             (Stage 3 global normalization)
```

---

## Reproducibility

### Committed Artifacts
- `artifacts/stage0_filtered_posts.jsonl` — Stage 0 corpus (1,103 posts)

### Generated Artifacts (Not Committed)
All other artifacts in `artifacts/` are generated at runtime and not version-controlled.

### Re-Running the Pipeline

**Stage 0:**
```bash
# Skip if stage0_lock.json exists with status="locked"
python -m wgu_reddit_analyzer.pipeline.run_stage0
```

**Stage 1:**
```bash
python -m wgu_reddit_analyzer.stage1.run_stage1_full_corpus \
  --model gpt-5-mini \
  --prompt prompts/s1_optimal.txt
```

**Stage 2 Preprocessing:**
```bash
python -m wgu_reddit_analyzer.stage2.preprocess_painpoints
```

**Stage 2 Clustering:**
```bash
python -m wgu_reddit_analyzer.stage2.run_stage2_clustering \
  --model gpt-5-mini \
  --prompt prompts/s2_cluster_batch.txt
```

**Stage 3 Preprocessing:**
```bash
python -m wgu_reddit_analyzer.stage3.preprocess_clusters \
  --stage2-run-dir artifacts/stage2/runs/<latest>
```

**Stage 3 Global Clustering:**
```bash
python -m wgu_reddit_analyzer.stage3.run_stage3_global_clusters \
  --model gpt-5-mini \
  --stage2-run-dir artifacts/stage2/runs/<latest>
```

**Stage 4 Reporting:**
```bash
python -m wgu_reddit_analyzer.report_data.build_analytics
python -m wgu_reddit_analyzer.report_data.build_pipeline_counts
python -m wgu_reddit_analyzer.report_data.build_reports
```

### Determinism Notes

**Non-deterministic components:**
- LLM responses (temperature > 0)
- API call timing and costs

**Deterministic components:**
- Stage 0 filtering rules
- Stage 2 preprocessing rules
- Post ordering (by `created_utc`)

---

## Schema Version

**Current version:** `1.0.0`

**Defined in:** `src/wgu_reddit_analyzer/core/schema_definitions.py`

**Version field appears in:**
- `metrics.json` (Stage 1 benchmark)
- All manifest files

**Global issue families are fixed** in schema v1.0.0:
- `assessment_material_misalignment`
- `unclear_or_ambiguous_instructions`
- `course_pacing_or_workload`
- `technology_or_platform_issues`
- `staffing_or_instructor_availability`
- `course_structure_or_navigation`
- `prerequisite_or_readiness_mismatch`
- `other_or_uncategorized`

**Global issue instances are data-driven** and may vary across runs.

---

## END OF PIPELINE SPECIFICATION
