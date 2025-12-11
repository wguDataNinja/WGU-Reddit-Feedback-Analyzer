# Dev Log — Stage 1 Zero-Shot, Fixed 25-post DEV Subset

Run label: run01_zero_fixed25_25dev  
Date: 2025-11-19  
Prompt: `prompts/s1_zero.txt`  
Dataset: DEV-25, fixed slice (same 25 posts for all models and prompts)  

---

## 1. Purpose

Re-establish a clean zero-shot baseline on a **fixed** 25-post DEV subset.

Earlier exploratory runs used slightly different 25-post slices per model, which made cross-model and cross-prompt comparisons unreliable. This run fixes that by:

- using the same 25 post_ids for all models  
- recording canonical zero-shot metrics for later comparison with few-shot and optimal prompts  

Models evaluated:

- llama3 (ollama)  
- gpt-5-nano (openai)  
- gpt-5-mini (openai)  
- gpt-5 (openai)  

---

## 2. Metrics Summary (zero-shot, fixed 25)

From `docs/benchmark/run_index_25dev.md`:

- gpt-5-mini: tp=7, fp=15, fn=0, tn=3, precision=0.318, recall=1.000, f1=0.483, accuracy=0.400  
- gpt-5-nano: tp=7, fp=14, fn=0, tn=4, precision=0.333, recall=1.000, f1=0.500, accuracy=0.440  
- gpt-5: tp=6, fp=5, fn=1, tn=13, precision=0.545, recall=0.857, f1=0.667, accuracy=0.760  
- llama3: tp=7, fp=8, fn=0, tn=10, precision=0.467, recall=1.000, f1=0.636, accuracy=0.680  

Key pattern:

- Recall is very high (often 1.0), especially for nano, mini, llama3.  
- False positives are common, especially on the smaller models.  
- gpt-5 trades a small recall drop (one FN) for much better precision.

This confirms the original diagnosis: zero-shot tends to treat many kinds of frustration or difficulty as course defects.

---

## 3. Qualitative Behavior

Even on the fixed subset, zero-shot still:

- over-labels emotional or “this class is killing me” posts as pain points  
- treats OA difficulty and repeated failures as structural defects without explicit evidence  
- often infers misalignment (PA vs OA) from short descriptions  
- converts debugging / lab issues into root-cause statements even when the post is just asking for help  

Better models (gpt-5, llama3) show the same tendencies, just less frequently.

---

## 4. Role of This Run

This run is now the **canonical** zero-shot baseline for DEV-25:

- All future few-shot and optimized prompts must be compared against these numbers.  
- Any FP/FN analysis for prompt tuning should use this run as the reference.

Deeper FP pattern analysis is handled in:

- `docs/analysis/fp_analysis_run01_zero_fixed25_25dev.md` (separate analysis doc, to be created)  

---

## 5. Next Steps

- Run few-shot v1 on the exact same DEV-25 subset.  
- Compare per-model changes in fp, fn, precision, recall.  
- Use the pair (zero vs few) to decide what needs to change for the s1_optimal prompt.