STAGE 2 SPEC  
Course-Level Pain-Point Clustering  
Last updated: 2025-11-30

---

# 1. Purpose

Stage 2 groups Stage-1 pain-points **within each course** into coherent clusters of shared root causes.

Outputs:

- one JSON cluster file per course  
- painpoint snapshots  
- a Stage-2 manifest including **run_id**  
- these become the inputs for Stage 3 (global cross-course meta-clustering)

**Important:**  
Stage 2 does **not** apply confidence thresholds, soft filters, or ambiguity heuristics.  
It consumes all valid Stage-1 rows with `pred_contains_painpoint = "y"` and no parse/schema/LLM errors.

---

# 2. Inputs

- `artifacts/stage1/full_corpus/<run_slug>/predictions_FULL.csv`  
- `data/course_list_with_college.csv`

Stage 2 reads Stage-1 provenance via the Stage-1 manifest.  
Stage 3 later reads Stage-2 provenance via the Stage-2 manifest’s **run_id**.

---

# 3. Responsibilities

Stage 2:

1. Filter Stage-1 predictions into a LLM-friendly CSV  
2. Group painpoints by `course_code`  
3. Build one LLM prompt per course  
4. Call the model client on each course  
5. Strictly validate outputs  
6. Write:  
   - per-course cluster JSON  
   - per-course painpoint snapshots (`jsonl`)  
   - `stage2_prompt.txt`  
   - `manifest.json` (with `run_id`)

Confidence is preserved only as metadata; it is never used for filtering or weighting.

---

# 4. Preprocessing

Script: `stage2/preprocess_painpoints.py`  
Writes:

- `artifacts/stage2/painpoints_llm_friendly.csv`

Fields:

- `post_id`  
- `course_code`  
- `root_cause_summary`  
- `pain_point_snippet`  
- optional metadata (e.g., `confidence_pred`)

Filtering:

Include rows where:

- `pred_contains_painpoint == "y"`  
- `llm_failure == False`  
- `parse_error == False`  
- `schema_error == False`  
- summary/snippet non-empty

Exclude rows where:

- any error flag True  
- summary/snippet empty  

**Documented behavior (must be explicit):**

> Stage 2 excludes any Stage-1 rows with `parse_error=True` or `schema_error=True`.  
> This leads to occasional Stage-1 → Stage-2 painpoint count discrepancies.

---

# 5. Clustering Runner

Script: `stage2/run_stage2_clustering.py`

Run slug format:  
`<model>_s2_cluster_<corpus_tag>`

Outputs:  
`artifacts/stage2/runs/<run_slug>/`

Files:

- `clusters/<course_code>.json`  
- `painpoints_used_<course_code>.jsonl`  
- `stage2_prompt.txt`  
- `manifest.json`

Manifest includes:

- **run_id** (canonical Stage-2 identifier)  
- num courses  
- total painpoints  
- per-course cost + latency  
- model + prompt  
- paths  
- wallclock + total cost  
- one entry per course

Stage 3 reads this via Stage-3 manifest’s `source_stage2_run`.

---

# 6. Cluster Schema (Authoritative)

Per course:

```json
{
  "courses": [
    {
      "course_code": "CXXX",
      "course_title": "...",
      "total_posts": <unique post count>,
      "clusters": [
        {
          "cluster_id": "CXXX_1",
          "issue_summary": "short root-cause summary",
          "num_posts": <int>,
          "post_ids": ["...", "..."]
        }
      ]
    }
  ]
}
```

Rules:

- **Multi-cluster membership allowed** (must be explicit)  
  A post may appear in multiple clusters for that course.  
  No exclusivity constraint exists.
- `cluster_id` must begin with `course_code`  
- `num_posts = len(post_ids)`  
- `total_posts = unique post_ids across clusters`  
- `issue_summary` non-empty  
- output must be valid JSON only

---

# 7. Validation

`stage2/validate_clusters.py` checks:

- schema correctness  
- prefix-matching cluster_ids  
- accurate `total_posts`  
- all `post_ids` in the LLM-friendly CSV  
- no empty summaries  
- no missing files  
- version-stable behavior

Directory validator cross-checks all clusters vs. `painpoints_llm_friendly.csv`.

---

# 8. Cost and Runtime

Each course → one LLM call.

Typical:

- 5–20 seconds per course  
- full university catalog: 25–35 minutes  
- cost: very low (cents)

All actual cost + timing appear in the Stage-2 manifest.

---

# 9. Reproducibility and Provenance

Stable if:

- Stage-0 input unchanged  
- Stage-1 predictions fixed  
- Stage-2 prompt and code fixed  

Each Stage-2 run stores:

- `run_id`  
- `run_slug`  
- full manifest  
- prompt snapshot  
- per-course inputs and outputs

Downstream should always use **run_id** and the Stage-3 manifest’s:

```json
"source_stage2_run": {
  "run_id": "<stage2_run_id>",
  "stage2_run_dir": "artifacts/stage2/runs/<stage2_run_slug>",
  "stage2_run_slug": "<stage2_run_slug>",
  "manifest_path": "artifacts/stage2/runs/<stage2_run_slug>/manifest.json"
}
```

This provenance chain is authoritative for Stage 3 and Stage 4.