# Runbook

Smoke test Llama 3
- `python scripts/llama3_smoketest.py`
- Output: `output/tmp/llama_test.jsonl`

Stage 1 extraction (JSONL source)
- Edit knobs at top of `scripts/stage1_extract.py`:
  - `INPUT_JSONL`, `PROVIDER` ("ollama" or "openai"), `STRENGTH`, optional `MODEL_OVERRIDE="llama3"`.
- Run:
  - `python scripts/stage1_extract.py`
- Output:
  - `output/runs/{run_id}/stage1/{provider}/{strength}/pain_points.jsonl`

Compare providers (optional)
- Run twice with `PROVIDER="openai"` then `PROVIDER="ollama"`.
- Diff JSONL counts and sample items.

Combine code snapshot (optional)
- `python scripts/combine_scripts_to_doc.py`
- Output: `output/combined_pipeline_code.txt`