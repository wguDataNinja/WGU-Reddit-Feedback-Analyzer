WGU Reddit Analyzer – Stage 1 Specification  
Pain-Point Detection, Benchmarking, and Full-Corpus Classification  
Last updated: 2025-11-30

---

# 1. Purpose and Scope

Stage 1 decides whether a Reddit post contains a course-side, actionable pain point and, if so, extracts:

- a root-cause summary  
- a short snippet anchored in the post  
- a model confidence score (metadata only — not used as a filter)

Stage 1 has two modes:

1. **Benchmark mode (DEV/TEST)**  
   Used for model/prompt selection, cost/latency measurement, and behavior evaluation.

2. **Full-corpus mode**  
   Applies a chosen model + prompt to the entire Stage-0 dataset to produce the inputs for Stage 2 clustering.

Stage 1 is the only stage with comprehensive empirical benchmarking.  
All outputs follow one stable normalized schema.  
Stage 1 uses **run_id** as canonical provenance.

---

# 2. Inputs and Dependencies

From Stage 0:

- `artifacts/stage0_filtered_posts.jsonl`  
  Cleaned Reddit posts, frozen.

Benchmark sampling inputs:

- `artifacts/benchmark/DEV_candidates.jsonl`
- `artifacts/benchmark/TEST_candidates.jsonl`
- `artifacts/benchmark/gold/gold_labels.csv`

Prompts:

- `prompts/s1_zero.txt`
- `prompts/s1_few.txt`
- `prompts/s1_optimal.txt` (frozen final prompt)

Model system:

- `benchmark/model_registry.py`
- `benchmark/model_client.py`

---

# 3. Stage 1 Responsibilities

Stage 1:

1. Builds deterministic DEV/TEST samples from Stage 0  
2. Runs LLM classifiers with different prompts and models  
3. Parses JSON, normalizes outputs, enforces schema safety  
4. Computes metrics, cost, latency  
5. Supports prompt iteration and FN/FP analysis  
6. Runs the chosen model+prompt on all Stage-0 posts  
7. Produces stable per-post predictions for Stage 2  
8. Records `run_id` in each manifest for downstream provenance

**Removed:**  
No confidence thresholds, soft filtering, or heuristics.  
Confidence is kept only as metadata.

---

# 4. Datasets and Sampling (DEV / TEST)

## 4.1 Base
- Source: `artifacts/stage0_filtered_posts.jsonl`  
- After cleaning: 1053 posts (20–600 tokens)

## 4.2 Sampling rules

Sampling code under `src/wgu_reddit_analyzer/benchmark/` produces:

- `DEV_candidates.jsonl`
- `TEST_candidates.jsonl`

Rules:

- Stratify by `(course_code, length_bucket)`  
  - short 20–149 tokens  
  - medium 150–299 tokens  
  - long 300–600 tokens
- A focus course retains all posts  
- Deterministic round-robin selection to ≈200 posts  
- 70/30 DEV/TEST split via fixed seed  
- No overlap

Result:

- DEV = 140  
- TEST = 60  

A manifest records the sampling parameters.

## 4.3 Gold labels
Stored in `artifacts/benchmark/gold/gold_labels.csv`

Fields:

- post_id  
- split  
- course_code  
- contains_painpoint ∈ {y,n,u}  
- root_cause_summary  
- ambiguity_flag  
- labeler_id  
- notes  

Evaluation uses rows with:

- matching split  
- ambiguity_flag = 0  
- contains_painpoint ∈ {y,n}

Gold labels are immutable.

---

# 5. Stage-1 Prediction Schema (Authoritative)

All predictions normalize to:

- `post_id`
- `course_code`
- `true_contains_painpoint ∈ {y,n}` (benchmark only)
- `pred_contains_painpoint ∈ {y,n,u}`
- `root_cause_summary_pred`
- `pain_point_snippet_pred`
- `confidence_pred ∈ [0.0,1.0]`
- `parse_error` (bool)
- `schema_error` (bool)
- `used_fallback` (bool)
- `llm_failure` (bool)

Rules:

- If pred = "y": summary + snippet taken from first painpoint
- If pred ∈ {"n","u"}: summary+snippet empty
- Invalid/missing confidence → 0.0
- Any parse/schema error → pred = "u" unless safely recoverable

Downstream (Stage 2+3+4) never use confidence for filtering.

---

# 6. Benchmark Code Layout

At `src/wgu_reddit_analyzer/benchmark/`:

- `stage1_classifier.py` – prompt render, LLM call, parsing, normalization  
- `stage1_types.py` – pydantic models  
- `model_client.py` – LLM interface, timing, retries  
- `model_registry.py` – pricing metadata  
- `run_stage1_benchmark.py` – DEV/TEST runner  
- `build_stage1_panel.py` – unified DEV/TEST analysis panels  
- `combine_runs_for_analysis.py` – optional collation  
- `cost_latency.py` – token/cost calculations  
- `update_run_index.py` – global index manager  
- `llm_connectivity_check.py` – sanity checks

Artifacts:

- `artifacts/benchmark/stage1/runs/<run_slug>/`
- `artifacts/benchmark/stage1_run_index.csv`
- `artifacts/benchmark/stage1_panel_DEV.csv`
- `artifacts/benchmark/stage1_panel_TEST.csv`

---

# 7. Prompt Benchmarking

