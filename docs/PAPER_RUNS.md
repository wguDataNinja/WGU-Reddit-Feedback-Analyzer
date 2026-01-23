# PAPER_RUNS.md

This file pins all results reported in the paper.

It lists the exact artifact runs used and the files derived from them. All reported tables and figures trace back to these runs.

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
Repository prompt filenames may differ (e.g., `s1_optimal.txt`). The prompt snapshot stored with the run defines what was executed.

This run defines the complete Stage 1 classification layer used in the paper.

---

### Stage 2 full clustering run (per-course clustering)

- `artifacts/stage2/runs/gpt-5-mini_s2_cluster_full_20251126_080011`
- Total pain points clustered: 390
- Courses clustered: 170

Stage 2 clusters fewer posts than Stage 1 predictions because posts with empty or malformed summaries are dropped during preprocessing.

This run defines all course-level clusters referenced in the paper.

---

### Stage 3 global normalization run

- `artifacts/stage3/runs/gpt-5-mini_s3_global_gpt-5-mini_s2_cluster_full_20251130_084422`
- Global issue instances defined: 63
- Post-to-global issue mappings (`post_global_index.csv` rows): 421
- Courses represented: 170

Authoritative Stage 3 outputs:
- `global_clusters.json`
- `post_global_index.csv`
- `cluster_global_index.csv`

These files define the global issue catalog and mappings used for reporting.

A single post may map to multiple global issue instances by design.

---

### Stage 3 preprocessed summary directory

- `artifacts/stage3/preprocessed/gpt-5-mini_s2_cluster_full_20251126_080011`
- File: `clusters_llm.csv`

The directory name matches the Stage 2 run slug listed above. This is the only preprocessed input consumed by Stage 4 reporting.

---

## Deterministic rebuild commands

The commands below rebuild derived artifacts only.

They do not require LLM access and do not modify pinned runs. All rebuilds assume the artifacts listed above are present.

---

### Rebuild Stage 2 preprocessing from pinned Stage 1 predictions

This command regenerates the Stage 2 preprocessing output using the pinned Stage 1 predictions.

```bash
python -m wgu_reddit_analyzer.stage2.preprocess_painpoints \
  --input-predictions artifacts/stage1/full_corpus/gpt-5-mini_s1_optimal_fullcorpus_20251126_023336/predictions_FULL.csv \
  --output artifacts/stage2/painpoints_llm_friendly.csv \
  --manifest artifacts/stage2/manifest.json
```

Counts reported in the paper reflect post–Stage 0 filtering and the behavior of the pinned runs listed above.
