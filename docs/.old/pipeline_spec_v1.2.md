# Pipeline Specification – v1.2

**Status**: PLANNED  
**Scope**: Stages 1–5  
**Last Updated**: 2025-08-03  
**Audience**: Internal developers, maintainers

---

## — STAGE 1 —  
**Title:** Extract and Classify Pain Points  
**Purpose:**  
Filter Reddit posts for course relevance and negative sentiment, then extract structured pain points using LLM.

---

### Config

All pipeline stages use centralized config modules in config/. Each script should import from its stage config or common.py.
	•	config/common.py – shared constants (e.g., date formats, model names)
	•	config/stage1.py – Stage 1 settings (e.g., input DB, sentiment threshold, output paths)
	•	config/stage2.py – Stage 2 settings (e.g., cluster thresholds, cache paths)
	•	config/stage3.py – Stage 3 planned (e.g., advice summary format, file paths)
	•	config/stage4.py – Stage 4 planned (e.g., alignment logic, prompt strategy)

### Step 01 – Fetch Filtered Posts
- Script: `scripts/stage1/step01_fetch_filtered_posts.py`
- Input:  
  - Posts DB via `load_posts_dataframe()`  
  - Course list: `data/2025_06_course_list_with_college.csv`
- Output:  
  - `outputs/runs/{DATE}/stage1/filtered_posts_stage1.jsonl`  
  - Log: `outputs/runs/{DATE}/logs/stage1/fetch.log`

### Step 02 – Classify Single Post
- Script: `scripts/stage1/step02_classify_post.py`
- Output (per call): structured JSON with pain points

### Step 03 – Classify File
- Script: `scripts/stage1/step03_classify_file.py`
- Output:  
  - `outputs/runs/{DATE}/stage1/pain_points_stage1.jsonl`  
  - Log: `outputs/runs/{DATE}/logs/stage1/classify_file.log`

### Step 04 – Orchestrator
- Script: `scripts/stage1/step04_run_stage1.py`  
- Output: final logs, full batch run

---

## — STAGE 2 —  
**Title:** Cluster Pain Points  
**Purpose:**  
Group pain points into root-cause clusters per course using LLM, to surface common issues.

---

### Config
- `scripts/stage2/config_stage2.py`

### Step 01 – Group by Course
- Script: `scripts/stage2/step01_group_by_course.py`
- Output:  
  - `outputs/stage2_cache/course_inputs/{COURSE}.jsonl`  
  - `outputs/runs/{DATE}/stage2_input/{COURSE}.jsonl`

### Step 02 – Prepare Prompt Data  
- Script: `scripts/stage2/step02_prepare_prompt_data.py`

### Step 03 – Cluster via LLM  
- Script: `scripts/stage2/step03_call_llm.py`
- Output: validated JSON per course

### Step 04 – Apply Actions (cluster updates, alerts)
- Script: `scripts/stage2/step04_apply_actions.py`

```
Alerting logic is scaffolded but not active. Alerts are based on the number of new pain points per feedback topic exceeding a global threshold (currently 2). This mechanism is not yet connected to any downstream notification or review system.

You could also tag the threshold variable like:

Threshold defined in config_stage2.py as PAINPOINT_ALERT_THRESHOLD = 2

also each course cluster.json has by-course threshold override
```


### Step 05 – Orchestrator  
- Script: `scripts/stage2/step05_run_stage2.py`  
- Output:  
  - `outputs/runs/{DATE}/stage2_output/{COURSE}_clusters.json`  
  - Cache copy: `outputs/stage2_cache/course_clusters/{COURSE}_clusters.json`

---
Here’s the Stage 3 and Stage 4 spec updates with comment advice fully integrated, assuming comments are short and treated as direct advice with no summarization.

⸻

✅ UPDATED — STAGE 3 —

Title: Extract and Cluster Advice
Purpose:
Collect advice from Reddit posts and comments, then organize them into root-cause-aligned cluster groups.

⸻

Inputs:
	•	Filtered posts: outputs/runs/{DATE}/stage1/filtered_posts_stage1.jsonl
	•	Extracted comments: outputs/comments/{DATE}/comments_by_post.jsonl
	•	Course clusters: outputs/stage2_cache/course_clusters/{COURSE}_clusters.json

⸻

Pass 1a – Format Post Advice
	•	Script: scripts/stage3/step01a_format_post_advice.py
	•	Clean and format post body text as advice.

⸻

Pass 1b – Format Comment Advice
	•	Script: scripts/stage3/step01b_format_comment_advice.py
	•	Filter for meaningful comments (e.g. length > 20 chars).
	•	Output advice directly with no summarization.

