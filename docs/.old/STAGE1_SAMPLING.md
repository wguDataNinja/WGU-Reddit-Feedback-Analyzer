Length bins: Short ≤80 tokens, Medium 81–220, Long ≥221 (tiktoken, 4o-mini)
Filter: vader_compound < -0.2; single-course only
Focal course: D335
Sample: 30 from Course A (10/10/10 S/M/L), 70 pooled (≈24/23/23 S/M/L), min 2 and max 10 per course
Split: DEV 60 / TEST 40 (preserve proportions)
Seed: 20250824
Artifacts: data/labels/{TRAIN,DEV,TEST}.jsonl


Labelling Guide:
Definitions:
- Pain point: negative experience caused by course design/delivery/support/assessment.
- Root cause: fixable course deficiency.

Unit: one post. Zero or more pain points.
Each pain point:
- summary (5–15 words)
- root_cause (short phrase)
- quoted_text (verbatim substring, 1–2 sentences)

Exclude:
- fear/anticipation with no cause
- self-ability only
- off-topic

Gold format: one JSONL object per post with "gold": [ ... ].








