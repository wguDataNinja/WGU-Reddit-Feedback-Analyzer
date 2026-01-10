# WGU Reddit Analyzer – Stage 1 Benchmark Guide

**Version:** 2025-11-22  
**Scope:** Evaluation framework for Stage 1 pain-point detection using LLMs.

---

## 1 · Purpose

This guide defines:

- how Stage 1 LLM classifiers are evaluated  
- how prompts and models are compared  
- how metrics, cost, and latency are computed  
- how DEV and TEST benchmarks are run  
- how error analysis informs prompt selection  

Benchmarks are evaluative and do not define core pipeline guarantees.

---

## 2 · Benchmark Goals

### 2.1 Model comparison

Evaluate `llama3`, `gpt-5-nano`, `gpt-5-mini`, and `gpt-5` across:

- accuracy, precision, recall, F1  
- cost  
- latency  

### 2.2 Prompt comparison

For each model:

- zero-shot baseline (`s1_zero.txt`)  
- few-shot v1 (`s1_few.txt`)  
- final tuned prompt (`s1_optimal.txt`)

In documentation and paper text, *refined* is a narrative alias for the selected prompt.
Executable authority is defined by the prompt snapshot stored with each run.

### 2.3 Schema stability

All models are expected to return outputs that can be normalized into the Stage 1 schema.

The parser is designed to normalize outputs where possible. Parse and schema errors are recorded and surfaced in artifacts rather than prevented.

### 2.4 Prompt promotion and evaluation criteria

Prompt changes are evaluated on the same labeled examples.

Disagreements between a baseline prompt and a candidate prompt are analyzed using McNemar’s test on DEV to assess whether observed differences are statistically meaningful. These results guide prompt selection but are not treated as mechanical acceptance gates.

Core classification metrics, particularly F1, are used to detect regressions. Operational metrics such as cost and latency are recorded for analysis but do not determine selection.

### 2.5 Prompt selection under metric tradeoffs

Prompt refinement does not imply improvement across all metrics.

In practice, tighter prompts often reduce false positives and improve precision while lowering recall. Prompt selection is therefore treated as a multi-objective decision informed by:

- paired statistical testing on DEV  
- balance between precision and recall  
- error and schema stability  
- cost and latency characteristics  

Final selection favors prompts that demonstrate statistically supported improvements without clear regression. The selected prompt is referred to as the *refined* Stage 1 prompt.

---

## 3 · Benchmark Code Layout

**Code:** `src/wgu_reddit_analyzer/benchmark/`

- `stage1_classifier.py`  
- `stage1_types.py`  
- `model_client.py`  
- `run_stage1_benchmark.py`  
- `build_stage1_panel.py`  
- `combine_runs_for_analysis.py`  
- `cost_latency.py`  
- `model_registry.py`  
- `update_run_index.py`  
- `llm_connectivity_check.py`  

**Artifacts:** `artifacts/benchmark/`

- `stage1/runs/`  
- `stage1_run_index.csv`  
- `stage1_panel_DEV.csv`  
- `stage1_panel_TEST.csv`  
- `DEV_candidates.jsonl`  
- `TEST_candidates.jsonl`  
- `gold/gold_labels.csv`  
- `gating/`  

Gating artifacts support comparative analysis and review. They are not authoritative acceptance records.

---

## 4 · Datasets

Two frozen splits are used.

### DEV

- used for prompt iteration  
- used for model comparison  
- used for FP/FN analysis  
- authoritative for guiding prompt selection  

### TEST

- held fixed until prompt selection is complete  
- used for final evaluation only  

`gold_labels.csv` must not change without a dataset version bump.

Only `artifacts/benchmark/gold/gold_labels.csv` is authoritative. Any backups are stored under `artifacts/benchmark/gold/.old`.

---

## 5 · Prompt Benchmarking

**Prompt directory:** `prompts/`

Each benchmark run copies its prompt file into the run directory for reproducibility.
Prompt snapshots inside run directories define executable behavior.

| Prompt | Purpose |
|---|---|
| `s1_zero.txt` | Zero-shot baseline |
| `s1_few.txt` | Few-shot v1 |
| `s1_optimal.txt` | Final tuned prompt (refined) |

Benchmark runs require explicit prompt and model flags. Code defaults are historical and not assumed runnable.

**Runner flag:**
```bash
--prompt prompts/<prompt>.txt
```

___
