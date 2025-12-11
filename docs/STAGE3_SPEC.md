STAGE 3 SPEC  
Cross-Course Meta-Clustering and Global Pain-Point Themes  
Last updated: 2025-11-30

---

# 1. Purpose

Stage 3 merges all **course-level clusters** (from Stage 2) into a smaller number of cross-course **global issue themes**.

It answers:  
**Which root-cause problems recur across WGU courses and programs?**

Consumers include program chairs, curriculum designers, and leadership.

---

# 2. Inputs

From a specific Stage-2 run:

- `artifacts/stage2/runs/<stage2_run_slug>/clusters/*.json`

Each Stage-2 cluster provides:

- `cluster_id`  
- `issue_summary`  
- `num_posts`  
- `course_code`, `course_title` (metadata, not preserved in final global JSON)

Stage 3 also reads:

- the **Stage-2 manifest** (for provenance, including Stage-2 `run_id`)  
- the Stage-3 prompt  
- the preprocessed flattened CSV:  
  `artifacts/stage3/preprocessed/<stage2_run_slug>/clusters_llm.csv`

---

# 3. Responsibilities

Stage 3:

1. Loads all Stage-2 clusters  
2. Normalizes summaries into LLM-friendly units  
3. Merges semantically similar clusters across courses  
4. Assigns each merged group a provisional label + normalized_issue_label + short description  
5. Produces a canonical global JSON with:  
   - `provisional_label`  
   - `normalized_issue_label`  
   - `short_description`  
   - `member_cluster_ids`  
   - internally added counts and `global_cluster_id`  
6. Ensures coverage and exclusivity:  
   - every Stage-2 cluster_id appears *exactly once* in a global_cluster or in `unassigned_clusters`  
   - no duplicates  
   - no silent drops  
   - **if the LLM omits some cluster_ids in a batch, they are treated as unassigned (not errors)**  
7. Writes a Stage-3 manifest with:  
   - `run_id`  
   - complete provenance including `source_stage2_run`

---

# 4. Global Theme Rules

## provisional_label
- lowercase natural-language phrase  
- describes the dominant, **fixable** root cause  
- stable within a run; editable by analysts

Examples:  
- "practice and study materials misaligned with assessments"  
- "ambiguous or incomplete instructions"  
- "inconsistent or unhelpful evaluator feedback"

## normalized_issue_label
- canonical machine-friendly tag  
- must reuse the seeded taxonomy when possible

Examples:  
- `assessment_material_misalignment`  
- `unclear_or_ambiguous_instructions`  
- `missing_or_low_quality_materials`  
- `evaluator_inconsistency_or_poor_feedback`  

**Important:**  
There are typically **fewer normalized labels than global clusters**  
(e.g., 16 normalized labels vs. 63 global clusters).  
One label spans multiple global clusters.

## short_description
One-sentence explanation of the fixable mechanism behind this issue.

Example:  
“Course practice materials do not match the OA’s content or difficulty, leaving students unprepared.”

## member_cluster_ids
List of Stage-2 `cluster_id` values that make up the global cluster.

---

# 5. Assignment Rules

- Each Stage-2 cluster appears **once**:  
  - either inside a global cluster’s membership list  
  - or inside `unassigned_clusters`
- No duplicates  
- No cluster in multiple themes  

## unassigned_clusters used when:
- summary too vague to infer a fixable cause  
- issue is not actionable (pure emotion)  
- the LLM fails to include that cluster in its batch response  

These “omitted” cluster_ids must still be listed in `unassigned_clusters`.  
**This rule changed recently and must be documented.**

Emotions like confusion or frustration are not root causes.

---

# 6. Output Format (Strict)

Canonical JSON:

```json
{
  "global_clusters": [
    {
      "provisional_label": "string",
      "normalized_issue_label": "string",
      "short_description": "string",
      "member_cluster_ids": ["C123_1", "C456_2"]
    }
  ],
  "unassigned_clusters": ["C789_3"]
}
```

Rules:

- sorted by descending `total_num_posts` (added in post-processing)  
- no course_code or course_title in output  
- a normalized_issue_label may appear multiple times across global clusters  
- `unassigned_clusters` collects vague, non-actionable, or LLM-omitted clusters  

Additional internal index files add:

- `global_cluster_id`  
- `total_num_posts`  
- `num_clusters`  
- `num_courses`

These live in `cluster_global_index.csv`.

---

# 7. Workflow

1. Load Stage-2 clusters (JSON)  
2. Load Stage-3 CSV (`clusters_llm.csv`)  
3. Join Stage-2 metadata for weighting: post_ids, num_posts  
4. Sort clusters by impact (largest first)  
5. Batch clusters (default ~60 per batch)  
6. For each batch:  
   - construct strict LLM prompt  
   - call model  
   - parse JSON  
   - enforce exclusivity and coverage **within that batch**  
