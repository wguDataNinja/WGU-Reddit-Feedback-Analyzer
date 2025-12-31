# WGU Course Issues Report

This document presents how student pain points were extracted, grouped, and normalized across a sample of the ten courses with the highest number of extracted painpoints. The full dataset can be explored in the `WGU-Reddit Analyzer GUI` and the CSV/JSONL artifacts in `artifacts/report_data/`.

All work was performed with an unsupervised multi-stage large language model pipeline with no manual editing.

- Stage 0 — collect strongly negative Reddit student posts about specific WGU courses.
- Stage 1 — extract direct pain points from those posts into structured records.
- Stage 2 — cluster similar pain points within each course based on the root cause.
- Stage 3 — normalize clusters into a shared issue taxonomy across courses.

---

## Pipeline walkthrough on one example post

This section follows a single Reddit post (`1d80my9`) through all four stages of the pipeline.

### Stage 0 – Post filtering

Stage 0 selects strongly negative Reddit posts that mention a specific WGU course, using course code and sentiment filters. Course code, title, and college are looked up from the WGU catalog, and we use the VADER sentiment model (social-media sentiment) with a `vader_compound ≤ -0.2` filter so Stage 0 focuses on clearly negative posts.

**Example Post:**

`post_id`: `1d80my9`
`course`: D287 – Java Frameworks — School of Technology
`title`: D287 - Confused About Associating Parts
`vader_compound`: -0.9032

`selftext` (truncated):
```text
This PA has been pretty easy-breezy for me so far but then I've gotten to part H. I already did bullets 1 and 3 but I am stuck on the second bullet here and I need some guidance. I've done some research and it seems like I'm not the only one who has had this question, but none of the responses people have gotten has cleared this up for me.

In case it's been a while since you've taken the course or you need a quick refresher on what part H is all about:

H.  Add validation for between or at the maximum and minimum fields. The validation must include the following:

* Display error messages for low inventory when adding and updating parts if the inventory is less than the minimum number of parts.
* **Display error messages for low inventory when adding and updating products lowers the part inventory below the minimum.**
* Display error messages when adding and updating parts if the inventory is greater than the maximum.

I am stuck on this part because nowhere before this section did the course say we need to have the products and parts associated. Ultimately, I really have one question:

1. Do I need to make it so that the products I create on the first startup have parts associated with them already?
```

`permalink`:
  https://www.reddit.com/r/WGU_CompSci/comments/1d80my9/d287_confused_about_associating_parts/
___
### Stage 1 – Painpoint extraction

Stage 1 uses an LLM to decide whether the post contains at least one course-side pain point and to extract a quoted snippet and summary.

<details>
<summary><strong>Stage 1 LLM prompt</strong></summary>

```text
You are a course designer reviewing a Reddit post about a WGU course.

A pain point is a negative student experience caused by a specific, fixable flaw in course design, materials, instructions, assessments, evaluator behavior, or platform.
Only label y when the post states or clearly implies such a defect.

Valid course defects (eligible for “y”):
• contradictory, unclear, or misleading rubric/instructions
• broken, outdated, or missing required materials
• evaluator inconsistency or misapplication of rubric
• platform/system malfunction preventing progress
• misalignment between course materials and assessments

Always label “n” when the post is mainly:
• emotional struggle, discouragement, OA fear
• requests for study tips, strategies, or “how do I pass”
• debugging help or evaluator-feedback interpretation without claiming a defect
• celebration or “I passed” posts
• WGU policy, mentor, program, deadline, or term-structure questions
• external certification exam or third-party proctoring issues
• vague dissatisfaction (“disorganized,” “instructor unhelpful”) without a concrete flaw

Borderline:
Difficulty alone ≠ defect. If no specific fixable issue is named or implied, label n.
Use u only when the post is too vague to determine if a defect exists.

Examples (compressed):
Not a pain point: “I’m terrified I’ll fail C201.”
Not a pain point: “Any tips for D335?”
Not a pain point: “My code won’t run; what am I missing?”
Not a pain point: “What happens if I don’t finish tasks before term end?”
Clear pain point: “The OA covered topics not in the readings.”
Clear pain point: “Rubric says X but evaluator demanded Y.”

Read the post and identify all distinct pain points. Merge duplicates.

Return exactly one JSON object:

{
“contains_painpoint”: “y” | “n” | “u”,
“confidence”: number between 0.0 and 1.0,
“pain_points”: [
{
“root_cause_summary”: “…”,
“pain_point_snippet”: “[…]”
}
]
}

If “n” or “u”, set pain_points to [] and include no extra fields.

Reddit post metadata:
• post_id: {post_id}
• course_code: {course_code}

Reddit post text:
{post_text}
```

</details>

Stage 1 Output, from example post:
Stage 1 — painpoint 1: `root cause summary`
  The PA rubric requires validation that adding/updating products can lower part inventory below a part's minimum, which implies products must be associated with parts, but the course materials never explained or required associating parts with products (or pre-populating startup data). This is an unclear/misaligned instruction in the assignment.

Stage 1 — painpoint 1: `quoted snippet`
  Display error messages for low inventory when adding and updating products lowers the part inventory below the minimum.

___
### Stage 2 – Within-course clustering

Stage 2 groups painpoints within a course into clusters that share the same underlying course-side issue (root cause).

For D287 – Java Frameworks, Stage 1 produced 11 painpoints, which Stage 2 grouped into 6 course-level clusters.

<details>
<summary><strong>Stage 2 LLM prompt</strong></summary>

