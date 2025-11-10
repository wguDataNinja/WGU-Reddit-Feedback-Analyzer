# Stage 1B — Sampling & Composition Strategy

_Date: 2025-11-08_  
_Data Source: `artifacts/stage0_filtered_posts.jsonl` (1053 after length trim)_  
_Length Profile: 20–600 tokens (from Stage 1A)_

---

## 1. Objective
Build a small, auditable, stratified sample for manual labeling and model evaluation.  
The sample should:
- Retain all valid **D335** posts (focus course)  
- Preserve coverage across courses and length buckets  
- Stay within fixed length limits  
- Be deterministic for full reproducibility  
- Remain manageable (~200 posts) for manual labeling

---

## 2. Sampling Process

| Step | Description |
|------|--------------|
| **Input** | Locked Stage 0 dataset (1053 posts within 20–600 tokens) |
| **Stratification** | Each post assigned to `(course_code, length_bucket)` — short (20–149), medium (150–299), long (300–600) |
| **Focus course** | All 27 D335 posts retained |
| **Non-focus selection** | Deterministic round-robin sampling from remaining strata until total = 200 |
| **DEV/TEST split** | 70/30 global split, `SEED = 20251107` |
| **Output** | `DEV_candidates` (140) and `TEST_candidates` (60) saved to `artifacts/benchmark/` |
| **Manifest** | Logged under `artifacts/runs/sample_<timestamp>/` with parameters and logs |

---

## 3. Quantitative Summary

| Metric | Value |
|---------|--------|
| Stage 0 after trim | 1053 posts |
| Focus course (D335) | 27 kept (22 DEV, 5 TEST) |
| Non-focus selected | 173 posts across ≈110 courses |
| Final total | 200 posts (140 DEV + 60 TEST) |
| DEV/TEST overlap | None |
| Length validity | All posts 20–600 tokens |

---

## 4. Composition Rationale
- **Balanced coverage:** Prevents large courses from dominating.  
- **Deterministic:** Same inputs always yield identical samples.  
- **Focus retention:** Keeps all D335 posts for targeted evaluation.  
- **Feasible size:** 200 posts ensures efficient manual labeling while maintaining diversity.

---

## 5. Labeling Plan (Stage 1C)
- Both DEV and TEST sets labeled using the shared schema and console tool.  
- DEV labels support model tuning; TEST labels remain unseen for final evaluation.  

---

## 6. Reproducibility
All run details — seed, file paths, parameters, and counts — are stored in  
`artifacts/runs/sample_<timestamp>/manifest.json`, ensuring full auditability and deterministic recreation of the Stage 1B sample.