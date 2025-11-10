# WGU Reddit Analyzer – Cost Estimation Guide

_Last updated: 2025-11-10_

---

## 1 · Purpose

Explains how benchmark costs and runtimes are estimated when running multiple models and prompt templates across DEV, TEST, and full datasets.  
Includes both API pricing and local runtime throughput (e.g., llama3 ≈ 1000 posts/hour).

---

## 2 · Inputs

- `artifacts/analysis/length_profile.json` — mean and distribution of tokens per post  
- `benchmark/model_registry.py` — per-model token pricing and metadata  
- `benchmark/cost_latency.py` — shared cost and latency helpers  
- `benchmark/estimate_benchmark_cost.py` — main estimator CLI  
- `prompts/` — prompt templates (`zero_shot.txt`, `few_shot_simple.txt`, `few_shot_optimized.txt`, etc.)  
- `configs/*.yml` — benchmark configs referencing models and prompt templates  

---

## 3 · Estimation Phases

### 3.1 Pre-Run Static Estimate

For each (model, prompt) × dataset (DEV/TEST/full) pair:
- Uses mean post length, prompt overhead, and expected output size  
- Produces projected:
  - total cost (USD)  
  - cost per 1K posts (USD)  
  - approximate runtime (for local models only)

### 3.2 Post-Run Observed Estimate

- Uses actual input/output token logs and per-call timing  
- Recomputes realized cost and latency (p50, p95)  
- Enables deviation analysis from pre-run estimates  

---

## 4 · Formula

For a given model *m*, prompt *p*, dataset *D*:

Let  
- *N_D* = number of posts  
- *T_post* = mean tokens per post  
- *T_prompt(p)* = tokens in prompt template *p*  
- *T_out* = expected output tokens  
- *c_in(m)*, *c_out(m)* = input/output cost per 1K tokens  

Then:

```
cost(m, p, D) ≈ N_D * [ (T_prompt(p) + T_post)/1000 * c_in(m)
                       + T_out/1000 * c_out(m) ]
cost_per_1k_posts = cost(m, p, D) / (N_D / 1000)
```

Cached-token discounts and batch sizes are handled by configuration.  
For local models, monetary cost = 0 but runtime (hours) is estimated via fixed throughput (default 1000 posts/hour for `llama3`).

---

## 5 · Reporting

**Pre-Run**

`artifacts/benchmark/cost_estimates.csv`  
Columns include:  
`prompt_label, model, dataset, num_posts, cost_usd, cost_per_1k_posts_usd, throughput_posts_per_hour, est_hours`

**Post-Run**

`artifacts/benchmark/final_cost_summary.json`  
Stores realized costs and latencies keyed by `(model, prompt, dataset)`.

Both files allow comparison between projected and observed results for every prompt variant.

---

## 6 · Usage

**Single configuration:**

```bash
python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost \
  --prompt-label zero_shot --prompt-tokens 260
```

**Multi-prompt estimate (3 scenarios in one run):**

```bash
python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost \
  --scenario zero_shot:260:120:4:0.0 \
  --scenario few_shot_simple:420:120:4:0.0 \
  --scenario few_shot_opt:600:140:4:0.0
```

The script automatically logs total API cost and local runtime (e.g., `llama3 ≈ 3.9 h` for sample dataset).

---

## 7 · Outputs

Each run generates:
- `artifacts/benchmark/cost_estimates.csv` — detailed per-row estimates  
- Console log summary:
  - total API cost across all configs  
  - per-model subtotal  
  - cumulative local runtime (hours)

**Example:**

```
Total estimated API cost across all configs: 7.5214 USD
  gpt-5 total: 6.0657 USD
  gpt-5-mini total: 1.2131 USD
  gpt-5-nano total: 0.2426 USD
  llama3 total: 0.0000 USD
  llama3 local runtime (sum): 3.909 hours
```

---

## 8 · Summary

This estimator provides transparent, reproducible accounting for both economic and temporal costs.  
It supports arbitrary prompt counts, model sets, and datasets without modifying code — only CLI configuration.  
Results are ready for publication-level reporting and prompt-efficiency comparison.

---