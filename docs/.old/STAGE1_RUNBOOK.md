Goal: extract pain points from negative posts.

Commands:
- python scripts/lock_input.py
- python scripts/run_stage1_both.py
- python scripts/qc_stage1.py
- python scripts/make_label_sample.py
- python scripts/eval_stage1.py

Inputs:
- data/stage1/posts_locked.jsonl (sha256: …)

Outputs:
- output/runs/{RUN_ID}/stage1/{provider}/{strength}/pain_points.jsonl
- qc.json, metrics.json

Env/assumptions:
- OPENAI_API_KEY set
- Ollama at http://localhost:11434/v1
- seed=1, temperature=0