```text
You will receive social media posts about university course {course_code} – {course_title}.

Your task is to cluster the posts by their underlying, course-related pain points.

A pain point is a specific, actionable issue in the course’s design, delivery, instructions, materials, or support—a friction that WGU can realistically fix or improve.
Do not group based on general frustration, motivation, or personal struggle.
Cluster only the actionable, course-side issues described in the summaries/snippets.

Your responsibilities:
	1.	Cluster posts by shared root-cause issue, from the perspective of WGU course designers.
	2.	Focus only on actionable pain points (unclear instructions, outdated materials, rubric mismatches, broken tools, missing resources, etc.).
	3.	Produce clean JSON only, strictly following the structure below.
	4.	Assign cluster_ids using the format: COURSECODE_INT (example: C211_1).
	5.	Sort clusters by largest size first.
	6.	A post may appear in multiple clusters if appropriate.
	7.	Output raw JSON only — no explanations, no commentary.

⸻

REQUIRED JSON STRUCTURE

{
  "courses": [
    {
      "course_code": "COURSE_CODE",
      "course_title": "COURSE_TITLE",
      "total_posts": 0,
      "clusters": [
        {
          "cluster_id": "COURSECODE_1",
          "issue_summary": "short root-cause description",
          "num_posts": 0,
          "post_ids": [
            "post_id_1",
            "post_id_2"
          ]
        }
      ]
    }
  ]
}


⸻

EXAMPLE OUTPUT

{
  "courses": [
    {
      "course_code": "C211",
      "course_title": "Scripting and Programming – Applications",
      "total_posts": 5,
      "clusters": [
        {
          "cluster_id": "C211_1",
          "issue_summary": "no instructor response for approvals or passwords",
          "num_posts": 3,
          "post_ids": ["1ci7efm", "1e12ncu", "1i5z4ev"]
        },
        {
          "cluster_id": "C211_2",
          "issue_summary": "OA result stuck, blocking progress",
          "num_posts": 1,
          "post_ids": ["1lu24vq"]
        },
        {
          "cluster_id": "C211_3",
          "issue_summary": "PA doesn’t match OAs",
          "num_posts": 1,
          "post_ids": ["1m2hl4r"]
        }
      ]
    }
  ]
}
```

</details>

Stage-2 clusters for this course:

