# PIPELINE_SPEC.md  
WGU Reddit Analyzer — Pipeline Specification

This document specifies the WGU Reddit Analyzer pipeline as implemented in the repository.  
It describes each stage’s purpose, inputs, outputs, rules, and reproduction boundaries.

---

## Scope

This pipeline is designed for analysis and reporting of Reddit posts related to WGU courses.

It is not designed for live production inference or automated decision making.

---

## Guarantees

- All reported results are derived from stored outputs in the repository.
- Results can be reproduced using the files included in the repository.
- LLM calls occur only in clearly defined stages.
- Each stage’s filtering and transformations are explicitly documented.

---

## Non-Goals

- Real-time inference  
- Automatic retraining or fine-tuning  
- End-to-end re-execution without stored outputs  
- Ranking or evaluating course quality  
- Use of institutional or private records  

---

## High-Level Pipeline Overview

Stage 0 → Stage 1 → Stage 2 → Stage 3 → Stage 4

| Stage | Purpose |
|---|---|
| Stage 0 | Data extraction and filtering |
| Stage 1 | Pain-point classification |
| Stage 2 | Pain-point preprocessing and clustering |
| Stage 3 | Cross-course normalization of pain points |
| Stage 4 | Reporting and analytics |

---

## Schema, Labels, and Hierarchy

### Top-Level Classes (Stage 1)

Each post is assigned exactly one value:

- `y` – contains a fixable course-side pain point  
- `n` – does not contain a fixable course-side pain point  
- `u` – unknown or unusable due to parsing or expected-format failure  

**Definition: fixable course-side pain point**

A post reports a fixable course-side pain point if it describes a persistent, actionable issue arising from course design, content, structure, assessment, tooling, or staffing that could plausibly be addressed by institutional action.

On parse or expected-format error:
- `pred_contains_painpoint = "u"`
- `confidence_pred` is set to `0.0`

---

### Global Issue Families (Stage 3)

Stage 3 normalizes course-level clusters into **global issue instances**.  
Each instance represents a concrete, reusable problem pattern observed across one or more courses.

These instances are grouped under a fixed set of **global issue families**.  
The families define the schema; the instances are the outputs.

Current issue families (`schema_version = "1.0.0"`):

- `assessment_material_misalignment`
- `unclear_or_ambiguous_instructions`
- `course_pacing_or_workload`
- `technology_or_platform_issues`
- `staffing_or_instructor_availability`
- `course_structure_or_navigation`
- `prerequisite_or_readiness_mismatch`
- `other_or_uncategorized`

The total number of global issue instances produced by a run is data-dependent and may be much larger than the number of families.

`global_clusters.json` is authoritative for the full set of global issue instances produced by a given run.

---

### Hierarchy Rules

The pipeline enforces the following hierarchy:

1. **Post**  
   Source: `artifacts/stage0_filtered_posts.jsonl`

2. **Pain point presence (Stage 1)**  
   `contains_painpoint ∈ {"y","n","u"}`  
   Only `y` rows flow to Stage 2.

3. **Course-level cluster (Stage 2 clustering)**  
   - Cluster IDs are unique within a course.
   - A post may belong to multiple clusters.

4. **Global issue instance (Stage 3)**  
   - Every course-level cluster appears exactly once.
   - Either assigned to a global issue instance or recorded as unassigned.

Stage 4 tables include `schema_version`.

---

## Stage 0 — Locked Reddit Corpus

**Purpose**  
Create a fixed Reddit dataset used by all downstream stages.

**Input**
- Raw Reddit post exports (not included)

**Output**
- `artifacts/stage0_filtered_posts.jsonl`

**Behavior**
- Filtering is performed once.
- The resulting corpus is treated as immutable.

**Sentiment-Based Pre-Filtering**
- VADER sentiment analysis is applied as a fixed gate.
- Posts are retained only if `compound < -0.2`.
- Sentiment is used only for filtering.

**Course Code Gating**
- Each post is assigned exactly one `course_code`.
- Course codes are validated against `data/course_list_with_college.csv`.
- Posts with zero or multiple valid course codes are excluded at Stage 0.

**Known Limitations**
- VADER sentiment filtering is imperfect.
- Some non-complaint posts may pass the filter.
- Some valid complaints may be excluded.
- These errors are accepted at Stage 0.

**Reproduction**
- Uses stored output  
- Stage 0 is not rerun  

---

## Stage 1 — Pain-Point Classification (LLM)

[unchanged content omitted for brevity in this explanation]

---

## Reproduction and Traceability

An external reviewer can:
- Inspect stored outputs
- Rebuild reporting tables
- Trace results using run IDs and manifests

No LLM access is required.

---

## Paper Reproduction Note

The authoritative pin for all paper-reported results is documented in:

`docs/PAPER_RUNS.md`

---

## Glossary

optimal refers to the final tuned prompt filename in `prompts/`.  
refined refers to the same final tuned prompt concept as used in paper wording, and the run snapshot file may be named `s1_refined.txt`.