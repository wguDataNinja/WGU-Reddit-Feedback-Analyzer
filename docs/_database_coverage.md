
WGU-Reddit Database Coverage and Data Integrity

Scope

This database supports longitudinal analysis of Reddit activity across WGU-related subreddits. The primary analytical unit is posts, with auxiliary tables providing contextual and aggregate signals.

Tables and Coverage

Posts
	•	Time span: 2014-12-28 to 2026-01-11
	•	Total posts: 31,631
	•	Primary analysis window: 2025-04-24 to 2026-01-11
	•	Coverage in window: 100 percent daily coverage
	•	Lowest daily volume: 9 posts (partial day at window end)
	•	Typical daily volume: 40 to 100+ posts

There are no missing days in the primary analysis window. Daily post counts show natural variance but no evidence of systemic gaps or collection failures. Coverage is sufficient for time-series, trend, and growth analyses.

Comments
	•	Comment fetching was intentionally disabled partway through the project.
	•	As a result, comment coverage is incomplete after late 2025.
	•	Comments are retained only where previously collected.

Comments are not relied upon for primary analyses. Where needed, comments can be re-fetched deterministically using stored post identifiers.

Subreddit Stats
	•	Coverage window: 2025-04-24 to 2026-01-11
	•	Snapshot cadence: Near-daily
	•	Typical snapshots per subreddit: 121 to 126

Subreddit-level metrics (subscriber count, activity signals) provide consistent longitudinal coverage suitable for growth and comparative analysis.

One subreddit (WGU_BSSE) shows partial coverage due to late inclusion or early removal and is treated as an outlier.

User Stats
	•	User-level aggregates exist but are not required for core analyses.
	•	Coverage gaps do not affect analytical validity.

Reproducibility Statement
	•	All analytical results are supported by stored artifacts in the database.
	•	The system is artifact-reproducible.
	•	Some historical fetch scripts are not present; however, no conclusions depend on missing raw-fetch logic.
	•	Coverage gaps are confined to non-critical tables and are fully documented.

Conclusion
	•	Post data coverage is complete and robust for the defined analysis window.
	•	Subreddit growth trends are reliable and well-sampled.
	•	Comment data is intentionally partial and non-essential.
	•	Overall data integrity supports the paper’s findings without qualification.

⸻
