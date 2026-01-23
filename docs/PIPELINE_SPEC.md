# PIPELINE_SPEC.md  
WGU Reddit Analyzer Pipeline Specification

This document describes the WGU Reddit Analyzer pipeline as implemented in the repository.  
It explains each stage’s purpose, inputs, outputs, and how results are produced and traced.

---

## Scope

This pipeline supports artifact-driven analysis and reporting of Reddit posts related to WGU courses.

It is not intended for live inference, automated decision-making, or institutional evaluation.

---

## Guarantees

- All reported results are derived from stored artifacts in the repository.
- Results can be reproduced using pinned runs and documented rebuild procedures.
- LLM calls occur only in explicitly defined stages.
- Each stage produces artifacts consumed downstream.

---

### Input Reference Caveat

Course codes and course names are derived from a scraped snapshot of the public WGU course catalog as of June 2025; only courses present in that snapshot are included. Reproducibility applies to stored artifacts and pipeline behavior given this fixed reference.
___

## Non-Goals

- Real-time inference  
- Automatic retraining or fine-tuning  
- End-to-end re-execution without stored artifacts  
- Ranking or evaluating course quality  
- Use of institutional or private records  

---

## High-Level Pipeline Overview

The analyzer is implemented as a staged pipeline. Each stage consumes stored artifacts and
produces new artifacts used downstream.

![Pipeline Diagram](figures/pipeline_diagram.png)

| Stage | Purpose |
|---|---|
| Stage 0 | Data extraction and filtering |
| Stage 1 | Pain-point classification |
| Stage 2 | Course-level clustering |
| Stage 3 | Cross-course normalization |
| Stage 4 | Reporting and analytics |

---

## Artifact Authority and Reproduction

- Stored artifacts define downstream behavior.
- Prompt snapshots stored with each run define executable behavior.
- Reproduction requires explicit runner commands and flags.
- Legacy or exploratory artifacts may exist but are not used for reporting.

---

## Schema, Labels, and Hierarchy

### Top-Level Classes (Stage 1)

Each post is assigned exactly one value:

- `y` — contains a fixable course-side pain point  
- `n` — does not contain a fixable course-side pain point  
- `u` — unknown due to parsing or format failure  

**Definition: fixable course-side pain point**

A post reports a fixable course-side pain point if it describes a persistent, actionable issue
arising from course design, content, structure, assessment, tooling, or staffing that could
plausibly be addressed by institutional action.

On parse or expected-format error:
- `contains_painpoint = "u"`
- `confidence_pred = 0.0`

---

### Global Issue Families (Stage 3)

Stage 3 normalizes course-level clusters into **global issue instances**.  
Each instance represents a concrete problem pattern observed across one or more courses.

Instances are grouped under a fixed set of **global issue families**, which define the schema.
The instances themselves are data-dependent outputs.

Current issue families (`schema_version = "1.0.0"`):

- `assessment_material_misalignment`
- `unclear_or_ambiguous_instructions`
- `course_pacing_or_workload`
- `technology_or_platform_issues`
- `staffing_or_instructor_availability`
- `course_structure_or_navigation`
- `prerequisite_or_readiness_mismatch`
- `other_or_uncategorized`

Authoritative Stage 3 outputs include:
- `global_clusters.json`  
- `post_global_index.csv`  
- `cluster_global_index.csv`

These files jointly define Stage 3 results.

---

### Hierarchy Rules

The pipeline follows a fixed hierarchy:

1. **Post**  
   Source: `artifacts/stage0_filtered_posts.jsonl`

2. **Pain-point presence (Stage 1)**  
   `contains_painpoint ∈ {"y","n","u"}`  
   Only `y` rows are eligible for Stage 2.

3. **Course-level cluster (Stage 2)**  
   - Cluster IDs are unique within a course.  
   - Posts may belong to multiple clusters.  
   - Empty or malformed summaries are dropped before clustering.

4. **Global issue instance (Stage 3)**  
   - Each course-level cluster appears at most once.  
   - Clusters are either assigned to a global issue instance or recorded as unassigned.

Stage 4 tables include `schema_version` for traceability.

---

## Robustness to Stage 1 Error

Stage 1 classification is imperfect by design, reflecting ambiguity in how course-related
complaints are expressed. The pipeline mitigates the impact of individual classification errors
through aggregation in later stages.

- A **false negative** excludes a single post from clustering, resulting primarily in lost signal
  for that post.
- A **false positive** may pass to Stage 2 but is unlikely to cluster with other posts describing
  the same issue, preventing it from forming a stable theme in Stage 3.

As a result, downstream analysis depends on repeated patterns across multiple posts rather than
perfect classification of individual posts.

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
- VADER sentiment analysis is applied as a fixed filter.
- Posts are retained only if `compound < -0.2`.
- Sentiment is used only for filtering.

**Course Code Gating**
- Each post is assigned exactly one `course_code`.
- Course codes are validated against `data/course_list_with_college.csv`.
- Posts with zero or multiple valid course codes are excluded.

**Known Limitations**
- Sentiment filtering is imperfect.
- Some non-complaint posts may pass the filter.
- Some valid complaints may be excluded.

**Reproduction**
- Uses stored output only.
- Stage 0 is not rerun.

---

## Stage 1 — Pain-Point Classification (LLM)

Stage 1 evaluates each post independently to determine whether it contains a fixable
course-side pain point.

Prompt selection for this stage is informed by benchmarking and paired statistical testing.

In documentation and paper text, *refined* refers to the prompt that was ultimately selected.
The exact prompt used in any run is the snapshot stored with that run’s artifacts.

Benchmark runs specify prompt and model explicitly.

---

## Reproduction and Traceability

An external reviewer can:

- Inspect stored artifacts  
- Rebuild reporting tables  
- Trace results using run manifests and run IDs  

No LLM access is required.

---

## Paper Reproduction Note

The authoritative pin for all paper-reported results is documented in:

`docs/PAPER_RUNS.md`

---

## Glossary

**optimal**  
The final tuned prompt filename stored in `prompts/`.

**refined**  
The prompt selected for reporting, as referenced in paper text.  
The executable prompt is the snapshot stored with the corresponding run.