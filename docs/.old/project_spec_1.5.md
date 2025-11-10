# Pipeline Spec (concise)

Scope
- Stage 1: extract pain points from negative posts (vader_compound < -0.2).
- Stage 2: cluster pain points by course.
- Stage 3: extract advice from full set and map to clusters.
- Stage 4: compose per-course guides.

Determinism
- temperature=0, fixed seed, stable IDs:
  - pp_{post_id}_{i}, cl_{course_code}_{nnn}, adv_{post_id}_{i}, run_id=YYYYMMDD_HHMMSS
  - prompt_id = filename#sha8, model_id = provider:model

I/O layout
- Config drives paths.
- Outputs:
  - runs/{run_id}/stage1/{provider}/{strength}/pain_points.jsonl
  - stage1/pain_points_master.jsonl
  - stage2/clusters_master/{course}.json
  - logs/pipeline.log

Validation
- Pydantic validation on all stages.
- If OpenAI rejects `json_schema`, fall back to `json_object` and still validate.

Eval (high level)
- Stage 1: accuracy, precision, recall, F1, confusion matrix; McNemar for prompt variants.
- Stage 2: ARI, NMI, pairwise precision/recall with Hungarian alignment.

Notes
- Use prompts/s*_v001.txt; bump v002 when changed.
- Cache seen posts and updated courses to keep idempotence.