Prompts:

- `s1_zero.txt`
- `s1_few.txt`
- `s1_optimal.txt`

Each run copies the exact prompt file into the run dir.

CLI flag:

- `--prompt prompts/<file>.txt`

Official DEV/TEST use only `s1_optimal.txt`.

---

# 8. LLM Call Logic

Uses `model_client.generate()`:

- provider-neutral  
- timeout + retries  
- returns `LlmCallResult`: raw text, errors, token usage, cost, latency

OpenAI models:

- Chat Completions API  
- messages=[{role:"user", content:prompt}]  
- temperature not forced to 0

Ollama (e.g., llama3):

- local HTTP POST  
- defaults for decoding

Runs are slightly stochastic because temperature is not 0.

---

# 9. Benchmark Runner Flow

`run_stage1_benchmark.py`:

1. Load DEV/TEST split  
2. Load candidates + gold  
3. Load prompt  
4. For each post (fixed order):  
   - render prompt  
   - call model  
   - write raw to `raw_io_<split>.jsonl`  
   - parse+normalize  
5. Write predictions  
6. Compute metrics  
7. Write manifest with `run_id`  
8. Copy prompt  
9. Append run_index row

Directory:

```
artifacts/benchmark/stage1/runs/<run_slug>/
    predictions_*.csv
    metrics_*.json
    raw_io_*.jsonl
    manifest.json
    s1_*.txt
```

Run slug pattern:

`<model>_<prompt>_<tag>`

---

# 10. Metrics + Run Index

Metrics:

- num_examples  
- tp,fp,fn,tn  
- precision, recall, f1, accuracy  

Errors:

- parse  
- schema  
- llm_failure  
- fallback  

Costs:

- total_cost  
- total_elapsed_sec  
- avg_elapsed_sec_per_example  

The run index stores:

- run_id  
- run_slug  
- model  
- provider  
- split  
- prompt  
- metrics  
- cost  
- is_official  
- paths  
- timestamps

run_id is the canonical key for downstream provenance.

---

# 11. Raw IO Logging

Every LLM call → append to `raw_io_<split>.jsonl`:

- post_id  
- course_code  
- model  
- provider  
- split  
- prompt name  
- prompt text  
- raw response  
- timestamps  
- parse/schema/fallback/llm_failure flags

Used for debugging and audits.

---

# 12. Unified Post-Level Panel

`build_stage1_panel.py` creates:

- `stage1_panel_DEV.csv`  
- `stage1_panel_TEST.csv`

Each row includes:

- full post text  
- gold  
- predictions  
- confidence  
- parse/schema/LLM flags  
- error type (tp/fp/fn/tn)  
- run metadata (model, prompt, run_slug, run_id)  

Used for FN/FP clustering and prompt refinement.

---

# 13. Prompt Iteration

Two scales:

- DEV-N (~25 posts)  
- Full DEV  

Validation requirements:

1. Schema-valid  
2. Generalizes to full DEV  
3. Avoids new FP clusters  
4. Acceptable FN rate  
5. Low parse/schema failures

DEV cycle:

1. Run  
2. Build panel  
3. Analyze FP/FN  
4. Document results  
5. Propose improvements  
6. Update prompt manifest

---

# 14. Evaluation Metrics

Precision = TP/(TP+FP)  
Recall = TP/(TP+FN)  
F1 = harmonic mean  
Accuracy = (TP+TN)/all

`pred="u"` counts as an error mapped to FP or FN depending on gold.

Cost/latency used for planning and model selection.

---

# 15. Cost Estimation

Logged in metrics for each run.

Helper: `estimate_benchmark_cost.py`  
Uses model registry, token profiles, prompt length, etc.

Not authoritative; real costs come from provider usage.

---

# 16. Full-Corpus Runner

`run_stage1_full_corpus.py`

Inputs:

- Stage 0 posts  
- `s1_optimal.txt`

Outputs:

- predictions_FULL.csv  
- raw_io_FULL.jsonl  
- manifest.json (with run_id)  
- prompt copy

Extra fields:

- painpoint_id (unique ID)
- model_name  
- prompt_name  
- run_slug  
- run_id  

Allows linking all downstream stages.

---

# 17. Model Requirements

Models must:

- output valid JSON / parseable structure  
- be stable under retry policy  
- expose token usage  
- set llm_failure correctly  

Registry includes:

- llama3  
- gpt-5-nano  
- gpt-5-mini  
- gpt-5

---

# 18. Empirical Findings

**gpt-5-mini**  
Best balance of precision/recall/F1/cost.

**gpt-5**  
Highest precision, lowest recall, highest cost.

**gpt-5-nano**  
High recall, many FPs, cheap.

**llama3**  
Moderate precision, high recall, no API cost, more schema quirks.

Prompt trends:

- zero-shot over-labels venting  
- few-shot improves  
- optimal collapses FP clusters with good recall

Default:

- Model: gpt-5-mini  
- Prompt: s1_optimal.txt

---

# 19. Reproducibility

Guarantees:

- deterministic DEV/TEST order  
- immutable gold  
- prompt archived  
- run_id recorded  
- manifest captures all provenance  
- global run index tracks every run  
- panels rebuilt from inputs  
- error flags recorded

Downstream should key on **run_id**.

Everything is reproducible given Stage-0 lock + manifests.