7. Merge batch outputs:  
   - merge provisional labels  
   - merge normalized labels  
   - unify membership sets  
8. Compute aggregated counts  
9. Write:  
   - global_clusters.json  
   - cluster_global_index.csv  
   - post_global_index.csv  
   - global_clusters_summary.csv (aux only)  
   - prompt  
   - manifest.json

---

# 8. Provenance

Every post is traceable via the full chain:

```
post_id  
  → Stage 1 painpoint  
  → Stage 2 cluster_id  
  → Stage 3 global_cluster_id (and normalized_issue_label)
```

This is captured in two index files:

### cluster_global_index.csv
- one row per Stage-2 cluster_id  
- maps to global_cluster_id  
- carries normalized_issue_label, provisional_label, counts

### post_global_index.csv
- one row per (post_id, cluster_id, global_cluster_id)  
- preserves multi-cluster membership  
- used by Stage-4 to build post_master.csv

### Stage-3 manifest includes:
```
run_id
source_stage2_run: {
    run_id: "<stage2_run_id>",
    stage2_run_dir: "artifacts/stage2/runs/<stage2_run_slug>",
    stage2_run_slug: "<stage2_run_slug>",
    manifest_path: "artifacts/stage2/runs/<stage2_run_slug>/manifest.json"
}
```

Downstream should rely on **run_id**, not path guessing.

---

# 9. Cost and Runtime

For ~300–400 Stage-2 clusters:

- 6–12 LLM batches  
- cost ≈ $0.02–$0.15 depending on model  
- wall time ~3–15 minutes  
- parallelizable by batches

LLM calls may require long timeouts (≈90s) for large batches.

---

# 10. Deliverables

Every Stage-3 run produces:

- **global_clusters.json** (canonical definition)
- **cluster_global_index.csv** (cluster → global mapping)
- **post_global_index.csv** (post → cluster → global)
- `global_clusters_summary.csv` (auxiliary, not used by Stage 4)
- LLM batch request/response logs  
- `stage3_prompt.txt`  
- `manifest.json` (including run_id + source_stage2_run provenance)

Notes:

- `global_clusters.json` is authoritative  
- `global_clusters_summary.csv` is **not consumed** by Stage 4  
- Stage-4 solely uses:  
  - global_clusters.json  
  - cluster_global_index.csv  STAGE 3 SPEC  
Cross-Course Meta-Clustering and Global Pain-Point Themes  
Last updated: 2025-11-30

---

# 1. Purpose

Stage 3 merges all **course-level clusters** (from Stage 2) into a smaller number of cross-course **global issue themes**.

It answers:  
**Which root-cause problems recur across WGU courses and programs?**

Consumers include program chairs, curriculum designers, and leadership.

---

# 2. Inputs

From a specific Stage-2 run:

- `artifacts/stage2/runs/<stage2_run_slug>/clusters/*.json`

Each Stage-2 cluster provides:

- `cluster_id`  
- `issue_summary`  
- `num_posts`  
- `course_code`, `course_title` (metadata, not preserved in final global JSON)

Stage 3 also reads:

- the **Stage-2 manifest** (for provenance, including Stage-2 `run_id`)  
- the Stage-3 prompt  
- the preprocessed flattened CSV:  
  `artifacts/stage3/preprocessed/<stage2_run_slug>/clusters_llm.csv`

---

# 3. Responsibilities

Stage 3:

1. Loads all Stage-2 clusters  
2. Normalizes summaries into LLM-friendly units  
3. Merges semantically similar clusters across courses  
4. Assigns each merged group a provisional label + normalized_issue_label + short description  
5. Produces a canonical global JSON with:  
   - `provisional_label`  
   - `normalized_issue_label`  
   - `short_description`  
   - `member_cluster_ids`  
   - internally added counts and `global_cluster_id`  
6. Ensures coverage and exclusivity:  
   - every Stage-2 cluster_id appears *exactly once* in a global_cluster or in `unassigned_clusters`  
   - no duplicates  
   - no silent drops  
   - **if the LLM omits some cluster_ids in a batch, they are treated as unassigned (not errors)**  
7. Writes a Stage-3 manifest with:  
   - `run_id`  
   - complete provenance including `source_stage2_run`

---

# 4. Global Theme Rules

## provisional_label
- lowercase natural-language phrase  
- describes the dominant, **fixable** root cause  
- stable within a run; editable by analysts

Examples:  
- "practice and study materials misaligned with assessments"  
- "ambiguous or incomplete instructions"  
- "inconsistent or unhelpful evaluator feedback"

## normalized_issue_label
- canonical machine-friendly tag  
- must reuse the seeded taxonomy when possible

