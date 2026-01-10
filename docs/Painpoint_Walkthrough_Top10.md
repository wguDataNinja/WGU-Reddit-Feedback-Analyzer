# Course Painpoint and Cluster Walkthrough

This document presents a walkthrough of how student pain points were extracted, grouped, and normalized across a sample of ten Western Governors University (WGU) courses. The full dataset includes additional courses; these ten are shown because they contain the most pain points.

All work was performed automatically using a three-stage large language model pipeline with no human review or manual editing. The same process was applied consistently:

1. Stage 0 — collect strongly negative Reddit student posts about specific WGU courses.
2. Stage 1 — extract direct pain points from those posts.
3. Stage 2 — cluster similar pain points within each course based on student language.
4. Stage 3 — normalize clusters into a shared issue taxonomy across courses.
5. Redundancy reduction — show how many raw clusters consolidate into fewer normalized issues.

Each course section below shows:

- counts at each stage,
- the raw Stage-2 cluster wording,
- the Stage-3 normalized category,
- the number of posts in each issue,
- and a short student excerpt that demonstrates cluster validity.

These samples allow quick visual confirmation of proper grouping and consistency in issue labeling.

---

## D287 – Java Frameworks

Pipeline summary:
- Stage 0 posts: 16
- Stage 1 painpoints: 11
- Stage 2 clusters: 6
- Stage 3 normalized issues: 6
- Redundancy reduction: 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Unclear or misaligned assignment and rubric requirements for UI customization and inventory behavior | unclear_or_ambiguous_instructions | 5 | "inventory maximum and minimum validation is not working correctly" |
| Missing or incorrect form validation messages in starter code | missing_or_broken_resources | 2 | "custom validator doesn’t display a message" |
| Evaluator reports build/runtime errors not reproducible locally | evaluator_inconsistency_or_poor_feedback | 1 | "evaluator is claiming it won’t build… runs fine for me" |
| Poorly formatted starter code modeled as required example | missing_or_low_quality_materials | 1 | "pre-existing code is formatted terribly" |
| Course assumes Java file I/O knowledge not previously covered | prerequisite_gaps_or_unpreparedness | 1 | "never seen FileInputStream or PrintWriter before" |
| Starter files misconfigured (ports, DB names, properties) | tooling_environment_misconfiguration_or_guidance | 1 | "localhost:8080 not working… had to use alternate port" |

---

## D197 – Version Control

Pipeline summary:
- Stage 0 posts: 19
- Stage 1 painpoints: 11
- Stage 2 clusters: 4
- Stage 3 normalized issues: 4
- Redundancy reduction: 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Unclear requirements for evidence and artifacts | unclear_or_ambiguous_instructions | 6 | "does it matter what the changes are" |
| Outdated or missing course media | missing_or_broken_resources | 2 | "can’t find these videos anywhere" |
| Repository access and authentication failures | platform_or_environment_failures | 2 | "could not be found or you don’t have permission" |
| Pipeline artifacts not produced after CI | tooling_environment_misconfiguration_or_guidance | 1 | "pipeline ran but workspace doesn’t show expected files" |

---

## D427 – Data Management – Applications

Pipeline summary:
- Stage 0 posts: 29
- Stage 1 painpoints: 10
- Stage 2 clusters: 6
- Stage 3 normalized issues: 5
- Redundancy reduction: 16.7%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| ZyBooks autograder and environment bugs | platform_or_environment_failures | 4 | "ZyBooks kept marking a primary key wrong" |
| Practice materials are misaligned with OA | assessment_material_misalignment | 3 | "practice tests scoring 80s… OA felt different" |
| Assessment content errors or internal inconsistencies | grading_or_answer_key_or_process_issues | 1 | "asked to create view MyMovie… correct syntax but rejected" |
| Missing ZyBooks labs referenced by course | missing_or_broken_resources | 1 | "lab 7 and 8 not present anywhere" |
| No clear rules on formatting for machine-graded SQL | unclear_or_ambiguous_instructions | 1 | "does it care about capitalization, spacing, quotes" |

Merged issues:
- platform_or_environment_failures combines 2 Stage-2 clusters.

---

## C777 – Web Development Applications

Pipeline summary:
- Stage 0 posts: 24
- Stage 1 painpoints: 9
- Stage 2 clusters: 6
- Stage 3 normalized issues: 6
- Redundancy reduction: 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Practice materials not representative of OA | assessment_material_misalignment | 2 | "scored 80 percent on practice… failed OA hard" |
| CSS content contradictory or inconsistent | missing_or_low_quality_materials | 2 | "keeps going over flex, box, grid but not consistently" |
| OA launch errors or platform failures | platform_or_environment_failures | 2 | "pressed take test… got error message" |
| Instructor responsiveness issues | instructor_or_support_unresponsiveness | 1 | "can’t get instructors to approve retake" |
| Broken links in study guide | missing_or_broken_resources | 1 | "broken links… nothing fixed" |
| Proctoring problems with video visibility | proctoring_or_exam_platform_issues | 1 | "proctor couldn’t see my video" |

