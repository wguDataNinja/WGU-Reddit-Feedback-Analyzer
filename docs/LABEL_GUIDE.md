# WGU Reddit Analyzer – Stage 1C Label Guide

_Last updated: 2025-11-08_

---

## Purpose
Defines a clear and minimal framework for manual labeling of the Stage 1B benchmark sample (≈200 posts).  
Gold labels are saved to:

```
artifacts/benchmark/gold/gold_labels.csv
```

These labels support:
- Model tuning (**DEV**)  
- Final evaluation (**TEST**)  
- Root-cause clustering in Stage 2  

---

## Scope
**Input posts:**  
- Source files:
  - `artifacts/benchmark/DEV_candidates.jsonl`
  - `artifacts/benchmark/TEST_candidates.jsonl`
- 20–600 tokens each  
- Exactly one `course_code`  
- Negative sentiment (VADER < −0.2)

---

## Schema (8 Fields)

| Field | Type | Description |
|--------|------|-------------|
| **post_id** | str | Reddit post ID |
| **split** | DEV / TEST | Source split |
| **course_code** | str | WGU course identifier |
| **contains_painpoint** | y / n / u | Student pain point present |
| **root_cause_summary** | str | One-line issue summary (if y) |
| **ambiguity_flag** | 0 / 1 | 1 = unclear or edge case |
| **labeler_id** | str | Default `AI1` |
| **notes** | str | Optional free-text note |

---

## Definition of a Pain Point
A **pain point** is a fixable, course-related friction that WGU designers or instructors could address.  
It is *not* general venting or personal circumstance.

**Mark y** when the post reports an actionable course-side problem (design, clarity, grading, pacing, support, or process).

*Examples:*  
- “Rubric feedback contradicts instructions.”  
- “Examity kept freezing during OA.”  
- “Unclear citation rules in AFT2.”  

**Mark n** when the issue is personal or external (alarm, internet, family, motivation) or general chatter.  
*Example:* “Finally passed C214!”  

**Mark u** only if the relation to course issues is uncertain.  
*Example:* “Failed OA again, not sure why.”  
(Otherwise treat as n and set `ambiguity_flag = 1` if unclear.)

---

## root_cause_summary
Short, concrete phrase for the course-side issue.  
Examples:  
- “Unclear OA rubric”  
- “Proctoring delays”  
- “Mentor unresponsive”  

Leave blank for `n` or `u`.

---

## ambiguity_flag
Use `1` if the case could reasonably be labeled differently (sarcasm, mixed causes, missing context).  
`0` = clear decision.  
This flag helps identify edge cases for LLM error analysis.

---

## notes (optional)
Brief clarifications, observations, or patterns.  
Leave empty to skip.

---

## Operational Notes
- Run with:  
  ```bash
  python -m wgu_reddit_analyzer.labeling.label_posts
  ```
- Skips already-labeled posts and resumes safely.  
- Writes after each label; deterministic order (DEV → TEST → course → post_id).  
- Once verified, `gold_labels.csv` is locked for benchmarking.

---

## Example Decision
> “I reworded UPs and EPs and sent back for resubmission. Is it due to not citing? Help!”

→ `y`  **root_cause_summary:** “Unclear citation requirements for AFT2 Task 1.”  
→ `ambiguity_flag:` 0  
→ `notes:` (blank)

---

