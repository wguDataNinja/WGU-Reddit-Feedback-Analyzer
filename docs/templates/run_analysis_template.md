# Stage-1 Benchmark Analysis Template

Use this template for each new Stage-1 benchmark run (e.g., run03, run04).  
Replace placeholder text with actual analysis.

---

## 1. Overview

Summarize the run being analyzed (e.g., run03_something_25dev).  
Include:
- prompt file used  
- how it differs from previous run’s prompt  
- intention of the change  

---

## 2. Metrics Comparison Summary

Compare the previous run vs this run for each model.

For each model, include short bullets:

- precision: prev → current  
- recall: prev → current  
- f1: prev → current  
- accuracy: prev → current  
- surprising notes  

---

## 3. False-Positive Pattern Comparison

### 3.1 FP categories that decreased  
Short list based on comparing FP CSVs.

### 3.2 FP categories that increased  
Short list based on comparing FP CSVs.

### 3.3 Posts that flipped  
Report by post_id:

- FP → TN  
- TN → FP  
- FP → FN (if any)  

Include one-sentence reason for each.

---

## 4. Per-Model Notes

For each model:
- 1–2 bullets max  
- note the change in behavior compared to the previous run  
- avoid repeating numeric metrics  

---

## 5. Recommendations for Next Prompt Version

List 3–6 concrete prompt revisions derived from the patterns you observed.  
Avoid generic suggestions.

---

## 6. Final Summary

One paragraph:  
Summarize whether the new prompt helped or hurt overall, and the most important next iteration step.