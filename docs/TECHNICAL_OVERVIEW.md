# WGU Reddit Analyzer Pipeline – Technical Overview

_Last updated: 2025-11-10_

---

## Purpose

The WGU Reddit Analyzer is a reproducible LLM-based pipeline for extracting actionable student pain-points from Reddit discussions.  
It supersedes the legacy sentiment-monitoring prototype with a structured, auditable benchmark framework emphasizing transparency in cost, accuracy, and reproducibility.

---

## 1 · System Architecture

### 1.1 Core Package Layout

```
src/wgu_reddit_analyzer/
│
├── fetchers/       → Reddit ingest (PRAW collectors)
├── utils/          → config loader, DB helpers, logging, token utilities
├── pipeline/       → Stage 0 dataset build
├── benchmark/      → Stage 1 sampling, labeling, cost & model utilities
└── llm_pipeline/   → Stage 2–3 model evaluation (future)
```

---

### 1.2 Supporting Folders

| Folder | Purpose |
|---------|----------|
| configs/ | YAML job configs |
| prompts/ | prompt templates |
| artifacts/ | all generated data, metrics, and logs |
| docs/ | markdown technical docs |
| archive_legacy/ | deprecated or prototype code |
| site/ | Hugo PaperMod static site |

---

### 1.3 Daily Ingest Pipeline

**Script:** `wgu_reddit_analyzer.daily.daily_update`  
**Purpose:** automated Reddit ingest and DB update for all WGU subreddits.

- Reads canonical list from `data/wgu_subreddits.txt`
- Uses credentials from `.env` and `configs/config.yaml`
- Writes logs to `logs/daily_update.log` and data to `db/WGU-Reddit.db`
- Outputs run manifests under `artifacts/runs/<timestamp>/`
- Invoked via:
  ```bash
  python -m wgu_reddit_analyzer.daily.daily_update
  ```
- **Status:** Operational (as of 2025-11-10, Failures = 0)

---

## 2 · Analytical Flow

### 2.1 Stage 0 — Data Collection & Filtering

Collect Reddit posts (PRAW), filter for single valid WGU course code and negative VADER sentiment (< –0.2).  
**Output →** `artifacts/stage0_filtered_posts.jsonl`  
**Database mirror →** `db/WGU-Reddit.db`

---

### 2.2 Stage 1A — Length Profile & Trim Analysis

Token distribution computed with `dev/build_length_profile.py`.  
Empirical cutoffs `20 ≤ tokens ≤ 600` cover >99% of posts.

**Artifacts:**
- `artifacts/analysis/length_profile.json`
- `artifacts/analysis/length_histogram_tokens.png`
- `docs/STAGE1A_SAMPLING_STRATEGY.md`

---

### 2.3 Stage 1B — Stratified Sampling (DEV / TEST)

**Script:** `benchmark/build_stratified_sample.py`  
**Purpose:** deterministic, balanced 200-post subset for manual labeling.

**Parameters**
- Focus course D335 (retained in full)
- Buckets: 20–149 / 150–299 / 300–600 tokens
- Global target = 200 posts (70 / 30 DEV:TEST)
- Seed = 20251107

**Outputs**
- `artifacts/benchmark/DEV_candidates.jsonl`
- `artifacts/benchmark/TEST_candidates.jsonl`
- `artifacts/runs/sample_<timestamp>/manifest.json`

---

### 2.4 Stage 1C — Manual Labeling (Gold Dataset)

**Script:** `benchmark/label_posts.py`  
Interactive console tool for labeling DEV/TEST candidates.

**Commands:**  
`y` pain-point · `n` none · `u` ambiguous · `q` quit

**Output →** `artifacts/benchmark/gold/gold_labels.csv`  
All labels logged and manifest-tracked under `artifacts/runs/`.

---

### 2.5 Benchmark Utilities and Model Metadata

| Module | Role |
|---------|------|
| `benchmark/model_registry.py` | Defines model metadata and per-1K-token rates (OpenAI GPT-5 tiers and local Llama 3). |
| `benchmark/cost_latency.py` | Computes token-based cost and latency estimates using registry values. |
| `benchmark/hello_llm.py` | Minimal connectivity and cost test; validates LLM environment setup. |

