# WGU Reddit Monitoring Capstone (Prototype)

**Capstone Title**: *WGU Reddit Monitoring Pipeline with Sentiment Analysis and NLP*  
**Submission Date**: July 2025  
**Project Type**: Prototype – static, client-side GUI built on curated Reddit data  
**Author**: Buddy Owens 

---

## Project Overview

This project builds a pipeline to classify and explore Reddit posts related to WGU courses. 
The prototype includes a web-based interface that enables users to filter posts by course, category, sentiment, and intent.
Posts are preprocessed and labeled using Chat GPT-based classification, with metadata drawn from WGU’s Institutional Catalog.

---

## Prototype Scope

This prototype uses:

- A curated dataset of **930 Reddit posts** from **2025 only**
- Posts mentioning **only one** of the **top 20 most-discussed WGU courses**  
  > Posts that mentioned **multiple courses** were excluded due to added complexity.
- Pre-filtered, pre-processed data. No live NLP, scraping or API usage. 
- A fully client-side HTML post viewer with filters, included in the public GitHub repository — suitable for deployment via GitHub Pages or local file browsing.

> This is a **limited-scope mock dataset** built for prototyping and demonstration purposes.

---

## Data Source

Reddit posts were collected from public WGU-related subreddits using the Reddit API.

### Data Collection Timeline

**Initial Population (April 24, 2025):**  
The database was populated using PRAW, retrieving up to 1,000 posts per subreddit. This created a substantial starting dataset but introduced temporal clustering, as Reddit only provides access to the most recent posts.

**Daily Collection (July 4, 2025 – Present):**  
Automated daily fetching was implemented on July 4, 2025, as tracked by `logs/launchd_daily_update.log`. From this date forward, post collection is ongoing. While all new posts should be captured from that point, full verification of collection completeness has not been established.

### Dataset Scope

- The prototype uses a filtered snapshot of Reddit posts from the year 2025 only.
- Due to the 1,000-post API limit per subreddit, complete coverage for early 2025 is not guaranteed.
- As of [INSERT_APPROVAL_DATE], daily scraping is active and considered complete moving forward.

### Data Captured

Each post record includes:

- post_id
- title
- selftext
- created_utc (original Reddit post timestamp)
---

### Known Limitations:
- Current list of wgu-related subreddits is not actively updated. New subreddits will not be picked up. 



## GPT Model Usage & Expansion Plans

### Prototype Model: `gpt-4o-mini`

This project uses **OpenAI’s `gpt-4o-mini` (2024-07-18)** to classify posts by:

- **Category** (e.g., “Assessment & Exam Content”)
- **Intent Tag** (e.g., “help_request”)

**Classification Details**:
- Posts classified: **930**
- Total cost: **$0.12**
- Structured output enforced via: `response_format: {type: "json_schema"}`

### ⚙ Supported Models for Structured Output

| Model        | Input   | Cached Input | Output  | JSON Schema |
|--------------|---------|--------------|---------|--------------|
| `gpt-4o-mini`| $0.15   | $0.075       | $0.60   | ✅ Yes       |
| `gpt-4o`     | $2.50   | $1.25        | $10.00  | ✅ Yes       |

> `gpt-4o-mini` was chosen for affordability and structured output support.  
> `gpt-4o` may be used in future research for longer context or higher precision tasks.

---
## Planned Expansion

### 1. Open-Source LLMs with Ollama

To reduce reliance on commercial APIs and improve privacy, we plan to evaluate open-source models using Ollama, a macOS-native tool that enables fast, local inference with models such as LLaMA 2 and Mistral.

This will allow future iterations of the pipeline to run classification and summarization tasks locally, without token limits or external data transmission, and support reproducible research workflows.

---

### 2. Multi-Pass LLM for Pain Point Extraction

In future stages, we plan to run one or more additional LLM passes over the dataset to extract actionable summaries and themes for stakeholders.

#### Pass 1: Cluster by Course, Category, and Intent

Posts will be grouped by course, filtered by relevant categories (e.g., Course Content Issues) and intent tags (e.g., help_request), then clustered into course-specific problem areas.

#### Pass 2: Extract Structured "Pain Points"

Each cluster will be labeled with a short descriptive title and associated post references.

**Example (Course: D427)**

Pain Point: **Chapters 7 & 8 Update**

| post_id   | Title                                            |
|-----------|--------------------------------------------------|
| 1kezkuh   | Are Chapters 7 & 8 still on OA?                  |
| 1kffhci   | ZyBooks Lab 7/8 missing?                         |
| 1lepi38   | D427 updated? OA same as before?                 |
| 1kda0zr   | Did D427 change for enrolled students?           |

LLMs will also be prompted to flag **emerging pain points**, supporting the monitoring goal of the capstone.

### 3. Including Comments
- comments are an important source of additional help seeking, as well as advice. Comments are API-intensive and currently 
- currently only fetched at 3 comments per level, and two levels deep. Only comments made before post fetch will be fetched. 
Plan: identify potential sources of high value comments (post classification, sentiment) re-fetch the post, and using `num_comments` 
plan an API comments-fetch for comment-level analysis. 
---

## Possible Expansion

### 1. Feedback by Institutional Area

Using the WGU catalog and website structure as a guide, we may explore grouping posts by **institutional areas**, beyond course-level classification. These could include:

- Degree programs (e.g., MBA, IT bachelor's)
- Tuition and financial aid
- Admissions and transfer policies
- Success centers:
  - Academic Coaching Center
  - Career & Professional Development Center
- Financial services and student billing
- Student mentors and advising

This would allow us to identify and summarize what students are saying about specific support structures, policies, or systems. While WGU already gathers end-of-term feedback through formal surveys, social media provides a source of **unsolicited, unfiltered feedback** that may surface trends and concerns in real time.

---

### 2. WGU Mentions Beyond Known Subreddits

Another possible area of exploration is identifying **WGU-related posts outside the known set of WGU-focused subreddits**.

By searching for keywords like "WGU" or "Western Governors University" across Reddit more broadly, we may be able to analyze:

- How prospective students talk about WGU in general forums
- Where WGU is being discussed outside of student channels
- What themes emerge in unrelated subreddits (e.g., r/college, r/onlineeducation)

This is not part of the current pipeline but remains a possible extension for broader sentiment analysis or institutional reputation tracking.
---

## WGU Catalog Scraper

The WGU catalog parser was used to generate supporting metadata but is not included in this repo.

### Used Outputs

- **`college_snapshots.json`**  
  Historical record of WGU college names from **2017–2024**  
  Used for mapping course codes to college filters (2024-04 snapshot only)

- **`2025_06_course_list_with_college.csv`**  
  Most recent course list from June 2025  
  Used to enrich Reddit posts with course titles and affiliated colleges

> Course-to-college mappings were **manually spot-checked**, but exhaustive verification is not guaranteed.

While historical catalogs were scraped, **this prototype limits itself to the 2025 course list** for simplicity and accuracy.

---

## Dataset Description for GUI

Each post in the GUI uses a unified JSON structure:

```json
{
  "post_id": "1abcxyz",
  "title": "How do I pass the OA?",
  "selftext": "...",
  "permalink": "/r/WGU/comments/1abcxyz/...",
  "created_utc": 1745101200,
  "created_date": "2025-07-19",
  "course_code": "C207",
  "course_title": "Introduction to Data-Driven Decision-Making",
  "colleges": ["School of Business"],
  "text_length": 271,
  "VADER_Compound": 0.78,
  "categories": [0, 2],
  "category_labels": ["Assessment & Exam Content", "Study Support & Resources"],
  "intent_tags": [0],
  "intent_labels": ["help_request"]
}