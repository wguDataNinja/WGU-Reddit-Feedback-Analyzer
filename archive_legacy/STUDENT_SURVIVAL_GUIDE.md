NEW: Pain point comments:

⸻

🔧 Per Topic Structure (Max 4 Advice Examples)

🧩 1. Topic Overview
	•	Title (cluster label)
	•	Short “What’s Happening” paragraph (describes shared issue)

⸻

🧠 2. Pain Points
	•	2–4 direct quotes from Reddit posts that express the struggle
“The OA was nothing like the PA at all.”
“I don’t understand the formula setup in Excel.”

⸻

🛠 3. Advice Section: Show the Range

a. Two Short Paired Comment Advice
	•	Pulled from direct replies to posts
	•	Format:
“I just failed and don’t know why.”
→ “Triple check whitespace. The grader fails you for even small formatting issues.”

b. One Long Comment Advice (Summarized)
	•	Condense high-quality advice to 2–3 sentences
	•	Link to original full comment
Advice Summary:
Use PA and Chapter 34 to prep for OA. Skip the labs. Test edge cases and clean inputs.
Full comment ↗

c. One Unrelated Post with Useful Advice
	•	Pulled from elsewhere, but matches the topic
	•	Labeled clearly
From Another Post:
“Use only textbook and Reddit reviews — ignore the extra videos.”
Source: Reddit post ↗

⸻

🧾 Summary:
	•	Pain points show what’s going wrong
	•	Advice shows how real students are solving it — directly, indirectly, and deeply
	•	This structure gives high coverage, clarity, and trust

⸻







# Unofficial WGU Reddit Survival Guide

_Formerly: WGU Reddit Feedback Analyzer_

---

## Why Reddit? 

Reddit is just one of the multitude of social medias available today. Many others have WGU-related discussion, such as Facebook, X (Formerly Twitter), Tiktok, Instagram, all have a presence. 
Reddit was selected due to the ease of API access to download their data. 

First,  we identified 51 WGU-related subreddits. The largest, r/WGU was created in 2011 and has over 150k subscribers. 
Subreddit Description: "Place for Western Governors University students, faculty and alumni to offer positive
discussions and positive support for each other."

We created a custom database to store posts from the 51-WGU-related subreddits we found. Using their API, we extracted over 20k posts into our sqlite database for analsysis.

Most of the discussion is positive, and most fits into these 5 natural categories: 
	1.	Course Content Issues
	2.	Study Support & Resources
	3.	Course Planning & Timing
	4.	Celebration & Motivation
5. Assessment & Exam Discussion

One small subset of these posts, though, are people looking for help. Often struggling, overwhelmed, and asking for help. 
Our aim in this project was to find these posts, and document what the causes of their struggles, and find advice within the posts, that matched. Comments are surely a valuable source for advice as well and are a *planned expansion* . 

By aligning those struggles with actual student advice, we create course-specific survival guides that give future and staff valuable info: 

What are the course-specific issues causing students to struggle, and what is the advice given, about those same issues? 


### Project Goals

- Extract relevant posts from a curated database of 20,000+ WGU-related Reddit posts.  
- Identify and structure *pain points* expressed by students, tied to specific courses.  
- Cluster pain points by shared root cause to reveal recurring course-level issues.  
- Summarize and align peer-shared *advice* to those clusters, enabling targeted guidance.  
- Deliver quote-backed, structured survival guides for curriculum teams and future students.  
- Ensure reproducibility through schema-validated LLM stages and transparent processing.
---

## What the Homepage Shows

The homepage (GitHub Pages) displays a sortable table of WGU courses, showing:

- Course Code & Name  
- Number of Pain Points (from Reddit posts)  
- Number of Advice Items (student-suggested tips)  

Courses are sorted by pain point count, highlighting where students struggle most.  
This lets users immediately ask:  
**“Where are students having the most trouble—and what has worked for others?”**

---

## What Users See in a Course Guide

Clicking a course opens its survival guide, which includes:

- Quoted pain points (e.g., “Chapter 7 is really hard”)  
- Matching student advice (e.g., “Review the Chapter 7 walkthrough videos before the OA”)  
- A GPT-generated summary paragraph combining top struggles and suggestions  

---

## Why Advice Matters

Advice isn’t just collected — it’s clustered and matched to the right pain points.  
Each cluster represents a core struggle. Advice is aligned to help solve that issue.

This turns scattered Reddit threads into structured, actionable guidance for students and a transparent feedback lens for staff.

---

## What This Enables

- Quick visibility into the most problematic courses  
- Real, peer-shared experiences not visible in surveys  
- Data-informed support for course improvements  
- A replicable, LLM-supported process for course intelligence  

---

## What to Expect

- Not all courses will have enough data for full guides  
- Some guides may only include pain points or advice  
- Strong guides will show:
  - Multiple clusters  
  - Multiple pain points per cluster  
  - Matched advice  
  - GPT summary paragraph  
- Some advice may still be off-topic—we are refining the filtering and alignment process  

---

## How This Guide Was Built

This guide was generated from Reddit student feedback using a structured, multi-stage LLM pipeline, each tied to a distinct processing stage:

---

### LLM Stage 1 — Pain Point Extraction

Filtered Reddit posts (single-course mentions + low sentiment) are processed by an LLM.  
It extracts structured pain points, each including:

- A one-sentence summary of the struggle  
- A root cause tied to course design or support  
- A quoted snippet from the original post  

Strict schema validation ensures clean, usable output.

---

### LLM Stage 2 — Pain Point Clustering

Pain points are grouped into root-cause-aligned clusters (e.g., “Unclear OA Instructions”).  
The LLM handles naming, merging similar issues, and fitting new feedback into existing themes.

Each course receives a cluster file with pain point groupings and titles.

---

### LLM Stage 3 — Advice Summarization

A second dataset (no sentiment filter) is used to extract potential advice posts.  
Posts are summarized into 1–n short advice lines (e.g., “Watch all videos before the OA”).  
This stage does not yet match advice to pain points.

---

### LLM Stage 4 — Advice → Cluster Assignment

The LLM maps summarized advice items to the most relevant pain point cluster for that course.  
Each cluster ends up with a set of student-suggested strategies relevant to its theme.

---

### LLM Stage 4b (Optional) — Advice → Pain Point Matching

For courses with rich data, an additional LLM pass can align advice to specific pain points.  
This supports even more targeted matching (e.g., advice that refers directly to “Chapter 7”).

---

### LLM Stage 5 — GPT Summary Paragraph Generation

Each guide includes a final GPT-written paragraph that introduces the course and summarizes:

- How many pain points were found  
- Which issues were most common  
- What students say helps most  

---

## Final Output Assembly

Guides are rendered in Markdown using Jinja2 templates, then optionally exported as PDFs.

Each course guide includes:

- Cluster-level sections  
- Title  
- Root cause summary  
- Pain points (quoted, linked)  
- Advice (summarized, linked)  
- GPT-written intro paragraph  
- Fallback text if data is missing  
- Final file exports:
  - `CXXX_Survival_Guide.md`  
  - `CXXX_Survival_Guide.pdf` (optional)  

---

## Data Overview

- ~20,000 Reddit posts from WGU-related subreddits  
- ~4,000 posts with single-course mentions  
- Low-sentiment posts used to extract pain points (VADER < 0.2)  
- All posts reused to summarize advice  
- Fewer than 200 total courses, most will be light—focus is on strong, well-populated guides  

---

Let me know if you want this version saved as a `README.md`, split into homepage + internal version, or converted into a presentation/slide deck.