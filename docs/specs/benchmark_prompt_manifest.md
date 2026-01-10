Benchmark Prompt Manifest

This document lists all prompts used during Stage 1 benchmarking and explains how they evolved.
The definition of a pain point lives in docs/LABEL_GUIDE.md and is not repeated here.

⸻

Prompt: s1_zero.txt (zero-shot baseline)

Purpose:
Initial untuned prompt used to establish a baseline for detecting course-related pain points.

Used in:
run01_zero_25dev (see docs/benchmark/run_index_25dev.md)

Observed behavior on the 25-post DEV subset:
• Zero false negatives across all four models
• High false-positive rate, with patterns including:
– emotional overload mistaken for course issues
– generic difficulty complaints
– debugging or technical setup issues
– life or scheduling events
• Differences in models were largely differences in FP frequency

Reason for replacement:
Reduce false positives without introducing false negatives.

⸻

Prompt: s1_few.txt (few-shot v1)

Purpose:
A minimal few-shot prompt designed after reviewing the zero-shot FPs.

Key changes relative to s1_zero.txt:
• Adds a small rule block clarifying what is NOT a pain point
• Adds targeted negative examples (emotion, difficulty, debugging, life events)
• Adds light positive examples (rubric/assessment issues, missing resources)

Planned usage:
run02_fewshot_v1_25dev (will be added to docs/benchmark/run_index_25dev.md)

Notes:
Each prompt used in benchmarking should appear here.
Canonical (current) prompt templates live in the prompts/ directory.
For each benchmark run, an exact copy of the prompt used is archived inside that run’s artifacts directory (see manifest.json → prompt_copied_path).
Associated FP analyses live in docs/analysis.
