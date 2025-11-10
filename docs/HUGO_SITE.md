# WGU Reddit Analyzer – Hugo Site Overview

_Last updated: 2025-11-08_

---

## 1. Purpose
Describes the web-facing component of the WGU Reddit Analyzer — a static site built with **Hugo** and **PaperMod** that visualizes Reddit post analyses, course summaries, and AI-generated insights.  
The site provides transparent, reproducible visual access to benchmark results and aggregated discussion data.

---

## 2. Architecture Overview
The site presents processed Reddit data and model outputs from the LLM pipeline in an interactive, filterable interface.  
All content is based on precomputed artifacts — no live Reddit API access is required.

**Stack:** Hugo v0.150+ · Vanilla JS · PaperMod Theme

**Key Directories:**
```
site/
  ├── content/        # Markdown pages and generated post/course entries
  ├── assets/json/    # Static data (posts, threads, summaries)
  ├── static/js/      # Filters, search, pagination
  └── static/css/     # Layout and comment styling
```

---

## 3. Data Integration
The static assets are produced by earlier analysis stages that:

- Enrich Reddit posts with course codes and sentiment  
- Extract structured pain points and summaries using LLMs  
- Aggregate results by course and college  

These outputs are converted into JSON and Markdown for rendering in Hugo.  
No private data, credentials, or live API calls are included.

---

## 4. Features
- **Post Feed:** searchable and filterable by course, keyword, or sentiment  
- **Course Pages:** display aggregate statistics, thread samples, and AI summaries  
- **Pain Point Explorer:** lists recurring issue categories across courses  
- **Thread Views:** minimal, privacy-safe comment trees  
- **PDF Reports:** downloadable course-level summaries  

---

## 5. Future Work
- Integrate full-thread LLM summaries (Stage 4)  
- Add date range filters and URL-based persistent states  
- Enhance accessibility, responsive design, and cached JSON rendering  

---

## 6. Status
🚧 **In Development** — core site and data integration are functional; AI summaries under validation.  
All public site content is derived from verified, anonymized datasets produced by the benchmarking pipeline.

---

