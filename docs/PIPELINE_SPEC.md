# PIPELINE_SPEC.md  
WGU Reddit Analyzer — Pipeline Specification

This document specifies the WGU Reddit Analyzer pipeline as implemented in the repository.  
It describes each stage’s purpose, inputs, outputs, invariants, and reproduction boundaries.

---

## Scope

This pipeline is designed for artifact-driven analysis and reporting of Reddit posts related to WGU courses.

It is not designed for live inference, automated decision making, or institutional evaluation.

---

## Guarantees

- All reported results are derived from stored artifacts included in the repository.  
- Results can be reproduced using pinned runs and documented rebuild procedures.  
- LLM calls occur only in explicitly defined stages.  
- Each stage’s transformations and filters are documented at the artifact level.

---

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

## Invariants and Artifact Authority

- Stored artifacts are authoritative for all downstream behavior.  
- Prompt snapshots, not narrative labels, define executable behavior.  
- Historical defaults in code are not assumed runnable.  
- Reproduction requires explicit runner commands and flags.  
- Orphaned or legacy artifacts may exist for analysis but are not normative.

---

## Schema, Labels, and Hierarchy

### Top-Level Classes (Stage 1)

Each post is assigned exactly one value:

- `y` — contains a fixable course-side pain point  
- `n` — does not contain a fixable course-side pain point  
- `u` — unknown or unusable due to parsing or expected-format failure  

**Definition: fixable course-side pain point**

A post reports a fixable course-side pain point if it describes a persistent, actionable issue
arising from course design, content, structure, assessment, tooling, or staffing that could
plausibly be addressed by institutional action.

On parse or expected-format error:
- `contains_painpoint = "u"`
- `confidence_pred` is set to `0.0`

Parsing and schema errors are recorded, not prevented.

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

The number of global issue instances produced by a run may be much larger than the number of families.

Authoritative Stage 3 outputs include:
- `global_clusters.json`  
- `post_global_index.csv`  
- `cluster_global_index.csv`

These files are co-authoritative and jointly define Stage 3 results.

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
   - Empty or malformed summaries are dropped prior to clustering.

4. **Global issue instance (Stage 3)**  
   - Every course-level cluster appears at most once.  
   - Each cluster is either assigned to a global instance or recorded as unassigned.

Stage 4 tables include `schema_version` for traceability.

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
- These errors are accepted at Stage 0.

**Reproduction**
- Uses stored output only.  
- Stage 0 is not rerun.

---

## Stage 1 — Pain-Point Classification (LLM)

Stage 1 evaluates each post independently to determine whether it contains a fixable
course-side pain point.

Prompt selection for this stage is informed by benchmarking and paired statistical testing.
These procedures guide selection but do not mechanically enforce acceptance.

In documentation and paper text, *refined* is a narrative alias for the selected prompt.
Executable authority comes from prompt snapshots stored with each run.

Benchmark runs require explicit prompt and model flags. Code defaults are historical and
non-runnable.

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
A narrative alias for the selected prompt used in paper text.  
Executable authority is defined by the stored prompt snapshot for a given run.