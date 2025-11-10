# WGU Reddit Analyzer Pipeline

_Last updated: 2025-11-10_

---

## Purpose
The **WGU Reddit Analyzer** is a reproducible, auditable LLM pipeline for extracting actionable student pain points from Reddit discussions.  
It replaces the legacy sentiment-monitoring prototype with a structured benchmark framework focused on **cost**, **accuracy**, and **reproducibility**.

---

## System Architecture

### Core Package Layout
```
src/wgu_reddit_analyzer/
│
├── fetchers/       → Reddit ingest (PRAW collectors)
├── utils/          → config loader, DB helpers, logging, token utilities
├── pipeline/       → Stage 0 dataset build
├── benchmark/      → Stage 1 sampling, labeling, cost & model utilities
└── llm_pipeline/   → Stage 2–3 evaluation (future)
```

### Supporting Folders

| Folder | Purpose |
|---------|----------|
| `configs/` | YAML job configs |
| `prompts/` | Prompt templates |
| `artifacts/` | Generated data and logs |
| `docs/` | Markdown technical documentation |
| `archive_legacy/` | Deprecated code |
| `site/` | Hugo PaperMod static site (source only) |

---

## Daily Ingest Pipeline

**Script:** `wgu_reddit_analyzer.daily.daily_update`  
Automates Reddit ingest and database updates for all WGU subreddits.

- Reads canonical list from `data/wgu_subreddits.txt`  
- Uses credentials from `.env` and `configs/config.yaml`  
- Writes logs to `logs/daily_update.log` and data to `db/WGU-Reddit.db`  
- Outputs run manifests under `artifacts/runs/<timestamp>/`  

Run manually:
```bash
python -m wgu_reddit_analyzer.daily.daily_update
```

---

## Analytical Flow

### Stage 0 — Data Collection & Filtering
Collect Reddit posts via PRAW, filter for valid WGU course codes and negative VADER sentiment (< –0.2).  
**Outputs:** `artifacts/stage0_filtered_posts.jsonl`, `db/WGU-Reddit.db`

### Stage 1A — Length Profile & Trim Analysis
Token distribution computed with `benchmark/build_length_profile.py`.  
Cutoffs of 20–600 tokens cover > 99% of posts.  
**Artifacts:** `length_profile.json`, `length_histogram_tokens.png`, and `docs/STAGE1A_SAMPLING_STRATEGY.md`

### Stage 1B — Stratified Sampling
Script `benchmark/build_stratified_sample.py` creates deterministic, balanced DEV/TEST splits (200 posts total, seed 20251107).  
**Outputs:** `DEV_candidates.jsonl`, `TEST_candidates.jsonl`, `manifest.json`

### Stage 1C — Manual Labeling (Gold Dataset)
Script `benchmark/label_posts.py` provides an interactive CLI (`y n u q`).  
**Output:** `artifacts/benchmark/gold/gold_labels.csv`

---

### Benchmark Utilities

| Module | Role |
|---------|------|
| `benchmark/model_registry.py` | Defines model metadata and per-1K-token rates (OpenAI GPT-5, Llama 3). |
| `benchmark/cost_latency.py` | Computes token cost and latency from registry values. |
| `benchmark/hello_llm.py` | Connectivity and cost validation. |

---

## Future Work
- **Stage 2 – Root-Cause Clustering:** LLM groups posts by course and summarizes recurring issues.  
- **Stage 3 – Benchmark Evaluation:** Computes F1, precision, recall, and cost–accuracy Pareto fronts.  
- **Prompt Benchmarking:** Compare zero-shot and few-shot templates from `prompts/`.  
- **Cost Estimation:** `benchmark/estimate_benchmark_cost.py` projects runtime and API costs.

---

## Datasets & Artifacts

| File | Description |
|-------|--------------|
| `stage0_filtered_posts.jsonl` | Locked negative-only dataset |
| `DEV_candidates.jsonl` | 70% DEV subset |
| `TEST_candidates.jsonl` | 30% TEST subset |
| `gold_labels.csv` | Final labeled benchmark set |

All outputs live under `artifacts/` and are **immutable once published**.

---

## Repository Policy
- **Active:** `src/`, `configs/`, `prompts/`, `artifacts/`, `docs/`  
- **Legacy:** `archive_legacy/` *(ignored)*  
- Each script writes logs and manifests under `artifacts/runs/`.

---

## Environment and Secrets
All credentials are managed via `wgu_reddit_analyzer.utils.config_loader`.

**Environment Variables**
```
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
REDDIT_USERNAME
REDDIT_PASSWORD
OPENAI_API_KEY
```
No secrets are committed to source control.

---

## Install and Run
```bash
pip install -e .
python -m wgu_reddit_analyzer.daily.daily_update
python -m wgu_reddit_analyzer.benchmark.build_stratified_sample
python -m wgu_reddit_analyzer.benchmark.label_posts
```

**Imports use the package namespace:**
```python
from wgu_reddit_analyzer.utils.logging_utils import get_logger
```

---

## References
- Rao et al. (2025) – *QuaLLM Framework for Reddit Feedback Extraction*  
- De Santis et al. (2025) – *LLM Robustness on Noisy Social Text*  
- Koltcov et al. (2024) – *Class Imbalance Methods for Short Social Data*

---

✅ **Status:** Stage 0 locked · Stage 1A/1B complete · Stage 1C ready · Benchmark modules verified · Prompt benchmarking pending