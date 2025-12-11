
WGU Reddit Analyzer – Code Standards

Goals:
	1.	Consistent, professional Python style across all stages.
	2.	Code that matches the written specs exactly (no hidden thresholds, no silent behavior changes).
	3.	Reproducible, inspectable runs with clear provenance.

⸻

1. Modules, imports, and layout

1.1 Each module starts in this order:
	1.	Module docstring
	2.	from __future__ import annotations
	3.	Standard library imports
	4.	Third-party imports
	5.	Local package imports

1.2 Use absolute package imports under wgu_reddit_analyzer, not relative imports.

1.3 One top-level responsibility per module. Stage drivers live under:
	•	wgu_reddit_analyzer.benchmark.* for Stage 1 benchmarking
	•	wgu_reddit_analyzer.stage2.* for Stage 2
	•	wgu_reddit_analyzer.stage3.* for Stage 3
	•	wgu_reddit_analyzer.report_data.* for Stage 4

⸻

2. Naming and style

2.1 Follow PEP 8:
	•	snake_case for functions, variables, and module names
	•	PascalCase for classes
	•	UPPER_SNAKE_CASE for constants

2.2 Keep line length Black-compatible (88 chars). Use 4-space indentation.

2.3 Use double quotes for docstrings and human-readable messages. Either style is allowed in code, but be consistent within a file.

2.4 Keep functions under ~50–70 lines where possible. Extract helpers as needed (for example, _extract_json_block, _regex_contains_painpoint).

⸻

3. Typing and Pydantic models

3.1 Every public function and method must have type hints on parameters and return values.
Use -> None explicitly for no return.

3.2 Use from __future__ import annotations in all modules to avoid forward-reference strings.

3.3 All cross-module data contracts must be modeled as Pydantic BaseModel classes or typed DataFrame schemas:
	•	Stage 1 I/O: Stage1PredictionInput, Stage1PredictionOutput, LlmCallResult
	•	Additional stages should add similar typed models under stage2_types.py, stage3_types.py, report_data_types.py as needed.

3.4 Use typing.Literal for categorical fields that are defined in the specs, for example:
	•	Literal["y", "n", "u"] for painpoint flags
	•	Literal["DEV", "TEST", "FULL"] for splits, if used

3.5 Add short docstrings to each model explaining what layer it belongs to and which files it mirrors (for example, “Normalized Stage 1 prediction, mirrors predictions_FULL.csv schema”).

⸻

4. Specs alignment and invariants

4.1 Code must never contradict the stage specs. If specs change, update both code and docs in the same branch.

4.2 Stage 1:
	•	Implement the authoritative prediction schema fields exactly as defined.
	•	Respect the rule: any parse or schema error defaults contains_painpoint to "u" and sets flags.
	•	Ensure confidence_pred is always in [0.0, 1.0]; invalid values map to 0.0.

4.3 Stage 2:
	•	Filter only by the documented flags:
	•	Include pred_contains_painpoint == "y"
	•	Exclude any rows with parse_error, schema_error, used_fallback, or llm_failure set to true.
	•	Do not apply any confidence thresholds in Stage 2 preprocessing.
The current MIN_CONFIDENCE pattern in preprocess_painpoints.py should be removed or set to 0.0 and treated as a legacy option only via CLI flags.

4.4 Stage 3:
	•	Ensure every Stage-2 cluster_id appears exactly once, either in a global cluster or unassigned_clusters.
	•	Never drop clusters silently; omitted ones go into unassigned_clusters.

4.5 Stage 4:
	•	No LLM calls, no thresholds, no additional filtering.
	•	All transformations must be pure joins, reshapes, and deterministic aggregations.

⸻

5. Paths, I/O, and project root

5.1 Use pathlib.Path everywhere for filesystem paths.

5.2 Never hardcode user-specific absolute paths (for example, /Users/buddy/...).
Stage paths must be:
	•	Passed via CLI arguments, or
	•	Derived from a single artifacts_dir / data_dir root given to functions.

5.3 Provide a single helper for project root or artifact root (like project_root() in build_analytics.py), but avoid baking it into library logic. CLI entry points resolve paths; core functions accept Path objects.

