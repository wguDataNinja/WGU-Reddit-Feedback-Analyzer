# WGU Reddit Analyzer – Stage 1 Benchmark Guide
Version: 2026-01-17  
Scope: Evaluation framework for Stage 1 pain-point detection using LLMs.

## 1 · Purpose
This guide describes how Stage 1 models and prompts are compared, evaluated, and selected.

## 2 · Benchmark Goals

### 2.1 Model comparison
The benchmark compares `llama3`, `gpt-5-nano`, `gpt-5-mini`, and `gpt-5` using core classification metrics (precision, recall, F1), along with cost and latency.

### 2.2 Prompt comparison
Prompts evaluated:

- zero-shot baseline (`s1_zero.txt`)
- few-shot v1 (`s1_few.txt`)
- final tuned prompt (`s1_optimal.txt`)

In documentation and paper text, *refined* refers to the prompt that was ultimately selected. The exact prompt used in any run is the copy saved in that run’s directory.

### 2.3 Prompt promotion and evaluation criteria
Prompt changes are evaluated on the same labeled examples.

Disagreements between a baseline prompt and a candidate prompt are analyzed using McNemar’s test on DEV to determine whether observed differences are statistically meaningful.

Core classification metrics, particularly F1, are used to detect regressions. Cost and latency are recorded for comparison, but selection is not based on these metrics alone.

### 2.4 Prompt selection under metric tradeoffs
Prompt selection reflects tradeoffs among:

- paired statistical testing on DEV (McNemar)
- balance between precision and recall (F1 as the primary summary metric)
- review of false-positive and false-negative errors
- cost and latency characteristics

Final selection favors prompts that improve F1 without introducing clear regressions. The selected prompt is referred to as the refined Stage 1 prompt.

## 3 · Benchmark Code Layout
Code: `src/wgu_reddit_analyzer/benchmark/`

- `run_stage1_benchmark.py`
- `build_stage1_panel.py`
- `combine_runs_for_analysis.py`

Artifacts: `artifacts/benchmark/`

- `stage1/runs/`
- `stage1_run_index.csv`
- `stage1_panel_DEV.csv`
- `stage1_panel_TEST.csv`
- `DEV_candidates.jsonl`
- `TEST_candidates.jsonl`
- `gold/gold_labels.csv`
- `gating/`

Gating artifacts support comparison and review; they are not final acceptance decisions on their own.

## 4 · Datasets
Two frozen splits are used.

### DEV
- used for prompt iteration
- used for model comparison
- used for false-positive and false-negative analysis
- used to guide prompt selection

### TEST
- held fixed until prompt selection is complete
- used for final evaluation only

The benchmark uses `artifacts/benchmark/gold/gold_labels.csv` as the labeled reference.

## 5 · Prompt Benchmarking
Prompt directory: `prompts/`

Each benchmark run copies its prompt file into the run directory for reproducibility. Prompt snapshots inside run directories define executable behavior.

| Prompt | Purpose |
|------|---------|
| `s1_zero.txt` | Zero-shot baseline |
| `s1_few.txt` | Few-shot v1 |
| `s1_optimal.txt` | Final tuned prompt (refined) |

Benchmark runs specify the prompt and model explicitly.

Runner flag:

`--prompt prompts/<prompt>.txt`

## 6 · Interpreting Accuracy and Error Analysis

### 6.1 Ambiguity in the task
Benchmark accuracy reflects agreement with a specific labeling policy rather than an objective ground truth. The distinction between a fixable, course-side pain point and student-side general difficulty (venting, anxiety, study stress) is inherently ambiguous, including for human coders.

This ambiguity is present in the gold labels (`gold_labels.csv`), including labeler notes such as “general difficulty,” “venting,” or “course anxiety” for `n` classifications, and posts explicitly flagged as ambiguous (`ambiguity_flag=1`).

The goal of prompt refinement is to align the LLM classifier with the labeling policy while preserving the usefulness of retrieved pain-point posts.

Under ideal research conditions, multiple independent human coders would label the same posts and inter-rater agreement would be measured to quantify this ambiguity. In this project, a single, consistently applied labeling policy was used instead. The benchmark therefore evaluates model alignment with that policy rather than consensus across multiple annotators.

### 6.2 Purpose of error review
DEV error review artifacts (`dev_errors_fp.csv`, `dev_errors_fn.csv`) show how the model diverges from the labeling policy. Review consistently indicates that the most difficult cases are boundary examples: high-emotion complaints that do not identify a specific, actionable course defect.

Error review informs prompt changes and guards against over-filtering true pain points.

### 6.3 Implications for pipeline robustness
The overall pipeline is intentionally structured so that individual classification errors have limited impact.

A false negative excludes a single post from downstream clustering, resulting primarily in lost signal for that post. A false positive is unlikely to cluster with other genuine pain points in later stages, preventing it from forming a stable issue in final summaries.

As a result, final outputs depend on repeated patterns across many posts rather than perfect classification of individual posts.