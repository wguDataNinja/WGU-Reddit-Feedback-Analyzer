# Pipeline Counts Overview

This document describes the Stage 4 pipeline-count artifacts that summarize data volumes across pipeline stages by course and by college.

These counts are derived **only** from existing Stage 4 report data tables:

- `post_master.csv`
- `course_summary.csv`
- `course_cluster_detail.jsonl`
- `issue_course_matrix.csv`
- `global_issues.csv`

No new LLM calls, thresholds, or filters are introduced. The outputs are deterministic given the Stage 0–3 artifacts.

---

## Artifacts

All files live under `artifacts/report_data/`:

- `pipeline_counts_by_course.csv`
- `pipeline_counts_by_college.csv`
- `pipeline_counts_overview.md`

### `pipeline_counts_by_course.csv`

Grain: **1 row per `course_code`**.

Columns:

- `course_code` – canonical course identifier.
- `course_title` – final course title used for reporting.
- `college` – semicolon-separated list of colleges that own or cross-list the course.

- `stage0_posts` – total number of Stage 0 posts mapped to this course.
- `stage1_painpoints` – number of posts flagged as pain points (`is_pain_point == 1`).
- `stage1_non_painpoints` – number of posts not flagged as pain points.
- `stage1_error_rows` – number of posts with Stage 1 parsing/schema/LLM errors (currently 0 for all courses; retained for future compatibility).

- `stage2_clusters` – number of distinct Stage 2 clusters (`cluster_id`) for this course.
- `stage2_clustered_posts` – number of unique posts that appear in any Stage 2 cluster for this course.
- `stage2_unclustered_painpoints` – `stage1_painpoints - stage2_clustered_posts`, floored at zero.

- `stage3_global_issues_in_course` – number of distinct global issue labels (`normalized_issue_label`) associated with this course.
- `stage3_posts_with_global_issue` – total posts contributing to any global issue for this course (sum of `num_posts` across all `(normalized_issue_label, course_code)` pairs).

### `pipeline_counts_by_college.csv`

Grain: **1 row per college**.

Courses that belong to multiple colleges (via `college_list`) contribute their counts to **each** listed college.

Columns:

- `college` – name of the college.
- `stage0_posts` – sum of `stage0_posts` across all courses in the college.
- `stage1_painpoints` – sum of `stage1_painpoints` across member courses.
- `stage1_non_painpoints` – sum of `stage1_non_painpoints`.
- `stage1_error_rows` – sum of `stage1_error_rows` (currently 0, retained for consistency).
- `stage2_clusters` – sum of `stage2_clusters`.
- `stage2_clustered_posts` – sum of `stage2_clustered_posts`.
- `stage2_unclustered_painpoints` – sum of `stage2_unclustered_painpoints`.
- `stage3_global_issues_in_course` – sum of `stage3_global_issues_in_course`.
- `stage3_posts_with_global_issue` – sum of `stage3_posts_with_global_issue`.

### `pipeline_counts_overview.md`

A short, auto-generated markdown summary that reports:

- total Stage 0 posts
- total Stage 1 pain points
- total Stage 2 clusters
- total Stage 3 global issues
- number of courses with at least one pain point
- number of colleges represented

and includes a compact interpretation note.

---

## Interpretation Guidelines

- The underlying corpus is a **filtered, strongly negative subset** of Reddit posts about WGU courses.
- Counts are designed to show **where data is concentrated** (by course and by college) and which courses have global issues identified.
- These counts are **not** suitable for ranking courses by difficulty, satisfaction, or overall quality. They reflect where students chose to post complaints, not the full population of experiences.
- Differences in counts across courses may be driven by many factors (enrollment, course age, visibility, subreddit norms), not just course design.