---

## D196 – Principles of Financial and Managerial Accounting

Pipeline summary:
- Stage 0 posts: 22
- Stage 1 painpoints: 9
- Stage 2 clusters: 6
- Stage 3 normalized issues: 2
- Redundancy reduction: 66.7%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Coaching and pre-assessment reports blank or missing | platform_or_environment_failures | 5 | "coaching report blank" |
| Practice tests do not align with OA | assessment_material_misalignment | 4 | "questions on OA not in PA" |

Merged issues:
- assessment_material_misalignment combines 2 Stage-2 clusters.
- platform_or_environment_failures combines 4 Stage-2 clusters.

---

## D288 – Back-End Programming

Pipeline summary:
- Stage 0 posts: 21
- Stage 1 painpoints: 9
- Stage 2 clusters: 5
- Stage 3 normalized issues: 4
- Redundancy reduction: 20.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Seed data mismatches and 404 purchase requests | missing_or_broken_resources | 4 | "tracking number won’t show… 404 request" |
| Environment and configuration mismatch between lab and evaluator | tooling_environment_misconfiguration_or_guidance | 3 | "runs fine locally… evaluator says won’t compile" |
| Panopto outage blocking required video content | platform_or_environment_failures | 1 | "no access to javabits video" |
| Lab use unclear versus rubric requirements | unclear_or_ambiguous_instructions | 1 | "conflicted if lab environment required" |

Merged issues:
- missing_or_broken_resources combines 2 Stage-2 clusters.

---

## C214 – Financial Management

Pipeline summary:
- Stage 0 posts: 26
- Stage 1 painpoints: 8
- Stage 2 clusters: 4
- Stage 3 normalized issues: 3
- Redundancy reduction: 25.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Course resources misaligned with OA | assessment_material_misalignment | 5 | "OA was nothing like the PA" |
| PA Excel file will not load | platform_or_environment_failures | 2 | "problem with PA not loading in Excel" |
| Pre-assessment report missing | missing_or_broken_resources | 1 | "pre-assessment report empty" |

Merged issues:
- platform_or_environment_failures combines 2 Stage-2 clusters.

---

## D277 – Front-End Web Development

Pipeline summary:
- Stage 0 posts: 14
- Stage 1 painpoints: 7
- Stage 2 clusters: 6
- Stage 3 normalized issues: 5
- Redundancy reduction: 16.7%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Inconsistent evaluator application of rubric | evaluator_inconsistency_or_poor_feedback | 2 | "submitted and still rejected" |
| Instructor or tutor no-shows | instructor_or_support_unresponsiveness | 2 | "fifth attempt to get instructor help flaked" |
| Required hosting services unreliable | external_tool_dependency_risks | 1 | "hosting service is garbage" |
| Pipeline fails after commit | tooling_environment_misconfiguration_or_guidance | 1 | "pipeline failing after commit" |
| Assignment scope wording unclear | unclear_or_ambiguous_instructions | 1 | "what pages do I do requirements for" |

Merged issues:
- instructor_or_support_unresponsiveness combines 2 Stage-2 clusters.

---

## D278 – Scripting and Programming – Foundations

Pipeline summary:
- Stage 0 posts: 12
- Stage 1 painpoints: 7
- Stage 2 clusters: 5
- Stage 3 normalized issues: 5
- Redundancy reduction: 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Course prep materials do not align with OA expectations | assessment_material_misalignment | 2 | "not written like this in zybooks" |
| ZyBooks content poorly structured | missing_or_low_quality_materials | 2 | "zybooks material not great" |
| Exam browser malfunction | proctoring_or_exam_platform_issues | 1 | "browser stopped functioning" |
| Coral environment unclear | tooling_environment_misconfiguration_or_guidance | 1 | "not understanding how to set input variable" |
| Workflow forces wrong programming track | workflow_or_policy_barriers | 1 | "everyone starts in Java track" |

---

## D101 – Cost and Managerial Accounting

Pipeline summary:
- Stage 0 posts: 15
- Stage 1 painpoints: 7
- Stage 2 clusters: 4
- Stage 3 normalized issues: 4
- Redundancy reduction: 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|---------------------|-----------------------|----------:|----------------|
| Missing input data for Excel tasks | missing_or_low_quality_materials | 3 | "gives units but not required numbers" |
| Quiz questions misaligned with covered content | assessment_material_misalignment | 2 | "questions require content not yet taught" |
| False similarity flags with no guidance | ai_detection_confusion_and_false_flags | 1 | "similarity over 50 percent every time" |
| Proctor interruptions remove exam time | proctoring_or_exam_platform_issues | 1 | "proctor took fifty minutes" |