| cluster_id | stage2_cluster_label | num_posts |
|-----------|----------------------|----------:|
| D287_1 | Unclear or misaligned assignment/rubric requirements for UI customization and inventory behavior (associating product... ← contains example post | 5 |
| D287_3 | Form validation messages not shown due to missing/incorrect HTML or form configuration in provided files, hindering u... | 2 |
| D287_2 | Course starter/project files misconfigured (database names, ports, application properties) preventing local server fr... | 1 |
| D287_4 | Pre-existing course code formatting is inconsistent and poorly formatted, reducing clarity and modeling bad coding pr... | 1 |
| D287_5 | Automated evaluator or grading environment reports build/runtime errors not reproducible locally, indicating environm... | 1 |
| D287_6 | Course assumes prior knowledge of Java file I/O (FileInputStream, FileOutputStream, PrintWriter) that students haven'... | 1 |

___
### Stage 3 – Cross-course normalization

Stage 3 maps each course-specific cluster into a shared normalized issue label, so that structurally similar problems can be compared across courses and colleges.

<details>
<summary><strong>Stage 3 LLM prompt</strong></summary>

```text
You will receive a flat list of Stage-2 course-level pain point clusters.

Each cluster has:
	•	cluster_id
	•	issue_summary
	•	course_code (input only — do NOT include in output)
	•	course_title (input only — do NOT include in output)
	•	num_posts

Your job is to merge these into cross-course global issues.

⸻

ROOT-CAUSE CLASSIFICATION RULES
	•	Group clusters by the fixable course-side root cause only.
	•	If a summary includes both a cause and a symptom (e.g., “wrong resource list causing confusion”), classify by the course-side cause, never by the student symptom.
	•	Student feelings (confusion, stress, frustration, delay) are not categories.
	•	Exclusive assignment: each cluster_id appears once in the final output.

⸻

USE SEEDED GLOBAL ISSUE TYPES WHEN THEY MATCH

Reuse these labels exactly when applicable:

unclear_or_ambiguous_instructions
assessment_material_misalignment
platform_or_environment_failures
missing_or_low_quality_materials
evaluator_inconsistency_or_poor_feedback
workflow_or_policy_barriers
missing_or_broken_resources
instructor_or_support_unresponsiveness
tooling_environment_misconfiguration_or_guidance
grading_or_answer_key_or_process_issues
workload_or_scope_issues
proctoring_or_exam_platform_issues
scheduling_or_simulation_availability_issues
ai_detection_confusion_and_false_flags
prerequisite_gaps_or_unpreparedness
external_tool_dependency_risks

If a cluster fits one of these meanings, reuse that issue.
Create a new global issue only if no seeded one matches.

⸻

SORTING RULE

Sort global_clusters by total num_posts per issue (sum across its member clusters), highest first.

⸻

OUTPUT FORMAT (STRICT)

{
  "global_clusters": [
    {
      "provisional_label": "string",
      "normalized_issue_label": "string",
      "short_description": "string",
      "member_cluster_ids": ["id1","id2"]
    }
  ],
  "unassigned_clusters": ["cluster_id_a"]
}

	•	No text outside JSON
	•	Do not include course_code or course_title
	•	Every cluster_id must appear exactly once
```

</details>

For the example post, Stage 3 does:

- Stage-2 cluster: `D287_1`
- Stage-2 label: Unclear or misaligned assignment/rubric requirements for UI customization and inventory behavior (associating products/parts, inventory min/max, and tracking) leaving students unsure what to implement
- Stage-3 normalized issue label: `unclear_or_ambiguous_instructions`

This normalized issue appears in 85 posts across 56 courses.

Top courses with this issue:

| course_code | course_title | college | total_posts |
|-------------|-------------|---------|------------:|
| D197 | Version Control | School of Technology | 6 |
| D287 | Java Frameworks | School of Technology | 5 |
| D596 | The Data Analytics Journey | School of Technology | 3 |
| D335 | Introduction to Programming in Python | School of Technology | 3 |
| D602 | Deployment | School of Technology | 3 |
| D660 | Instructional Technology and Online Pedagogy | School of Education | 3 |
| C716 | Business Communication | School of Business | 3 |
| D483 | Security Operations | School of Technology | 2 |


---

## Top 10 courses by painpoints

Each course section below shows:

- counts at each stage,
- the raw Stage-2 cluster wording,
- the Stage-3 normalized category,
- the number of posts in each issue,
- and sample Reddit posts that demonstrate cluster validity.

Column legend:
- `stage2_cluster_label` – course-level description from Stage 2
- `normalized_issue_label` – shared issue category from Stage 3
- `num_posts` – number of posts assigned to that normalized issue
- `example_snippet` – short excerpt illustrating the issue

Courses are ordered by Stage-1 painpoint count (highest to lowest).

---

<details>
<summary><strong>D287 – Java Frameworks — School of Technology</strong></summary>


Pipeline summary:
- Stage 0 posts: 16
- Stage 1 painpoints: 11
- Stage 2 clusters: 6
- Stage 3 normalized issues: 6
- Redundancy reduction (Stage 2 → 3): 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Unclear or misaligned assignment/rubric requirements for UI customization and inventory behavior (associating product... | unclear_or_ambiguous_instructions |         5 | [Attempt 3 report comments: ... inventory maximum and minimum validation is not working correctly. Attempt 4 report c... |
| Form validation messages not shown due to missing/incorrect HTML or form configuration in provided files, hindering u... | missing_or_broken_resources |         2 | the custom validator I made to confirm the inventory is between the min and max inventory works but doesn't display a... |
| Automated evaluator or grading environment reports build/runtime errors not reproducible locally, indicating environm... | evaluator_inconsistency_or_poor_feedback |         1 | The evaluator is claiming it won't build and is experiencing CommandLineRunner errors... I am able to run and build t... |
| Pre-existing course code formatting is inconsistent and poorly formatted, reducing clarity and modeling bad coding pr... | missing_or_low_quality_materials |         1 | “pre-existing code is formatted in Java Frameworks actually terrible… Not to mention none of it is consistent. They N... |
| Course assumes prior knowledge of Java file I/O (FileInputStream, FileOutputStream, PrintWriter) that students haven'... | prerequisite_gaps_or_unpreparedness |         1 | After just finishing Java Fundamentals, I've never seen any of these 3 things... I want to learn how to use FileInput... |
| Course starter/project files misconfigured (database names, ports, application properties) preventing local server fr... | tooling_environment_misconfiguration_or_guidance |         1 | my localhost:8080 was not working... I was able to still access the website... by using localhost:63342. After meetin... |

Sample Reddit posts by normalized issue

**`unclear_or_ambiguous_instructions`** (5 posts)
- `1d80my9` – D287 - Confused About Associating Parts
  https://www.reddit.com/r/WGU_CompSci/comments/1d80my9/d287_confused_about_associating_parts/
- `1era7to` – D287 Task C
  https://www.reddit.com/r/WGU_CompSci/comments/1era7to/d287_task_c/
- `1f38klq` – Java Frameworks - D287 Task G
  https://www.reddit.com/r/WGU_CompSci/comments/1f38klq/java_frameworks_d287_task_g/

**`missing_or_broken_resources`** (2 posts)
- `1fz1860` – D287 PA- Section H validator logic works but not returning message, ideas?
  https://www.reddit.com/r/WGU_CompSci/comments/1fz1860/d287_pa_section_h_validator_logic_works_but_not/
- `1grzgjg` – D287 Part H validator working but won't display error.
  https://www.reddit.com/r/WGU_CompSci/comments/1grzgjg/d287_part_h_validator_working_but_wont_display/

**`evaluator_inconsistency_or_poor_feedback`** (1 posts)
- `1jdkvg0` – D287 Evaluator is citing an error that will not replicate on my system?
  https://www.reddit.com/r/WGU_CompSci/comments/1jdkvg0/d287_evaluator_is_citing_an_error_that_will_not/

**`missing_or_low_quality_materials`** (1 posts)
- `1hyofpu` – D287 - Terrible Code Formatting?
  https://www.reddit.com/r/WGU_CompSci/comments/1hyofpu/d287_terrible_code_formatting/

**`prerequisite_gaps_or_unpreparedness`** (1 posts)
- `1nh2uyk` – Confused about D287 Java Frameworks, need advise pls :)
  https://www.reddit.com/r/WGU_CompSci/comments/1nh2uyk/confused_about_d287_java_frameworks_need_advise/

**`tooling_environment_misconfiguration_or_guidance`** (1 posts)
- `1by7wbq` – D287 -- Struggling? May be the course and not you, reach out to an Instructor
  https://www.reddit.com/r/WGU_CompSci/comments/1by7wbq/d287_struggling_may_be_the_course_and_not_you/

</details>


---

<details>
<summary><strong>D197 – Version Control — School of Technology</strong></summary>


Pipeline summary:
- Stage 0 posts: 19
- Stage 1 painpoints: 11
- Stage 2 clusters: 4
- Stage 3 normalized issues: 4
- Redundancy reduction (Stage 2 → 3): 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Unclear or inconsistent submission/rubric requirements about required evidence and artifacts (specific screenshots, C... | unclear_or_ambiguous_instructions |         6 | Does it matter what the changes are? I hate the vagueness in this task, they don't even give us a general direction w... |
| Outdated or missing instructional materials (removed PA videos, screenshots that no longer match current GitLab UI) | missing_or_broken_resources |         2 | [I can't seem to find these videos anywhere... Or did WGU just outright remove the videos?] |
| Repository access/authentication problems preventing students from cloning or accessing course GitLab repos (404 link... | platform_or_environment_failures |         2 | [...] I keep getting the "could not be found or you don't have permission to view it" error. [...] SOLVED: I have old... |
| Course pipeline or environment not producing expected artifacts in the D197 workspace after running CI steps | tooling_environment_misconfiguration_or_guidance |         1 | I've been stuck at step 9 of "Gitlab How To" wherein you have to run the pipeline and after I ran it I don't see any ... |

Sample Reddit posts by normalized issue

**`unclear_or_ambiguous_instructions`** (6 posts)
- `1b8ks9p` – d197 Version Control help.
  https://www.reddit.com/r/WGU_CompSci/comments/1b8ks9p/d197_version_control_help/
- `1bco480` – D197 Version Control, screen shots
  https://www.reddit.com/r/WGU_CompSci/comments/1bco480/d197_version_control_screen_shots/
- `1j1cwxy` – D197 Part C
  https://www.reddit.com/r/wgu_devs/comments/1j1cwxy/d197_part_c/

**`missing_or_broken_resources`** (2 posts)
- `1lhdi9o` – D197 - Version Control - Where can I find Dr. Tomeos videos?
  https://www.reddit.com/r/WGU_CompSci/comments/1lhdi9o/d197_version_control_where_can_i_find_dr_tomeos/
- `1lqxp9w` – D197 GitLab Environment stuck on repository graph
  https://www.reddit.com/r/WGU/comments/1lqxp9w/d197_gitlab_environment_stuck_on_repository_graph/

**`platform_or_environment_failures`** (2 posts)
- `1bqrzmb` – D197 Submission Link 404 Error
  https://www.reddit.com/r/WGU_CompSci/comments/1bqrzmb/d197_submission_link_404_error/
- `1cly2hq` – D197 Version Control help
  https://www.reddit.com/r/WGU_CompSci/comments/1cly2hq/d197_version_control_help/

**`tooling_environment_misconfiguration_or_guidance`** (1 posts)
- `1gl3fu1` – WGU-D197-Step 9-Gitlab How to
  https://www.reddit.com/r/WGU_CompSci/comments/1gl3fu1/wgud197step_9gitlab_how_to/

</details>


---

<details>
<summary><strong>D427 – Data Management - Applications — School of Technology</strong></summary>


Pipeline summary:
- Stage 0 posts: 29
- Stage 1 painpoints: 10
- Stage 2 clusters: 6
- Stage 3 normalized issues: 5
- Redundancy reduction (Stage 2 → 3): 16.7%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| ZyBooks autograder/test harness and environment bugs (parser errors, execution timeouts, MySQL/version or environment... | platform_or_environment_failures |         4 | [...] There was one questions that I kept getting wrong according to ZyBooks, it was asking to add a primary key to a... |
| Practice materials, PAs, and study guides are outdated or misaligned with the proctored OA (content, question styles,... | assessment_material_misalignment |         3 | [Honestly took all 3 Practice tests scoring in the 80s and studied the redword study guide and none of that felt like... |
| Assessment content errors/typos and internal inconsistencies (e.g., mismatched object names between prompt and test c... | grading_or_answer_key_or_process_issues |         1 | [one question asked me to create a view called MyMovie. I created the view, correct syntax, but when I ran it, there ... |
| Required ZyBooks labs referenced by students/instructions are missing from the course materials (lab 7 and 8 not pres... | missing_or_broken_resources |         1 | I literally do not see it anywhere when I go thru the course material... EVERYONE is saying do the zybooks lab 7 and ... |
| Lack of clear grading/formatting guidance for machine‑graded SQL (unclear rules on capitalization, spacing, quotes, d... | unclear_or_ambiguous_instructions |         1 | I know that the test is graded by machine and cares about capitalization. My question ... does anyone know if it care... |

Merged issues (multiple Stage-2 clusters per normalized label):
- platform_or_environment_failures combines 2 Stage-2 clusters in D427.

Sample Reddit posts by normalized issue

**`platform_or_environment_failures`** (4 posts)
- `1fbzi1g` – Has anyone had issues testing SQL with Zybooks? 
  https://www.reddit.com/r/WGU_Accelerators/comments/1fbzi1g/has_anyone_had_issues_testing_sql_with_zybooks/
- `1ke2mfm` – Just had the worst testing experience D427 OA
  https://www.reddit.com/r/WGUIT/comments/1ke2mfm/just_had_the_worst_testing_experience_d427_oa/
- `1ki7dpf` – Having Trouble With Zybooks PA D427 DATA MANAGEMENT
  https://www.reddit.com/r/WGU/comments/1ki7dpf/having_trouble_with_zybooks_pa_d427_data/
- `1ni5x75` – D427 - Question about ZyBooks Labs (Syntax Error)
  https://www.reddit.com/r/WGUCyberSecurity/comments/1ni5x75/d427_question_about_zybooks_labs_syntax_error/

**`assessment_material_misalignment`** (3 posts)
- `1fnzs9g` – This class is trash
  https://www.reddit.com/r/WGUCyberSecurity/comments/1fnzs9g/this_class_is_trash/
- `1lboa9z` – D427v3 PA Question
  https://www.reddit.com/r/WGU_CompSci/comments/1lboa9z/d427v3_pa_question/
- `1njtta8` – D427 Failed Exam
  https://www.reddit.com/r/WGU/comments/1njtta8/d427_failed_exam/

**`grading_or_answer_key_or_process_issues`** (1 posts)
- `1kdhnm6` – Passed D427 - Data Management Applications - My First Attempt! Please Read To Save Yourself!
  https://www.reddit.com/r/wgu_devs/comments/1kdhnm6/passed_d427_data_management_applications_my_first/

**`missing_or_broken_resources`** (1 posts)
- `1kffhci` – Is D427 ZyBooks Lab 7/8 gone??
  https://www.reddit.com/r/WGU/comments/1kffhci/is_d427_zybooks_lab_78_gone/

**`unclear_or_ambiguous_instructions`** (1 posts)
- `1ksc94f` – D427 Data Management Applications
  https://www.reddit.com/r/WGU/comments/1ksc94f/d427_data_management_applications/

</details>


---

<details>
<summary><strong>C777 – Web Development Applications — School of Technology</strong></summary>


Pipeline summary:
- Stage 0 posts: 24
- Stage 1 painpoints: 9
- Stage 2 clusters: 6
- Stage 3 normalized issues: 6
- Redundancy reduction (Stage 2 → 3): 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Practice materials and Practice Assessment (PA) are not representative of the Objective Assessment (OA), causing stud... | assessment_material_misalignment |         2 | Don't waste your time with Quizzets. I scored over 80% on each test. These test are easy to guess ... Failed the fuck... |
| Course content is disorganized or presented inconsistently/contradictorily (e.g., CSS topics not structured clearly),... | missing_or_low_quality_materials |         2 | Working on the CSS portion. Makes no sense. Keeps going over flex and box and grid, but not consistently. |
| Platform/system errors prevent students from accessing or launching scheduled OAs (errors, queues, or failed launches... | platform_or_environment_failures |         2 | At 11:40pm on the dot after the timer ran down I was given access to take the test button. I pressed it and.....GOT a... |
| Instructor/course team unresponsiveness or delays in approving time-sensitive requests (e.g., retake approvals), risk... | instructor_or_support_unresponsiveness |         1 | [Can't get any instructors to approve me for a retake of the C777 OA ... I emailed the instructor last week, automate... |
| Broken or missing links and study guide resources that remain unrepaired after feedback, leaving required materials i... | missing_or_broken_resources |         1 | [...broken links in the study guide... I even emailed feedback about some of them and was emailed back that the issue... |
| Proctoring/connectivity problems during live proctored exams (proctor can't see video), risking exam validity or flags. | proctoring_or_exam_platform_issues |         1 | Proctor said they couldn’t see my video during the exam ... I immediately looked at my webcam ... they said "okay I s... |

Sample Reddit posts by normalized issue

**`assessment_material_misalignment`** (2 posts)
- `1c1vf93` – Fuck C777.
  https://www.reddit.com/r/WGUIT/comments/1c1vf93/fuck_c777/
- `1kh8lb4` – Web Development C777
  https://www.reddit.com/r/WGU/comments/1kh8lb4/web_development_c777/

**`missing_or_low_quality_materials`** (2 posts)
- `1e4jxx7` – C777 - Web Applications Dev.      Holy crap is this class poorly laid out.
  https://www.reddit.com/r/WGU_BSIT/comments/1e4jxx7/c777_web_applications_dev_holy_crap_is_this_class/
- `1l6s63q` – Frustrated Rant!
  https://www.reddit.com/r/WGU/comments/1l6s63q/frustrated_rant/

**`platform_or_environment_failures`** (2 posts)
- `1ftiqcp` – I can't Sleep....
  https://www.reddit.com/r/WGUIT/comments/1ftiqcp/i_cant_sleep/
- `1krvn5n` – C777 OA (or any OA error)
  https://www.reddit.com/r/WGU/comments/1krvn5n/c777_oa_or_any_oa_error/

**`instructor_or_support_unresponsiveness`** (1 posts)
- `1kxvduo` – Can't get any instructors to approve me for a retake of the C777 OA, so looks like I'm failing it. (vent)
  https://www.reddit.com/r/WGU/comments/1kxvduo/cant_get_any_instructors_to_approve_me_for_a/

**`missing_or_broken_resources`** (1 posts)
- `1gxegch` – C777 Study Guide Broken Links
  https://www.reddit.com/r/WGUIT/comments/1gxegch/c777_study_guide_broken_links/

**`proctoring_or_exam_platform_issues`** (1 posts)
- `1ng8x0e` – Proctor advised he couldn’t see my video mid exam
  https://www.reddit.com/r/WGU/comments/1ng8x0e/proctor_advised_he_couldnt_see_my_video_mid_exam/

</details>


---

<details>
<summary><strong>D196 – Principles of Financial and Managerial Accounting — School of Business</strong></summary>


Pipeline summary:
- Stage 0 posts: 22
- Stage 1 painpoints: 9
- Stage 2 clusters: 6
- Stage 3 normalized issues: 2
- Redundancy reduction (Stage 2 → 3): 66.7%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Coaching/pre-assessment reports or section-level feedback are missing or not displaying (blank), preventing students ... | platform_or_environment_failures |         5 | Can’t see Coaching report for D196?? I did a pre assessment yesterday but my score won’t show? This is all I can see |
| Practice assessments, module final tests, and PAs do not align with the Objective Assessment (OA), leaving students u... | assessment_material_misalignment |         4 | [Some questions that were on the OA weren't even included in the PA, and a few that were went slightly more indepth t... |

Merged issues (multiple Stage-2 clusters per normalized label):
- assessment_material_misalignment combines 2 Stage-2 clusters in D196.
- platform_or_environment_failures combines 4 Stage-2 clusters in D196.

Sample Reddit posts by normalized issue

**`platform_or_environment_failures`** (5 posts)
- `1ie22kq` – Probably a very stupid question
  https://www.reddit.com/r/wguaccounting/comments/1ie22kq/probably_a_very_stupid_question/
- `1jvo1mj` – Failed D196
  https://www.reddit.com/r/WGU/comments/1jvo1mj/failed_d196/
- `1k2wxpv` – Can’t see Coaching report for D196??
  https://www.reddit.com/r/wguaccounting/comments/1k2wxpv/cant_see_coaching_report_for_d196/
- `1kc7dpy` – D196-OA results not showing up
  https://www.reddit.com/r/WGU/comments/1kc7dpy/d196oa_results_not_showing_up/
- `1lr075i` – How many courses use MyEducator codes for tests?
  https://www.reddit.com/r/wguaccounting/comments/1lr075i/how_many_courses_use_myeducator_codes_for_tests/

**`assessment_material_misalignment`** (4 posts)
- `1h9qiii` – D196 Kicked me down again, considering another degree
  https://www.reddit.com/r/wguaccounting/comments/1h9qiii/d196_kicked_me_down_again_considering_another/
- `1hrk5zi` – D196 - 2 PA's Passed. First OA attempted - FAILED.
  https://www.reddit.com/r/wguaccounting/comments/1hrk5zi/d196_2_pas_passed_first_oa_attempted_failed/
- `1ltij8p` – D196 Did not pass OA
  https://www.reddit.com/r/wguaccounting/comments/1ltij8p/d196_did_not_pass_oa/
- `1ndm9ql` – People who previously failed D196 Principles of Financial and Managerial Accounting - when did things finally 'click?'
  https://www.reddit.com/r/WGU/comments/1ndm9ql/people_who_previously_failed_d196_principles_of/

</details>


---

<details>
<summary><strong>D288 – Back-End Programming — School of Technology</strong></summary>


Pipeline summary:
- Stage 0 posts: 21
- Stage 1 painpoints: 9
- Stage 2 clusters: 5
- Stage 3 normalized issues: 4
- Redundancy reduction (Stage 2 → 3): 20.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Seed data / bootstrap mismatches or broken checkout backend causing cart not found/empty and purchase request failure... | missing_or_broken_resources |         4 | [I just cannot get this tracking number to show up. I get a 404 error on my purchase request.] |
| Environment, dependency, or configuration mismatches between WGU lab, local student setups, and assessor environments... | tooling_environment_misconfiguration_or_guidance |         3 | My project runs flawlessly in the lab ... But I got a rejection saying the code doesn't even compile ... it appears t... |
| Essential course materials hosted on Panopto were inaccessible during an outage, blocking access to fix/instructional... | platform_or_environment_failures |         1 | [no longer have access to Panopto to view the javabits video which describes how to fix a drop down issue ... I saw a... |
| Conflicting or unclear instructions about whether the Lab environment is required for the project | unclear_or_ambiguous_instructions |         1 | [I'm conflicted based on what the rubric and the Panopto videos are showing. Am I required to use the Lab environment... |

Merged issues (multiple Stage-2 clusters per normalized label):
- missing_or_broken_resources combines 2 Stage-2 clusters in D288.

Sample Reddit posts by normalized issue

**`missing_or_broken_resources`** (4 posts)
- `1bj6kdn` – D288 JSON infinite recursion error
  https://www.reddit.com/r/WGU_CompSci/comments/1bj6kdn/d288_json_infinite_recursion_error/
- `1cbonta` – D288 - Hardcoded cart ID?
  https://www.reddit.com/r/WGU_CompSci/comments/1cbonta/d288_hardcoded_cart_id/
- `1fyi1im` – D288 - This Tracking Number will be the death of me
  https://www.reddit.com/r/WGU_CompSci/comments/1fyi1im/d288_this_tracking_number_will_be_the_death_of_me/
- `1nenzqe` – D288 Followed the guides, followed the videos still alittle stuck
  https://www.reddit.com/r/WGU_CompSci/comments/1nenzqe/d288_followed_the_guides_followed_the_videos/

**`tooling_environment_misconfiguration_or_guidance`** (3 posts)
- `1gnkpzc` – D288 Browser error ExpressionChangedAfterItHasBeenChechedError
  https://www.reddit.com/r/wgu_devs/comments/1gnkpzc/d288_browser_error/
- `1k4uzgm` – D288 Project Runs in Lab but not on local machines?
  https://www.reddit.com/r/WGU_CompSci/comments/1k4uzgm/d288_project_runs_in_lab_but_not_on_local_machines/
- `1nks1up` – D288: Failed assessment because of console error, cannot recreate
  https://www.reddit.com/r/WGU_CompSci/comments/1nks1up/d288_failed_assessment_because_of_console_error/

**`platform_or_environment_failures`** (1 posts)
- `1eo5j5r` – WGU D288 - How the heck are you all passing??
  https://www.reddit.com/r/WGU_CompSci/comments/1eo5j5r/wgu_d288_how_the_heck_are_you_all_passing/

**`unclear_or_ambiguous_instructions`** (1 posts)
- `1lnowd1` – D288 - Back-end Programming Questions
  https://www.reddit.com/r/WGU_CompSci/comments/1lnowd1/d288_backend_programming_questions/

</details>


---

<details>
<summary><strong>C214 – Financial Management — School of Business</strong></summary>


Pipeline summary:
- Stage 0 posts: 26
- Stage 1 painpoints: 8
- Stage 2 clusters: 4
- Stage 3 normalized issues: 3
- Redundancy reduction (Stage 2 → 3): 25.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Course resources (lectures, problem sets, study guide, textbook, PA) are misaligned with the Objective Assessment (co... | assessment_material_misalignment |         5 | The OA was nothing like the PA at all. |
| Required PA file/feature fails to load in Excel (technical/tool malfunction preventing completion). | platform_or_environment_failures |         2 | [Has anyone had a problem with the PA not loading in Excel? ... I was told it 'should' be fixed in 24 hours, but I’m ... |
| Required course material (pre-assessment report) is missing or empty on the platform. | missing_or_broken_resources |         1 | [Is the pre-assessment report supposed to be empty for C214?] |

Merged issues (multiple Stage-2 clusters per normalized label):
- platform_or_environment_failures combines 2 Stage-2 clusters in C214.

Sample Reddit posts by normalized issue

**`assessment_material_misalignment`** (5 posts)
- `1cykd6l` – c214 assessment and preparation
  https://www.reddit.com/r/WGU_MBA/comments/1cykd6l/c214_assessment_and_preparation/
- `1dr8yxy` – C214 close but did not pass
  https://www.reddit.com/r/WGU_MBA/comments/1dr8yxy/c214_close_but_did_not_pass/
- `1e476c5` – Failed C214 OA 
  https://www.reddit.com/r/WGU_MBA/comments/1e476c5/failed_c214_oa/

**`platform_or_environment_failures`** (2 posts)
- `1jtwrw1` – C214 problem
  https://www.reddit.com/r/WGU_MBA/comments/1jtwrw1/c214_problem/
- `1n5t34o` – C214 OA results not posting
  https://www.reddit.com/r/WGU/comments/1n5t34o/c214_oa_results_not_posting/

**`missing_or_broken_resources`** (1 posts)
- `1krk5zw` – Is the pre-assessment report supposed to be empty for C214?
  https://www.reddit.com/r/WGU_MBA/comments/1krk5zw/is_the_preassessment_report_supposed_to_be_empty/

</details>


---

<details>
<summary><strong>D277 – Front-End Web Development — School of Technology</strong></summary>


Pipeline summary:
- Stage 0 posts: 14
- Stage 1 painpoints: 7
- Stage 2 clusters: 6
- Stage 3 normalized issues: 5
- Redundancy reduction (Stage 2 → 3): 16.7%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Evaluators inconsistently apply the rubric or misreview submissions, resulting in incorrect missing-item feedback and... | evaluator_inconsistency_or_poor_feedback |         2 | He just told me to put labels to describe the nav, etc era so I submitted this and he still rejected it. I’m guessing... |
| Provided instructional/support resources (tutors/instructors) are unreliable or fail to show up, leaving students wit... | instructor_or_support_unresponsiveness |         2 | [...] I have just had my 5th attempt to get instructor help flaked on. Every time I reach out to one of our provided ... |
| Required/encouraged external hosting services are unreliable or behave inconsistently, causing hosted submissions to ... | external_tool_dependency_risks |         1 | Problem #1 Hosting: After completing the requirements trying to use the hosting services they want you to use is garb... |
| Course commit → pipeline → deployment process or its instructions are failing, so student commits do not publish and ... | tooling_environment_misconfiguration_or_guidance |         1 | “I am having an issue with literally very pipeline failing after i commit in VSCode. I’m doing it exactly as I did in... |
| Assignment wording is ambiguous about scope (e.g., what 'all pages from part A' includes), causing confusion about re... | unclear_or_ambiguous_instructions |         1 | What pages do I do these requirements for? I'm assuming it means the capital city and 2 noncapital city pages, but th... |

Merged issues (multiple Stage-2 clusters per normalized label):
- instructor_or_support_unresponsiveness combines 2 Stage-2 clusters in D277.

Sample Reddit posts by normalized issue

**`evaluator_inconsistency_or_poor_feedback`** (2 posts)
- `1njjy68` – Web dev D277
  https://www.reddit.com/r/wgu_devs/comments/1njjy68/web_dev_d277/
- `1nt2zmj` – D277 Help
  https://www.reddit.com/r/WGUIT/comments/1nt2zmj/d277_help/

**`instructor_or_support_unresponsiveness`** (2 posts)
- `1gq27yl` – D277- really struggling, Task 2 coding assistance, and commiseration?
  https://www.reddit.com/r/wgu_devs/comments/1gq27yl/d277_really_struggling_task_2_coding_assistance/
- `1kuii8v` – Are evaluators off this weekend because of Memorial Day?
  https://www.reddit.com/r/WGU/comments/1kuii8v/are_evaluators_off_this_weekend_because_of/

**`external_tool_dependency_risks`** (1 posts)
- `1d8p0bo` – D277 Rant
  https://www.reddit.com/r/wgu_devs/comments/1d8p0bo/d277_rant/

**`tooling_environment_misconfiguration_or_guidance`** (1 posts)
- `1m6umpu` – D277 Questions
  https://www.reddit.com/r/wgu_devs/comments/1m6umpu/d277_questions/

**`unclear_or_ambiguous_instructions`** (1 posts)
- `1io32ox` – D277 Task 2 clarification (Front-end web dev)
  https://www.reddit.com/r/wgu_devs/comments/1io32ox/d277_task_2_clarification_frontend_web_dev/

</details>


---

<details>
<summary><strong>D278 – Scripting and Programming - Foundations — School of Technology</strong></summary>


Pipeline summary:
- Stage 0 posts: 12
- Stage 1 painpoints: 7
- Stage 2 clusters: 5
- Stage 3 normalized issues: 5
- Redundancy reduction (Stage 2 → 3): 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Course materials (readings/prep) do not align with assessments (OAs/labs) — exam/lab expectations differ from what is... | assessment_material_misalignment |         2 | [Some of these aren’t even written like this in the zybooks for learning nor the cohorts I’ve seen...] [I passed as c... |
| ZyBooks content is poorly organized or presented in large, non-incremental chunks, making learning difficult and prom... | missing_or_low_quality_materials |         2 | For anyone who struggles with zybooks and the material being not great |
| Exam platform/browser reliability issues prevent viewing required materials (diagrams) during assessment | proctoring_or_exam_platform_issues |         1 | Near the end of the exam the browser we are supposed to use stopped functioning properly. I was unable to see the dia... |
| Coral coding environment lacks clear instructions or tutorials (e.g., how to set input variables); missing demo/video... | tooling_environment_misconfiguration_or_guidance |         1 | [...] not understanding how to set the input each time. My thought was that numScarves would set the variable but eac... |
| Degree-plan/track assignment workflow prevents selecting or assigning the correct programming track before course sta... | workflow_or_policy_barriers |         1 | [By default everyone "starts" in the Java track, ... my transfer would be re-evaluated after I was assigned to the C#... |

Sample Reddit posts by normalized issue

**`assessment_material_misalignment`** (2 posts)
- `1iostbs` – What do I do here? D278
  https://www.reddit.com/r/wgu_devs/comments/1iostbs/what_do_i_do_here_d278/
- `1n6hkl6` – Struggling with D278 labs should I skip them and focus on passing the class
  https://www.reddit.com/r/WGU/comments/1n6hkl6/struggling_with_d278_labs_should_i_skip_them_and/

**`missing_or_low_quality_materials`** (2 posts)
- `1bkid8q` – D278 Scripting and Programming
  https://www.reddit.com/r/wgu_devs/comments/1bkid8q/d278_scripting_and_programming/
- `1bu2jk3` – D278: Scripting & Programming Resource (Coral pdf)
  https://www.reddit.com/r/wgu_devs/comments/1bu2jk3/d278_scripting_programming_resource_coral_pdf/

**`proctoring_or_exam_platform_issues`** (1 posts)
- `1lxgkdq` – Frustrated
  https://www.reddit.com/r/WGU/comments/1lxgkdq/frustrated/

**`tooling_environment_misconfiguration_or_guidance`** (1 posts)
- `1lvp63k` – Just started D278 need help with Coral
  https://www.reddit.com/r/WGUCyberSecurity/comments/1lvp63k/just_started_d278_need_help_with_coral/

**`workflow_or_policy_barriers`** (1 posts)
- `1i313yn` – When did your mentor let you choose tracks?
  https://www.reddit.com/r/wgu_devs/comments/1i313yn/when_did_your_mentor_let_you_choose_tracks/

</details>


---

<details>
<summary><strong>D101 – Cost and Managerial Accounting — School of Business</strong></summary>


Pipeline summary:
- Stage 0 posts: 15
- Stage 1 painpoints: 7
- Stage 2 clusters: 4
- Stage 3 normalized issues: 4
- Redundancy reduction (Stage 2 → 3): 0.0%

Stage-2 clusters mapped to Stage-3 normalized issues

| stage2_cluster_label | normalized_issue_label | num_posts | example_snippet |
|----------------------|-----------------------|----------:|----------------|
| Inadequate or missing instructional/support materials and assignment data for Excel-based tasks (missing required dat... | missing_or_low_quality_materials |         3 | It’s asking me to calculate the total hours needed for labor in June and it gives me the # of units to be produced in... |
| Assessments contain items that are misaligned with taught content or have unclear instructions (quiz questions coveri... | assessment_material_misalignment |         2 | [...] what you need to know to solve some of the quiz questions aren't even taught until the unit after ... quiz ques... |
| Similarity/plagiarism checking produces consistently high similarity scores and lacks clear guidance or configuration... | ai_detection_confusion_and_false_flags |         1 | “every-time I submit it the similarity comes out to over 50%... There are over 200k students write the same words how... |
| Proctoring/platform interruptions consume exam time and force reconnections, creating time pressure and guesswork. | proctoring_or_exam_platform_issues |         1 | [proctor took 50 minutes of my time because the came cut off and I had to re connect. I ended up guessing few questio... |

Sample Reddit posts by normalized issue

**`missing_or_low_quality_materials`** (3 posts)
- `1kvxwes` – D101 PA Excel
  https://www.reddit.com/r/wguaccounting/comments/1kvxwes/d101_pa_excel/
- `1lrkoa1` – D101 PA Resource Help
  https://www.reddit.com/r/wguaccounting/comments/1lrkoa1/d101_pa_resource_help/
- `1lz26g7` – D101 killing me😭
  https://www.reddit.com/r/wguaccounting/comments/1lz26g7/d101_killing_me/

**`assessment_material_misalignment`** (2 posts)
- `1kr6du0` – D101
  https://www.reddit.com/r/wguaccounting/comments/1kr6du0/d101/
- `1neictp` – How is the D101 PA vs Oa ?
  https://www.reddit.com/r/wguaccounting/comments/1neictp/how_is_the_d101_pa_vs_oa/

**`ai_detection_confusion_and_false_flags`** (1 posts)
- `1lnmizo` – Similarity score wack!!
  https://www.reddit.com/r/wguaccounting/comments/1lnmizo/similarity_score_wack/

**`proctoring_or_exam_platform_issues`** (1 posts)
- `1kq49wb` – D101 attempts one failed
  https://www.reddit.com/r/wguaccounting/comments/1kq49wb/d101_attempts_one_failed/

</details>


---

## Cross-course normalized issue summary
This section summarizes the most common normalized issues across all courses, and then breaks them down by college.

### Overall top normalized issues

| normalized_issue_label | total_posts | num_courses |
|------------------------|------------:|------------:|
| assessment_material_misalignment | 85 | 53 |
| unclear_or_ambiguous_instructions | 85 | 56 |
| missing_or_low_quality_materials | 50 | 40 |
| platform_or_environment_failures | 45 | 30 |
| missing_or_broken_resources | 30 | 23 |
| evaluator_inconsistency_or_poor_feedback | 27 | 21 |
| tooling_environment_misconfiguration_or_guidance | 20 | 16 |
| instructor_or_support_unresponsiveness | 13 | 10 |
| workflow_or_policy_barriers | 12 | 12 |
| proctoring_or_exam_platform_issues | 10 | 9 |
| grading_or_answer_key_or_process_issues | 8 | 6 |
| external_tool_dependency_risks | 7 | 6 |
| ai_detection_confusion_and_false_flags | 4 | 3 |
| scheduling_or_simulation_availability_issues | 4 | 4 |
| workload_or_scope_issues | 4 | 4 |
| prerequisite_gaps_or_unpreparedness | 1 | 1 |

### Top normalized issues by college

When a course is tagged to multiple colleges, its issues contribute to each of those colleges’ counts.

#### Leavitt School of Health

| normalized_issue_label | total_posts | num_courses |
|------------------------|------------:|------------:|
| assessment_material_misalignment | 8 | 8 |
| unclear_or_ambiguous_instructions | 7 | 6 |
| evaluator_inconsistency_or_poor_feedback | 6 | 5 |
| missing_or_low_quality_materials | 6 | 6 |
| instructor_or_support_unresponsiveness | 4 | 4 |
| workflow_or_policy_barriers | 3 | 3 |
| ai_detection_confusion_and_false_flags | 2 | 1 |
| missing_or_broken_resources | 2 | 2 |
| grading_or_answer_key_or_process_issues | 1 | 1 |
| platform_or_environment_failures | 1 | 1 |
| proctoring_or_exam_platform_issues | 1 | 1 |
| scheduling_or_simulation_availability_issues | 1 | 1 |

#### School of Business

| normalized_issue_label | total_posts | num_courses |
|------------------------|------------:|------------:|
| assessment_material_misalignment | 41 | 26 |
| missing_or_low_quality_materials | 21 | 16 |
| unclear_or_ambiguous_instructions | 18 | 14 |
| platform_or_environment_failures | 16 | 10 |
| missing_or_broken_resources | 10 | 9 |
| evaluator_inconsistency_or_poor_feedback | 8 | 6 |
| instructor_or_support_unresponsiveness | 8 | 6 |
| ai_detection_confusion_and_false_flags | 4 | 3 |
| grading_or_answer_key_or_process_issues | 4 | 4 |
| tooling_environment_misconfiguration_or_guidance | 4 | 4 |
| external_tool_dependency_risks | 3 | 2 |
| workflow_or_policy_barriers | 3 | 3 |
| workload_or_scope_issues | 3 | 3 |
| proctoring_or_exam_platform_issues | 2 | 2 |
| scheduling_or_simulation_availability_issues | 1 | 1 |

#### School of Education

| normalized_issue_label | total_posts | num_courses |
|------------------------|------------:|------------:|
| unclear_or_ambiguous_instructions | 17 | 10 |
| missing_or_low_quality_materials | 10 | 7 |
| assessment_material_misalignment | 5 | 5 |
| evaluator_inconsistency_or_poor_feedback | 3 | 3 |
| instructor_or_support_unresponsiveness | 3 | 3 |
| missing_or_broken_resources | 2 | 2 |
| platform_or_environment_failures | 2 | 2 |
| scheduling_or_simulation_availability_issues | 2 | 2 |
| workflow_or_policy_barriers | 2 | 2 |
| external_tool_dependency_risks | 1 | 1 |
| grading_or_answer_key_or_process_issues | 1 | 1 |
| proctoring_or_exam_platform_issues | 1 | 1 |

#### School of Technology

| normalized_issue_label | total_posts | num_courses |
|------------------------|------------:|------------:|
| unclear_or_ambiguous_instructions | 53 | 32 |
| assessment_material_misalignment | 44 | 25 |
| platform_or_environment_failures | 30 | 20 |
| missing_or_low_quality_materials | 25 | 23 |
| missing_or_broken_resources | 21 | 15 |
| tooling_environment_misconfiguration_or_guidance | 17 | 13 |
| evaluator_inconsistency_or_poor_feedback | 14 | 11 |
| workflow_or_policy_barriers | 9 | 9 |
| instructor_or_support_unresponsiveness | 7 | 6 |
| proctoring_or_exam_platform_issues | 6 | 5 |
| external_tool_dependency_risks | 5 | 4 |
| ai_detection_confusion_and_false_flags | 2 | 1 |
| grading_or_answer_key_or_process_issues | 2 | 2 |
| prerequisite_gaps_or_unpreparedness | 1 | 1 |
| workload_or_scope_issues | 1 | 1 |

