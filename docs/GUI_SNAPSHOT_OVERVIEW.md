# WGU Reddit Snapshot

## What This Is
The WGU Reddit Snapshot is a public, read-only interface for exploring the dataset produced by the **WGU Reddit Analyzer** capstone project.

The Analyzer performs all analysis.  
This site displays its outputs only.

## The Dataset
The GUI displays the fixed dataset used by the pipeline.

It includes:
- 1,103 Reddit posts
- 242 WGU courses
- Posts collected from 51 WGU-related subreddits

Posts were filtered upstream for:
- public availability
- strongly negative sentiment
- exactly one identifiable WGU course code

Counts represent posts, not students or outcomes.

## What You’re Seeing
All groupings, categories, and counts shown on this site are precomputed pipeline outputs.

- course groupings are derived from course-level clustering
- cross-course categories come from normalized clusters
- excerpts are truncated, privacy-reviewed fragments
- ordering reflects post volume only

The GUI does not generate or evaluate data.

## Limits
This site presents a single, frozen dataset.  
It does not represent all student experiences or institutional performance.

Methodology and interpretation are documented in the project paper and pipeline artifacts.