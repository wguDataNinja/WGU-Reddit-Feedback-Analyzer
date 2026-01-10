
STAGE 2 SPEC
Course-Level Pain-Point Clustering
Last updated: 2025-12-11
Schema version: 1.0.0

⸻

0. Versioning

Stage 2 artifacts are tagged with a schema version.
	•	All Stage-2 manifests include:
	•	schema_version (example: "1.0.0")
	•	All Stage-2 evaluation tables include:
	•	schema_version
	•	Stage-2 provenance fields (run_id, run_slug, run_dir)

The canonical version string is defined in:
	•	wgu_reddit_analyzer.core.schema_definitions.SCHEMA_VERSION

⸻

1. Purpose

Stage 2 groups Stage-1 pain-points within each course into coherent clusters of shared root causes.

Outputs:
	•	one JSON cluster file per course
	•	painpoint snapshots
	•	a Stage-2 manifest including run_id and schema_version
	•	Stage-2 evaluation tables (cluster and course coverage diagnostics)
	•	these become the inputs for Stage 3 (global cross-course meta-clustering)

Important:
Stage 2 does not apply confidence thresholds, soft filters, or ambiguity heuristics.
It consumes all valid Stage-1 rows with pred_contains_painpoint = "y" and no parse/schema/LLM errors.

Confidence is preserved only as metadata; it is never used for filtering or weighting.

⸻

2. Inputs
	•	artifacts/stage1/full_corpus/<run_slug>/predictions_FULL.csv
	•	data/course_list_with_college.csv

Stage 2 reads Stage-1 provenance via the Stage-1 manifest.
Stage 3 later reads Stage-2 provenance via the Stage-2 manifest’s run_id and schema_version.

⸻

3. Responsibilities

Stage 2:
	1.	Filter Stage-1 predictions into a LLM-friendly CSV
	2.	Group painpoints by course_code
	3.	Build one LLM prompt per course
	4.	Call the model client on each course
	5.	Strictly validate outputs
	6.	Write:
	•	per-course cluster JSON
	•	per-course painpoint snapshots (jsonl)
	•	stage2_prompt.txt
	•	manifest.json (with run_id and schema_version)
	7.	Produce evaluation artifacts (diagnostics-only), via stage2/eval_builders.py:
	•	artifacts/stage2/eval/cluster_size_summary.csv
	•	artifacts/stage2/eval/course_cluster_coverage.csv

Eval tables:
	•	are defined by Pydantic models in stage2/eval_types.py
	•	are deterministic and unit-tested
	•	always include schema_version and Stage-2 provenance fields
	•	never influence clustering behavior

⸻

4. Preprocessing

Script: stage2/preprocess_painpoints.py
Writes:
	•	artifacts/stage2/painpoints_llm_friendly.csv

Fields:
	•	post_id
	•	course_code
	•	root_cause_summary
	•	pain_point_snippet
	•	optional metadata (e.g., confidence_pred)

Filtering:

Include rows where:
	•	pred_contains_painpoint == "y"
	•	llm_failure == False
	•	parse_error == False
	•	schema_error == False
	•	summary/snippet non-empty

Exclude rows where:
	•	any error flag True
	•	summary/snippet empty

Documented behavior (must be explicit):

Stage 2 excludes any Stage-1 rows with parse_error=True or schema_error=True.
This leads to occasional Stage-1 → Stage-2 painpoint count discrepancies.

⸻

5. Clustering Runner

Script: stage2/run_stage2_clustering.py

Run slug format:
<model>_s2_cluster_<corpus_tag>

Outputs:
artifacts/stage2/runs/<run_slug>/

Files:
	•	clusters/<course_code>.json
	•	painpoints_used_<course_code>.jsonl
	•	stage2_prompt.txt
	•	manifest.json
	•	(optionally) eval/cluster_size_summary.csv
	•	(optionally) eval/course_cluster_coverage.csv

Manifest includes:
	•	schema_version (for example, "1.0.0")
	•	run_id (canonical Stage-2 identifier)
	•	run_slug, run_dir
	•	num courses
	•	total painpoints
	•	per-course cost + latency
	•	model + prompt
	•	paths
	•	wallclock + total cost
	•	one entry per course

Stage 3 reads this via Stage-3 manifest’s source_stage2_run.

⸻

6. Cluster Schema (Authoritative)

Per course:

{
  "courses": [
    {
      "course_code": "CXXX",
      "course_title": "...",
      "total_posts": <unique post count>,
      "clusters": [
        {
          "cluster_id": "CXXX_1",
          "issue_summary": "short root-cause summary",
          "num_posts": <int>,
          "post_ids": ["...", "..."]
        }
      ]
    }
  ]
}

Rules:
	•	Multi-cluster membership allowed (must be explicit)
A post may appear in multiple clusters for that course.
No exclusivity constraint exists.
	•	cluster_id must begin with course_code
	•	num_posts = len(post_ids)
	•	total_posts = unique post_ids across clusters
	•	issue_summary non-empty
	•	output must be valid JSON only

⸻

7. Validation

stage2/validate_clusters.py checks:
	•	schema correctness
	•	prefix-matching cluster_ids
	•	accurate total_posts
	•	all post_ids in the LLM-friendly CSV
	•	no empty summaries
	•	no missing files
	•	version-stable behavior

Directory validator cross-checks all clusters vs. painpoints_llm_friendly.csv.

Stage 2 evaluation:
	•	stage2/eval_builders.py plus tests/stage2/test_eval_builders_stage2.py ensure:
	•	cluster_size_summary.csv and course_cluster_coverage.csv exist (when eval is run)
	•	they live under artifacts/stage2/eval/
	•	their column schemas match stage2/eval_types.py
	•	they carry schema_version and Stage-2 provenance fields

⸻

8. Cost and Runtime

Each course → one LLM call.

Typical:
	•	5–20 seconds per course
	•	full university catalog: 25–35 minutes
	•	cost: very low (cents)

All actual cost + timing appear in the Stage-2 manifest.

Eval builders:
	•	run as pure Pandas transforms over Stage-2 outputs
	•	add negligible runtime cost compared to LLM calls

⸻

9. Reproducibility and Provenance

Stable if:
	•	Stage-0 input unchanged
	•	Stage-1 predictions fixed
	•	Stage-2 prompt and code fixed

Each Stage-2 run stores:
	•	schema_version
	•	run_id
	•	run_slug
	•	full manifest
	•	prompt snapshot
	•	per-course inputs and outputs
	•	optional eval outputs under eval/

Downstream should always use run_id and the Stage-3 manifest’s:

"source_stage2_run": {
  "run_id": "<stage2_run_id>",
  "stage2_run_dir": "artifacts/stage2/runs/<stage2_run_slug>",
  "stage2_run_slug": "<stage2_run_slug>",
  "manifest_path": "artifacts/stage2/runs/<stage2_run_slug>/manifest.json",
  "schema_version": "1.0.0"
}

This provenance chain is authoritative for Stage 3 and Stage 4.

Stage-2 evaluation tables are reproducible from:
	•	Stage-1 predictions
	•	Stage-2 cluster outputs
	•	the Stage-2 manifest (run_id, run_slug, schema_version)

They are used for:
	•	alignment matrices
	•	refinement-loop decisions
	•	comparisons across models/prompts and schema versions.