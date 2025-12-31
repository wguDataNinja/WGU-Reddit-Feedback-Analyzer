# WGU Reddit Analyzer – Stage 1 Benchmark Guide

**Version:** 2025-11-22  
**Scope:** Full evaluation pipeline for Stage-1 pain-point detection using LLMs.

---

## 1 · Purpose

This guide defines:

- how Stage-1 LLM classifiers are evaluated  
- how prompts and models are compared  
- how metrics, cost, and latency are computed  
- how DEV and TEST benchmarks are run  
- how FP/FN analysis drives prompt optimization  

---

## 2 · Benchmark Goals

### 2.1 Model comparison

Evaluate `llama3`, `gpt-5-nano`, `gpt-5-mini`, and `gpt-5` across:

- accuracy / precision / recall / F1  
- cost  
- latency  

### 2.2 Prompt comparison

For each model:

- zero-shot baseline (`s1_zero.txt`)  
- few-shot v1 (`s1_few.txt`)  
- final tuned prompt (`s1_optimal.txt`, refined Stage 1 prompt selected after DEV analysis)

### 2.3 Schema stability

All models must return outputs that can be normalized into the Stage-1 schema.  
The parser must behave identically across all model outputs.

### 2.4 Prompt promotion and acceptance criteria

Changes to Stage-1 prompts are accepted only if they satisfy explicit acceptance criteria on the same labeled examples.

Disagreements between a baseline prompt and a candidate prompt are evaluated using McNemar’s test on DEV to ensure that observed improvements are not due to chance. Prompt promotion additionally requires improvement without performance regression on core classification metrics, particularly F1.

Operational metrics such as cost and latency are recorded but do not affect acceptance decisions.

### 2.5 Prompt selection under metric tradeoffs

Prompt refinement does not guarantee improvement across all metrics. In practice, tighter prompts often reduce false positives and improve precision while lowering recall.

Prompt selection is therefore treated as a multi-objective decision rather than a single-metric optimization. Candidate prompts are evaluated jointly on:

- statistical improvement under McNemar’s test  
- balance between precision and recall (F1)  
- error and schema stability  
- cost and latency characteristics  

Final selection favors prompts that achieve statistically justified improvements without performance regression. The selected prompt is referred to as the **refined** Stage 1 prompt.

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
- `gating/` (pairwise prompt comparison artifacts)

Each prompt comparison produces a gating directory containing a summary of the acceptance decision and the paired example rows used for evaluation.

---

## 4 · Datasets

Two frozen splits are used.

### DEV
- used for prompt iteration  
- used for model comparison  
- used for FP/FN clustering  
- authoritative for selecting the final prompt  

### TEST
- untouched until prompt freeze  
- used for final evaluation only  

`gold_labels.csv` must not change without a dataset version bump.

Only `artifacts/benchmark/gold/gold_labels.csv` is authoritative; any backups are stored under `artifacts/benchmark/gold/.old`.

---

## 5 · Prompt Benchmarking

**Prompt directory:** `prompts/`

Each benchmark run copies its prompt file into the run directory for reproducibility.

| Prompt | Purpose |
|---|---|
| `s1_zero.txt` | Zero-shot baseline |
| `s1_few.txt` | Few-shot v1 |
| `s1_optimal.txt` | Final tuned prompt (refined) |

**Runner flag:**
```bash
--prompt prompts/<prompt>.txt