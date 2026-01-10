# PAPER_RUNS.md

This file pins all results reported in the paper.

It records the exact artifact runs used and documents deterministic rebuild procedures.
All reported tables and figures are derived from the runs listed here.

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
Note: repository prompt filenames may differ (for example, `s1_optimal.txt`).  
Executable authority is defined by the prompt snapshot stored with the run.

This run defines the complete Stage 1 classification layer used by the paper.

---

### Stage 2 full clustering run (per-course clustering)

- `artifacts/stage2/runs/gpt-5-mini_s2_cluster_full_20251126_080011`
- Total pain points clustered: 390
- Courses clustered: 170

Stage 2 clusters fewer pain points than Stage 1 predictions because posts with empty or malformed summaries are dropped during preprocessing.

This run defines all course-level pain-point clusters referenced by the paper.

---

### Stage 3 global normalization run

- `artifacts/stage3/runs/gpt-5-mini_s3_global_gpt-5-mini_s2_cluster_full_20251130_084422`
- Global issue instances defined: 63
- Post-to-global issue mappings (`post_global_index.csv` rows): 421
- Courses represented in mappings: 170

Authoritative Stage 3 outputs include:
- `global_clusters.json`
- `post_global_index.csv`
- `cluster_global_index.csv`

These files are co-authoritative and jointly define the global issue catalog and mappings used for reporting.

A single post may map to multiple global issue instances by design.

---

### Stage 3 preprocessed summary directory

- `artifacts/stage3/preprocessed/gpt-5-mini_s2_cluster_full_20251126_080011`
- File: `clusters_llm.csv`

The directory name matches the Stage 2 run slug used for the paper.
This is the only preprocessed directory consumed by Stage 4 reporting.

---

## Deterministic rebuild commands

The commands below rebuild derived artifacts only.

They do not require LLM access and do not modify any pinned runs.
All rebuilds assume artifacts listed above are present.

---

### Rebuild Stage 2 pain-point preprocessing from pinned Stage 1 predictions

This command regenerates the Stage 2 preprocessing output using the pinned Stage 1 predictions.
It is provided as an example; similar commands exist for downstream stages and are documented elsewhere.

```bash
python -m wgu_reddit_analyzer.stage2.preprocess_painpoints \
  --input-predictions artifacts/stage1/full_corpus/gpt-5-mini_s1_optimal_fullcorpus_20251126_023336/predictions_FULL.csv \
  --output artifacts/stage2/painpoints_llm_friendly.csv \
  --manifest artifacts/stage2/manifest.json
```

Counts reported in the paper reflect post–Stage 0 filtering and the behavior of the pinned runs listed above.

___