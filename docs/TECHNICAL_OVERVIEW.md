WGU Reddit Analyzer — Unified Internal Developer Specification

Last updated: 2025-11-17

⸻

0. Overview

This document consolidates all project details across the full pipeline: Stage 0 ingestion, Stage 1 sampling and benchmarking, model registry, LLM stack, smoke tests, artifacts, dev logs, and future roadmap. It is the authoritative internal reference for implementation, debugging, and onboarding.

⸻

1. Repository Layout & Execution

1.1 Repo & Package
	•	Repo root: /Users/buddy/Desktop/WGU-Reddit
	•	Package name: wgu_reddit_analyzer (src layout)
	•	Module execution:

PYTHONPATH=src python -m wgu_reddit_analyzer.<module>



1.2 Key Directories
	•	src/wgu_reddit_analyzer/pipeline/ — Stage 0 build
	•	src/wgu_reddit_analyzer/benchmark/ — Stage 1 sampling, LLM client, smoke tests
	•	prompts/ — prompt templates
	•	artifacts/ — datasets, labels, benchmark outputs
	•	docs/ — markdown documentation
	•	site/ — static site

1.3 High-Level Folder Roles

src/wgu_reddit_analyzer/
├── fetchers/          Reddit ingest
├── utils/             config, db, logging, tokens
├── pipeline/          Stage 0 build
├── benchmark/         Stage 1 sampling, LLM utils
└── llm_pipeline/      Stage 2–3 (future)

Supporting top-level dirs:
	•	configs/ YAML configs
	•	prompts/ Templates
	•	artifacts/ All generated data
	•	docs/ Notes
	•	archive_legacy/ Deprecated

⸻

2. Stage 0 — Dataset Build

2.1 Data Source
	•	Daily Reddit ingest (already configured).

2.2 Main Output
	•	artifacts/stage0_filtered_posts.jsonl
	•	Locked negative-only base dataset
	•	Sole source for Stage 1 sampling

2.3 Stage 0 Run Artifacts

Under: artifacts/runs/stage0_<timestamp>/
	•	manifest.json
	•	stage0.log

Stage 1 does not modify Stage 0 artifacts.

⸻

3. Stage 1 — Sampling, Labeling, Benchmarking

3.1 Candidate Generation (Sampling)

Artifacts:
	•	artifacts/benchmark/DEV_candidates.jsonl
	•	artifacts/benchmark/TEST_candidates.jsonl

JSONL schema (per line):
	•	post_id: str
	•	course_code: str
	•	title: str
	•	selftext: str
	•	optional metadata

Stage 1 classifier input (Stage1PredictionInput):
	•	post_id: str
	•	course_code: str
	•	text: str (title + blank line + selftext if available)

smoke_test_stage1 reconstructs inputs from these candidates.

⸻

4. Gold Labels (Ground Truth)

4.1 Current Gold File
	•	Path: artifacts/benchmark/gold/gold_labels.csv
	•	Only DEV is labeled at present.

Columns:
	•	post_id
	•	split (DEV only for now)
	•	course_code
	•	contains_painpoint {y, n, blank}
	•	root_cause_summary (free text)
	•	ambiguity_flag {0, 1}
	•	labeler_id (“AI1”)
	•	notes

4.2 Scoring Filter

Evaluated rows must satisfy:
	•	split == "DEV"
	•	ambiguity_flag != "1"
	•	contains_painpoint ∈ {"y", "n"}

Filtering implemented in load_gold_labels inside smoke_test_stage1.py.

4.3 Intersection Logic

Gold and candidate IDs are intersected.
	•	Missing gold IDs logged, not fatal.
	•	Only overlapping IDs evaluated.

Current: 8 DEV labels; 2 overlap with DEV candidates.

⸻

5. Model Registry & LLM Client

5.1 Model Registry (model_registry.py)

ModelInfo fields:
	•	name: str
	•	provider: str (openai | ollama)
	•	input_per_1k: float
	•	output_per_1k: float
	•	cached_input_per_1k: float = 0.0
	•	is_local: bool = False

5.2 Current Models
	•	llama3 — provider=ollama, local CPU, cost=0
	•	gpt-5-nano — openai, baseline
	•	gpt-5-mini — openai
	•	gpt-5 — openai, flagship
	•	gpt-4o-mini — openai, cheap+fast recommended

OpenAI pricing is per-1M converted to per-1K.

Entry point: get_model_info(name).

5.3 LLM Client (model_client.py)

generate(model_name, prompt) -> LlmCallResult
	•	OpenAI provider → client.chat.completions.create
	•	Ollama provider → local POST /api/generate
	•	Computes token usage, cost, latency

Returned fields:
	•	model name, provider
	•	raw text
	•	input/output tokens
	•	cost
	•	elapsed seconds

5.4 Sanity Checker

benchmark/llm_sanity_check.py
	•	Validates model is in registry
	•	Produces output with tokens, latency, cost

All models currently pass.

5.5 Stable OpenAI Path

GPT-5 Responses API was unstable; all Stage 1 calls use Chat Completions for reliability.

⸻

6. Stage 1 Classifier

Files:
	•	benchmark/stage1_types.py
	•	benchmark/stage1_classifier.py