Examples:  
- `assessment_material_misalignment`  
- `unclear_or_ambiguous_instructions`  
- `missing_or_low_quality_materials`  
- `evaluator_inconsistency_or_poor_feedback`  

**Important:**  
There are typically **fewer normalized labels than global clusters**  
(e.g., 16 normalized labels vs. 63 global clusters).  
One label spans multiple global clusters.

## short_description
One-sentence explanation of the fixable mechanism behind this issue.

Example:  
“Course practice materials do not match the OA’s content or difficulty, leaving students unprepared.”

## member_cluster_ids
List of Stage-2 `cluster_id` values that make up the global cluster.

---

# 5. Assignment Rules

- Each Stage-2 cluster appears **once**:  
  - either inside a global cluster’s membership list  
  - or inside `unassigned_clusters`
- No duplicates  
- No cluster in multiple themes  

## unassigned_clusters used when:
- summary too vague to infer a fixable cause  
- issue is not actionable (pure emotion)  
- the LLM fails to include that cluster in its batch response  

These “omitted” cluster_ids must still be listed in `unassigned_clusters`.  
**This rule changed recently and must be documented.**

Emotions like confusion or frustration are not root causes.

---

# 6. Output Format (Strict)

Canonical JSON:

```json
{
  "global_clusters": [
    {
      "provisional_label": "string",
      "normalized_issue_label": "string",
      "short_description": "string",
      "member_cluster_ids": ["C123_1", "C456_2"]
    }
  ],
  "unassigned_clusters": ["C789_3"]
}
```

Rules:

- sorted by descending `total_num_posts` (added in post-processing)  
- no course_code or course_title in output  
- a normalized_issue_label may appear multiple times across global clusters  
- `unassigned_clusters` collects vague, non-actionable, or LLM-omitted clusters  

Additional internal index files add:

- `global_cluster_id`  
- `total_num_posts`  
- `num_clusters`  
- `num_courses`

These live in `cluster_global_index.csv`.

---

# 7. Workflow

1. Load Stage-2 clusters (JSON)  
2. Load Stage-3 CSV (`clusters_llm.csv`)  
3. Join Stage-2 metadata for weighting: post_ids, num_posts  
4. Sort clusters by impact (largest first)  
5. Batch clusters (default ~60 per batch)  
6. For each batch:  
   - construct strict LLM prompt  
   - call model  
   - parse JSON  
   - enforce exclusivity and coverage **within that batch**  
7. Merge batch outputs:  
   - merge provisional labels  
   - merge normalized labels  
   - unify membership sets  
8. Compute aggregated counts  
9. Write:  
   - global_clusters.json  
   - cluster_global_index.csv  
   - post_global_index.csv  
   - global_clusters_summary.csv (aux only)  
   - prompt  
   - manifest.json

---

# 8. Provenance

Every post is traceable via the full chain:

```
post_id  
  → Stage 1 painpoint  
  → Stage 2 cluster_id  
  → Stage 3 global_cluster_id (and normalized_issue_label)
```

This is captured in two index files:

### cluster_global_index.csv
- one row per Stage-2 cluster_id  
- maps to global_cluster_id  
- carries normalized_issue_label, provisional_label, counts

### post_global_index.csv
- one row per (post_id, cluster_id, global_cluster_id)  
- preserves multi-cluster membership  
- used by Stage-4 to build post_master.csv

### Stage-3 manifest includes:
```
run_id
source_stage2_run: {
    run_id: "<stage2_run_id>",
    stage2_run_dir: "artifacts/stage2/runs/<stage2_run_slug>",
    stage2_run_slug: "<stage2_run_slug>",
    manifest_path: "artifacts/stage2/runs/<stage2_run_slug>/manifest.json"
}
```

Downstream should rely on **run_id**, not path guessing.

---

# 9. Cost and Runtime

For ~300–400 Stage-2 clusters:

- 6–12 LLM batches  
- cost ≈ $0.02–$0.15 depending on model  
- wall time ~3–15 minutes  
- parallelizable by batches

LLM calls may require long timeouts (≈90s) for large batches.

---

# 10. Deliverables

Every Stage-3 run produces:

- **global_clusters.json** (canonical definition)
- **cluster_global_index.csv** (cluster → global mapping)
- **post_global_index.csv** (post → cluster → global)
- `global_clusters_summary.csv` (auxiliary, not used by Stage 4)
- LLM batch request/response logs  
- `stage3_prompt.txt`  
- `manifest.json` (including run_id + source_stage2_run provenance)

Notes:

- `global_clusters.json` is authoritative  
- `global_clusters_summary.csv` is **not consumed** by Stage 4  
- Stage-4 solely uses:  
  - global_clusters.json  
  - cluster_global_index.csv  
  - post_global_index.csv

These define the cross-course systemic instructional issues for WGU.
  - post_global_index.csv

These define the cross-course systemic instructional issues for WGU.