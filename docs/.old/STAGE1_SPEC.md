# Stage 1 — Pain-point Extraction

Purpose
- Extract course-tied pain points from negative posts for downstream clustering.

Inputs
- `data/stage1/posts_locked.jsonl` (filtered `vader_compound < -0.2`; single-course only)
- `prompts/s1_v002_*.txt`

Outputs
- `output/runs/{RUN_ID}/stage1/{provider}/{strength}/{prompt_slug}/pain_points.jsonl`
- `run_manifest.json`, `qc.json`, `metrics.json`


	1.	Input locked
We ran scripts/lock_input.py. It wrote data/stage1/posts_locked.jsonl and a manifest with SHA256 and row count.
	2.	Length exploration
We ran scripts/research/lengths_stage1.py and scripts/research/length_by_d335.py.
Artifacts: output/tmp/length_hist.png, length_stats.json, length_stats_D335.json, length_hist_D335.png, len_by_course.csv.
Decisions from this pass: short ≤ 80 tokens, long ≥ 221 tokens (global p90 ≈ 220).
Focal course D335 had n = 25 with short 10, medium 13, long 2.
	3.	DEV and TEST sample
We configured the sampler for Stage 1: FOCAL_COURSE = “D335”, take all D335 and exclude from random pool; bin targets totaling 100 as short 34, medium 33, long 33; random-pool per-course min 2 and max 10; fixed SEED = 7; 60/40 split stratified by course × length.
Run produced: data/labels/DEV.jsonl, TEST.jsonl, DEV.csv, TEST.csv, sample_manifest.json.

Observed results from sample_manifest.json
seed: 7
short_max: 80, long_min: 221
focal_selected: short 10, medium 13, long 2
counts: DEV 62, TEST 38, TOTAL 100
by-length totals (DEV+TEST): short 34, medium 33, long 33
by_len_DEV: long 22, short 20, medium 20
by_len_TEST: short 14, medium 13, long 11
by_course totals include D335 = 25 split as DEV 15 and TEST 10
global_bin_counts in the source data: short 463, medium 399, long 96

Notes on invariants met
Total selected equals 100.
By-length targets hit exactly after combining DEV and TEST.
All D335 came from the focal block; D335 was excluded from the random pool.
Split preserved course × length proportions with approximate 60/40 (singletons land in DEV).
JSONL lines include an empty gold list for labels.



	4.	Manual labeling
Annotate DEV and TEST CSVs. Save adjudicated labels back into
data/labels/DEV.jsonl and data/labels/TEST.jsonl under the gold list.

5) Run models × prompts on sample (DEV first)  
   `python scripts/research/run_stage1_grid_sample.py`  
   Same `RUN_ID` for all combos; sets `prompt_path` per run.

6) Evaluate and select finalists  
   `python scripts/research/eval_stage1_sample.py` on DEV to down-select;  
   switch to TEST to confirm significance and pick the winner.

7) Full run (locked input)  
   Use the chosen prompt/model settings; shared `RUN_ID` for both providers.  
   Example: `python scripts/run_stage1_both.py`  
   Then `python scripts/qc_stage1.py` and `python scripts/eval_stage1.py`.

## Sampling + Labeling

- Length bins (tiktoken, 4o-mini tokenizer): **Short ≤ 80**, **Medium 81–220**, **Long ≥ 221**.  
  Confirm with `lengths_stage1.py`; copy final cutoffs here.
- Focal course “Course A”: 30 posts → 10/10/10 by length.
- Random pool: 70 posts → ≈24/23/23 by length; min 2 and max 10 per course.
- Split: DEV 60 / TEST 40 (preserve course and length proportions). Fixed seed.
- Label per post: zero or more items `{summary, root_cause, quoted_text}`; `quoted_text` must be a verbatim substring (1–2 sentences).
- Double-label 10–15 mixed items; adjudicate; freeze labels at `data/labels/{DEV,TEST}.jsonl`.

## Prompts

- `s1_v002_zero.txt` — strict JSON, up to 3 items, verbatim-quote rule.  
- `s1_v002_fs1.txt` — same as above + one compact few-shot example.  
- `s1_v002_neg.txt` — same as zero-shot + 2–3 “not a pain point” negatives.  
Keep a one-line change log in `docs/PROJECT.md` when versions change.

## Evaluation

Primary
- Micro Precision/Recall/F1 via quote-overlap match (normalized, ≥12 chars).

Secondary
- JSON validity rate, `num_pain_points` accuracy, per-course F1, latency/cost.

Significance (TEST only)
- Accuracy → McNemar exact (paired).  
- F1 → Paired approximate randomization.  
Report winner and p-values.

## Acceptance criteria

- Locked input + SHA256 recorded; shared `RUN_ID` across providers.
- JSON validity ≥ 98%.
- Winner confirmed significant on TEST.
- Both providers complete full run; outputs present with `run_manifest.json`.

## Notes

- Stage 1 caps items per post (≤3) to reduce over-splitting.  
- For later clustering, pass all available pain points per course in a single pass; if sharded, reconcile with a merge/rename pass keeping stable cluster IDs.
- `stage1_extract.run_stage1` accepts `run_id` and `prompt_path` and writes per-prompt subfolders.