5.4 All loaders must:
	•	Validate file existence with clear FileNotFoundError messages.
	•	Validate required columns and fail fast with explicit messages (as you do in load_painpoints_stage2 and load_course_metadata).

⸻

6. Logging and error handling

6.1 Use a shared logging utility (for example, wgu_reddit_analyzer.utils.logging_utils.get_logger) in every module, with namespacing like:
	•	benchmark.stage1_classifier
	•	stage2.preprocess_painpoints
	•	report_data.build_analytics

6.2 Never print directly from library code. Use logging at appropriate levels:
	•	logger.info for high-level progress
	•	logger.debug for per-record detail when needed
	•	logger.warning for recoverable issues
	•	logger.error for failures

6.3 All stages must respect the error flag semantics defined in the specs:
	•	parse_error
	•	schema_error
	•	used_fallback
	•	llm_failure

6.4 When catching exceptions during parsing or schema validation, always set the correct flags and normalize to a safe default rather than crashing Stage 1 runs.

⸻

7. LLM integration (Stage 1–3)

7.1 All LLM calls must go through model_client.generate(). No direct HTTP calls scattered across the codebase.

7.2 LlmCallResult is the single source of truth for:
	•	model_name, provider
	•	raw_text
	•	token counts
	•	timing
	•	llm_failure, num_retries, error_message

7.3 Stage-specific code may add derived fields, but may not change the meaning of the base LlmCallResult.

7.4 JSON parsing must:
	•	First try strict json.loads().
	•	Fall back to controlled regex / block extraction (as in _extract_json_block and _regex_contains_painpoint).
	•	Never pass unvalidated model output directly into downstream stages.

⸻

8. Pandas and CSV handling

8.1 For pandas-based scripts (Stage 3 and 4):
	•	Always validate the presence of required columns right after loading.
	•	Keep all joins explicit, with join keys listed in one place.

8.2 Use pd.read_csv and pd.read_json with explicit lines=True where appropriate.

8.3 When writing CSVs and JSONL:
	•	Always write headers for CSVs (writer.writeheader() or DataFrame.to_csv(..., index=False)).
	•	Use UTF-8 encoding.

8.4 For multi-membership fields (in post_master.csv):
	•	Use semicolon-separated strings.
	•	Document the behavior in code docstrings and ensure it matches the Stage 4 spec.

⸻

9. CLI entry points

9.1 Each runnable script must expose a main() function and a standard guard:

def main() -> None:
    ...

if __name__ == "__main__":
    main()

9.2 CLI arguments must be parsed via argparse:
	•	No hard-coded filenames in code.
	•	All run-specific paths (run_slug, stage3 dirs, etc.) passed as flags.

9.3 Defaults are allowed but must be:
	•	Repository-relative (for example, under artifacts/)
	•	Documented clearly in the --help text

9.4 Stage names and tags in run slugs must follow documented patterns (for example, <model>_<prompt>_<tag> for Stage 1; <model>_s2_cluster_<corpus_tag> for Stage 2).

⸻

10. Testing and reproducibility hooks

10.1 Provide small, deterministic unit tests for:
	•	JSON parsing (safe_parse_stage1_response)
	•	CSV and DataFrame loaders
	•	Filtering logic in Stage 2
	•	Post and cluster indexing logic in Stage 3–4

10.2 Any randomness (sampling, batching) must:
	•	Use a fixed seed
	•	Be passed explicitly from the caller or configured centrally

10.3 Make it possible to re-run any stage from manifests and run_ids alone.
Functions should accept:
	•	artifacts_dir
	•	specific run directories or run_ids

⸻

11. Documentation and comments

11.1 Module and function docstrings must describe:
	•	Purpose
	•	Inputs (paths, DataFrames, typed models)
	•	Outputs (files and in-memory structures)
	•	Any invariants that are important downstream (for example, “every Stage-2 cluster_id appears exactly once”).

11.2 Keep inline comments short and only where the intent is not obvious from the code.

11.3 When behavior differs from legacy expectations (for example, removing confidence thresholds in Stage 2), explain it in the docstring and reference the spec section.

⸻