⸻

Output (combined)
	•	outputs/stage3/advice_by_course/{COURSE}.jsonl
	•	Schema:

{
  "post_id": "18067ig",
  "comment_id": "t1_gx3h8v0", // null if from post
  "text_clean": "Use flashcards to prepare.",
  "source": "comment" | "post",
  "course": "D335"
}


⸻

Pass 2 – Cluster Advice by Topic
	•	Script: scripts/stage3/step02_cluster_advice.py
	•	Input: Combined advice file
	•	Output:
	•	outputs/stage3/{COURSE}_summary_cluster.jsonl

{
  "post_id": "18067ig",
  "comment_id": "t1_gx3h8v0",
  "cluster_map": {
    "1": ["Use flashcards."],
    "2": [null]
  }
}


⸻

✅ UPDATED — STAGE 4 —

Title: Align Advice to Pain Points
Purpose:
Match advice (from posts or comments) to specific pain points within clusters.

⸻

Input
	•	Pain points:
outputs/stage2_cache/course_clusters/{COURSE}_clusters.json
	•	Clustered advice (posts + comments):
outputs/stage3/{COURSE}_summary_cluster.jsonl

⸻

Matching Logic

Per course → per cluster:
	1.	Load all pain points
	2.	Load all advice from both posts and comments
	3.	Prompt LLM to:
	•	Match each advice item to one or more pain points
	•	Maintain source tag for display

⸻

Output
	•	File:
outputs/stage4_cache/{COURSE}_aligned_advice.json
	•	Schema:

{
  "course": "D335",
  "cluster_id": "D335_1",
  "pain_point_id": "D335_abc123[0]",
  "matched_advice": [
    {
      "post_id": "18067ig",
      "comment_id": null,
      "text_clean": "Watch all the videos.",
      "source": "post"
    },
    {
      "post_id": "18067ig",
      "comment_id": "t1_gx3h8v0",
      "text_clean": "Use flashcards.",
      "source": "comment"
    }
  ]
}


⸻

Stage 5 Impact

Display logic now includes:
	•	Pain point with matching post advice
	•	Pain point with matching comment advice
	•	Clearly label source of each recommendation

⸻

Let me know if you’d like to gate comment inclusion by karma, parent match, or any other rule.

### Future Extensions (optional)

- Add `confidence` or `match_type` fields if LLM supports multi-tier reasoning  
- Add back-reference map of advice → all matched pain points (reverse index)

---

## — STAGE 5 —  
**Title:** Generate Survival Guide  
**Purpose:**  
Convert clustered pain points and advice into a well-written, readable markdown (and PDF) per course, including summary paragraphs and post links.

**Status:** PLANNED — structure finalized, pending implementation

---

### Input

- Course metadata  
- Clustered pain points (`{COURSE}_clusters.json`)  
- Clustered advice (`advice_by_course/{COURSE}.jsonl`)  
- Advice alignment (`{COURSE}_aligned_advice.json`)

---

### Process

For each course:
1. Load cluster-level pain points and advice  
2. Include quoted snippets (linked via post_id → permalink)  
3. Use LLM to generate a final paragraph per cluster:
   - Summarize challenges
   - Summarize advice
   - Maintain tone suitable for students and faculty
4. Format output for UI and PDF

---

### Output

- Markdown:  
  `outputs/stage5_guides/{COURSE}_survival_guide.md`

- JSONL (one paragraph per cluster):  
  `outputs/stage5_guides/{COURSE}_survival_guide.jsonl`

- PDF:  
  `outputs/runs/{DATE}/pdfs/{COURSE}_Student_Survival_Guide.pdf`

---

### Output Schema

```json
{
  "cluster_id": "D335_1",
  "title": "Assessment Clarity and Preparation",
  "guide_paragraph": "To succeed in D335, students suggest watching the videos..."
}
```

### Special Logic

- If a course has only one pain point or one piece of advice, the guide still renders as a minimal but valid document.
- If a cluster has advice but no matched pain point (or vice versa), the unmatched content is still shown under the topic heading.
- If no advice is available at all, the section title is shown with a placeholder such as:  
  _“No peer advice was available for this topic.”_
- If the content in a guide is sparse overall, the document may include a note such as:  
  _“This guide reflects a limited number of Reddit posts. For deeper support, consult official resources or your mentor.”_
- LLM summaries adjust automatically to reflect how much data is present — long if content-rich, short if minimal.
- Course metadata (e.g., college, degree, course title) is prepended or embedded in the guide as context.
- Optionally: add a disclaimer at the end noting that Reddit is unofficial and may not reflect verified advice.








