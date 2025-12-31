# PAPER_RUNS.md

This file pins all paper-reported results.

It records the exact artifact runs used in the paper and provides deterministic rebuild commands.

---

## Pinned runs and inputs

### Stage 1 full-corpus run (pain-point classification)

- `artifacts/stage1/full_corpus/gpt-5-mini_s1_optimal_fullcorpus_20251126_023336`
- `predictions_FULL.csv` rows: 1103
- `pred_contains_painpoint` counts:  
  - `y`: 396  
  - `n`: 700  
  - `u`: 7
- Error flags:  
  - `llm_failure`: 0  
  - `parse_error`: 6  
  - `schema_error`: 6  
  - `used_fallback`: 6

Prompt snapshot inside run directory: `s1_refined.txt`  
Note: repository prompt name may still be `s1_optimal.txt`; the run directory stores the exact snapshot used.

This run defines the complete classification layer used by the paper.

---

### Stage 2 full clustering run (per-course clustering)

- `artifacts/stage2/runs/gpt-5-mini_s2_cluster_full_20251126_080011`
- Total pain points clustered: 390
- Courses clustered: 170

This run defines all course-level pain-point clusters referenced by the paper.

---

### Stage 3 global normalization run (artifact-only)

- `artifacts/stage3/runs/gpt-5-mini_s3_global_gpt-5-mini_s2_cluster_full_20251130_084422`
- Global issue instances defined: 63
- Post-to-global issue mappings (`post_global_index.csv` rows): 421
- Courses represented in mappings: 170

Each row in `post_global_index.csv` represents a mapping between a post and a global issue instance.  
A single post may map to multiple global issues by design.

This run defines the global issue catalog and all post-to-issue mappings used by reporting.

---

### Stage 3 preprocessed summary directory

- `artifacts/stage3/preprocessed/gpt-5-mini_s2_cluster_full_20251126_080011`
- File: `clusters_llm.csv`

This directory name matches the Stage 2 run slug used for the paper and is the only preprocessed directory used by Stage 4 reporting.

---

## Deterministic rebuild commands

This command rebuilds derived artifacts only.  
It does not require LLM access and does not alter any pinned runs.

### Rebuild Stage 2 pain points from pinned Stage 1 predictions

This uses the pinned Stage 1 predictions file directly.

```bash
python -m wgu_reddit_analyzer.stage2.preprocess_painpoints \
  --input-predictions artifacts/stage1/full_corpus/gpt-5-mini_s1_optimal_fullcorpus_20251126_023336/predictions_FULL.csv \
  --output artifacts/stage2/painpoints_llm_friendly.csv \
  --manifest artifacts/stage2/manifest.json