---

### 2.6 Stage 2 — Root-Cause Clustering (Future)

LLM groups positive posts by course and summarizes recurring issues.

---

### 2.7 Stage 3 — Benchmark & Evaluation (Future)

Computes accuracy metrics (F1, precision, recall) plus token cost and latency via `cost_latency.py`.  
Plots cost-accuracy Pareto fronts for OpenAI and Ollama models.

---

### 2.8 Prompt Benchmarking (Upcoming)

The benchmark framework supports configurable prompt templates stored in `prompts/`:

```
prompts/
  ├── zero_shot.txt
  ├── few_shot_simple.txt
  └── few_shot_optimized.txt
```

Each run specifies a template via `prompt.template_path` in the benchmark YAML config.  
This enables reproducible comparison of zero-shot, few-shot, and optimized prompts across models while tracking accuracy, latency, and token cost.

---

### 2.9 Cost Estimation and Runtime Projection

**Script:** `benchmark/estimate_benchmark_cost.py`  
Projects per-model / prompt / dataset costs using length profiles and model pricing.  
**Outputs:**  
- `artifacts/benchmark/cost_estimates.csv`  
- Logs total API cost and local runtime (~1000 posts/hour for Llama 3)

**Planned enhancement (to-do):**  
Add post-run cost aggregation (`final_cost_summary.json`) to record actual token usage and latency after benchmarks are executed.

---

## 3 · Datasets

| File | Description |
|------|--------------|
| stage0_filtered_posts.jsonl | Locked negative-only dataset |
| DEV_candidates.jsonl | Stratified 70% DEV subset |
| TEST_candidates.jsonl | Stratified 30% TEST subset |
| gold_labels.csv | Manual labels for Stage 1 benchmark |

All Stage 0 and 1 artifacts are immutable once published.

---

## 4 · Key Outputs

| Artifact | Description |
|-----------|-------------|
| manifest.json | Run metadata (seed, bounds, counts) |
| length_profile.json | Token distribution summary |
| DEV/TEST *.jsonl | Stratified benchmark sets |
| gold_labels.csv | Final gold dataset |
| leaderboard.csv | Model performance summary |
| pareto_points.csv | Cost-accuracy Pareto front |
| reports/*.pdf | Course-level insight summaries |

All outputs reside under `artifacts/`.

---

## 5 · Repository Policy

- Active dirs: `src/`, `configs/`, `prompts/`, `artifacts/`, `docs/`  
- Legacy code: `archive_legacy/` (ignored at runtime)  
- `dev/` holds verification scripts only  
- Every executable writes a log and manifest under `artifacts/runs/`

---

## 6 · Environment and Secrets

All credentials loaded via `wgu_reddit_analyzer.utils.config_loader`.

**Environment Variables:**
- Reddit API: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`
- LLM API: `OPENAI_API_KEY`

No other secret files used.

---

## 7 · Python Package / CLI Layout

This repository uses an installable `src/` layout.  
- **Package:** `wgu_reddit_analyzer`  
- **Source root:** `src/wgu_reddit_analyzer/`  
- **Config:** `pyproject.toml` at repo root

**Install locally:**
```bash
pip install -e .
```

**Usage examples:**
```bash
python -m wgu_reddit_analyzer.benchmark.build_stratified_sample
python -m wgu_reddit_analyzer.benchmark.label_posts
```

**Imports use the package namespace:**
```python
from wgu_reddit_analyzer.utils.logging_utils import get_logger
```

Ensures stable imports and reproducible CLI runs.

---

## 8 · References

- Rao et al. (2025) – QuaLLM Framework for Reddit Feedback Extraction  
- De Santis et al. (2025) – LLM Robustness on Noisy Social Text  
- Koltcov et al. (2024) – Class Imbalance Methods for Short Social Data

---

✅ **Status:** Stage 0 locked · Stage 1A / 1B complete · Stage 1C ready · Benchmark modules verified · Prompt benchmarking and post-run cost summary pending