# WGU Reddit Analyzer — Cost Estimation Guide
Last updated: 2026-01-17



## 1 · Purpose
This document explains how benchmark cost and runtime are:

- estimated before execution, and
- measured from recorded usage after execution.

It supports planning, comparison across models and prompts, and transparent reporting. Reported costs reflect recorded usage at execution time and should not be interpreted as current pricing.

---

## Recorded Total Cost (All Runs)

Based on summing `total_cost_usd` across all `manifest.json` files in the repository:

- **Total recorded cost:** **$1.15335 USD**
- **Number of runs:** **19**

This total reflects historical usage recorded at execution time, including exploratory and legacy runs. It is not a forecast of future cost.

---


## 2 · Inputs
Cost estimation and measurement use:

- `artifacts/analysis/length_profile.json`
- `src/wgu_reddit_analyzer/benchmark/model_registry.py`
- `src/wgu_reddit_analyzer/benchmark/cost_latency.py`
- `src/wgu_reddit_analyzer/benchmark/estimate_benchmark_cost.py`
- `prompts/`
- `configs/*.yml`

Model pricing is recorded in `model_registry.py` as used for the run.

---

## 3 · Estimation and Measurement

### 3.1 Pre-run estimation
Before execution, cost is estimated from:

- mean post length from prior analysis
- prompt token length
- expected output length
- dataset size

These estimates are for planning and comparison only.

### 3.2 Post-run measurement
After execution, cost and latency are computed from recorded usage:

- input tokens
- output tokens
- wall-clock time
- recorded cost in USD

Observed values are used for reporting.

---

## 4 · Cost Model
For a model `m`, prompt `p`, and dataset `D`:

cost(m,p,D) ≈ N_D · [ ((T_prompt + T_post) / 1000) · c_in(m)
+ (T_out / 1000) · c_out(m) ]

Where:

- `N_D` = number of posts
- `T_prompt` = prompt tokens
- `T_post` = post text tokens
- `T_out` = output tokens
- `c_in`, `c_out` = per-1k-token input and output costs recorded for the model

Local models have zero API cost but non-zero runtime.

---

## 5 · Cost Artifacts

### Pre-run
- `artifacts/benchmark/cost_estimates.csv`

### Post-run
- `artifacts/benchmark/final_cost_summary.json`

Common fields include:

- `model`
- `dataset`
- `prompt_label`
- `num_posts`
- `tokens_in`
- `tokens_out`
- `cost_usd`
- `seconds_elapsed`

### Per-run manifests
Pipeline stage runs record `total_cost_usd` in their `manifest.json` when applicable. These values are the source of truth for historical cost.

---

## 6 · CLI Usage

Single scenario:

```bash
python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost \
  --prompt-label zero_shot \
  --prompt-tokens 260
```

## 7 · Summing Recorded Costs

The total recorded cost shown at the top of this document was computed by summing total_cost_usd across all manifests:

```bash
find . -name manifest.json -print0 \
| xargs -0 jq -r 'select(.total_cost_usd != null) | "\(.total_cost_usd)\t\(input_filename)"' \
| sort -nr \
| awk '
BEGIN {print "List:\nCost\tFilename\n"}
{print $0; sum+=$1; count+=1}
END {
  print "\nNum of Runs:", count;
  print "Total $:", sum
}'

```
⸻

## 8 · Interpretation
- Output tokens typically dominate cost for hosted LLMs.
- Few-shot prompts increase input tokens but may reduce verbose outputs.
- Local models trade zero API cost for increased runtime.

⸻

## 9 · Summary
- Pre-run estimates support planning.
- Observed usage is recorded per run.
- Manifests provide a complete historical cost record.
- This supports transparent evaluation without assumptions about future pricing.
