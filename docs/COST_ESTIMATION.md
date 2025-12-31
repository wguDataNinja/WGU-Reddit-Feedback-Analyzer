# WGU Reddit Analyzer — Cost Estimation Guide

_Last updated: 2025-11-19_

---

## 1 · Purpose

This document defines how **benchmark cost and runtime** are:

- estimated prior to execution, and  
- measured from observed API usage after execution.

It supports planning, comparison across models and prompts, and transparent reporting.  
All reported costs reflect **historical recorded usage** at execution time and should not be interpreted as current or future pricing.

---

## 2 · Inputs

Cost estimation and measurement rely on the following inputs:

- `artifacts/analysis/length_profile.json`
- `benchmark/model_registry.py`
- `benchmark/cost_latency.py`
- `benchmark/estimate_benchmark_cost.py`
- `prompts/` (prompt templates)
- `configs/*.yml`

Model pricing information is recorded in `model_registry.py` at the time of each run.

---

## 3 · Estimation Phases

### 3.1 Pre-Run (Static Estimation)

Before execution, cost is estimated using:

- mean post length from prior analysis,
- prompt token length,
- expected output length,
- dataset size.

These estimates are used for planning and comparison only.

---

### 3.2 Post-Run (Observed Measurement)

After execution, cost and latency are computed from logged API usage:

- input tokens
- output tokens
- elapsed wall-clock time
- total recorded cost

Observed values are authoritative for reporting.

---

## 4 · Cost Model

For a model *m*, prompt *p*, and dataset *D*:

```
cost(m,p,D) ≈ N_D · [
  (T_prompt + T_post) / 1000 · c_in(m)
+ T_out / 1000 · c_out(m)
]
```

Where:

- `N_D` = number of posts  
- `T_prompt` = prompt tokens  
- `T_post` = post text tokens  
- `T_out` = output tokens  
- `c_in`, `c_out` = per-1k-token input and output costs recorded for the model  

Local models have zero API cost but non-zero runtime.

---

## 5 · Cost Artifacts

### Pre-Run

- `artifacts/benchmark/cost_estimates.csv`

### Post-Run

- `artifacts/benchmark/final_cost_summary.json`

Common fields include:

- model  
- dataset  
- prompt_label  
- num_posts  
- tokens_in  
- tokens_out  
- cost_usd  
- seconds_elapsed  

---

## 6 · CLI Usage

### Single scenario

```bash
python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost \
  --prompt-label zero_shot \
  --prompt-tokens 260
```

### Multiple scenarios

```bash
python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost \
  --scenario zero_shot:260:120:4:0.0 \
  --scenario few_shot_simple:420:120:4:0.0 \
  --scenario few_shot_opt:600:140:4:0.0
```

These commands produce planning estimates only.

---

## 7 · Observed Costs (DEV Runs)

The following summarize **historical observed API usage** from DEV benchmark runs.  
They reflect pricing at execution time and are included for transparency, not forecasting.

### gpt-5
- Input tokens: 0.018 USD  
- Output tokens: 0.127 USD  
- Notes: Output tokens dominate total cost.

### gpt-5-mini
- Input tokens: 0.003 USD  
- Output tokens: 0.029 USD  
- Notes: 5× cheaper per call than gpt-5.

### gpt-5-nano
- Input tokens: 0.003 USD  
- Output tokens: 0.081 USD  
- Notes: 5× cheaper per call than 5-mini. but higher output verbosity.

### llama3
- Input/output cost: 0.000 USD (local)  
- Notes: CPU-only execution; runtime is the primary cost.

---

## 8 · Interpretation

- Even with multiple DEV smoke tests, total API spend remains very low.
- Output tokens dominate cost for most hosted LLMs.
- Few-shot prompts increase input tokens but may reduce verbose outputs.
- Local models trade zero API cost for increased runtime.

---

## 9 · Summary

- Pre-run estimation provides reliable planning guidance.
- Observed usage is recorded for all benchmark runs.
- Cost and latency are first-class benchmark metrics.
- All reported costs are historical and tied to recorded artifacts.

This cost framework supports transparent, reproducible evaluation without embedding assumptions about future pricing.