6.1 Types

Stage1PredictionInput:
	•	post_id, course_code, text

Stage1PredictionOutput:
	•	post_id
	•	course_code
	•	contains_painpoint {y, n, u}
	•	root_cause_summary (optional)
	•	ambiguity_flag (optional)
	•	raw_response (full LLM text)

6.2 Classification Flow

classify_post(model_name, example, prompt_template):
	1.	Load template
	2.	Render prompt
	3.	Call LLM client
	4.	Extract first JSON object
	5.	Parse + validate
	6.	On failure: fallback regex for y/n/u

Returns both prediction + LlmCallResult.

⸻

7. Stage 1 Smoke Test

File: benchmark/smoke_test_stage1.py

CLI:

PYTHONPATH=src python -m wgu_reddit_analyzer.benchmark.smoke_test_stage1 \
  --model gpt-5-nano \
  --prompt prompts/s1_optimal.txt \
  --split DEV

Arguments:
	•	--model (required)
	•	--prompt (default: prompts/s1_optimal.txt)
	•	--split DEV|TEST (default DEV)
	•	--gold-path default gold CSV
	•	--candidates-path optional override

7.1 Evaluation Steps
	1.	Load gold
	2.	Load candidates
	3.	Compute ID intersection
	4.	For each matching ID:
	•	build prediction input
	•	classify via model
	•	compare with gold
	5.	Compute metrics: tp, fp, fn, tn, precision, recall, f1, accuracy
	6.	Aggregate timing + cost

7.2 Current Behavior
	•	8 gold DEV labels
	•	Only 2 intersect with DEV candidates
	•	All models benchmark only on these 2 examples

Performance snapshot:
	•	gpt-5: 1 TP, 0 FP, 0 FN, 1 TN → f1=1.0
	•	others: 1 TP, 1 FP, 0 FN, 0 TN → f1≈0.67

⸻

8. Stage 1 Run Artifacts

Directory pattern:

artifacts/benchmark/runs/stage1_/<model>_<split>_<YYYYMMDD_HHMMSS>/

Contents:
	1.	predictions_<split>.csv
	2.	metrics_<split>.json
	3.	manifest.json with:
	•	model, provider, prompt, split
	•	gold path, candidates path
	•	num examples
	•	file paths
	•	timestamps

Existing run dirs include:
	•	gpt-5-nano_DEV_20251117_121029
	•	gpt-5-mini_DEV_20251117_131021
	•	gpt-5_DEV_20251117_131038
	•	gpt-4o-mini_DEV_20251117_131108
	•	llama3_DEV_20251117_131114

⸻

9. Development Log (Milestone Summary)

Completed
	1.	Verified and extended MODEL_REGISTRY
	2.	Validated all OpenAI models via sanity check
	3.	Fixed Ollama llama3 (CPU-only config)
	4.	Upgraded smoke test to full CLI
	5.	Implemented Stage 1 run directory and artifact system
	6.	Ran smoke test on all models successfully
	7.	Measured initial performance snapshot

Current Status
	•	Stage 1 stack fully implements end-to-end benchmarking
	•	Artifacts clean, reproducible, and structured

⸻

10. Updated High-Level Technical Overview

10.1 System Architecture Summary
	•	Ingest → Stage 0 → Stage 1 sampling → Gold labeling → LLM benchmarking
	•	Future: clustering + final evaluation

10.2 Daily Ingest
	•	Script: daily_update under fetchers/
	•	Reads subreddit list, authenticates, writes DB + logs

10.3 Stage 1A Length Profile
	•	Token coverage 20–600
	•	Artifacts: histogram + JSON

10.4 Stratified Sampling
	•	Deterministic seed
	•	Balanced DEV/TEST

10.5 Manual Labeling
	•	CLI tool, produces gold CSV

10.6 Prompt Benchmarking
	•	Templates under prompts/

10.7 Cost Projection
	•	Script estimate_benchmark_cost.py

10.8 Datasets
	•	Locked artifacts under artifacts/

⸻

11. Environment & CLI

11.1 Secrets (env vars)
	•	Reddit API keys
	•	OPENAI_API_KEY

11.2 Local Install

pip install -e .
python -m wgu_reddit_analyzer.<module>


⸻

12. Git Workflow (Internal)
	•	Feature branches
	•	main stays stable
	•	Check remotes with git remote -v
	•	Standard commit cycle
	•	Guidance for nested .git cleanup + submodule removal

⸻

13. To-Do Roadmap

Short Term
	1.	Documentation cleanup (Stage 1 overview, registry doc)
	2.	Prompt notes + edge-case documentation
	3.	Utility scripts (latest runs, model diffs)

Medium Term
	1.	Full gold-label completion
	2.	Rerun full benchmarks on DEV/TEST
	3.	Clean-slate benchmark sweep, produce leaderboard + Pareto data

Long Term
	1.	Dedicated benchmark runner (config-driven)
	2.	Stage 2 clustering integration
	3.	Cleanup / archival utilities

⸻

14. Status Summary
	•	Stage 0 complete
	•	Stage 1A/B complete
	•	Stage 1C ready
	•	LLM stack stable
	•	Benchmark runner next
	•	Cost summary pending

⸻

End of unified internal specification.