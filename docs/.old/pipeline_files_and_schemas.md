pipeline_files_and_schemas.md

Title: Pipeline File Map and Schemas
Audience: Internal dev
Status: WIP — updated for v1.2 plans
Last Updated: 2025-08-03

⸻

STAGE 1 – Extract and Classify Pain Points

Step 01 – Fetch Filtered Posts
	•	Input:
	•	db/WGU-Reddit.db (via load_posts_dataframe())
	•	data/2025_06_course_list_with_college.csv
	•	Output:
	•	outputs/runs/{DATE}/stage1/filtered_posts_stage1.jsonl
	•	outputs/runs/{DATE}/logs/stage1/fetch.log

Schema:

{
  "post_id": "abc123",
  "course_code": "C949",
  "title": "...",
  "selftext": "...",
  "text_clean": "...",
  "subreddit": "WGU",
  "permalink": "https://..."
}


⸻

Step 02 – Classify Single Post (LLM)
	•	Input: Single post JSON
	•	Output (per call):
	•	outputs/runs/{DATE}/logs/stage1/llm/{course}_{post_id}_{timestamp}.log

Output Schema (if pain points present):

{
  "num_pain_points": 2,
  "pain_points": [
    {
      "pain_point_id": "C949_abc123[0]",
      "summary": "...",
      "root_cause": "...",
      "quoted_text": "..."
    }
  ]
}


⸻

Step 03 – Classify File (batch)
	•	Input:
	•	outputs/runs/{DATE}/stage1/filtered_posts_stage1.jsonl
	•	Output:
	•	outputs/runs/{DATE}/stage1/pain_points_stage1.jsonl
	•	outputs/runs/{DATE}/logs/stage1/classify_file.log

⸻

STAGE 2 – Cluster Pain Points

Step 01 – Group by Course
	•	Input:
	•	outputs/runs/{DATE}/stage1/pain_points_stage1.jsonl
	•	Output:
	•	outputs/stage2_cache/course_inputs/{COURSE}.jsonl
	•	outputs/runs/{DATE}/stage2_input/{COURSE}.jsonl
	•	outputs/runs/{DATE}/stage1/updated_courses.txt

Step 03 – LLM Clustering
	•	Output:
	•	outputs/runs/{DATE}/stage2_output/{COURSE}_clusters.json
	•	outputs/stage2_cache/course_clusters/{COURSE}_clusters.json

Cluster Schema:

{
  "course": "C949",
  "clusters": [
    {
      "cluster_id": "C949_1",
      "title": "Unclear OA expectations",
      "root_cause_summary": "...",
      "pain_point_ids": ["C949_abc123[0]", "..."]
    }
  ]
}


⸻

STAGE 3 – Extract and Cluster Advice

Status: In development — tested on D335

Pass 1 – Summarize Advice
	•	Input:
	•	outputs/advice/all_posts_no_sent_1course.jsonl OR
	•	outputs/stage3/filtered_posts_by_course/{COURSE}.jsonl
	•	Output:
	•	outputs/stage3/{COURSE}_plain_summary.jsonl

Schema:

{
  "post_id": "18067ig",
  "course": "D335",
  "text_clean": "...",
  "plain_summary": "Watch videos before OA. Practice quizzes."
}

Pass 2 – Clustered Advice
	•	Input:
	•	Plain summaries
	•	Stage 2 clusters: outputs/stage2_cache/course_clusters/{COURSE}_clusters.json
	•	Output:
	•	outputs/stage3/{COURSE}_summary_cluster.jsonl

Schema:

{
  "post_id": "18067ig",
  "summary_cluster": {
    "1": ["Watch videos before OA"],
    "2": [null],
    "3": ["Review Python basics"]
  }
}

Step – Flatten Advice
	•	Output:
	•	outputs/stage3/advice_by_course/{COURSE}.jsonl

Schema:

{
  "advice_id": "D335_18067ig[01]",
  "post_id": "18067ig",
  "course": "D335",
  "cluster_id": "1",
  "cluster_title": "Assessment Clarity and Preparation",
  "advice": "Watch all videos before the OA"
}


⸻

STAGE 4 – Align Advice to Pain Points

Status: PLANNED

Input
	•	outputs/stage2_cache/course_clusters/{COURSE}_clusters.json
	•	outputs/stage3/advice_by_course/{COURSE}.jsonl

Output
	•	outputs/stage4_cache/{COURSE}_aligned_advice.json

Schema:

{
  "course": "D335",
  "cluster_id": "D335_1",
  "pain_point_id": "D335_abc123[0]",
  "matched_advice_ids": ["D335_18067ig[01]", "..."]
}


⸻

STAGE 5 – Generate Survival Guide

Status: PLANNED

Input:
	•	Aligned advice (from Stage 4)
	•	Cluster definitions (from Stage 2)
	•	Pain point and advice source data

Output:
	•	outputs/stage5_guides/{COURSE}_survival_guide.jsonl
	•	outputs/stage5_guides_markdown/{COURSE}_guide.md
	•	outputs/stage5_guides_pdfs/{COURSE}_guide.pdf

Schema (JSONL):

{
  "cluster_id": "D335_1",
  "title": "Assessment Clarity and Preparation",
  "guide_paragraph": "To succeed in D335..."
}

Markdown and PDF include:
	•	Cluster titles
	•	Pain points (quotes + summaries)
	•	Advice (quotes + summaries, matched if available)
	•	Final summary paragraph per topic

⸻

TO DO
	•	Document Reddit fetch logic paths (daily scrape)
	•	Add schema for merged_course_feedback.json
	•	Track full PDF output folder names
	•	Include token count metrics + logging formats