Project overview (concise, LLM-first, HITL-light)

Purpose
Surface common student pain points and attach practical advice, then publish per-course Survival Guides.

Data inputs
	1.	Reddit posts with course tags and timestamps.
	2.	Comment trees for posts.
	3.	Sentiment score per post.
Stored in a local DB; exported as JSONL snapshots under path/to/data/.

LLM pipeline (stages)
	1.	Filter and prep
a) Deduplicate, clean text, keep course_id, post_id, comment_id, permalink, timestamp.
b) Split into low-sentiment posts and the full unfiltered set.
	2.	Anchor-course HITL labeling (small, early)
a) Select 4–6 diverse courses.
b) Manually label 30–50 low-sentiment posts per anchor to calibrate prompts and choose the engine.
c) Lock a single prompt and primary engine for scale.
	3.	Pain-point extraction
a) Run the locked prompt on low-sentiment posts.
b) Run the same prompt on the unfiltered set; allow “unassigned” when none apply.
Output: path/to/data/processed/pain_points.jsonl
	4.	Advice from comments
a) Pull comments only for posts that contain at least one pain point.
b) Classify each comment as advice or not; if advice, produce a one-sentence action summary.
c) Comments inherit the parent post for pairing.
Output: path/to/data/processed/advice.jsonl (source=comment)
	5.	Advice from standalone posts
a) Classify all posts for actionable advice not tied to a complaint thread.
b) Keep high-confidence items only; produce a one-sentence action summary.
Output: path/to/data/processed/advice.jsonl (append with source=post_fallback)
	6.	Global clustering of pain points
a) Create embeddings for all pain-point items.
b) Cluster once at the global level to define root causes.
c) Assign each pain point to a global cluster.
Output: path/to/data/processed/clusters/global_clusters.json
	7.	Pairing advice to pain points and clusters
a) Comments: direct parent-child attach to the post’s pain points.
b) Standalone advice: within the same course, match to pain-point clusters via embedding similarity to cluster centroids (threshold + top-k).
c) Minimal HITL: quick pass on near-threshold or “unassigned” cases only.
Output: path/to/data/processed/pairs.jsonl

Deliverable

Per-course Survival Guides (Markdown and PDF) at path/to/output/guides/{COURSE}.md|pdf including:
	1.	Common problems: top pain-point clusters seen in that course, short descriptions, example quotes with permalinks.
	2.	Advice from replies: distilled actions linked to the originating complaint posts.
	3.	Advice from unconnected posts: additional actions matched to the course’s root causes, with links.
	4.	Provenance: post_id/comment_id and permalinks for every quoted item.
	5.	Notes: small-n caveats when course volume is low.

Notebooks and artifacts (minimal)

00_setup_env.ipynb
01_filter_and_export.ipynb → path/to/data/interim/filtered_posts.jsonl
02_painpoints_low_sent.ipynb → pain_points.jsonl (low-sent subset)
03_painpoints_all_posts.ipynb → pain_points.jsonl (full set)
04_fetch_comments.ipynb → path/to/data/interim/comments.jsonl
05_advice_from_comments.ipynb → advice.jsonl (source=comment)
06_advice_from_posts.ipynb → advice.jsonl (append source=post_fallback)
07_cluster_global.ipynb → global_clusters.json
08_pair_advice.ipynb → pairs.jsonl
09_build_survival_guides.ipynb → path/to/output/guides/

Notes
	1.	Everything after the small anchor-course HITL is unsupervised LLM with a final light review at the pairing step.
	2.	Keep IDs, timestamps, and permalinks throughout so every guide item traces back to source text.
	3.	Optional A/B prompts and engines happen only during the anchor-course calibration in Steps 2–3 and in Step 5 for advice classification.