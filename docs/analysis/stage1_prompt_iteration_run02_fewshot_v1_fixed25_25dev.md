# Dev Log — Stage 1 Few-Shot v1, Fixed 25-post DEV Subset

Run label: run02_fewshot_v1_fixed25_25dev  
Date: 2025-11-19  
Prompt: `prompts/s1_few.txt`  
Dataset: DEV-25, fixed slice (same 25 posts as zero-shot baseline)  

---

## 1. Purpose

Evaluate the few-shot v1 prompt on the **same fixed DEV-25 subset** used in the zero-shot run.

Design intent of `s1_few.txt`:

- keep the core definition of a pain point  
- add a small rule block describing what is *not* a pain point  
- add minimal examples (negative + positive)  
- reduce false positives without heavily impacting recall  

Models evaluated:

- llama3 (ollama)  
- gpt-5-nano (openai)  
- gpt-5-mini (openai)  
- gpt-5 (openai)  

---

## 2. Metrics Summary vs Zero-Shot (fixed 25)

From `docs/benchmark/run_index_25dev.md`:

- gpt-5-mini:  
  - zero:  tp=7, fp=15, fn=0, tn=3,  precision=0.318, recall=1.000, f1=0.483, accuracy=0.400  
  - few:   tp=6, fp=9,  fn=1, tn=9,  precision=0.400, recall=0.857, f1=0.545, accuracy=0.600  

- gpt-5-nano:  
  - zero:  tp=7, fp=14, fn=0, tn=4,  precision=0.333, recall=1.000, f1=0.500, accuracy=0.440  
  - few:   tp=7, fp=12, fn=0, tn=6,  precision=0.368, recall=1.000, f1=0.538, accuracy=0.520  

- gpt-5:  
  - zero:  tp=6, fp=5,  fn=1, tn=13, precision=0.545, recall=0.857, f1=0.667, accuracy=0.760  
  - few:   tp=6, fp=1,  fn=1, tn=17, precision=0.857, recall=0.857, f1=0.857, accuracy=0.920  

- llama3:  
  - zero:  tp=7, fp=8,  fn=0, tn=10, precision=0.467, recall=1.000, f1=0.636, accuracy=0.680  
  - few:   tp=6, fp=3,  fn=1, tn=15, precision=0.667, recall=0.857, f1=0.750, accuracy=0.840  

High-level:

- nano:    same recall, fewer FPs, better precision and accuracy  
- mini:    fewer FPs, one FN, higher precision and accuracy  
- gpt-5:   much fewer FPs, same recall, higher f1 and accuracy  
- llama3:  fewer FPs, one FN, higher precision, f1, and accuracy  

The few-shot v1 prompt improves overall performance on this fixed subset for all four models.

---

## 3. Behavioral Change vs Zero-Shot

Qualitatively, few-shot v1:

- stops labeling some raw emotional venting as structural defects  
- becomes more cautious about posts that only show “this class is hard”  
- still occasionally over-labels policy / proctor / support posts as pain points  
- may under-label subtle pain points where the course defect is implied rather than explicit  

The stronger models (gpt-5, llama3) show the largest precision gains and small recall reductions.  
The smallest model (nano) keeps recall at 1.0 while shedding some false positives.

---

## 4. Prompt Implications

The fixed-25 results suggest:

- the negative examples and rule block work as intended  
- further improvement should focus on:  
  - policy and administrative posts  
  - mentor responsiveness complaints  
  - ambiguous OA difficulty posts without explicit course-side issues  

The next prompt (`s1_optimal.txt`) should:

- keep the current “what is not a pain point” block  
- add 1–2 targeted negative examples for policy/support posts  
- tighten an example around “confusing instructions” where only clear course defects count  

---

## 5. Role of This Run

This run is the primary basis for:

- designing `s1_optimal.txt`  
- deciding whether DEV-25 is a reasonable proxy for full DEV in terms of patterns  

Aggregation and FP details are captured in:

- `docs/analysis/fp_analysis_run02_fewshot_v1_fixed25_25dev.md` (separate analysis doc, to be created)  

---

## 6. Next Steps

- Run `s1_optimal.txt` on the same fixed DEV-25 subset once it is drafted.  
- If trends look good, move to full DEV (all labeled posts) for zero, few, and optimal.  
- After full DEV, freeze the final Stage 1 prompt before touching TEST.