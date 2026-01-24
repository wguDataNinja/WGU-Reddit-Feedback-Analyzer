# WGU-Reddit Snapshot — Static Website

This directory contains the **static Hugo website** that accompanies the WGU-Reddit Analyzer capstone project.

The website is a **presentation-only deliverable**. It performs **no analysis**, runs **no models**, and applies **no transformations** to the data it displays.

All analytical behavior, guarantees, and artifacts are defined exclusively in `docs/PIPELINE_SPEC.md`.

---

## Role in the Project

The website exists to:

- Present the **final, frozen outputs** of the analytical pipeline.
- Allow reviewers and stakeholders to **inspect results without interacting with code or CSV files**.
- Demonstrate how a reproducible, artifact-based LLM pipeline can be surfaced through a static interface.

The site is intentionally:
- Static
- Read-only
- Backed by precomputed artifacts
- Decoupled from all analysis and inference

---

## Data Source and Snapshot

All content shown on the site comes from a **single fixed snapshot** of Reddit discussion about WGU courses.

Snapshot characteristics:
- 1,103 Reddit posts
- 242 courses
- Posts created between June 18, 2018 and October 3, 2025
- Filtered for strongly negative sentiment
- Counts represent **posts**, not students

No live data collection or refresh occurs.

---

## Relationship to the Pipeline

The website consumes **only Stage 4 outputs** of the pipeline, including:

- `post_master.csv`
- `course_summary.csv`
- `global_issues.csv`
- `issue_course_matrix.csv`
- Precomputed per-course and per-issue detail files

These artifacts are converted into Hugo-friendly static data files prior to site build.

The site itself:
- Performs no joins
- Performs no aggregation
- Performs no filtering beyond client-side search over static payloads
- Executes no LLM calls

---

## Pages and Functionality

### Homepage
Provides a high-level overview of the project and snapshot, including:
- Total post and course counts
- Courses with highest discussion volume
- Most common cross-course issue categories
- Top categories by college

### About
Explains the motivation, research context, and high-level pipeline used to produce the snapshot. Includes a pipeline diagram and clarifies that the site is presentation-only.

### Privacy
Describes data handling and privacy constraints:
- All content is from public Reddit posts
- No usernames or identifiers are shown
- No private or restricted data is used
- No live collection occurs

### Courses
Lists all courses present in the snapshot, ordered by post volume. Course detail pages show:
- Course-level counts
- Associated colleges
- Clustered difficulty categories
- Example excerpts (truncated and privacy-scanned)

### Categories
Lists cross-course issue categories aligned by the pipeline. Category detail pages show:
- Description of the category
- Affected courses and colleges
- Aggregate counts

### Source Posts
Provides a searchable, filterable view of the underlying Reddit posts used in the snapshot. Filtering operates only on static data.

---

## Interpretation Guidance

- Counts reflect **discussion volume**, not prevalence or severity.
- Category names summarize patterns in student discussion and are not official classifications.
- The site does not evaluate course quality, student performance, or satisfaction.
- Ordering reflects counts only.

---

## Implementation Notes

- Built with Hugo as a static site.
- All data is precomputed and bundled at build time.
- No server-side logic is present.
- No runtime dependencies on the analytical pipeline exist.

---

## Non-Goals

The website does not:
- Run or reproduce the pipeline
- Provide live updates
- Perform inference or interpretation
- Replace the technical documentation

For analytical details, reproducibility guarantees, and artifact definitions, refer to `docs/PIPELINE_SPEC.md`.
