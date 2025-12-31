# WGU Reddit Snapshot

## What This Is

The WGU Reddit Snapshot is a public, read-only interface for exploring the dataset produced by the **WGU Reddit Analyzer** capstone project.

The Analyzer is the analytical system.  
This site only displays its outputs.

No analysis is performed in the GUI.

---

## The Dataset

The GUI displays the **fixed dataset used by the pipeline**.

It includes:
- 1,103 Reddit posts
- 242 WGU courses
- Posts collected from 51 WGU-related subreddits

Posts were filtered upstream by the pipeline for:
- Public availability
- Strongly negative sentiment
- Exactly one identifiable WGU course code

Counts represent **posts**, not students or outcomes.

---

## What You’re Seeing

All groupings, categories, and counts shown on this site are **precomputed pipeline outputs**.

- Course groupings come from course-level clustering
- Cross-course categories come from Stage 3 normalized clusters
- Excerpts are truncated, privacy-reviewed fragments of posts
- Ordering reflects post volume only

The GUI does not create, infer, or evaluate anything.

---

## Limits

This site shows a single, frozen dataset.  
It does not represent all student experiences or institutional performance.

Methodology and interpretation belong to the paper and pipeline artifacts.