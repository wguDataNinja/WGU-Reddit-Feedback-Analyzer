# WGU Reddit Analyzer — Stage 1 Label Guide

_Last updated: 2025-11-08_

---

## Purpose

This document defines the manual labeling procedure for the Stage 1 benchmark sample of Reddit posts.  
Gold labels are stored in:


`artifacts/benchmark/gold/gold_labels.csv`


These labels are used for model tuning on DEV data, final evaluation on TEST data, and downstream error and clustering analysis.

---

## Scope

Labeling applies only to posts drawn from:

- `artifacts/benchmark/DEV_candidates.jsonl`
- `artifacts/benchmark/TEST_candidates.jsonl`

All posts are:
- 20–600 tokens in length  
- associated with exactly one WGU course code  
- filtered for negative sentiment (VADER compound < −0.2)

---

## Label Schema

Each labeled row contains the following fields:

| Field | Type | Description |
|------|------|-------------|
| post_id | string | Reddit post ID |
| split | DEV or TEST | Dataset split |
| course_code | string | WGU course identifier |
| contains_painpoint | y / n / u | Whether a fixable course-side pain point is present |
| root_cause_summary | string | One-line description of the issue (if y) |
| ambiguity_flag | 0 / 1 | Indicates unclear or borderline cases |
| labeler_id | string | Defaults to `AI1` |
| notes | string | Optional clarifying notes |

---

## Definition of a Pain Point

A pain point is a **fixable, course-side issue** that could plausibly be addressed through changes to course design, instructions, assessment, tooling, staffing, or process.

Mark `y` when a post reports an actionable course-related problem.  
Examples include unclear instructions, contradictory rubric feedback, assessment tooling failures, or support delays.

Mark `n` when the post reflects personal circumstances, general venting, celebration, or non-actionable commentary.

Mark `u` only when it is genuinely unclear whether a course-side issue is present. In most unclear cases, prefer `n` and set the ambiguity flag.

---

## Root Cause Summary

For `y` labels, provide a short, concrete phrase describing the issue, such as:

- “Unclear OA rubric”
- “Proctoring delays”
- “Mentor unresponsive”

Leave this field blank for `n` and `u`.

---

## Ambiguity Flag

Set `ambiguity_flag = 1` if the post could reasonably be labeled differently due to missing context, sarcasm, or mixed causes.  
Set to `0` when the decision is clear.

This flag is used to analyze edge cases and is excluded from metric calculations.

---

## Operational Notes

Labeling is performed using:

```bash
python -m wgu_reddit_analyzer.labeling.label_posts
```

The labeling tool:
- skips posts that are already labeled,
- processes posts in deterministic order (DEV → TEST → course → post_id),
- writes results incrementally after each label.

Once reviewed and verified, `gold_labels.csv` is treated as locked for benchmarking.


