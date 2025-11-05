Pipeline Specification Document

1. Overview

Purpose

The pipeline processes student feedback from Reddit posts to identify and cluster pain points experienced in courses, providing actionable insights to course designers.

Scope
	•	Extract relevant posts.
	•	Classify and group pain points.
	•	Summarize and cluster feedback.
	•	Generate comprehensive PDF reports.

High-Level Goals
	•	Automate feedback analysis.
	•	Enable proactive course improvement.
	•	Provide clear, actionable summaries.

Data Flow Diagram

Reddit Posts (DB)
  ↓
Stage 1: Fetch & Filter → Classify Posts
  ↓
Stage 2: Group by Course → Cluster Pain Points → Apply Actions
  ↓
Generate PDFs & Merge Feedback

2. Architecture

Major Components
	•	Stage 1: Data fetching, cleaning, filtering, classification.
	•	Stage 2: Grouping, clustering via LLM, action application.
	•	Utilities: Logging, data handling (JSONL), PDF generation.

Orchestration Strategy

Scripts orchestrated sequentially via scripts/run_daily_pipeline.py.

Tools/Libraries Used
	•	Python
	•	OpenAI API (gpt-4o-mini)
	•	Pandas
	•	Pydantic
	•	Playwright (PDF generation)
	•	Markdown/BeautifulSoup (report generation)

3. Data Specifications

Input Data
	•	Raw Reddit post data (JSON format).

Output Data
	•	JSONL formatted files (pain_points_stage1.jsonl, clustered outputs).
	•	PDF reports summarizing pain points.

Schemas

Defined via Pydantic models in scripts (PainPoint, Cluster, FinalOutput).

Data Retention
	•	Processed posts archived indefinitely.
	•	Daily run outputs retained for historical analysis.

Validation Rules
	•	JSON schema validation with strict adherence enforced by Pydantic.
	•	Deduplication based on post content and IDs.

4. Stage-by-Stage Description

Stage 1

Step01: step01_fetch_filtered_posts.py
	•	Fetches and filters Reddit posts.
	•	Utilizes course code filters, sentiment analysis.
	•	Outputs filtered posts to filtered_posts_stage1.jsonl.

Step02 & Step03: step02_classify_post.py, step03_classify_file.py
	•	Classify posts into structured pain points via OpenAI API.
	•	Includes robust error handling, retries, logging detailed errors.

Step04: step04_run_stage1.py
	•	Coordinates classification, summarizes results in log files.

Stage 2

Step01: step01_group_by_course.py
	•	Groups pain points by course and tracks updates.

Step02: step02_prepare_prompt_data.py
	•	Prepares data formatted specifically for LLM processing.

Step03: step03_call_llm.py
	•	Calls LLM to cluster pain points by root causes.

Step04: step04_apply_actions.py
	•	Updates clustering state based on LLM output.
	•	Implements alert conditions based on threshold criteria.

Step05: step05_run_stage2.py
	•	Orchestrates complete Stage 2 workflow, handling token limit checks and detailed logging.

Other Files
	•	batch_generate_pdfs.py: Generates human-readable PDF reports summarizing clustered feedback.
	•	merge_course_feedback.py: Consolidates clustered pain points into a unified JSON file.
	•	run_daily_pipeline.py: Main orchestration script that sequences stages and logs pipeline health.

5. Orchestration & Scheduling

(Placeholder - to be completed)

6. Infrastructure

Environments
	•	Development and production environments maintained separately.

Resources
	•	Local or cloud-based environments.
	•	Playwright setup for PDF generation.

Security Considerations
	•	Sensitive keys (OpenAI API key) managed via environment variables.
	•	Restricted access to output data directories.

7. Monitoring & Alerting

Metrics
	•	Posts processed, pain points extracted, clustering statistics.

Logging
	•	Centralized logs in outputs/runs/YYYY-MM-DD/logs.
	•	Detailed logs per script/stage.

Error Notifications
	•	Alerts generated for clustering threshold exceedances.
	•	Logs provide comprehensive error details.

8. Error Handling & Recovery

Retry/Backfill Strategies
	•	Automatic retries on LLM/API call failures.
	•	Idempotent design allows re-running scripts safely.

9. Versioning & Governance

Change Management Practices
	•	Git-based version control.
	•	Pull request workflows for review and approvals.
	•	Documented changes in commit messages and pipeline logs.

10. Examples

Sample Input Data

{"post_id": "abc123", "text": "The OA instructions were unclear..."}

Sample Output Data

{
  "num_pain_points": 1,
  "pain_points": [
    {
      "pain_point_summary": "Student confused by OA instructions.",
      "root_cause": "Unclear instructions",
      "quoted_text": "The OA instructions were unclear..."
    }
  ]
}

Execution Flow Example
	1.	Fetch posts.
	2.	Classify posts into pain points.
	3.	Group by course and cluster.
	4.	Generate PDF reports.

Configuration Files

Configuration driven by:
	•	config/common.py (shared paths, keys)
	•	config/stage1.py & config/stage2.py (stage-specific paths, settings)

Interaction between Stages
	•	Stage 1 outputs feed directly into Stage 2 as inputs.
	•	OTHER_FILES (batch_generate_pdfs.py, merge_course_feedback.py) use Stage 2 outputs to produce final artifacts.