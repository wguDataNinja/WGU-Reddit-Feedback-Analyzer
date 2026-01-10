# WGU Reddit Analyzer – Schema and Hierarchy

Schema version: `1.0.0`  
Last updated: 2025-12-10

## 1. Top-level classes (Stage 1)

We classify each post into one of three mutually exclusive values:

- `y` – contains a **fixable course-side pain point**
- `n` – **does not** contain a fixable course-side pain point
- `u` – **unknown / unusable** due to parsing or schema issues

### Definition: fixable course-side pain point

A post has a course-side pain point if it describes a persistent, actionable problem that:

- arises from the design, content, structure, assessment, or staffing of a WGU course or program, and  
- could plausibly be improved by faculty, course designers, or program leadership.

Examples of **in-scope** pain points:

- “The quizzes test content that never appears in the course materials.”
- “The project rubric is vague and my mentor gives different instructions.”
- “The labs keep timing out and support can’t fix it.”

Examples of **out-of-scope** issues (usually `n`):

- One-off technical glitches fixed by standard support.
- Purely personal situations (illness, work schedule) without course-level implications.
- Generic venting with no concrete, changeable problem.

The Stage 1 classifier must obey:

- On parse or schema error → `contains_painpoint = "u"`  
- `confidence_pred` is always in `[0.0, 1.0]` (invalid values are coerced to `0.0`)

---

## 2. Global normalized issue labels (Stage 3)

Global issues represent reusable, cross-course problem types. They are shared across courses.

Current catalog (schema_version `1.0.0`):

1. `assessment_material_misalignment`  
   - **Definition:** Assessments test content that is missing, under-emphasized, or inconsistent with course materials.  
   - **Examples:**  
     - “The OA covered topics that were never mentioned in the modules.”  
     - “Practice questions are nothing like the actual exam.”

2. `unclear_or_ambiguous_instructions`  
   - **Definition:** Students cannot understand what is required due to vague, contradictory, or missing instructions.  
   - **Examples:**  
     - “The project instructions and rubric contradict each other.”  
     - “I don’t know what artifacts I’m supposed to upload.”

3. `course_pacing_or_workload`  
   - **Definition:** The expected time or effort is unreasonable relative to credits or other courses.  
   - **Examples:**  
     - “This 3-credit course is more work than my entire term.”  
     - “Deadlines pile up in the last week with no warning.”

4. `technology_or_platform_issues`  
   - **Definition:** Persistent issues with labs, third-party platforms, or course-integrated tools.  
   - **Examples:**  
     - “The lab environment crashes every time I start task 3.”  
     - “The proctoring tool disconnects and I have to start over.”

5. `staffing_or_instructor_availability`  
   - **Definition:** Difficulty getting timely help from course instructors, evaluators, or mentors for course-specific questions.  
   - **Examples:**  
     - “My course instructor hasn’t responded in two weeks.”  
     - “No one is available to clarify the project rubric.”

6. `course_structure_or_navigation`  
   - **Definition:** The layout or ordering of content makes it hard to progress logically.  
   - **Examples:**  
     - “Modules reference content that appears later in the course.”  
     - “Important resources are buried and hard to find.”

7. `prerequisite_or_readiness_mismatch`  
   - **Definition:** Course assumes knowledge or skills students commonly lack, or repeats material excessively.  
   - **Examples:**  
     - “This course expects advanced statistics we never learned.”  
     - “Half the course repeats content from the previous class.”

8. `other_or_uncategorized`  
   - **Definition:** Real, course-side pain points that do not fit any other label or represent new/emerging themes.  
   - **Examples:**  
     - “Mentor incentives create pressure to accelerate through this course.”  
     - “Mandatory live sessions are at impossible times.”

---

## 3. Hierarchy

The system enforces a four-level hierarchy:

1. **Post**  
   - Unit: Reddit post (optionally with comments).  
   - Source: `stage0_filtered_posts.jsonl` (frozen).

2. **Pain point presence (Stage 1)**  
   - `contains_painpoint ∈ {"y", "n", "u"}`  
   - Only posts with `contains_painpoint = "y"` flow into Stage 2.  
   - Any parse/schema failure sets `contains_painpoint = "u"`.

3. **Course-level cluster (Stage 2)**  
   - For each course, Stage 2 groups pain-point posts into clusters:  
     - `course_cluster_id` (unique within course)  
     - `course_cluster_label` (short human-readable label)  
     - `course_cluster_summary` (1–3 sentence description)  
   - Each pain-point post belongs to **one or more** course clusters (multi-membership allowed via semicolon-separated IDs).

4. **Global issue label (Stage 3)**  
   - Stage 3 maps course clusters to exactly one of:  
     - A global issue label from the catalog above, or  
     - A special `unassigned` status if not yet mapped.  
   - Every `course_cluster_id` appears exactly once in the global index:
     - Either assigned to a global issue label, or  
     - Marked as `unassigned`.

Stage 4 consumes this hierarchy and produces deterministic tables:

- `post_master.csv` – post → pain point → course cluster(s) → global issue(s)  
- `course_summary.csv` – course-level counts and highlights  
- `global_issues.csv` – global issue metrics and examples  
- `issue_course_matrix.csv` – matrix of global issue by course

All Stage 4 tables must include a `schema_version` column.

---

## 4. Schema versioning

The current schema version is:

- `schema_version = "1.0.0"`

It must appear in:

- Stage 1 / 2 / 3 run manifests (as a field).  
- Stage 4 tables (as a column).  
- Any serialized prediction or cluster records that cross stage boundaries.

Schema changes (label set, definitions, hierarchy) must increment this version and be described in `docs/schema_and_hierarchy.md`.