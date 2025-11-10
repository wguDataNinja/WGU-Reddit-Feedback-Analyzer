# WGU Reddit Analyzer – Benchmark Guide

_Last updated: 2025-11-10_

---

## 1 · Purpose

Defines how Large Language Models (LLMs) are evaluated for extracting course-level pain points from Reddit posts.  
Focus: accuracy, efficiency, and reproducibility across fixed datasets.

---

## 2 · Benchmark Goals

The benchmark serves two core evaluation goals:

1. **Model Comparison** — measure performance and efficiency across LLMs (e.g., GPT-5, Llama 3).  
2. **Prompt Comparison** — assess multiple prompt templates to identify the most effective configuration for the full dataset run.

Both dimensions are evaluated on identical datasets to ensure fair, reproducible comparison of accuracy, cost, and latency.

---

## 3 · Benchmark Structure

```
src/wgu_reddit_analyzer/benchmark/
  ├── data_io.py
  ├── runner.py
  ├── metrics.py
  ├── cost_latency.py
  ├── estimate_benchmark_cost.py
  └── report.py
```

All benchmark outputs and reports are stored in:

```
artifacts/benchmark/
```

---

## 4 · Datasets

Two locked splits: **DEV** and **TEST**.  
Each contains Reddit posts referencing a single WGU course.  
Datasets are versioned and immutable once released; any relabeling requires a version bump.

---

## 5 · Prompt Benchmarking

The benchmark framework supports configurable prompt templates stored in:

```
prompts/
  ├── zero_shot.txt
  ├── few_shot_simple.txt
  └── few_shot_optimized.txt
```

Each template defines a unique prompting strategy:

| Prompt Type | Description | Purpose |
|--------------|-------------|----------|
| **Zero-shot** | Basic task instructions only | Establish baseline accuracy |
| **Few-shot (simple)** | Includes 2–3 labeled examples | Tests example-driven gains |
| **Few-shot (optimized)** | DEV-tuned for clarity and efficiency | Maximizes accuracy-to-cost ratio |

Each run specifies the template via `prompt.template_path` in its YAML configuration.  
This allows reproducible multi-prompt benchmarking across models, tracking **accuracy**, **latency**, and **cost per 1K posts**.

---

## 6 · Benchmark Flow

1. Load dataset and prompt configuration.  
2. Run selected models and prompt templates.  
3. Collect predictions, token usage, and latency.  
4. Compute evaluation metrics (Precision, Recall, F1, Accuracy).  
5. Aggregate results via leaderboard and Pareto chart.  
6. Select the top-performing prompt per model based on DEV results for final TEST evaluation.

---

## 7 · Metrics & Analysis

Includes standard classification metrics plus **Macro / Weighted F1** to mitigate class imbalance.  
Efficiency metrics track:
- **Cost per 1K posts (USD)**  
- **p50 / p95 latency (ms)**  

Results are summarized in a **Pareto cost–accuracy plot**, highlighting trade-offs between performance and efficiency across both models and prompt types.

---

## 8 · Running the Benchmark

```bash
python -m wgu_reddit_analyzer.benchmark.runner --config configs/benchmark_example.yml
python -m wgu_reddit_analyzer.benchmark.report
```

Outputs appear under:

```
artifacts/benchmark/
```

---

## 9 · Results & Deliverables

- Reproducible leaderboard of model × prompt performance  
- Cost–accuracy Pareto summary  
- Optimal prompt per model for full dataset deployment  
- Locked and versioned evaluation datasets  
- Clear linkage between benchmark artifacts and project documentation

---

